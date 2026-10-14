# TMTrack Live Production Test Suite

A standalone, portable live test suite for the `tmtrack` backend REST API and `tmtrack-ui` frontend deployed on `realms.org`.

This test suite is designed to be copied **whole** to any modern environment (workstation, server, or container) along with `~/.tmtrack.creds` and executed independently against the live production server.

---

## Prerequisites

1. **Python 3.12+**
2. **Docker** (optional, required for the headless browser Playwright CDP tests)
3. **Credentials file**: `~/.tmtrack.creds` (or pass `TMTRACK_CREDS_FILE=/path/to/creds`)

---

## Directory Structure

```text
live-tests/
├── README.md                          # Documentation and instructions
├── requirements.txt                   # Test dependencies (pytest, httpx, playwright, python-dotenv)
├── run-live-tests.sh                  # Main entrypoint script (boots browser container, creates venv, runs pytest)
├── docker/
│   ├── Dockerfile.headless-shell      # Debian bookworm-slim Chromium headless container spec
│   └── run-headless-browser.sh        # Boots headless browser container on port 9333
└── tests/
    ├── conftest.py                    # Pytest fixtures and credential ingestion
    ├── test_api_auth.py               # Authentication and user/group authorization tests
    ├── test_api_categories.py         # Category schema, retrieval, and validation tests
    ├── test_api_tasks_crud.py         # Deep CRUD lifecycle (POST, GET, PUT, DELETE) and validation tests
    ├── test_web_and_assets.py         # Static web UI, CSS, JS assets, and Nginx ingress tests
    └── test_browser_e2e.py            # Playwright headless browser E2E interaction over CDP
```

---

## Running the Tests

Simply execute the runner:
```bash
./run-live-tests.sh
```

You can pass standard pytest arguments:
```bash
# Run only API contract tests:
./run-live-tests.sh tests/test_api_tasks_crud.py

# Run only headless browser tests:
./run-live-tests.sh tests/test_browser_e2e.py
```

---

## Credentials Format (`~/.tmtrack.creds`)

```bash
TMTRACK_BASE_URL="https://www.realms.org"
TMTRACK_API_URL="https://www.realms.org/api/v1"
TMTRACK_UI_URL="https://www.realms.org/tmtrack/"

# Test User Token (TemporaryHero from user_authentication.json)
TMTRACK_AUTH_TOKEN="c379025dd04a981bd81d"
TMTRACK_USERID="TemporaryHero"

# Secondary Test User Token (WanderingPixel)
TMTRACK_ALT_TOKEN="d4b69c69dd0059b59bcc"
TMTRACK_ALT_USERID="WanderingPixel"

# Headless Browser CDP Endpoint
HEADLESS_CHROME_CDP="http://127.0.0.1:9333"
```

---

## Disaster Recovery Backup Archive

A full comprehensive production disaster recovery backup was captured prior to test execution and is stored in:
- `twentysixdotfour:/home/dana/backups/tmtrack/`
- `thalos:/mnt/thalos-storage-a/dana-backups/tmtrack/` (Primary)
- `thalos:/mnt/thalos-storage-b/dana-backups/tmtrack/` (Secondary)
- `orostar:/home/dana/backups/tmtrack/`

---

## TODO / Future Improvements
- [ ] **Automated Backend Test Artifact Cleanup**: Implement a scheduled cleanup job on realms.org (e.g. systemd timer or cron) to periodically delete synthetic test tasks (`livetest-*`) from `tmtrack_db.daily_tasks`.
