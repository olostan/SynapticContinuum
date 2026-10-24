#!/usr/bin/env bash
set -euo pipefail

# Portable EXP-0003 Benchmark Runner for Linux x86-64 and macOS ARM64
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Ensure common tool locations are on PATH
export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:${PATH}"

PROFILE="all"
OUT_DIR="${EXP_DIR}/runs"
SKIP_TESTS=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile)
            PROFILE="$2"
            shift 2
            ;;
        --out)
            OUT_DIR="$2"
            shift 2
            ;;
        --skip-tests)
            SKIP_TESTS=1
            shift
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 [--profile standard|extended|all] [--out <dir>] [--skip-tests]"
            exit 1
            ;;
    esac
done

echo "=== SynapticContinuum EXP-0003 Native Engine Scaling ==="
echo "Experiment Directory: ${EXP_DIR}"
echo "Selected Profile:     ${PROFILE}"
echo "Output Directory:     ${OUT_DIR}"

# 1. Build Native C++ Engines via CMake
BUILD_DIR="${EXP_DIR}/build"
mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"

if command -v cmake >/dev/null 2>&1; then
    CMAKE_BIN="cmake"
else
    echo "Error: cmake not found on PATH. Please install cmake or run ~/.local/bin/uv tool install cmake"
    exit 1
fi

echo "Configuring and compiling native engines with CMake..."
"${CMAKE_BIN}" "${EXP_DIR}"
"${CMAKE_BIN}" --build . -j"$(getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)"

# 2. Setup / verify Python Virtual Environment
VENV_DIR="${EXP_DIR}/.venv"
if [[ ! -d "${VENV_DIR}" ]]; then
    echo "Creating virtual environment at ${VENV_DIR}..."
    if command -v uv >/dev/null 2>&1; then
        uv venv "${VENV_DIR}"
        uv pip install -p "${VENV_DIR}" -r "${EXP_DIR}/requirements.txt"
    else
        python3 -m venv "${VENV_DIR}"
        "${VENV_DIR}/bin/pip" install -r "${EXP_DIR}/requirements.txt"
    fi
fi

PYTHON_BIN="${VENV_DIR}/bin/python"

# 3. Execute Campaign
cd "${EXP_DIR}"
export PYTHONPATH="${EXP_DIR}"

CMD=("${PYTHON_BIN}" "src/python/run_campaign.py" "--profile" "${PROFILE}" "--out" "${OUT_DIR}")
if [[ "${SKIP_TESTS}" -eq 1 ]]; then
    CMD+=("--skip-tests")
fi

echo "Executing benchmark runner..."
"${CMD[@]}"
