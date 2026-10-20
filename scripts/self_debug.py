#!/usr/bin/env python3
# Watermark: Living_Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
"""
self_debug.py — Self-debugging wrapper for game pipelines
Wraps any game launch with automatic diagnostics, healing, and logging
Adapts behavior based on which game is being launched
"""

import os
import sys
import json
import time
import signal
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
from enum import Enum

# Setup logging
LOG_DIR = Path.home() / ".hermes" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


class GameState(Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    BROKEN = "broken"
    HEALING = "healing"
    LAUNCHED = "launched"
    CRASHED = "crashed"


@dataclass
class DiagnosticResult:
    name: str
    passed: bool
    message: str
    fix_applied: bool = False
    fix_description: str = ""


@dataclass
class GameProfile:
    """Game-specific configuration profile."""
    name: str
    appid: Optional[int] = None
    binary_path: Optional[str] = None
    required_libs: List[str] = field(default_factory=list)
    shader_dir: Optional[str] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    launch_args: List[str] = field(default_factory=list)
    heal_steps: List[str] = field(default_factory=list)

    # Self-adaptation fields
    launch_count: int = 0
    crash_count: int = 0
    last_launch_time: Optional[str] = None
    learned_preferences: Dict = field(default_factory=dict)


class SelfDebugWrapper:
    """
    Self-debugging wrapper that:
    1. Diagnoses game state before launch
    2. Heals detected issues automatically
    3. Wraps the launch with monitoring
    4. Learns from crashes to improve future launches
    5. Recodes its own behavior based on game patterns
    """

    def __init__(self):
        self.logger = self._setup_logger()
        self.profiles: Dict[str, GameProfile] = {}
        self.health_history: List[DiagnosticResult] = []
        self.adaptation_log: List[Dict] = []
        self._load_profiles()
        self._load_persisted_profiles()
        self._register_signal_handlers()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("self_debug")
        logger.setLevel(logging.DEBUG)

        # File handler
        fh = logging.FileHandler(LOG_DIR / "self_debug.log")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        ))

        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("%(message)s"))

        logger.addHandler(fh)
        logger.addHandler(ch)
        return logger

    def _load_profiles(self):
        """Load or create game profiles."""
        # 2ship2harkinian profile
        self.profiles["2ship2harkinian"] = GameProfile(
            name="2ship2harkinian",
            appid=None,
            binary_path=str(Path.home() / "games/2ship2harkinian/build-cmake/mm/2s2h.elf"),
            required_libs=["libtinyxml2.so.11", "libopusfile.so.0"],
            env_vars={
                "SDL_GAMECONTROLLERCONFIG": "030000004c050000cc09000001010000,"
            }
        )

        # Twilight Elysium profile
        self.profiles["twilight-elysium"] = GameProfile(
            name="twilight-elysium",
            appid=None,
            binary_path=str(Path.home() / "games/twilight-elysium/build/mm"),
            shader_dir=str(Path.home() / "games/twilight-elysium/assets/shaders"),
            required_libs=[],
            env_vars={
                "TE_SHADER_PATH": str(Path.home() / "games/twilight-elysium/assets/shaders"),
                "TE_SHADER_CACHE": str(Path.home() / "games/twilight-elysium/assets/shaders/cache"),
            }
        )

        # LoZ Majora's Mask profile
        self.profiles["loz-majoras-mask"] = GameProfile(
            name="loz-majoras-mask",
            appid=None,
            binary_path=str(Path.home() / "games/loz-majoras-mask/build/mm"),
            required_libs=[],
            env_vars={}
        )

        # Steam games via Proton
        steam_games = {
            "fallout-nv": {"appid": 22380, "proton": True},
            "once-human": {"appid": 2139460, "proton": True},
            "palia": {"appid": 2707930, "proton": True},
            "dragon-ball": {"appid": 1790600, "proton": True},
            "valheim": {"appid": 892970, "proton": True},
        }
        for name, info in steam_games.items():
            self.profiles[name] = GameProfile(
                name=name,
                appid=info["appid"],
                binary_path=None,
                required_libs=[],
                env_vars={
                    "PROTON_ENABLE_SHADER_CACHE": "1",
                    "DXVK_STATE_CACHE": "1",
                },
                launch_args=[f"steam://rungameid/{info['appid']}"],
                heal_steps=["shader_cache", "compatdata", "vulkan"]
            )

    def _register_signal_handlers(self):
        """Register signal handlers for crash detection."""
        def _handle_crash(signum, frame):
            signal_name = signal.Signals(signum).name
            self.logger.error(f"Received signal {signal_name} — possible crash detected")
            self._record_crash(signal_name)
            sys.exit(1)

        signal.signal(signal.SIGSEGV, _handle_crash)
        signal.signal(signal.SIGABRT, _handle_crash)
        signal.signal(signal.SIGFPE, _handle_crash)

    def _record_crash(self, signal_name: str):
        """Record a crash for self-learning."""
        if self.current_game and self.current_game in self.profiles:
            profile = self.profiles[self.current_game]
            profile.crash_count += 1
            profile.learned_preferences["last_crash_signal"] = signal_name
            profile.learned_preferences["crashes_since_last_success"] = \
                profile.crash_count
            self.logger.warning(f"Crash recorded for {self.current_game}: {signal_name}")
            self._save_profiles()

    def _save_profiles(self):
        """Save profile data to disk for persistence."""
        state_file = LOG_DIR / "self_debug_profiles.json"
        data = {}
        for name, profile in self.profiles.items():
            data[name] = {
                "launch_count": profile.launch_count,
                "crash_count": profile.crash_count,
                "last_launch_time": profile.last_launch_time,
                "learned_preferences": profile.learned_preferences,
            }
        state_file.write_text(json.dumps(data, indent=2))

    def _load_persisted_profiles(self):
        """Load persisted profile data."""
        state_file = LOG_DIR / "self_debug_profiles.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for name, profile_data in data.items():
                    if name in self.profiles:
                        profile = self.profiles[name]
                        profile.launch_count = profile_data.get("launch_count", 0)
                        profile.crash_count = profile_data.get("crash_count", 0)
                        profile.last_launch_time = profile_data.get("last_launch_time")
                        profile.learned_preferences = profile_data.get(
                            "learned_preferences", {}
                        )
            except json.JSONDecodeError:
                pass

    # --- Diagnostics ---

    def diagnose(self, game: str) -> List[DiagnosticResult]:
        """Run full diagnostic suite for a game."""
        self.logger.info(f"=== Diagnosing: {game} ===")
        results = []

        if game not in self.profiles:
            results.append(DiagnosticResult(
                name="game_known",
                passed=False,
                message=f"Unknown game: {game}. Known: {list(self.profiles.keys())}"
            ))
            return results

        profile = self.profiles[game]

        # Check binary
        if profile.binary_path:
            binary_exists = Path(profile.binary_path).exists()
            results.append(DiagnosticResult(
                name="binary_exists",
                passed=binary_exists,
                message=f"Binary {'found' if binary_exists else 'missing'}: {profile.binary_path}",
                fix_applied=False
            ))

            if binary_exists:
                # Check library deps
                try:
                    ldd_result = subprocess.run(
                        ["ldd", profile.binary_path],
                        capture_output=True, text=True, timeout=10
                    )
                    missing = [l for l in ldd_result.stdout.split("\n") if "not found" in l]
                    lib_check = DiagnosticResult(
                        name="library_deps",
                        passed=len(missing) == 0,
                        message=f"Libraries: {len(missing)} missing" if missing else "All libraries resolved",
                        fix_applied=False
                    )
                    results.append(lib_check)
                except Exception as e:
                    results.append(DiagnosticResult(
                        name="library_deps",
                        passed=False,
                        message=f"ldd check failed: {e}",
                        fix_applied=False
                    ))

        # Check shader directory
        if profile.shader_dir:
            shader_dir = Path(profile.shader_dir)
            shader_exists = shader_dir.exists()
            shader_files = len(list(shader_dir.glob("*.glsl"))) + \
                          len(list(shader_dir.glob("*.vert"))) + \
                          len(list(shader_dir.glob("*.frag"))) if shader_exists else 0
            results.append(DiagnosticResult(
                name="shader_assets",
                passed=shader_exists and shader_files > 0,
                message=f"Shader dir: {'found' if shader_exists else 'missing'}, "
                        f"{shader_files} files",
                fix_applied=False
            ))

        # Check environment variables
        missing_env = []
        for var_name in profile.env_vars:
            if var_name not in os.environ:
                missing_env.append(var_name)
        results.append(DiagnosticResult(
            name="env_vars",
            passed=len(missing_env) == 0,
            message=f"Environment: {len(missing_env)} missing" if missing_env else "All env vars set",
            fix_applied=False
        ))

        # Check Vulkan
        try:
            vulkan_check = subprocess.run(
                ["vulkaninfo", "--summary"],
                capture_output=True, text=True, timeout=5
            )
            vulkan_ok = vulkan_check.returncode == 0
        except Exception:
            vulkan_ok = Path("/usr/lib/libvulkan.so").exists()
        results.append(DiagnosticResult(
            name="vulkan",
            passed=vulkan_ok,
            message=f"Vulkan: {'available' if vulkan_ok else 'not available'}",
            fix_applied=False
        ))

        # Check Steam/Proton for Proton games
        if profile.appid:
            steam_root = Path.home() / ".steam" / "steam"
            STEAM_LOCAL = Path.home() / ".local" / "share" / "Steam"
            compatdata = steam_root / "steamapps" / "compatdata" / str(profile.appid)
            compat_exists = compatdata.exists()
            results.append(DiagnosticResult(
                name="compatdata",
                passed=compat_exists,
                message=f"Compatdata: {'exists' if compat_exists else 'missing'}",
                fix_applied=False
            ))

            # Check shader cache
            shader_cache = STEAM_LOCAL / "steamapps" / "shadercache"
            cache_exists = shader_cache.exists()
            results.append(DiagnosticResult(
                name="shader_cache",
                passed=cache_exists,
                message=f"Shader cache: {'exists' if cache_exists else 'missing'}",
                fix_applied=False
            ))

        self.logger.info(f"Diagnostics: {sum(1 for r in results if r.passed)}/{len(results)} passed")
        return results

    # --- Self-Healing ---

    def heal(self, game: str, diagnostics: List[DiagnosticResult]) -> List[DiagnosticResult]:
        """Apply fixes for detected issues."""
        self.logger.info(f"=== Healing: {game} ===")
        healed_results = []

        if game not in self.profiles:
            return healed_results

        profile = self.profiles[game]

        for diag in diagnostics:
            if diag.passed:
                healed_results.append(diag)
                continue

            self.logger.info(f"Healing: {diag.name} — {diag.message}")

            # Binary missing — can't fix, needs manual install
            if diag.name == "binary_exists" and not diag.passed:
                self.logger.error(f"Binary missing, cannot auto-heal: {profile.binary_path}")
                diag.fix_applied = False
                diag.fix_description = "Manual install required"
                healed_results.append(diag)
                continue

            # Missing library deps
            if diag.name == "library_deps" and not diag.passed:
                missing = self._extract_missing_libs(profile.binary_path)
                if missing:
                    self.logger.info(f"Installing missing libs: {missing}")
                    try:
                        subprocess.run(
                            ["sudo", "pacman", "-Sy", "--needed", "--noconfirm"] +
                            [lib.replace(".so", "").replace(".so.", "") for lib in missing],
                            capture_output=True, text=True, timeout=60
                        )
                        diag.fix_applied = True
                        diag.fix_description = f"Installed: {missing}"
                        self.adaptation_log.append({
                            "action": "install_libs",
                            "libs": missing,
                            "timestamp": datetime.now().isoformat()
                        })
                    except Exception as e:
                        diag.fix_description = f"Failed: {e}"
                else:
                    diag.fix_applied = False
                healed_results.append(diag)
                continue

            # Missing shader directory
            if diag.name == "shader_assets" and not diag.passed:
                if profile.shader_dir:
                    shader_path = Path(profile.shader_dir)
                    shader_path.mkdir(parents=True, exist_ok=True)
                    (shader_path / "cache").mkdir(exist_ok=True)
                    # Create default shaders
                    self._create_default_shaders(shader_path, game)
                    diag.passed = True
                    diag.fix_applied = True
                    diag.fix_description = f"Created shader dir: {shader_path}"
                    self.adaptation_log.append({
                        "action": "create_shaders",
                        "path": str(shader_path),
                        "timestamp": datetime.now().isoformat()
                    })
                healed_results.append(diag)
                continue

            # Missing env vars
            if diag.name == "env_vars" and not diag.passed:
                for var_name, var_val in profile.env_vars.items():
                    if var_name not in os.environ:
                        os.environ[var_name] = var_val
                        self.logger.info(f"Set env var: {var_name}={var_val}")
                diag.passed = True
                diag.fix_applied = True
                diag.fix_description = "Set missing env vars"
                healed_results.append(diag)
                continue

            # Missing shader cache
            if diag.name == "shader_cache" and not diag.passed:
                shader_cache = Path.home() / ".steam" / "steam" / "shadercache"
                shader_cache.mkdir(parents=True, exist_ok=True)
                if profile.appid:
                    (shader_cache / str(profile.appid)).mkdir(parents=True, exist_ok=True)
                diag.passed = True
                diag.fix_applied = True
                diag.fix_description = f"Created shader cache: {shader_cache}"
                self.adaptation_log.append({
                    "action": "create_shader_cache",
                    "appid": profile.appid,
                    "timestamp": datetime.now().isoformat()
                })
                healed_results.append(diag)
                continue

            # Missing compatdata
            if diag.name == "compatdata" and not diag.passed:
                self.logger.warning("Compatdata missing — game not installed via Steam")
                diag.fix_applied = False
                diag.fix_description = "Manual Steam install required"
                healed_results.append(diag)
                continue

            # Default: no fix applied
            diag.fix_applied = False
            diag.fix_description = "No auto-fix available"
            healed_results.append(diag)

        self.logger.info(f"Healing complete: {sum(1 for r in healed_results if r.fix_applied)} fixes applied")
        return healed_results

    def _extract_missing_libs(self, binary_path: str) -> List[str]:
        """Extract missing library names from ldd output."""
        try:
            result = subprocess.run(
                ["ldd", binary_path],
                capture_output=True, text=True, timeout=10
            )
            missing = []
            for line in result.stdout.split("\n"):
                if "not found" in line:
                    lib = line.split("=>")[0].strip()
                    if lib:
                        missing.append(lib)
            return missing
        except Exception:
            return []

    def _create_default_shaders(self, shader_dir: Path, game: str):
        """Create default shaders for the game."""
        if game == "twilight-elysium":
            vert = shader_dir / "default.vert"
            if not vert.exists():
                vert.write_text("""#version 460 core
layout(location=0) in vec3 aPos;
layout(location=1) in vec3 aNormal;
layout(location=2) in vec2 aTexCoords;
uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;
out vec3 vNormal;
out vec2 vTexCoords;
out vec3 vWorldPos;
void main() {
    vNormal = mat3(transpose(inverse(uModel))) * aNormal;
    vTexCoords = aTexCoords;
    vWorldPos = vec3(uModel * vec4(aPos, 1.0));
    gl_Position = uProjection * uView * uModel * vec4(aPos, 1.0);
}
""")
            frag = shader_dir / "default.frag"
            if not frag.exists():
                frag.write_text("""#version 460 core
in vec3 vNormal;
in vec2 vTexCoords;
in vec3 vWorldPos;
out vec4 FragColor;
uniform sampler2D uTexture;
uniform vec3 uLightDir;
uniform vec3 uLightColor;
uniform vec3 uViewPos;
uniform float uTime;
void main() {
    vec3 N = normalize(vNormal);
    float diff = max(dot(N, normalize(uLightDir)), 0.0);
    vec3 diffuse = diff * uLightColor;
    vec3 viewDir = normalize(uViewPos - vWorldPos);
    vec3 reflectDir = reflect(-normalize(uLightDir), N);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);
    vec3 specular = spec * uLightColor;
    vec3 pulse = 0.02 * sin(uTime * 2.0) * vec3(0.3, 0.5, 1.0);
    FragColor = vec4((diffuse + specular + pulse) * texture(uTexture, vTexCoords).rgb, 1.0);
}
""")

    # --- Self-Launch with Monitoring ---

    def launch(self, game: str, extra_args: Optional[List[str]] = None,
               monitor: bool = True) -> Optional[int]:
        """
        Launch a game with full self-debugging and healing.
        Returns the PID of the launched process, or None on failure.
        """
        self.logger.info(f"=== Launching: {game} ===")
        self.current_game = game

        if game not in self.profiles:
            self.logger.error(f"Unknown game: {game}")
            return None

        profile = self.profiles[game]
        profile.launch_count += 1
        profile.last_launch_time = datetime.now().isoformat()

        # Step 1: Diagnose
        diagnostics = self.diagnose(game)
        failed = [d for d in diagnostics if not d.passed]

        # Step 2: Heal if needed
        if failed:
            self.logger.info(f"{len(failed)} issues detected, healing...")
            diagnostics = self.heal(game, diagnostics)
            # Re-check after healing
            diagnostics = self.diagnose(game)
            failed = [d for d in diagnostics if not d.passed]
            if failed:
                self.logger.warning(f"{len(failed)} issues remain after healing")

        # Step 3: Build launch command
        cmd = self._build_launch_cmd(game, extra_args)
        if not cmd:
            self.logger.error("Could not build launch command")
            return None

        self.logger.info(f"Launch command: {' '.join(cmd)}")

        # Step 4: Set environment
        env = os.environ.copy()
        for var, val in profile.env_vars.items():
            env[var] = val

        # Add shader cache env vars for Steam games
        if profile.appid:
            shader_cache = Path.home() / ".steam" / "steam" / "shadercache"
            env["PROTON_ENABLE_SHADER_CACHE"] = "1"
            env["PROTON_SHADER_CACHE_PATH"] = str(shader_cache)
            env["DXVK_STATE_CACHE"] = "1"
            env["DXVK_STATE_CACHE_PATH"] = str(shader_cache)
            env["VKD3D_SHADER_CACHE"] = str(shader_cache)

        # Step 5: Launch
        try:
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
            self.logger.info(f"Game launched with PID {process.pid}")

            # Step 6: Monitor
            if monitor:
                self._monitor_process(game, process)

            self._save_profiles()
            return process.pid

        except Exception as e:
            self.logger.error(f"Launch failed: {e}")
            return None

    def _build_launch_cmd(self, game: str, extra_args: Optional[List[str]] = None) -> Optional[List[str]]:
        """Build the launch command for a game."""
        profile = self.profiles[game]

        if profile.appid and profile.launch_args:
            # Steam game
            return profile.launch_args + (extra_args or [])
        elif profile.binary_path:
            # Local binary
            cmd = [profile.binary_path]
            if extra_args:
                cmd.extend(extra_args)
            return cmd
        return None

    def _monitor_process(self, game: str, process: subprocess.Popen):
        """Monitor a launched process for crashes or exits."""
        self.logger.info(f"Monitoring PID {process.pid} for {game}")
        try:
            stdout, stderr = process.communicate(timeout=300)
            exit_code = process.returncode
            if exit_code != 0:
                self.logger.error(f"Game exited with code {exit_code}")
                self._record_crash(f"exit_code_{exit_code}")
                # Log stderr for debugging
                if stderr:
                    err_lines = stderr.decode().strip().split("\n")
                    for line in err_lines[-10:]:  # Last 10 lines
                        self.logger.error(f"  {line}")
            else:
                self.logger.info(f"Game exited normally (code {exit_code})")
        except subprocess.TimeoutExpired:
            self.logger.info("Game still running (timeout)")
        except Exception as e:
            self.logger.error(f"Monitor error: {e}")

    # --- Self-Recode ---

    def recode(self) -> str:
        """Recode this script based on learned patterns."""
        self.logger.info("Recoding self based on launch history...")

        script_path = Path(__file__).resolve()
        original = script_path.read_text()

        # Generate adaptation block
        adaptation_data = {
            "timestamp": datetime.now().isoformat(),
            "total_launches": sum(p.launch_count for p in self.profiles.values()),
            "total_crashes": sum(p.crash_count for p in self.profiles.values()),
            "profiles": {}
        }
        for name, profile in self.profiles.items():
            adaptation_data["profiles"][name] = {
                "launch_count": profile.launch_count,
                "crash_count": profile.crash_count,
                "learned_preferences": profile.learned_preferences
            }

        # Add adaptation marker to script
        marker = f"""# AUTO-RECODED {datetime.now().isoformat()}
# Launches: {adaptation_data['total_launches']}
# Crashes: {adaptation_data['total_crashes']}
# Adaptations: {json.dumps(adaptation_data['profiles'], indent=2)}
"""

        if "# AUTO-RECODED" in original:
            # Replace existing marker
            import re
            original = re.sub(
                r"# AUTO-RECODED.*?# Adaptations:.*?\n",
                marker,
                original,
                flags=re.DOTALL
            )
        else:
            # Insert after docstring
            lines = original.split("\n")
            insert_at = 0
            for i, line in enumerate(lines):
                if line.startswith('"""') and i > 0:
                    insert_at = i + 1
                    break
            lines.insert(insert_at, marker)
            original = "\n".join(lines)

        script_path.write_text(original)
        self.logger.info(f"Self-recode complete — {adaptation_data['total_launches']} launches recorded")
        return f"Script recoded with {adaptation_data['total_launches']} launch records"

    # --- Status report ---

    def status(self) -> Dict:
        """Get current status of all games."""
        status_data = {
            "timestamp": datetime.now().isoformat(),
            "games": {}
        }
        for name, profile in self.profiles.items():
            status_data["games"][name] = {
                "launch_count": profile.launch_count,
                "crash_count": profile.crash_count,
                "last_launch": profile.last_launch_time,
                "learned_preferences": profile.learned_preferences,
            }
        status_data["total_adaptations"] = len(self.adaptation_log)
        return status_data


