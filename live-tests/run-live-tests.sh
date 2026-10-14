#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${DIR}"

VENV_DIR="${DIR}/.venv"
PORT="${HEADLESS_CHROME_PORT:-9333}"

echo "=== TMTrack Live Production Test Runner ==="

# 1. Start headless chrome in Docker container if Docker is available
if command -v docker >/dev/null 2>&1; then
    echo "Starting headless browser container..."
    "${DIR}/docker/run-headless-browser.sh" || {
        echo "Warning: headless browser could not be started; browser tests will be skipped."
    }
else
    echo "Docker not found; skipping headless browser startup."
fi

# 2. Setup python virtual environment if missing or incomplete
if [ ! -f "${VENV_DIR}/bin/pytest" ]; then
    echo "Creating virtual environment in ${VENV_DIR}..."
    python3 -m venv "${VENV_DIR}"
    "${VENV_DIR}/bin/pip" install --upgrade pip
    "${VENV_DIR}/bin/pip" install -r requirements.txt
fi

echo "Running test suite..."
export HEADLESS_CHROME_CDP="http://127.0.0.1:${PORT}"
"${VENV_DIR}/bin/pytest" -v tests/ "$@"
