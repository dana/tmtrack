#!/usr/bin/env python3
"""
TMTrack Live Tests Telemetry Profiler & Metric Exporter
Executes live test files, measures execution duration, outcome, max RSS memory,
and CPU utilization, writes atomic Prometheus textfile metrics, and delivers alerts to Alerta.
"""

import os
import sys
import time
import json
import glob
import subprocess
import psutil
import httpx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TESTS_DIR = os.path.join(BASE_DIR, "tests")
VENV_PYTEST = os.path.join(BASE_DIR, ".venv", "bin", "pytest")
DEFAULT_METRICS_PATH = "/var/lib/node_exporter/textfile_collector/tmtrack_live_tests.prom"
FALLBACK_METRICS_PATH = os.path.join(BASE_DIR, "tmtrack_live_tests.prom")

OUTPUT_METRICS_FILE = os.environ.get("LIVE_TESTS_METRICS_PATH", DEFAULT_METRICS_PATH)
ALERTA_ENDPOINT = os.environ.get("ALERTA_ENDPOINT", "http://192.168.1.247:8080/api")


def ensure_headless_browser():
    """Ensure headless browser container is started on port 9333 if docker is available."""
    docker_script = os.path.join(BASE_DIR, "docker", "run-headless-browser.sh")
    if os.path.exists(docker_script):
        try:
            subprocess.run([docker_script], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Warning: could not execute run-headless-browser.sh: {e}", file=sys.stderr)


def send_alerta_notification(all_passed, total_passed, total_failed, failed_test_names):
    """Dispatches alert resolution or failure alert directly to Alerta REST API."""
    if not ALERTA_ENDPOINT:
        return

    alert_url = f"{ALERTA_ENDPOINT.rstrip('/')}/alert"
    grafana_url = "http://192.168.1.247:3000/d/tmtrack-live-tests?viewPanel=1"

    if all_passed:
        payload = {
            "resource": "elwing:tmtrack:live-tests",
            "event": "TMTrackLiveTestSuiteFailed",
            "environment": "Production",
            "severity": "normal",
            "service": ["TMTrackLiveTests"],
            "group": "Application",
            "value": "Passed",
            "text": f"All {total_passed} TMTrack live production tests passed successfully.",
            "attributes": {
                "grafana": grafana_url
            }
        }
    else:
        failure_summary = ", ".join(failed_test_names[:5])
        if len(failed_test_names) > 5:
            failure_summary += f" (+{len(failed_test_names) - 5} more)"
        payload = {
            "resource": "elwing:tmtrack:live-tests",
            "event": "TMTrackLiveTestSuiteFailed",
            "environment": "Production",
            "severity": "critical",
            "service": ["TMTrackLiveTests"],
            "group": "Application",
            "value": f"{total_failed} failed",
            "text": f"TMTrack live production test suite failed with {total_failed} test failure(s): {failure_summary}",
            "attributes": {
                "grafana": grafana_url,
                "failedTests": failed_test_names
            }
        }

    try:
        resp = httpx.post(alert_url, json=payload, timeout=5.0)
        if resp.status_code not in (200, 201):
            print(f"Warning: Alerta responded with {resp.status_code}: {resp.text}", file=sys.stderr)
    except Exception as e:
        print(f"Notice: Could not send alert to Alerta at {alert_url}: {e}", file=sys.stderr)


def main():
    ensure_headless_browser()
    os.environ["HEADLESS_CHROME_CDP"] = os.environ.get("HEADLESS_CHROME_CDP", "http://127.0.0.1:9333")

    raw_args = sys.argv[1:]
    specified_files = [a for a in raw_args if a.endswith(".py") and os.path.exists(a)]
    extra_flags = [a for a in raw_args if a not in specified_files]

    if specified_files:
        test_files = sorted(specified_files)
    else:
        test_files = sorted(glob.glob(os.path.join(TESTS_DIR, "test_*.py")))

    if not test_files:
        print(f"No test files found in {TESTS_DIR}", file=sys.stderr)
        sys.exit(1)

    overall_start = time.time()
    all_tests_passed = True
    total_passed = 0
    total_failed = 0
    total_skipped = 0

    file_results = []
    test_case_results = []
    failed_test_names = []

    for tf in test_files:
        fname = os.path.basename(tf)
        report_file = f"/tmp/tmtrack_live_report_{fname}.json"
        if os.path.exists(report_file):
            try:
                os.remove(report_file)
            except OSError:
                pass

        cmd = [
            VENV_PYTEST,
            "-v",
            "--json-report",
            f"--json-report-file={report_file}"
        ] + extra_flags + [tf]

        start_time = time.time()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            ps_proc = psutil.Process(proc.pid)
        except Exception:
            ps_proc = None

        max_rss = 0
        cpu_samples = []

        while proc.poll() is None:
            if ps_proc:
                try:
                    rss = ps_proc.memory_info().rss
                    for child in ps_proc.children(recursive=True):
                        rss += child.memory_info().rss
                    if rss > max_rss:
                        max_rss = rss
                    cpu = ps_proc.cpu_percent(interval=None)
                    cpu_samples.append(cpu)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            time.sleep(0.04)

        stdout, stderr = proc.communicate()
        duration = time.time() - start_time
        avg_cpu = (sum(cpu_samples) / len(cpu_samples)) if cpu_samples else 0.0

        f_passed = 0
        f_failed = 0
        f_skipped = 0

        if os.path.exists(report_file):
            try:
                with open(report_file) as rf:
                    data = json.load(rf)
                for t in data.get("tests", []):
                    case_name = t["nodeid"].split("::")[-1].replace('"', '\\"')
                    dur = t.get("call", {}).get("duration", t.get("setup", {}).get("duration", 0.0))
                    outcome = t.get("outcome", "unknown")
                    if outcome == "passed":
                        f_passed += 1
                        total_passed += 1
                        status_val = 1
                    elif outcome == "skipped":
                        f_skipped += 1
                        total_skipped += 1
                        status_val = 2
                    else:
                        f_failed += 1
                        total_failed += 1
                        all_tests_passed = False
                        status_val = 0
                        failed_test_names.append(f"{fname}::{case_name}")

                    test_case_results.append({
                        "file": fname,
                        "test": case_name,
                        "status": status_val,
                        "duration": dur,
                        "outcome": outcome
                    })
            except Exception as e:
                print(f"Error parsing report {report_file}: {e}", file=sys.stderr)
                all_tests_passed = False
                f_failed += 1
                failed_test_names.append(f"{fname}::parse_error")
        else:
            if proc.returncode != 0:
                all_tests_passed = False
                f_failed += 1
                failed_test_names.append(f"{fname}::execution_failure")

        file_status = 1 if f_failed == 0 and proc.returncode == 0 else 0
        file_results.append({
            "file": fname,
            "status": file_status,
            "duration": duration,
            "max_rss_bytes": max_rss,
            "avg_cpu_percent": avg_cpu,
            "passed": f_passed,
            "failed": f_failed,
            "skipped": f_skipped
        })

    overall_duration = time.time() - overall_start

    # Format Prometheus Textfile Metrics
    lines = []
    lines.append("# HELP tmtrack_live_test_suite_status Overall status of TMTrack live test suite (1=passed, 0=failed)")
    lines.append("# TYPE tmtrack_live_test_suite_status gauge")
    lines.append(f'tmtrack_live_test_suite_status{{suite="tmtrack-live"}} {1 if all_tests_passed else 0}')

    lines.append("# HELP tmtrack_live_test_suite_duration_seconds Total execution time of entire test run")
    lines.append("# TYPE tmtrack_live_test_suite_duration_seconds gauge")
    lines.append(f'tmtrack_live_test_suite_duration_seconds{{suite="tmtrack-live"}} {overall_duration:.4f}')

    lines.append("# HELP tmtrack_live_test_suite_passed_count Count of passed tests in suite")
    lines.append("# TYPE tmtrack_live_test_suite_passed_count gauge")
    lines.append(f'tmtrack_live_test_suite_passed_count{{suite="tmtrack-live"}} {total_passed}')

    lines.append("# HELP tmtrack_live_test_suite_failed_count Count of failed tests in suite")
    lines.append("# TYPE tmtrack_live_test_suite_failed_count gauge")
    lines.append(f'tmtrack_live_test_suite_failed_count{{suite="tmtrack-live"}} {total_failed}')

    lines.append("# HELP tmtrack_live_test_suite_skipped_count Count of skipped tests in suite")
    lines.append("# TYPE tmtrack_live_test_suite_skipped_count gauge")
    lines.append(f'tmtrack_live_test_suite_skipped_count{{suite="tmtrack-live"}} {total_skipped}')

    lines.append("# HELP tmtrack_live_test_suite_last_timestamp Epoch timestamp of most recent test run")
    lines.append("# TYPE tmtrack_live_test_suite_last_timestamp gauge")
    lines.append(f'tmtrack_live_test_suite_last_timestamp{{suite="tmtrack-live"}} {int(time.time())}')

    # Per-file metrics
    lines.append("# HELP tmtrack_live_test_file_status Status of test module (1=passed, 0=failed)")
    lines.append("# TYPE tmtrack_live_test_file_status gauge")
    for fr in file_results:
        lines.append(f'tmtrack_live_test_file_status{{file="{fr["file"]}"}} {fr["status"]}')

    lines.append("# HELP tmtrack_live_test_file_duration_seconds Duration of test module in seconds")
    lines.append("# TYPE tmtrack_live_test_file_duration_seconds gauge")
    for fr in file_results:
        lines.append(f'tmtrack_live_test_file_duration_seconds{{file="{fr["file"]}"}} {fr["duration"]:.4f}')

    lines.append("# HELP tmtrack_live_test_file_memory_rss_bytes Peak resident memory (RSS) consumed by test module in bytes")
    lines.append("# TYPE tmtrack_live_test_file_memory_rss_bytes gauge")
    for fr in file_results:
        lines.append(f'tmtrack_live_test_file_memory_rss_bytes{{file="{fr["file"]}"}} {fr["max_rss_bytes"]}')

    lines.append("# HELP tmtrack_live_test_file_cpu_percent Average CPU percentage utilized by test module")
    lines.append("# TYPE tmtrack_live_test_file_cpu_percent gauge")
    for fr in file_results:
        lines.append(f'tmtrack_live_test_file_cpu_percent{{file="{fr["file"]}"}} {fr["avg_cpu_percent"]:.2f}')

    # Per individual test case metrics
    lines.append("# HELP tmtrack_live_test_case_status Status of individual test case (1=passed, 0=failed, 2=skipped)")
    lines.append("# TYPE tmtrack_live_test_case_status gauge")
    for tc in test_case_results:
        lines.append(f'tmtrack_live_test_case_status{{file="{tc["file"]}",test="{tc["test"]}"}} {tc["status"]}')

    lines.append("# HELP tmtrack_live_test_case_duration_seconds Execution duration of individual test case")
    lines.append("# TYPE tmtrack_live_test_case_duration_seconds gauge")
    for tc in test_case_results:
        lines.append(f'tmtrack_live_test_case_duration_seconds{{file="{tc["file"]}",test="{tc["test"]}"}} {tc["duration"]:.4f}')

    # Atomic write to destination file with fallback
    prom_content = "\n".join(lines) + "\n"
    target_path = OUTPUT_METRICS_FILE
    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        temp_file = target_path + ".tmp"
        with open(temp_file, "w") as out:
            out.write(prom_content)
        os.replace(temp_file, target_path)
    except (PermissionError, OSError) as e:
        target_path = FALLBACK_METRICS_PATH
        print(f"Notice: Destination {OUTPUT_METRICS_FILE} not writable ({e}); saving metrics to {target_path}", file=sys.stderr)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        temp_file = target_path + ".tmp"
        with open(temp_file, "w") as out:
            out.write(prom_content)
        os.replace(temp_file, target_path)

    print(f"TMTrack live tests completed in {overall_duration:.2f}s. Passed: {total_passed}, Failed: {total_failed}, Skipped: {total_skipped}.")
    print(f"Prometheus metrics updated in {target_path}")

    # Send status to Alerta
    send_alerta_notification(all_tests_passed, total_passed, total_failed, failed_test_names)

    sys.exit(0 if all_tests_passed else 1)


if __name__ == "__main__":
    main()
