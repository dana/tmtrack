import json
import pytest
from tests.conftest import (
    DANA_HEADERS,
    MICHELLE_HEADERS,
    DANA_GROUPS,
    MICHELLE_GROUPS,
    DANA_USERID,
    MICHELLE_USERID,
    assert_auth_info,
)


def test_create_task_success(client):
    """Test successful task creation with authentication."""
    task_data = {
        "userid": "testuser1", "date": "2023-01-01", "task_name": "Test Task 1",
        "category": "Testing", "expected_hours": 2.5
    }
    response = client.post('/api/v1/tasks', json=task_data, headers=DANA_HEADERS)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert_auth_info(data, DANA_USERID, DANA_GROUPS)
    assert data['status'] == 'success'
    assert 'task_id' in data


def test_create_task_as_guest(client):
    """Test task creation without authentication header results in guest user."""
    task_data = {
        "userid": "guestuser", "date": "2023-01-02", "task_name": "Guest Task",
        "category": "Testing", "expected_hours": 1.0
    }
    response = client.post('/api/v1/tasks', json=task_data) # No headers
    assert response.status_code == 201
    data = json.loads(response.data)
    assert_auth_info(data, "guest")
    assert data['status'] == 'success'


def test_modify_task_success(client):
    """Test successful modification of an existing task with auth."""
    create_response = client.post('/api/v1/tasks', json={
        "userid": MICHELLE_USERID, "date": "2023-02-01", "task_name": "Task to Modify",
        "category": "Modification", "expected_hours": 5.0
    }, headers=MICHELLE_HEADERS)
    created_task_id = json.loads(create_response.data)['task_id']

    modify_data = {"actual_hours": 4.5}
    response = client.put(f'/api/v1/tasks/{created_task_id}', json=modify_data, headers=MICHELLE_HEADERS)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert_auth_info(data, MICHELLE_USERID, MICHELLE_GROUPS)
    assert data['status'] == 'success'


def test_modify_task_unauthorized(client):
    """Test that a non-admin user cannot modify another user's task."""
    create_response = client.post('/api/v1/tasks', json={
        "userid": DANA_USERID, "date": "2023-02-01", "task_name": "Dana's Task",
        "category": "Modification", "expected_hours": 5.0
    }, headers=DANA_HEADERS)
    created_task_id = json.loads(create_response.data)['task_id']

    modify_data = {"actual_hours": 4.5}
    response = client.put(f'/api/v1/tasks/{created_task_id}', json=modify_data, headers=MICHELLE_HEADERS)
    assert response.status_code == 403
    data = json.loads(response.data)
    assert_auth_info(data, MICHELLE_USERID, MICHELLE_GROUPS)
    assert data['status'] == 'error'
    assert "Forbidden" in data['message']


def test_get_task_success(client):
    """Test retrieving a single task with auth."""
    create_response = client.post('/api/v1/tasks', json={
        "userid": "getuser1", "date": "2023-03-01", "task_name": "Task to Get",
        "category": "Retrieve", "expected_hours": 1.0
    }, headers=DANA_HEADERS)
    created_task_id = json.loads(create_response.data)['task_id']

    response = client.get(f'/api/v1/tasks/{created_task_id}', headers=DANA_HEADERS)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert_auth_info(data, DANA_USERID, DANA_GROUPS)
    assert data['status'] == 'success'
    assert data['task']['task_id'] == created_task_id


def test_get_all_tasks_as_guest(client):
    """Test retrieving all tasks as a guest."""
    response = client.get('/api/v1/tasks') # No headers
    assert response.status_code == 200
    data = json.loads(response.data)
    assert_auth_info(data, "guest")
    assert data['status'] == 'success'


def test_get_all_tasks_with_auth_and_filtering(client):
    """
    Test that GET /tasks returns only tasks for users in the same groups
    as the authenticated user.
    """
    # Create tasks for different users
    client.post('/api/v1/tasks', json={
        "userid": DANA_USERID, "date": "2023-04-01", "task_name": "Dana's Task",
        "category": "Work", "expected_hours": 8.0
    }, headers=DANA_HEADERS)
    client.post('/api/v1/tasks', json={
        "userid": MICHELLE_USERID, "date": "2023-04-01", "task_name": "Michelle's Task",
        "category": "Work", "expected_hours": 7.5
    }, headers=MICHELLE_HEADERS)
    client.post('/api/v1/tasks', json={
        "userid": "guest", "date": "2023-04-01", "task_name": "Guest's Task",
        "category": "Personal", "expected_hours": 1.0
    }) # No headers for guest

    # Dana sees dana and michelle
    response_dana = client.get('/api/v1/tasks', headers=DANA_HEADERS)
    assert response_dana.status_code == 200
    data_dana = json.loads(response_dana.data)
    assert_auth_info(data_dana, DANA_USERID, DANA_GROUPS)
    assert len(data_dana['tasks']) == 2
    userids_seen_by_dana = {t['userid'] for t in data_dana['tasks']}
    assert userids_seen_by_dana == {DANA_USERID, MICHELLE_USERID}

    # Michelle sees dana and michelle
    response_michelle = client.get('/api/v1/tasks', headers=MICHELLE_HEADERS)
    assert response_michelle.status_code == 200
    data_michelle = json.loads(response_michelle.data)
    assert_auth_info(data_michelle, MICHELLE_USERID, MICHELLE_GROUPS)
    assert len(data_michelle['tasks']) == 2
    userids_seen_by_michelle = {t['userid'] for t in data_michelle['tasks']}
    assert userids_seen_by_michelle == {DANA_USERID, MICHELLE_USERID}

    # Guest sees guest
    response_guest = client.get('/api/v1/tasks') # No headers
    assert response_guest.status_code == 200
    data_guest = json.loads(response_guest.data)
    assert_auth_info(data_guest, "guest")
    assert len(data_guest['tasks']) == 1
    assert data_guest['tasks'][0]['userid'] == 'guest'


