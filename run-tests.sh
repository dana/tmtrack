#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

VENV_DIR="${SCRIPT_DIR}/venv"

# Auto-bootstrap virtual environment if missing or incomplete
if [[ ! -f "${VENV_DIR}/bin/pytest" ]]; then
    echo "=== Bootstrapping Python Virtual Environment ==="
    python3 -m venv "${VENV_DIR}"
    "${VENV_DIR}/bin/pip" install --upgrade pip --quiet
    "${VENV_DIR}/bin/pip" install -r "${SCRIPT_DIR}/requirements-test.txt" --quiet
fi

PYTHON="${VENV_DIR}/bin/python"
PYTEST="${VENV_DIR}/bin/pytest"

echo "=== TMTrack Local Test Runner ==="
echo "Using Python: $(${PYTHON} --version 2>&1)"
echo "Using Pytest: $(${PYTEST} --version 2>&1)"

"${PYTEST}" tests/ -v --cov=app --cov=backup --cov=restore --cov=update_token --cov-report=term-missing "$@"
