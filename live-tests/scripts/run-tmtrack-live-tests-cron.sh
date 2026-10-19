#!/usr/bin/env bash
set -euo pipefail

LOCK_FILE="/tmp/tmtrack_live_tests.lock"
exec 200>"${LOCK_FILE}"
if ! flock -n 200; then
    echo "Another instance of tmtrack live tests is already running. Skipping."
    exit 0
fi

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${DIR}"

# Auto-update from main if git repository is clean and remote is accessible
if [ -d "${DIR}/../.git" ] && command -v git >/dev/null 2>&1; then
    (
        cd "${DIR}/.."
        if [ -z "$(git status --porcelain)" ]; then
            git fetch origin main >/dev/null 2>&1 || true
            CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
            if [ "${CURRENT_BRANCH}" = "main" ]; then
                git pull --ff-only origin main >/dev/null 2>&1 || true
            fi
        fi
    ) || true
fi

exec "${DIR}/run-live-tests.sh" --profile