def test_delete_task_success(client):
    """Test successful deletion of a task by its owner."""
    task_data = {
        "userid": DANA_USERID, "date": "2023-01-01", "task_name": "Task to be deleted",
        "category": "Testing", "expected_hours": 1.0
    }
    create_response = client.post('/api/v1/tasks', json=task_data, headers=DANA_HEADERS)
    task_id = json.loads(create_response.data)['task_id']

    delete_response = client.delete(f'/api/v1/tasks/{task_id}', headers=DANA_HEADERS)
    assert delete_response.status_code == 200
    data = json.loads(delete_response.data)
    assert_auth_info(data, DANA_USERID, DANA_GROUPS)
    assert data['status'] == 'success'
    assert data['message'] == 'Task deleted successfully'

    get_response = client.get(f'/api/v1/tasks/{task_id}', headers=DANA_HEADERS)
    assert get_response.status_code == 404


def test_delete_task_unauthorized(client):
    """Test that a user cannot delete a task owned by another user."""
    task_data = {
        "userid": DANA_USERID, "date": "2023-01-01", "task_name": "Dana's private task",
        "category": "Testing", "expected_hours": 1.0
    }
    create_response = client.post('/api/v1/tasks', json=task_data, headers=DANA_HEADERS)
    task_id = json.loads(create_response.data)['task_id']

    delete_response = client.delete(f'/api/v1/tasks/{task_id}', headers=MICHELLE_HEADERS)
    assert delete_response.status_code == 403
    data = json.loads(delete_response.data)
    assert_auth_info(data, MICHELLE_USERID, MICHELLE_GROUPS)
    assert data['status'] == 'error'
    assert "Forbidden" in data['message']


def test_delete_task_not_found(client):
    """Test deleting a task that does not exist."""
    delete_response = client.delete('/api/v1/tasks/non-existent-id', headers=DANA_HEADERS)
    assert delete_response.status_code == 404
    data = json.loads(delete_response.data)
    assert_auth_info(data, DANA_USERID, DANA_GROUPS)
    assert data['status'] == 'error'
    assert data['message'] == 'Task not found'


def test_delete_task_as_guest(client):
    """Test that a guest user cannot delete a task owned by Dana."""
    task_data = {
        "userid": DANA_USERID, "date": "2023-01-01", "task_name": "A task",
        "category": "Testing", "expected_hours": 1.0
    }
    create_response = client.post('/api/v1/tasks', json=task_data, headers=DANA_HEADERS)
    task_id = json.loads(create_response.data)['task_id']

    delete_response = client.delete(f'/api/v1/tasks/{task_id}') # No headers
    assert delete_response.status_code == 403
    data = json.loads(delete_response.data)
    assert_auth_info(data, "guest")
    assert data['status'] == 'error'
    assert "Forbidden" in data['message']


def test_happy_endpoint(client):
    response = client.get("/api/v1/happy")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"


def test_list_users_with_auth(client):
    """Test the list_users endpoint with authentication."""
    response = client.get('/api/v1/users', headers=MICHELLE_HEADERS)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert_auth_info(data, MICHELLE_USERID, MICHELLE_GROUPS)
    assert set(data['users']) == {DANA_USERID, MICHELLE_USERID}


def test_put_and_get_categories_with_auth(client):
    """Test PUT and GET categories with authentication."""
    put_payload = {"categories": ["work", "personal"]}
    put_response = client.put('/api/v1/categories', json=put_payload, headers=DANA_HEADERS)
    assert put_response.status_code == 200
    put_data = json.loads(put_response.data)
    assert_auth_info(put_data, DANA_USERID, DANA_GROUPS)
    assert put_data['status'] == 'success'

    get_response = client.get('/api/v1/categories', headers=MICHELLE_HEADERS)
    assert get_response.status_code == 200
    get_data = json.loads(get_response.data)
    assert_auth_info(get_data, MICHELLE_USERID, MICHELLE_GROUPS)
    assert get_data['categories'] == ["work", "personal"]


def test_get_categories_as_guest(client):
    """Test GET /categories as a guest."""
    response = client.get('/api/v1/categories') # No headers
    assert response.status_code == 200
    data = json.loads(response.data)
    assert_auth_info(data, "guest")
    assert data['categories'] == []


def test_create_task_missing_required_field(client):
    task_data = {"userid": "testuser2", "task_name": "Test Task 2"}
    response = client.post('/api/v1/tasks', json=task_data)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert_auth_info(data, "guest")
    assert data['status'] == 'error'
