#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UI_DIR="${SCRIPT_DIR}/../tmtrack-ui"
if [[ ! -d "${UI_DIR}" ]]; then
    UI_DIR="/home/dana/tmtrack-ui"
fi

DEV_MONGO_PORT=27018
DEV_API_PORT=5050
DEV_UI_PORT=8080
DEV_CHROME_PORT=9223

CONTAINER_NAME="tmtrack-dev-mongo"
DEV_DB_NAME="tmtrack_dev_db"
PID_FILE="/tmp/tmtrack-dev-stack.pids"
LOG_DIR="/tmp/tmtrack-dev-logs"
BACKUP_FILE="${SCRIPT_DIR}/tmtrack_backup.json"
CHROME_PROFILE="/tmp/tmtrack-dev-chrome"

mkdir -p "${LOG_DIR}"

status() {
    echo "=== TMTrack Dev Stack Status ==="
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$"; then
        echo "  [✓] MongoDB: Running on port ${DEV_MONGO_PORT} (Container: ${CONTAINER_NAME})"
    else
        echo "  [✗] MongoDB: Stopped"
    fi

    if [[ -f "${PID_FILE}" ]]; then
        API_PID=$(grep "^API=" "${PID_FILE}" 2>/dev/null | cut -d= -f2 || true)
        UI_PID=$(grep "^UI=" "${PID_FILE}" 2>/dev/null | cut -d= -f2 || true)
        CHROME_PID=$(grep "^CHROME=" "${PID_FILE}" 2>/dev/null | cut -d= -f2 || true)

        if [[ -n "${API_PID}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
            echo "  [✓] Backend API: Running on http://127.0.0.1:${DEV_API_PORT} (PID ${API_PID})"
        else
            echo "  [✗] Backend API: Stopped"
        fi

        if [[ -n "${UI_PID}" ]] && kill -0 "${UI_PID}" 2>/dev/null; then
            echo "  [✓] Frontend UI: Running on http://127.0.0.1:${DEV_UI_PORT} (PID ${UI_PID})"
        else
            echo "  [✗] Frontend UI: Stopped"
        fi

        if [[ -n "${CHROME_PID}" ]] && kill -0 "${CHROME_PID}" 2>/dev/null; then
            echo "  [✓] Headless Chrome: Running on port ${DEV_CHROME_PORT} (PID ${CHROME_PID})"
        else
            echo "  [✗] Headless Chrome: Stopped"
        fi
    else
        echo "  [✗] No active PID file found"
    fi
}

down() {
    echo "=== Tearing Down TMTrack Dev Stack ==="
    if [[ -f "${PID_FILE}" ]]; then
        while IFS='=' read -r name pid; do
            if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
                echo "Stopping ${name} (PID ${pid})..."
                kill "${pid}" 2>/dev/null || true
            fi
        done < "${PID_FILE}"
        rm -f "${PID_FILE}"
    fi

    # Release any held ports
    for port in "${DEV_API_PORT}" "${DEV_UI_PORT}" "${DEV_CHROME_PORT}"; do
        fuser -k "${port}/tcp" 2>/dev/null || true
    done

    # Stop and remove container
    if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$"; then
        echo "Stopping Docker container ${CONTAINER_NAME}..."
        docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    fi

    rm -rf "${CHROME_PROFILE}"
    echo "=== TMTrack Dev Stack Stopped Cleanly ==="
}

seed() {
    if [[ ! -f "${BACKUP_FILE}" ]]; then
        echo "Notice: Backup file  not found. Attempting to fetch via backup.py..."
        "${SCRIPT_DIR}/venv/bin/python" "${SCRIPT_DIR}/backup.py" "${BACKUP_FILE}" 2>/dev/null || true
    fi
    if [[ -f "${BACKUP_FILE}" ]]; then
        echo "Seeding dev database  from ..."
        "${SCRIPT_DIR}/venv/bin/python" "${SCRIPT_DIR}/restore.py" --yes \
            "mongodb://localhost:${DEV_MONGO_PORT}/" \
            "${DEV_DB_NAME}" \
            "${BACKUP_FILE}"
    else
        echo "Warning: No backup file available to seed. Proceeding with clean database."
    fi
}

up() {
    START_TIME=$(date +%s%N)
    echo "=== Launching TMTrack Dev Stack ==="

    # Clean any stale instances first
    down >/dev/null 2>&1 || true

    # 1. Start MongoDB container
    echo "Starting isolated MongoDB container on port ${DEV_MONGO_PORT}..."
    docker run -d --rm \
        -p "${DEV_MONGO_PORT}:27017" \
        --name "${CONTAINER_NAME}" \
        mongo:7 >/dev/null

    # Wait for Mongo ping
    READY=false
    for i in $(seq 1 30); do
        if "${SCRIPT_DIR}/venv/bin/python" -c "from pymongo import MongoClient; client=MongoClient('mongodb://localhost:${DEV_MONGO_PORT}/', serverSelectionTimeoutMS=800); client.admin.command('ping'); client.close()" >/dev/null 2>&1; then
            READY=true
            break
        else
            sleep 0.3
        fi
    done

    if [[ "${READY}" != "true" ]]; then
        echo "Error: MongoDB failed to start on port ${DEV_MONGO_PORT}" >&2
        down
        exit 1
    fi

    # 2. Seed database
    seed

    # 3. Start Backend Flask API
    echo "Starting Backend Flask API on port ${DEV_API_PORT}..."
    (
        cd "${SCRIPT_DIR}"
        export MONGO_URI="mongodb://localhost:${DEV_MONGO_PORT}/"
        export MONGO_DB_NAME="${DEV_DB_NAME}"
        export FLASK_ENV="development"
        export FLASK_DEBUG="1"
        export TMTRACK_COOKIE_PATH="/"
        exec "${SCRIPT_DIR}/venv/bin/python" -m flask run --port "${DEV_API_PORT}"
    ) > "${LOG_DIR}/api.log" 2>&1 &
    API_PID=$!

    # 4. Start Frontend UI
    echo "Starting Frontend UI server on port ${DEV_UI_PORT}..."
    python3 -m http.server --directory "${UI_DIR}" --bind 127.0.0.1 "${DEV_UI_PORT}" > "${LOG_DIR}/ui.log" 2>&1 &
    UI_PID=$!

    # 5. Start Headless Chrome
    echo "Starting Headless Chrome on port ${DEV_CHROME_PORT}..."
    mkdir -p "${CHROME_PROFILE}"
    /usr/bin/google-chrome \
        --headless=new \
        --remote-debugging-port="${DEV_CHROME_PORT}" \
        --user-data-dir="${CHROME_PROFILE}" \
        --no-first-run \
        --no-default-browser-check \
        --disable-gpu \
        --window-size=1280,900 \
        > "${LOG_DIR}/chrome.log" 2>&1 &
    CHROME_PID=$!

    # Save PIDs
    cat << PIDEOF > "${PID_FILE}"
API=${API_PID}
UI=${UI_PID}
CHROME=${CHROME_PID}
PIDEOF

    # Wait for API, UI, and Chrome to be responsive
    for i in $(seq 1 30); do
        if curl -s "http://127.0.0.1:${DEV_API_PORT}/api/v1/happy" >/dev/null 2>&1 && \
           curl -s "http://127.0.0.1:${DEV_UI_PORT}/" >/dev/null 2>&1 && \
           curl -s "http://127.0.0.1:${DEV_CHROME_PORT}/json/version" >/dev/null 2>&1; then
            break
        else
            sleep 0.3
        fi
    done

    END_TIME=$(date +%s%N)
    DURATION=$(awk "BEGIN {print int(($END_TIME - $START_TIME)/1000000)/1000}")

    echo "=== TMTrack Dev Stack Ready in ${DURATION}s ==="
    echo "  UI:     http://localhost:${DEV_UI_PORT}/"
    echo "  API:    http://localhost:${DEV_API_PORT}/"
    echo "  Mongo:  mongodb://localhost:${DEV_MONGO_PORT}/${DEV_DB_NAME}"
    echo "  Chrome: http://localhost:${DEV_CHROME_PORT}/ (CDP)"
    echo "Run './dev-stack.sh down' when finished."
}

case "${1:-status}" in
    up)
        up
        ;;
    down)
        down
        ;;
    status)
        status
        ;;
    reset)
        seed
        ;;
    *)
        echo "Usage: $0 {up|down|status|reset}"
        exit 1
        ;;
esac
