import json
import pytest
from tests.conftest import (
    DANA_HEADERS,
    MICHELLE_HEADERS,
    DANA_GROUPS,
    assert_auth_info,
)


def test_create_task_non_json_body(client):
    """Non-JSON request body or bad content-type returns 400 or 415."""
    response1 = client.post(
        '/api/v1/tasks',
        data="plain text not json",
        content_type='text/plain',
        headers=DANA_HEADERS
    )
    assert response1.status_code in (400, 415)

    response2 = client.post(
        '/api/v1/tasks',
        data="{bad json...",
        content_type='application/json',
        headers=DANA_HEADERS
    )
    assert response2.status_code == 400


def test_create_task_missing_date(client):
    """Missing date field returns 400 validation error."""
    payload = {"userid": "dana", "task_name": "Test", "category": "Testing", "expected_hours": 2.0}
    response = client.post('/api/v1/tasks', json=payload, headers=DANA_HEADERS)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "date" in data["errors"]


def test_create_task_missing_category(client):
    """Missing category field returns 400 validation error."""
    payload = {"userid": "dana", "task_name": "Test", "date": "2023-05-01", "expected_hours": 2.0}
    response = client.post('/api/v1/tasks', json=payload, headers=DANA_HEADERS)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "category" in data["errors"]


def test_create_task_missing_expected_hours(client):
    """Missing expected_hours field returns 400 validation error."""
    payload = {"userid": "dana", "task_name": "Test", "date": "2023-05-01", "category": "Testing"}
    response = client.post('/api/v1/tasks', json=payload, headers=DANA_HEADERS)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "expected_hours" in data["errors"]


@pytest.mark.parametrize("invalid_date", [
    "2023/05/01",
    "05-01-2023",
    "2023-13-01",
    "not-a-date",
    "2023-05-32",
])
def test_create_task_invalid_date_format(client, invalid_date):
    """Invalid date strings should return 400 with format error."""
    payload = {
        "userid": "dana",
        "task_name": "Test Date",
        "date": invalid_date,
        "category": "Testing",
        "expected_hours": 1.0,
    }
    response = client.post('/api/v1/tasks', json=payload, headers=DANA_HEADERS)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "date" in data["errors"]
    assert "YYYY-MM-DD" in data["errors"]["date"]


def test_create_task_date_as_non_string(client):
    """Date passed as int/dict should return 400 format error without crashing."""
    payload = {
        "userid": "dana",
        "task_name": "Test Date Type",
        "date": 20230501,
        "category": "Testing",
        "expected_hours": 1.0,
    }
    response = client.post('/api/v1/tasks', json=payload, headers=DANA_HEADERS)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "date" in data["errors"]
    assert "must be of type str" in data["errors"]["date"]


def test_create_task_invalid_expected_hours(client):
    """Non-numeric string for expected_hours returns 400."""
    payload = {
        "userid": "dana",
        "task_name": "Test Hours",
        "date": "2023-05-01",
        "category": "Testing",
        "expected_hours": "two",
    }
    response = client.post('/api/v1/tasks', json=payload, headers=DANA_HEADERS)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "expected_hours" in data["errors"]


def test_create_task_valid_float_and_actual_hours_zero(client):
    """Valid float hours and actual_hours 0.0 should be accepted."""
    payload = {
        "userid": "dana",
        "task_name": "Fraction task",
        "date": "2023-05-01",
        "category": "Testing",
        "expected_hours": 1.75,
        "actual_hours": 0.0,
    }
    response = client.post('/api/v1/tasks', json=payload, headers=DANA_HEADERS)
    assert response.status_code == 201
    data = json.loads(response.data)
    task_id = data["task_id"]

    get_resp = client.get(f'/api/v1/tasks/{task_id}', headers=DANA_HEADERS)
    assert get_resp.status_code == 200
    task = json.loads(get_resp.data)["task"]
    assert task["expected_hours"] == 1.75
    assert task["actual_hours"] == 0.0


