import json
import pytest
from tests.conftest import (
    DANA_HEADERS,
    MICHELLE_HEADERS,
    DANA_USERID,
    MICHELLE_USERID,
    DANA_GROUPS,
    MICHELLE_GROUPS,
    assert_auth_info,
)


def test_get_days_summary_and_incomplete(client):
    """Test GET /api/v1/days aggregates daily stats and identifies incomplete days."""
    # Create 3 tasks across 2 days for Michelle
    t1 = {
        "userid": MICHELLE_USERID, "date": "2026-10-10", "task_name": "Task 1 Complete",
        "category": "Testing", "expected_hours": 2.0, "actual_hours": 2.0
    }
    t2 = {
        "userid": MICHELLE_USERID, "date": "2026-10-10", "task_name": "Task 2 Complete",
        "category": "Testing", "expected_hours": 3.0, "actual_hours": 2.5
    }
    t3 = {
        "userid": MICHELLE_USERID, "date": "2026-10-05", "task_name": "Task 3 Incomplete",
        "category": "Testing", "expected_hours": 4.0
    }
    for t in (t1, t2, t3):
        res = client.post('/api/v1/tasks', json=t, headers=MICHELLE_HEADERS)
        assert res.status_code == 201

    # Fetch days for Michelle
    res = client.get(f'/api/v1/days?userid={MICHELLE_USERID}', headers=MICHELLE_HEADERS)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["total_days"] == 2
    assert data["total_incomplete_days"] == 1
    assert data["incomplete_dates"] == ["2026-10-05"]

    day_10 = next(d for d in data["days"] if d["date"] == "2026-10-10")
    assert day_10["task_count"] == 2
    assert day_10["total_expected"] == 5.0
    assert day_10["total_actual"] == 4.5
    assert day_10["incomplete_count"] == 0
    assert day_10["is_incomplete"] is False

    day_05 = next(d for d in data["days"] if d["date"] == "2026-10-05")
    assert day_05["task_count"] == 1
    assert day_05["total_expected"] == 4.0
    assert day_05["total_actual"] == 0.0
    assert day_05["incomplete_count"] == 1
    assert day_05["is_incomplete"] is True


def test_get_days_date_range_filtering(client):
    """Test date range filtering on GET /api/v1/days."""
    t1 = {"userid": DANA_USERID, "date": "2026-10-01", "task_name": "T1", "category": "Testing", "expected_hours": 1.0}
    t2 = {"userid": DANA_USERID, "date": "2026-10-08", "task_name": "T2", "category": "Testing", "expected_hours": 1.0}
    t3 = {"userid": DANA_USERID, "date": "2026-10-15", "task_name": "T3", "category": "Testing", "expected_hours": 1.0}
    for t in (t1, t2, t3):
        assert client.post('/api/v1/tasks', json=t, headers=DANA_HEADERS).status_code == 201

    # Filter to 2026-10-05 to 2026-10-12
    res = client.get(f'/api/v1/days?userid={DANA_USERID}&start_date=2026-10-05&end_date=2026-10-12', headers=DANA_HEADERS)
    assert res.status_code == 200
    data = res.get_json()
    dates = [d["date"] for d in data["days"]]
    assert dates == ["2026-10-08"]


def test_get_tasks_scoped_queries(client):
    """Test GET /api/v1/tasks with date and date-range query parameters."""
    t1 = {"userid": DANA_USERID, "date": "2026-10-01", "task_name": "Day 1 Task", "category": "Testing", "expected_hours": 1.0}
    t2 = {"userid": DANA_USERID, "date": "2026-10-02", "task_name": "Day 2 Task", "category": "Testing", "expected_hours": 2.0}
    t3 = {"userid": DANA_USERID, "date": "2026-10-03", "task_name": "Day 3 Task", "category": "Testing", "expected_hours": 3.0}
    for t in (t1, t2, t3):
        assert client.post('/api/v1/tasks', json=t, headers=DANA_HEADERS).status_code == 201

    # Exact date filter
    res = client.get('/api/v1/tasks?date=2026-10-02', headers=DANA_HEADERS)
    assert res.status_code == 200
    tasks = res.get_json()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["task_name"] == "Day 2 Task"

    # Range filter
    res = client.get('/api/v1/tasks?start_date=2026-10-02&end_date=2026-10-03', headers=DANA_HEADERS)
    assert res.status_code == 200
    tasks = res.get_json()["tasks"]
    assert len(tasks) == 2
    assert {t["task_name"] for t in tasks} == {"Day 2 Task", "Day 3 Task"}


