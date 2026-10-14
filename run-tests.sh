#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

VENV_DIR="${SCRIPT_DIR}/venv"

if [[ -f "${VENV_DIR}/bin/pytest" ]]; then
    PYTHON="${VENV_DIR}/bin/python"
    PYTEST="${VENV_DIR}/bin/pytest"
else
    PYTHON="python3"
    PYTEST="pytest"
fi

echo "=== TMTrack Local Test Runner ==="
echo "Using Python: $(${PYTHON} --version 2>&1)"
echo "Using Pytest: $(${PYTEST} --version 2>&1)"

"${PYTEST}" tests/ -v --cov=app --cov=backup --cov=restore --cov=update_token --cov-report=term-missing "$@"