def test_create_task_arbitrary_string_attribute_accepted(client):
    """Arbitrary attributes with string values should be stored."""
    payload = {
        "userid": "dana",
        "task_name": "Task with meta",
        "date": "2023-05-01",
        "category": "Testing",
        "expected_hours": 1.0,
        "client_code": "ACME-CORP",
        "billing_status": "billable",
    }
    response = client.post('/api/v1/tasks', json=payload, headers=DANA_HEADERS)
    assert response.status_code == 201
    task_id = json.loads(response.data)["task_id"]

    get_resp = client.get(f'/api/v1/tasks/{task_id}', headers=DANA_HEADERS)
    task = json.loads(get_resp.data)["task"]
    assert task.get("client_code") == "ACME-CORP"
    assert task.get("billing_status") == "billable"


def test_create_task_arbitrary_non_string_attribute_rejected(client):
    """Arbitrary attributes with non-string values should be rejected with 400."""
    payload = {
        "userid": "dana",
        "task_name": "Task with bad meta",
        "date": "2023-05-01",
        "category": "Testing",
        "expected_hours": 1.0,
        "numeric_metadata": 42,
    }
    response = client.post('/api/v1/tasks', json=payload, headers=DANA_HEADERS)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "numeric_metadata" in data["message"]
    assert "must be a string" in data["message"]


def test_modify_task_non_json(client):
    """PUT with non-JSON body returns 400 or 415."""
    response = client.put(
        '/api/v1/tasks/any-id',
        data="not json",
        content_type='text/plain',
        headers=DANA_HEADERS
    )
    assert response.status_code in (400, 415)


def test_modify_task_strips_task_id(client):
    """Passing task_id in PUT body should be stripped and not cause errors."""
    create_resp = client.post('/api/v1/tasks', json={
        "userid": "dana",
        "task_name": "Initial Name",
        "date": "2023-05-01",
        "category": "Testing",
        "expected_hours": 1.0
    }, headers=DANA_HEADERS)
    assert create_resp.status_code == 201
    task_id = json.loads(create_resp.data)["task_id"]

    modify_resp = client.put(
        f'/api/v1/tasks/{task_id}',
        json={"task_id": "spoofed-id", "task_name": "Updated Name"},
        headers=DANA_HEADERS
    )
    assert modify_resp.status_code == 200

    get_resp = client.get(f'/api/v1/tasks/{task_id}', headers=DANA_HEADERS)
    task = json.loads(get_resp.data)["task"]
    assert task["task_id"] == task_id
    assert task["task_name"] == "Updated Name"


def test_modify_task_non_existent(client):
    """Modifying a non-existent task returns 404."""
    response = client.put(
        '/api/v1/tasks/does-not-exist-12345',
        json={"task_name": "Ghost"},
        headers=DANA_HEADERS
    )
    assert response.status_code == 404
    data = json.loads(response.data)
    assert "not found" in data["message"]


def test_modify_task_validation_error(client):
    """Modifying with invalid date returns 400 validation error."""
    create_resp = client.post('/api/v1/tasks', json={
        "userid": "dana",
        "task_name": "Task before bad edit",
        "date": "2023-05-01",
        "category": "Testing",
        "expected_hours": 1.0
    }, headers=DANA_HEADERS)
    assert create_resp.status_code == 201
    task_id = json.loads(create_resp.data)["task_id"]

    modify_resp = client.put(
        f'/api/v1/tasks/{task_id}',
        json={"date": "invalid-date"},
        headers=DANA_HEADERS
    )
    assert modify_resp.status_code == 400
    data = json.loads(modify_resp.data)
    assert "date" in data["errors"]


def test_modify_task_non_string_extra_field_rejected(client):
    """Modifying with a non-string arbitrary field returns 400."""
    create_resp = client.post('/api/v1/tasks', json={
        "userid": "dana",
        "task_name": "Task before bad edit",
        "date": "2023-05-01",
        "category": "Testing",
        "expected_hours": 1.0
    }, headers=DANA_HEADERS)
    assert create_resp.status_code == 201
    task_id = json.loads(create_resp.data)["task_id"]

    modify_resp = client.put(
        f'/api/v1/tasks/{task_id}',
        json={"custom_counter": 99},
        headers=DANA_HEADERS
    )
    assert modify_resp.status_code == 400
    data = json.loads(modify_resp.data)
    assert "custom_counter" in data["message"]
    assert "must be a string" in data["message"]
