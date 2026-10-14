import datetime
from uuid import uuid4
import httpx
import pytest

def test_tasks_full_crud_lifecycle(creds, auth_headers):
    api_url = creds["api_url"]
    unique_suffix = uuid4().hex[:8]
    task_name = f"livetest-task-{unique_suffix}"
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    # 1. CREATE TASK (POST)
    new_task_payload = {
        "userid": creds["userid"],
        "date": today_str,
        "task_name": task_name,
        "category": "work",
        "expected_hours": 1.25,
        "actual_hours": 0.5,
        "description": "Automated production live test run"
    }

    create_resp = httpx.post(f"{api_url}/tasks", headers=auth_headers, json=new_task_payload, timeout=10.0)
    assert create_resp.status_code == 201, f"Create failed: {create_resp.text}"
    create_data = create_resp.json()
    assert create_data.get("status") == "success"
    task_id = create_data.get("task_id")
    assert task_id is not None

    try:
        # 2. READ SPECIFIC TASK (GET)
        get_resp = httpx.get(f"{api_url}/tasks/{task_id}", headers=auth_headers, timeout=10.0)
        assert get_resp.status_code == 200
        task_data = get_resp.json().get("task", {})
        assert task_data.get("task_id") == task_id
        assert task_data.get("task_name") == task_name
        assert task_data.get("userid") == creds["userid"]
        assert task_data.get("expected_hours") == 1.25
        assert task_data.get("actual_hours") == 0.5

        # 3. UPDATE TASK (PUT)
        update_payload = {
            "actual_hours": 1.75,
            "description": "Updated description by live test"
        }
        put_resp = httpx.put(f"{api_url}/tasks/{task_id}", headers=auth_headers, json=update_payload, timeout=10.0)
        assert put_resp.status_code == 200
        assert put_resp.json().get("status") == "success"

        # Verify update persisted
        get_resp_after = httpx.get(f"{api_url}/tasks/{task_id}", headers=auth_headers, timeout=10.0)
        assert get_resp_after.status_code == 200
        updated_data = get_resp_after.json().get("task", {})
        assert updated_data.get("actual_hours") == 1.75
        assert updated_data.get("description") == "Updated description by live test"

        # 4. LIST ALL TASKS (GET)
        list_resp = httpx.get(f"{api_url}/tasks", headers=auth_headers, timeout=10.0)
        assert list_resp.status_code == 200
        all_tasks = list_resp.json().get("tasks", [])
        found_in_list = any(t.get("task_id") == task_id for t in all_tasks)
        assert found_in_list, "Newly created task should be visible in user tasks list"

    finally:
        # 5. DELETE TASK (DELETE)
        del_resp = httpx.delete(f"{api_url}/tasks/{task_id}", headers=auth_headers, timeout=10.0)
        assert del_resp.status_code == 200
        assert del_resp.json().get("status") == "success"

        # 6. VERIFY TASK DELETED
        verify_del_resp = httpx.get(f"{api_url}/tasks/{task_id}", headers=auth_headers, timeout=10.0)
        assert verify_del_resp.status_code == 404

def test_create_task_validation_missing_fields(creds, auth_headers):
    api_url = creds["api_url"]
    # Missing expected_hours and task_name
    bad_payload = {
        "userid": creds["userid"],
        "date": "2026-10-13",
        "category": "work"
    }
    resp = httpx.post(f"{api_url}/tasks", headers=auth_headers, json=bad_payload, timeout=10.0)
    assert resp.status_code == 400
    assert resp.json().get("status") == "error"
    assert "errors" in resp.json()

def test_create_task_validation_invalid_date_format(creds, auth_headers):
    api_url = creds["api_url"]
    bad_payload = {
        "userid": creds["userid"],
        "date": "10-13-2026",  # Invalid format (expects YYYY-MM-DD)
        "task_name": "Invalid Date Task",
        "category": "work",
        "expected_hours": 1.0
    }
    resp = httpx.post(f"{api_url}/tasks", headers=auth_headers, json=bad_payload, timeout=10.0)
    assert resp.status_code == 400
    assert resp.json().get("status") == "error"
    assert "date" in resp.json().get("errors", {})

def test_get_nonexistent_task_returns_404(creds, auth_headers):
    api_url = creds["api_url"]
    random_uuid = str(uuid4())
    resp = httpx.get(f"{api_url}/tasks/{random_uuid}", headers=auth_headers, timeout=10.0)
    assert resp.status_code == 404
    assert resp.json().get("status") == "error"