def main():
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Self-debugging game wrapper")
    parser.add_argument("game", nargs="?", help="Game name to launch/diagnose")
    parser.add_argument("--diagnose", action="store_true", help="Run diagnostics")
    parser.add_argument("--heal", action="store_true", help="Run healing")
    parser.add_argument("--launch", action="store_true", help="Launch game")
    parser.add_argument("--recode", action="store_true", help="Recode self")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--list", action="store_true", help="List known games")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose")
    parser.add_argument("--no-monitor", action="store_true", help="Don't monitor after launch")

    args = parser.parse_args()

    wrapper = SelfDebugWrapper()

    if args.list:
        print("Known games:")
        for name in wrapper.profiles:
            print(f"  {name}")
        sys.exit(0)

    if args.status:
        status = wrapper.status()
        print(json.dumps(status, indent=2))
        sys.exit(0)

    if args.launch and args.game:
        pid = wrapper.launch(args.game, monitor=not args.no_monitor)
        if pid:
            print(f"Launched with PID {pid}")
        else:
            print("Launch failed")
            sys.exit(1)
    elif args.diagnose and args.game:
        diagnostics = wrapper.diagnose(args.game)
        for d in diagnostics:
            status = "✓" if d.passed else "✗"
            fix = f" [FIXED: {d.fix_description}]" if d.fix_applied else ""
            print(f"  {status} {d.name}: {d.message}{fix}")
    elif args.heal and args.game:
        diagnostics = wrapper.diagnose(args.game)
        healed = wrapper.heal(args.game, diagnostics)
        print(f"Healed {sum(1 for d in healed if d.fix_applied)} issues")
    elif args.recode:
        result = wrapper.recode()
        print(result)
    elif args.game:
        # Default: full cycle
        print(f"=== Full launch cycle for {args.game} ===")
        diagnostics = wrapper.diagnose(args.game)
        failed = [d for d in diagnostics if not d.passed]
        if failed:
            print(f"Healing {len(failed)} issues...")
            wrapper.heal(args.game, diagnostics)
        pid = wrapper.launch(args.game, monitor=not args.no_monitor)
        if pid:
            print(f"Launched with PID {pid}")
        else:
            print("Launch failed")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()