def test_group_collaboration_cross_user_read(client):
    """Test that group members can read each other's tasks and days."""
    # Dana creates a task
    t_dana = {"userid": DANA_USERID, "date": "2026-10-14", "task_name": "Dana's Work", "category": "Testing", "expected_hours": 4.0}
    assert client.post('/api/v1/tasks', json=t_dana, headers=DANA_HEADERS).status_code == 201

    # Michelle views Dana's days
    res = client.get(f'/api/v1/days?userid={DANA_USERID}', headers=MICHELLE_HEADERS)
    assert res.status_code == 200
    data = res.get_json()
    assert any(d["date"] == "2026-10-14" for d in data["days"])

    # Michelle queries Dana's tasks
    res = client.get(f'/api/v1/tasks?userid={DANA_USERID}', headers=MICHELLE_HEADERS)
    assert res.status_code == 200
    tasks = res.get_json()["tasks"]
    assert any(t["task_name"] == "Dana's Work" for t in tasks)


def test_group_collaboration_write_isolation(client):
    """Test that non-admin group members cannot edit, delete, or forge tasks of other users."""
    # Dana creates a task
    t_dana = {"userid": DANA_USERID, "date": "2026-10-14", "task_name": "Dana Private Task", "category": "Testing", "expected_hours": 2.0}
    create_res = client.post('/api/v1/tasks', json=t_dana, headers=DANA_HEADERS)
    task_id = create_res.get_json()["task_id"]

    # Michelle cannot modify Dana's task
    put_res = client.put(f'/api/v1/tasks/{task_id}', json={"actual_hours": 2.0}, headers=MICHELLE_HEADERS)
    assert put_res.status_code == 403
    assert "Forbidden" in put_res.get_json()["message"]

    # Michelle cannot delete Dana's task
    del_res = client.delete(f'/api/v1/tasks/{task_id}', headers=MICHELLE_HEADERS)
    assert del_res.status_code == 403
    assert "Forbidden" in del_res.get_json()["message"]

    # Michelle cannot forge Dana's userid on task creation
    forge_res = client.post('/api/v1/tasks', json={
        "userid": DANA_USERID, "date": "2026-10-14", "task_name": "Forged Task",
        "category": "Testing", "expected_hours": 1.0
    }, headers=MICHELLE_HEADERS)
    assert forge_res.status_code == 403
    assert "Forbidden" in forge_res.get_json()["message"]


def test_guest_isolation_rejected(client):
    """Test that unauthenticated guest cannot view or modify authenticated users' days/tasks."""
    t_dana = {"userid": DANA_USERID, "date": "2026-10-14", "task_name": "Private Task", "category": "Testing", "expected_hours": 1.0}
    create_res = client.post('/api/v1/tasks', json=t_dana, headers=DANA_HEADERS)
    task_id = create_res.get_json()["task_id"]

    # Guest cannot view Dana's days
    assert client.get(f'/api/v1/days?userid={DANA_USERID}').status_code == 403

    # Guest cannot view Dana's tasks
    assert client.get(f'/api/v1/tasks?userid={DANA_USERID}').status_code == 403

    # Guest cannot view specific task by ID
    assert client.get(f'/api/v1/tasks/{task_id}').status_code == 403

    # Guest cannot modify task
    assert client.put(f'/api/v1/tasks/{task_id}', json={"actual_hours": 1.0}).status_code == 403

    # Guest cannot delete task
    assert client.delete(f'/api/v1/tasks/{task_id}').status_code == 403
