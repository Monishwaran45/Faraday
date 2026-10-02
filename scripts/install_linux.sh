#!/usr/bin/env bash
# ==============================================================================
# Faraday Linux Automated Installer & Environment Setup
# Supported: Ubuntu, Debian, Fedora, Arch Linux, WSL2, and Snapdragon Linux (aarch64)
# Author: Monishwaran K (Qualcomm Snapdragon Innovation Challenge 2026)
# ==============================================================================

set -e

# Terminal styling
BOLD="\033[1m"
GREEN="\033[1;32m"
CYAN="\033[1;36m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
RESET="\033[0m"

echo -e "${CYAN}${BOLD}"
echo "  ⚡ FARADAY LINUX INSTALLATION & SILICON SETUP"
echo "  100% Air-Gapped Code Assurance Copilot for Linux & Snapdragon NPU"
echo -e "${RESET}"

# 1. Detect Architecture & OS
ARCH=$(uname -m)
OS=$(uname -s)

if [ "$OS" != "Linux" ]; then
    echo -e "${RED}[!] Error: This script is intended for Linux. Detected OS: $OS${RESET}"
    exit 1
fi

echo -e "${GREEN}[✓] Detected OS:${RESET} Linux ($ARCH)"

if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    echo -e "${CYAN}[*] ARM64 Architecture detected.${RESET}"
    if [ -f "/sys/devices/soc0/machine" ]; then
        SOC_MACHINE=$(cat /sys/devices/soc0/machine 2>/dev/null || true)
        echo -e "${GREEN}[✓] Qualcomm Silicon Identified:${RESET} $SOC_MACHINE"
    fi
else
    echo -e "${YELLOW}[*] x86_64 Architecture detected (CPU fallback & development mode).${RESET}"
fi

# 2. Check Python 3.11+
PYTHON_BIN=""
for cmd in python3.12 python3.11 python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
        PY_VER=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        PY_MAJOR=$($cmd -c 'import sys; print(sys.version_info.major)')
        PY_MINOR=$($cmd -c 'import sys; print(sys.version_info.minor)')
        if [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 11 ]; then
            PYTHON_BIN="$cmd"
            echo -e "${GREEN}[✓] Found compatible Python:${RESET} $cmd (v$PY_VER)"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}[!] Error: Python 3.11+ is required. Please install python3.11 or python3.12.${RESET}"
    echo "    Ubuntu/Debian: sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip"
    echo "    Fedora:        sudo dnf install -y python3.11"
    echo "    Arch:          sudo pacman -S python"
    exit 1
fi

# 3. Check for Package Manager (uv or pip)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

if command -v uv >/dev/null 2>&1; then
    echo -e "${GREEN}[✓] Found fast Python package manager: uv${RESET}"
    echo -e "${CYAN}[*] Syncing virtual environment and installing Faraday...${RESET}"
    uv sync
    RUN_CMD="uv run"
else
    echo -e "${YELLOW}[*] uv not found. Falling back to python3 -m venv...${RESET}"
    if [ ! -d ".venv" ]; then
        echo -e "${CYAN}[*] Creating virtual environment at .venv...${RESET}"
        $PYTHON_BIN -m venv .venv
    fi
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -e .
    RUN_CMD=""
fi

# 4. Check Qualcomm QNN libraries on Linux
echo -e "${CYAN}[*] Checking Qualcomm Hexagon NPU libraries...${RESET}"
QNN_FOUND=0
for path in "/opt/qcom/qnn/lib/aarch64-linux-gnu" "/usr/lib/aarch64-linux-gnu" "/usr/local/lib"; do
    if [ -f "$path/libQnnHtp.so" ]; then
        echo -e "${GREEN}[✓] Found QNN HTP acceleration library:${RESET} $path/libQnnHtp.so"
        QNN_FOUND=1
        if [[ ":$LD_LIBRARY_PATH:" != *":$path:"* ]]; then
            echo -e "${YELLOW}[*] Recommendation: Add to LD_LIBRARY_PATH:${RESET}"
            echo "    export LD_LIBRARY_PATH=\"$path:\$LD_LIBRARY_PATH\""
        fi
        break
    fi
done

if [ "$QNN_FOUND" -eq 0 ]; then
    echo -e "${YELLOW}[*] QNN native libraries not detected in /opt/qcom/qnn. Faraday will run in high-speed CPU fallback mode.${RESET}"
fi

# 5. Git Pre-Commit Hook Setup (Optional)
if [ -d ".git" ]; then
    echo -e "${CYAN}[*] Git repository detected. Installing high-speed pre-commit hook...${RESET}"
    if [ -n "$RUN_CMD" ]; then
        $RUN_CMD faraday --install-hook || true
    else
        faraday --install-hook || true
    fi
fi

# 6. Verification Diagnostic
echo -e "\n${GREEN}${BOLD}[✓] Faraday successfully configured for Linux!${RESET}\n"
if [ -n "$RUN_CMD" ]; then
    $RUN_CMD faraday doctor
else
    faraday doctor
fi

echo -e "\n${CYAN}Quick Commands:${RESET}"
echo "  Scan current directory:  faraday scan ."
echo "  Launch Visual Web UI:    faraday --ui"
echo "  Run Accuracy Benchmark:  faraday benchmark --dataset owasp"
echo "  Verify Silicon Status:   faraday --prove"
echo "  Generate SBOM:           faraday sbom --sbom cyclonedx"
