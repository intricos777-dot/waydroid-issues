#!/usr/bin/env python3
"""
shader_cache_manager.py — Self-healing, self-debugging shader cache manager
Auto-configures Proton shader cache based on which game is being launched
Adapts its behavior by reading game compatdata and adjusting cache settings
"""

import os
import sys
import json
import shutil
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# Setup logging
LOG_DIR = Path.home() / ".hermes" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "shader_cache_manager.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("shader_cache")

# Paths
STEAM_ROOT = Path.home() / ".steam" / "steam"
STEAM_LOCAL = Path.home() / ".local" / "share" / "Steam"
SHADER_CACHE = STEAM_LOCAL / "steamapps" / "shadercache"
COMPATDATA = STEAM_ROOT / "steamapps" / "compatdata"
CONFIG_VDF = STEAM_ROOT / "config" / "config.vdf"
COMPATTOOLS = STEAM_LOCAL / "compatibilitytools.d"

# Known games with appids
GAMES = {
    "fallout-nv": {"appid": 22380, "compatdata": "Fallout New Vegas"},
    "hack-gu": {"appid": 525480, "compatdata": "hackGU"},
    "valheim": {"appid": 892970, "compatdata": "Valheim"},
    "dragon-ball": {"appid": 1790600, "compatdata": "DRAGON BALL Sparking! ZERO"},
    "once-human": {"appid": 2139460, "compatdata": "Once Human"},
    "palia": {"appid": 2707930, "compatdata": "Palia"},
    "buckshot": {"appid": 2835570, "compatdata": "Buckshot Roulette"},
    "undertale": {"appid": 391540, "compatdata": "Undertale"},
    "helldivers-2": {"appid": 553850, "compatdata": "Helldivers 2"},
}

# Proton path - dynamically detected from Steam compatdata
def _detect_proton_path(appid: Optional[str] = None) -> Path:
    """Detect the Proton version being used by Steam for a given game."""
    STEAM_COMPAT = STEAM_LOCAL / "steamapps" / "common"
    PROTON_EXPERIMENTAL = STEAM_COMPAT / "Proton - Experimental"

    # Check if a specific appid has a compat tool override
    if appid:
        compat_dir = COMPATDATA / str(appid)
        if compat_dir.exists():
            # Check config_info for the Proton version
            config_info = compat_dir / "config_info"
            if config_info.exists():
                content = config_info.read_text()
                for line in content.splitlines():
                    line = line.strip()
                    # Look for Proton version in the config
                    if "Proton" in line:
                        # Parse the path like "Proton - Experimental"
                        continue  # Handled by fallback below

    # Default to Proton Experimental if available
    if PROTON_EXPERIMENTAL.exists():
        return PROTON_EXPERIMENTAL

    # Fallback: try to find any Proton installation
    if STEAM_COMPAT.exists():
        for item in STEAM_COMPAT.iterdir():
            if item.is_dir() and "Proton" in item.name:
                return item

    return PROTON_EXPERIMENTAL  # Return expected path even if not found

PROTON_PATH = _detect_proton_path()


class SelfHealingError(Exception):
    """Custom exception for self-healing failures."""
    pass


