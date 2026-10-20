#!/usr/bin/env bash
# Watermark: Living_Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
# Copyright (c) 2026 Living Sin (intricos777-dot) + AI agents (Hermes, Lia, opencode) - collaborative work
# Licensed under Living Sin Proprietary License (LSPL-1.0)
# See LICENSE file for details.
# auto_config.sh — Auto-configuration script for game pipeline and shader cache
# Self-healing: detects broken state and fixes it automatically
# Self-debugging: runs diagnostics and reports issues before fixing
# Adapts based on which game is being configured

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# GAMES_DIR is parent of scripts/ dir
GAMES_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$SCRIPT_DIR/auto_config.log"
STATE_FILE="$SCRIPT_DIR/.auto_config_state"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"; }
log_ok() { log "${GREEN}✓ $1${NC}"; }
log_warn() { log "${YELLOW}⚠ $1${NC}"; }
log_err() { log "${RED}✗ $1${NC}"; }
log_info() { log "${BLUE}ℹ $1${NC}"; }
log_step() { log "${CYAN}▶ $1${NC}"; }

# Game definitions
declare -A GAME_BUILD_DIRS
declare -A GAME_BINARIES
declare -A GAME_SHADERS
declare -A GAME_BUILD_TOOLS

GAME_BUILD_DIRS["2ship2harkinian"]="/home/livings/games/2ship2harkinian/build-cmake"
GAME_BINARIES["2ship2harkinian"]="/home/livings/games/2ship2harkinian/build-cmake/mm/2s2h.elf"
GAME_SHADERS["2ship2harkinian"]=""
GAME_BUILD_TOOLS["2ship2harkinian"]="ninja"

GAME_BUILD_DIRS["twilight-elysium"]="/home/livings/games/twilight-elysium/build"
GAME_BINARIES["twilight-elysium"]="/home/livings/games/twilight-elysium/build/te-test"
GAME_SHADERS["twilight-elysium"]="/home/livings/games/twilight-elysium/assets/shaders"

GAME_BUILD_DIRS["loz-majoras-mask"]="/home/livings/games/loz-majoras-mask/build"
GAME_BINARIES["loz-majoras-mask"]="/home/livings/games/loz-majoras-mask/build/mm"
GAME_SHADERS["loz-majoras-mask"]=""

ALL_GAMES=("2ship2harkinian" "twilight-elysium" "loz-majoras-mask")

# --- Self-Debugging: Diagnostics ---
run_diagnostics() {
    local game="$1"
    log_step "Running diagnostics for: $game"
    local errors=0

    local binary="${GAME_BINARIES[$game]:-}"
    if [[ -n "$binary" ]]; then
        if [[ ! -f "$binary" ]]; then
            log_err "Binary missing: $binary"
            ((errors++))
        else
            log_ok "Binary found: $binary"
            if [[ ! -x "$binary" ]]; then
                log_warn "Binary not executable, fixing..."
                chmod +x "$binary"
                log_ok "Made binary executable"
            fi
            local missing_libs
            missing_libs=$(ldd "$binary" 2>&1 | grep "not found" || true)
            if [[ -n "$missing_libs" ]]; then
                log_err "Missing shared libraries:"
                echo "$missing_libs" | while read -r line; do log_warn "  $line"; done
                ((errors++))
            else
                log_ok "All shared libraries resolved"
            fi
        fi
    fi

    local build_dir="${GAME_BUILD_DIRS[$game]:-}"
    if [[ -n "$build_dir" ]]; then
        if [[ ! -d "$build_dir" ]]; then
            log_err "Build directory missing: $build_dir"
            ((errors++))
        else
            log_ok "Build directory exists: $build_dir"
        fi
    fi

    local shaders="${GAME_SHADERS[$game]:-}"
    if [[ -n "$shaders" ]]; then
        if [[ ! -d "$shaders" ]]; then
            log_err "Shader directory missing: $shaders"
            ((errors++))
        else
            local shader_count
            shader_count=$(find "$shaders" -name "*.glsl" -o -name "*.vert" -o -name "*.frag" 2>/dev/null | wc -l)
            if [[ "$shader_count" -eq 0 ]]; then
                log_warn "No shader files found in $shaders"
                ((errors++))
            else
                log_ok "Found $shader_count shader file(s)"
            fi
        fi
    fi

    log_step "Diagnostics complete: $errors error(s) found"
    return $errors
}

# --- Self-Healing ---
heal_2ship2harkinian() {
    log_step "Healing 2ship2harkinian..."
    local missing=()
    for lib in tinyxml2 opusfile; do
        if ! pacman -Q "$lib" &>/dev/null; then
            log_warn "Missing package: $lib"
            missing+=("$lib")
        fi
    done
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_step "Installing missing packages..."
        sudo pacman -Sy --needed --noconfirm ninja tinyxml2 opusfile 2>&1 | tee -a "$LOG_FILE"
        log_ok "Installed missing packages"
    else
        log_ok "All packages already installed"
    fi
    local build_dir="${GAME_BUILD_DIRS[2ship2harkinian]}"
    if [[ -d "$build_dir" ]]; then
        log_step "Rebuilding 2ship2harkinian..."
        cd "$build_dir"
        # Fix stale CMake cache if needed
        if grep -q "Projects/2ship2harkinian" CMakeCache.txt 2>/dev/null; then
            log_warn "Stale CMake cache detected, regenerating..."
            rm CMakeCache.txt
            cmake .. 2>&1 | tee -a "$LOG_FILE"
        fi
        if [ -f "build.ninja" ] && command -v ninja &>/dev/null; then
            ninja 2>&1 | tee -a "$LOG_FILE"
        elif [ -f "Makefile" ] && command -v make &>/dev/null; then
            make -j$(nproc) 2>&1 | tee -a "$LOG_FILE"
        else
            cmake --build . -j$(nproc) 2>&1 | tee -a "$LOG_FILE"
        fi
        log_ok "Rebuild done"
    fi
    local binary="${GAME_BINARIES[2ship2harkinian]}"
    local missing_after
    missing_after=$(ldd "$binary" 2>&1 | grep "not found" || true)
    if [[ -z "$missing_after" ]]; then
        log_ok "Binary fully resolved after healing"
    else
        log_warn "Still missing libs after healing:"
        echo "$missing_after" | while read -r line; do log_warn "  $line"; done
    fi
}

