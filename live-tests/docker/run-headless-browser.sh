#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${HEADLESS_CONTAINER_NAME:-live-test-headless-chrome}"
PORT="${HEADLESS_CHROME_PORT:-9333}"
IMAGE_NAME="live-test-headless-chrome:latest"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(docker ps -q -f name="^/${CONTAINER_NAME}$")" ]; then
    echo "Headless browser container already running on port ${PORT}."
    exit 0
fi

if [ "$(docker ps -aq -f name="^/${CONTAINER_NAME}$")" ]; then
    echo "Removing stopped container ${CONTAINER_NAME}..."
    docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
fi

# Build image if missing
if ! docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
    echo "Building ${IMAGE_NAME}..."
    docker build -t "${IMAGE_NAME}" -f "${DIR}/Dockerfile.headless-shell" "${DIR}"
fi

echo "Starting ${CONTAINER_NAME} on port ${PORT}..."
docker run -d \
  --name "${CONTAINER_NAME}" \
  --rm \
  -p "${PORT}:9333" \
  --shm-size=2gb \
  "${IMAGE_NAME}"

# Wait up to 15s for CDP endpoint to respond
for i in {1..30}; do
    if curl -s "http://127.0.0.1:${PORT}/json/version" >/dev/null 2>&1; then
        echo "Headless browser ready on port ${PORT}."
        exit 0
    fi
    sleep 0.5
done

echo "Warning: browser did not respond on port ${PORT} within 15 seconds" >&2
exit 1