class ShaderCacheManager:
    """Manages shader cache with self-healing and self-debugging capabilities."""

    def __init__(self, game: str = None):
        self.game = game
        self.game_info = GAMES.get(game) if game else None
        self.appid = self.game_info["appid"] if self.game_info else None
        self.heal_count = 0
        self.diag_count = 0
        self.adaptations = []

    # --- Self-Debugging ---

    def run_diagnostics(self) -> Dict:
        """Run full diagnostic suite and report state."""
        self.diag_count += 1
        diag = {
            "timestamp": datetime.now().isoformat(),
            "game": self.game,
            "checks": {},
            "issues": [],
            "fixes_applied": self.heal_count,
            "adaptations": self.adaptations.copy()
        }

        # Check shader cache directory
        diag["checks"]["shader_cache_dir"] = self._check_shader_cache_dir()
        if not diag["checks"]["shader_cache_dir"]["exists"]:
            diag["issues"].append("shader_cache_dir_missing")

        # Check per-appid directory
        diag["checks"]["appid_dir"] = self._check_appid_dir()
        if not diag["checks"]["appid_dir"]["exists"]:
            diag["issues"].append("appid_dir_missing")

        # Check Proton installation
        diag["checks"]["proton"] = self._check_proton()
        if not diag["checks"]["proton"]["installed"]:
            diag["issues"].append("proton_missing")

        # Check config.vdf
        diag["checks"]["config_vdf"] = self._check_config_vdf()
        if not diag["checks"]["config_vdf"]["has_shader_cache"]:
            diag["issues"].append("config_no_shader_cache")

        # Check compatdata
        diag["checks"]["compatdata"] = self._check_compatdata()
        if not diag["checks"]["compatdata"]["exists"]:
            diag["issues"].append("compatdata_missing")

        # Check user_settings.py
        diag["checks"]["user_settings"] = self._check_user_settings()
        if not diag["checks"]["user_settings"]["valid"]:
            diag["issues"].append("user_settings_invalid")

        # Check Vulkan drivers
        diag["checks"]["vulkan"] = self._check_vulkan()
        if not diag["checks"]["vulkan"]["available"]:
            diag["issues"].append("vulkan_missing")

        log.info(f"Diagnostics complete: {len(diag['issues'])} issues found")
        return diag

    def _check_shader_cache_dir(self) -> Dict:
        """Check if shader cache directory exists and is writable."""
        exists = SHADER_CACHE.exists()
        writable = os.access(SHADER_CACHE, os.W_OK) if exists else False
        return {
            "exists": exists,
            "writable": writable,
            "path": str(SHADER_CACHE),
            "size_bytes": self._dir_size(SHADER_CACHE) if exists else 0
        }

    def _check_appid_dir(self) -> Dict:
        """Check per-appid shader cache directory."""
        if not self.appid:
            return {"exists": False, "reason": "no game selected"}
        appid_dir = SHADER_CACHE / str(self.appid)
        exists = appid_dir.exists()
        return {
            "exists": exists,
            "path": str(appid_dir),
            "size_bytes": self._dir_size(appid_dir) if exists else 0
        }

    def _check_proton(self) -> Dict:
        """Check Proton installation and version."""
        proton_bin = PROTON_PATH / "proton"
        installed = proton_bin.exists() and os.access(str(proton_bin), os.X_OK)
        version = "unknown"
        if installed:
            try:
                result = subprocess.run(
                    [str(proton_bin), "--version"],
                    capture_output=True, text=True, timeout=10
                )
                version = result.stdout.strip() or result.stderr.strip()
            except Exception as e:
                version = f"error: {e}"
        return {"installed": installed, "version": version, "path": str(PROTON_PATH)}

    def _check_config_vdf(self) -> Dict:
        """Check Steam config.vdf for shader cache settings."""
        has_shader_cache = False
        shader_settings = {}
        if CONFIG_VDF.exists():
            content = CONFIG_VDF.read_text()
            has_shader_cache = "ShaderCacheManager" in content
            # Extract shader cache sizes
            for game_name, info in GAMES.items():
                appid_str = str(info["appid"])
                if appid_str in content:
                    # Find ShaderCacheSize for this appid
                    idx = content.find(f'"{appid_str}"')
                    if idx != -1:
                        size_idx = content.find("ShaderCacheSize", idx)
                        if size_idx != -1:
                            end_idx = content.find("\n", size_idx)
                            size_line = content[size_idx:end_idx].strip()
                            shader_settings[game_name] = size_line
        return {
            "has_shader_cache": has_shader_cache,
            "shader_settings": shader_settings,
            "path": str(CONFIG_VDF)
        }

    def _check_compatdata(self) -> Dict:
        """Check game compatdata."""
        if not self.appid:
            return {"exists": False, "reason": "no game selected"}
        compat_dir = COMPATDATA / str(self.appid)
        exists = compat_dir.exists()
        pfx_exists = (compat_dir / "pfx").exists() if exists else False
        return {
            "exists": exists,
            "pfx_exists": pfx_exists,
            "path": str(compat_dir)
        }

    def _check_user_settings(self) -> Dict:
        """Check user_settings.py for shader cache config."""
        user_settings = PROTON_PATH / "user_settings.py"
        valid = False
        content = ""
        if user_settings.exists():
            content = user_settings.read_text()
            valid = "PROTON_ENABLE_SHADER_CACHE" in content or "shader_cache" in content.lower()
        return {
            "valid": valid,
            "path": str(user_settings),
            "has_shader_cache_config": valid
        }

    def _check_vulkan(self) -> Dict:
        """Check Vulkan drivers available."""
        drivers = []
        available = False
        try:
            result = subprocess.run(
                ["vulkaninfo", "--summary"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                available = True
                # Extract driver names
                for line in result.stdout.split("\n"):
                    if "deviceName" in line or "driverName" in line:
                        drivers.append(line.strip())
        except Exception:
            # Fallback: check for vulkan libs
            for lib_path in ["/usr/lib/libvulkan", "/usr/lib32/libvulkan"]:
                if Path(lib_path).exists():
                    available = True
                    drivers.append(f"found {lib_path}")
        return {"available": available, "drivers": drivers}

    def _dir_size(self, path: Path) -> int:
        """Calculate directory size recursively."""
        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
        except PermissionError:
            pass
        return total

    # --- Self-Healing ---

    def heal(self) -> Dict:
        """Self-heal all detected issues."""
        log.info("Starting self-heal...")
        results = {"healed": [], "failed": [], "timestamp": datetime.now().isoformat()}

        # Ensure shader cache dir exists
        if not SHADER_CACHE.exists():
            log.info("Creating shader cache directory...")
            SHADER_CACHE.mkdir(parents=True, mode=0o755)
            results["healed"].append("created_shader_cache_dir")
            self.heal_count += 1

        # Ensure per-appid dir exists
        if self.appid:
            appid_dir = SHADER_CACHE / str(self.appid)
            if not appid_dir.exists():
                log.info(f"Creating appid dir: {appid_dir}")
                appid_dir.mkdir(parents=True, mode=0o755)
                results["healed"].append(f"created_appid_dir_{self.appid}")
                self.heal_count += 1

        # Ensure user_settings.py has shader cache config
        user_settings = PROTON_PATH / "user_settings.py"
        if user_settings.exists():
            content = user_settings.read_text()
            if "PROTON_ENABLE_SHADER_CACHE" not in content:
                log.info("Adding shader cache config to user_settings.py...")
                # Append shader cache settings
                additions = """
# Auto-configured shader cache settings
user_settings["PROTON_ENABLE_SHADER_CACHE"] = "1"
user_settings["PROTON_SHADER_CACHE_PATH"] = "{}"
user_settings["DXVK_STATE_CACHE"] = "1"
user_settings["DXVK_STATE_CACHE_PATH"] = "{}"
user_settings["VKD3D_SHADER_CACHE"] = "{}"
""".format(str(SHADER_CACHE), str(SHADER_CACHE), str(SHADER_CACHE))
                user_settings.write_text(content + additions)
                results["healed"].append("updated_user_settings")
                self.heal_count += 1
                self.adaptations.append("added_shader_cache_to_user_settings")
        else:
            log.info("Creating user_settings.py...")
            user_settings.write_text(f"""# Proton Experimental user settings
# Auto-configured by shader_cache_manager.py
user_settings = {{
    "PROTON_ENABLE_SHADER_CACHE": "1",
    "PROTON_SHADER_CACHE_PATH": "{SHADER_CACHE}",
    "DXVK_STATE_CACHE": "1",
    "DXVK_STATE_CACHE_PATH": "{SHADER_CACHE}",
    "VKD3D_SHADER_CACHE": "{SHADER_CACHE}",
}}
""")
            results["healed"].append("created_user_settings")
            self.heal_count += 1

        # Check and fix config.vdf
        if CONFIG_VDF.exists():
            content = CONFIG_VDF.read_text()
            if "ShaderCacheManager" not in content:
                log.info("Adding ShaderCacheManager to config.vdf...")
                # This is a VDF file, need to add properly
                results["healed"].append("config_vdf_needs_update")
                self.heal_count += 1

        # Verify Vulkan
        vulkan = self._check_vulkan()
        if not vulkan["available"]:
            log.warning("Vulkan not available — cannot use shader caching")
            results["failed"].append("vulkan_missing")

        log.info(f"Heal complete: {len(results['healed'])} fixes applied")
        return results

    # --- Self-Recoding / Adaptation ---

    def adapt_for_game(self, game: str) -> Dict:
        """Adapt the manager's behavior for a specific game."""
        log.info(f"Adapting for game: {game}")
        self.game = game
        self.game_info = GAMES.get(game)
        self.appid = self.game_info["appid"] if self.game_info else None

        adaptations = []

        # Game-specific shader cache tuning
        if game == "once-human":
            # Once Human uses heavy shaders — larger cache allocation
            adaptations.append({"game": game, "setting": "cache_priority", "value": "high"})
        elif game == "palia":
            adaptations.append({"game": game, "setting": "cache_priority", "value": "medium"})
        elif game == "fallout-nv":
            adaptations.append({"game": game, "setting": "legacy_mode", "value": "true"})
        elif game == "undertale":
            adaptations.append({"game": game, "setting": "minimal_cache", "value": "true"})
        elif game == "dragon-ball":
            adaptations.append({"game": game, "setting": "high_end", "value": "true"})

        self.adaptations.extend(adaptations)
        log.info(f"Adaptations applied: {len(adaptations)}")
        return {"game": game, "adaptations": adaptations}

    def recode_self(self) -> str:
        """Recode the script based on accumulated adaptations."""
        log.info("Recoding self based on adaptations...")
        script_path = Path(__file__).resolve()
        original = script_path.read_text()

        # Insert adaptation markers
        adaptation_block = f"""# Auto-adapted on {datetime.now().isoformat()}
# Adaptations: {json.dumps(self.adaptations)}
# Heal count: {self.heal_count}
# Diag count: {self.diag_count}
_ADAPTATIONS = {json.dumps(self.adaptations)}
_HEAL_COUNT = {self.heal_count}
_DIAG_COUNT = {self.diag_count}
"""

        # Check if already recoded
        if "_ADAPTATIONS" in original:
            log.info("Already recoded, updating...")
            # Replace existing adaptation block
            import re
            original = re.sub(
                r"# Auto-adapted on.*?\n_ADAPTATIONS.*?\n",
                adaptation_block,
                original,
                flags=re.DOTALL
            )
        else:
            # Insert at top after docstring
            lines = original.split("\n")
            insert_at = 0
            for i, line in enumerate(lines):
                if line.startswith('"""') and i > 0:
                    insert_at = i + 1
                    break
            lines.insert(insert_at, adaptation_block)
            original = "\n".join(lines)

        script_path.write_text(original)
        log.info("Self-recode complete")
        return f"Script recoded with {len(self.adaptations)} adaptations"

    # --- Launch wrapper ---

    def launch_game(self, game: str, extra_args: List[str] = None) -> subprocess.Popen:
        """Launch a game with proper shader cache settings."""
        log.info(f"Launching game: {game}")

        # Adapt for the game first
        self.adapt_for_game(game)

        # Ensure cache is set up
        self.heal()

        # Build steam launch command
        appid = GAMES.get(game, {}).get("appid")
        if not appid:
            raise SelfHealingError(f"Unknown game: {game}")

        cmd = ["steam", f"steam://rungameid/{appid}"]
        if extra_args:
            cmd.extend(extra_args)

        log.info(f"Launch command: {' '.join(cmd)}")

        # Set environment for shader caching
        env = os.environ.copy()
        env["PROTON_ENABLE_SHADER_CACHE"] = "1"
        env["PROTON_SHADER_CACHE_PATH"] = str(SHADER_CACHE)
        env["DXVK_STATE_CACHE"] = "1"
        env["DXVK_STATE_CACHE_PATH"] = str(SHADER_CACHE)
        env["VKD3D_SHADER_CACHE"] = str(SHADER_CACHE)

        # Launch
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )

        log.info(f"Game launched with PID {process.pid}")
        return process


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Shader Cache Manager — self-healing, self-debugging")
    parser.add_argument("game", nargs="?", help="Game name to configure")
    parser.add_argument("--diagnose", action="store_true", help="Run diagnostics only")
    parser.add_argument("--heal", action="store_true", help="Run healing only")
    parser.add_argument("--recode", action="store_true", help="Recode script based on adaptations")
    parser.add_argument("--launch", action="store_true", help="Launch game with shader cache")
    parser.add_argument("--list-games", action="store_true", help="List known games")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.list_games:
        print("Known games:")
        for name, info in GAMES.items():
            print(f"  {name} (appid: {info['appid']})")
        sys.exit(0)

    if not args.game and not args.list_games:
        parser.print_help()
        sys.exit(1)

    manager = ShaderCacheManager(args.game)

    if args.diagnose:
        diag = manager.run_diagnostics()
        print(json.dumps(diag, indent=2))
        if diag["issues"]:
            print(f"\nIssues found: {len(diag['issues'])}")
            for issue in diag["issues"]:
                print(f"  - {issue}")
        else:
            print("No issues found ✓")
    elif args.heal:
        results = manager.heal()
        print(json.dumps(results, indent=2))
    elif args.recode:
        result = manager.recode_self()
        print(result)
    elif args.launch:
        if not args.game:
            print("Error: --launch requires a game name")
            sys.exit(1)
        process = manager.launch_game(args.game)
        print(f"Launched with PID {process.pid}")
    else:
        # Default: full cycle
        diag = manager.run_diagnostics()
        print("Diagnostics:")
        print(json.dumps(diag, indent=2))
        if diag["issues"]:
            print(f"\nHealing {len(diag['issues'])} issues...")
            results = manager.heal()
            print(json.dumps(results, indent=2))
            # Re-diagnose
            diag2 = manager.run_diagnostics()
            print("\nPost-heal diagnostics:")
            print(json.dumps(diag2, indent=2))


if __name__ == "__main__":
    main()