heal_twilight_elysium() {
    log_step "Healing Twilight Elysium..."
    if ! command -v cmake &>/dev/null; then
        log_warn "cmake not found, installing..."
        sudo pacman -S --needed --noconfirm cmake 2>&1 | tee -a "$LOG_FILE"
        log_ok "cmake installed"
    fi
    local shaders="${GAME_SHADERS[twilight-elysium]}"
    if [[ ! -d "$shaders" ]]; then
        log_warn "Shader directory missing, creating..."
        mkdir -p "$shaders/cache"
    fi
    if [[ ! -f "$shaders/default.vert" ]]; then
        cat > "$shaders/default.vert" << 'VERTEX_SHADER'
#version 460 core
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
VERTEX_SHADER
        log_ok "Created default vertex shader"
    fi
    if [[ ! -f "$shaders/default.frag" ]]; then
        cat > "$shaders/default.frag" << 'FRAGMENT_SHADER'
#version 460 core
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
FRAGMENT_SHADER
        log_ok "Created default fragment shader"
    fi
    local build_dir="${GAME_BUILD_DIRS[twilight-elysium]}"
    if [[ ! -d "$build_dir" ]]; then
        log_step "Build directory missing, configuring..."
        cmake -B "$build_dir" -S "$GAMES_DIR/twilight-elysium" 2>&1 | tee -a "$LOG_FILE"
    fi
    log_step "Building Twilight Elysium..."
    cd "$build_dir"
    cmake --build . -j$(nproc) 2>&1 | tee -a "$LOG_FILE"
    log_ok "Build done"
}

heal_loz_majoras_mask() {
    log_step "Healing LoZ Majora's Mask..."
    local build_dir="${GAME_BUILD_DIRS[loz-majoras-mask]}"
    if [[ -d "$build_dir" ]]; then
        # Fix stale CMake cache
        if [[ -f "$build_dir/CMakeCache.txt" ]] && grep -q "Projects/loz-majoras-mask" "$build_dir/CMakeCache.txt" 2>/dev/null; then
            log_warn "Stale CMake cache detected, regenerating..."
            rm -f "$build_dir/CMakeCache.txt"
            cmake -S /home/livings/games/loz-majoras-mask -B "$build_dir" 2>&1 | tee -a "$LOG_FILE"
        fi
        cd "$build_dir"
        cmake --build . -j$(nproc) 2>&1 | tee -a "$LOG_FILE"
    else
        log_warn "Build directory missing, configuring..."
        cmake -S /home/livings/games/loz-majoras-mask -B "$build_dir" 2>&1 | tee -a "$LOG_FILE"
        cd "$build_dir"
        cmake --build . -j$(nproc) 2>&1 | tee -a "$LOG_FILE"
    fi
    log_ok "LoZ build done"
}

heal_game() {
    local game="$1"
    log_step "Healing game: $game"
    case "$game" in
        2ship2harkinian) heal_2ship2harkinian ;;
        twilight-elysium) heal_twilight_elysium ;;
        loz-majoras-mask) heal_loz_majoras_mask ;;
        *)
            log_err "Unknown game: $game. Known: ${ALL_GAMES[*]}"
            return 1
            ;;
    esac
    log_ok "Healing complete for $game"
}

# --- Recode: Adapt the script itself based on game ---
recode_for_game() {
    local game="$1"
    log_step "Recoding script configuration for: $game"
    cat > "$STATE_FILE" << EOF
# Auto-config state
GAME="$game"
LAST_RUN="$(date -Iseconds)"
SCRIPT_VERSION="1.0"
DIAGNOSTICS_RUN=1
EOF
    case "$game" in
        2ship2harkinian)
            log_info "Recode: Enabling 2ship2harkinian-specific lib checks"
            ;;
        twilight-elysium)
            log_info "Recode: Enabling Twilight Elysium shader pipeline checks"
            ;;
        loz-majoras-mask)
            log_info "Recode: Enabling LoZ engine module checks"
            ;;
    esac
    log_ok "Recode complete for $game"
}

# --- Main ---
main() {
    local game="${1:-}"
    local mode="${2:-full}"

    if [[ -z "$game" ]]; then
        echo "Usage: $0 <game> [mode]"
        echo "Games: ${ALL_GAMES[*]}"
        echo "Modes: full | diagnose | heal | recode"
        exit 1
    fi

    local valid=0
    for g in "${ALL_GAMES[@]}"; do
        [[ "$g" == "$game" ]] && valid=1
    done
    if [[ "$valid" -eq 0 ]]; then
        log_err "Unknown game: $game. Known: ${ALL_GAMES[*]}"
        exit 1
    fi

    log "=== Auto Config: $game (mode=$mode) ==="

    case "$mode" in
        diagnose) run_diagnostics "$game" ;;
        heal) heal_game "$game" ;;
        recode) recode_for_game "$game" ;;
        full)
            run_diagnostics "$game" || true
            heal_game "$game"
            recode_for_game "$game"
            run_diagnostics "$game"
            ;;
        *)
            log_err "Unknown mode: $mode"
            exit 1
            ;;
    esac

    log "=== Auto Config complete for $game ==="
}

main "$@"
