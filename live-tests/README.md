# TMTrack Live Production Test Suite

A standalone, portable live test suite for the `tmtrack` backend REST API and `tmtrack-ui` frontend deployed in production on `diederich.ai`.

This test suite is designed to be copied **whole** to any modern environment (workstation, server, or `elwing`) along with `~/.tmtrack.creds` and executed independently against the live production cluster.

---

## Prerequisites

1. **Python 3.12+**
2. **Docker** (optional, required for the headless browser Playwright CDP tests)
3. **Credentials file**: `~/.tmtrack.creds` (mode 600, or pass `TMTRACK_CREDS_FILE=/path/to/creds`)

---

## Running the Tests

### Standard Execution
```bash
./run-live-tests.sh
```

### Profiled Execution with Prometheus & Alerta Delivery
```bash
./run-live-tests.sh --profile
# or set PROFILE_TELEMETRY=1
PROFILE_TELEMETRY=1 ./run-live-tests.sh
```

---

## Scheduled Execution on Elwing (Every 10 Minutes)

The test suite runs automatically every 10 minutes on `elwing`:
1. **Runner Script**: `scripts/run-tmtrack-live-tests-cron.sh` uses `flock` to guarantee non-overlapping runs.
2. **Systemd Service**: `systemd/tmtrack-live-tests.service` executes the runner under user `dana` with `docker` group permissions.
3. **Systemd Timer**: `systemd/tmtrack-live-tests.timer` fires every 10 minutes (staggered 5 minutes off `ainulindale-live-tests.timer`).
4. **Metric Collection**: Writes Prometheus metrics to `/var/lib/node_exporter/textfile_collector/tmtrack_live_tests.prom`.
5. **Telegraf Scrape**: Telegraf on `elwing` reads the textfile and exposes it to Prometheus on `thalos:9090`.
6. **Alerta Delivery**: Immediate direct REST notification on failure/recovery, plus Prometheus/Alertmanager webhook routing.
