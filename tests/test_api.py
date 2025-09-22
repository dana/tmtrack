import pytest
from app import create_app
from app.services.mongo_service import MongoService
from mongomock import MongoClient
from unittest.mock import patch
import json
import datetime

# Mock the MongoClient to prevent actual database connections during testing
@pytest.fixture(scope='module')
def mock_mongo_client():
    with patch('pymongo.MongoClient', new=MongoClient):
        yield

@pytest.fixture(scope='module')
def app(mock_mongo_client):
    app = create_app()
    app.config.update({
        "TESTING": True,
        "MONGO_URI": "mongodb://localhost:27017/", # Still needs to be set for config, but mock client intercepts
        "MONGO_DB_NAME": "tmtrack_test_db",
        "MONGO_COLLECTION_NAME": "daily_tasks_test"
    })
    # Clear the collection before each test suite run
    with app.app_context():
        mongo_service = MongoService()
        mongo_service.clear_collection()
    yield app
    # Clear collection after tests
    with app.app_context():
        mongo_service = MongoService()
        mongo_service.clear_collection()


@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def runner(app):
    return app.test_cli_runner()

# --- Test Cases ---

def test_create_task_success(client):
    """Test successful task creation."""
    task_data = {
        "userid": "testuser1",
        "date": "2023-01-01",
        "task_name": "Test Task 1",
        "category": "Testing",
        "expected_hours": 2.5,
        "arbitrary_field": "some_value"
    }
    response = client.post('/api/v1/tasks', json=task_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'task_id' in data
    assert data['message'] == 'Task created successfully'

    # Verify task exists in the mocked DB
    with patch('pymongo.MongoClient', new=MongoClient): # Re-patch for service instance if needed
        with client.application.app_context():
            mongo_service = MongoService()
            retrieved_task = mongo_service.get_task(data['task_id'])
            assert retrieved_task is not None
            assert retrieved_task['userid'] == "testuser1"
            assert retrieved_task['arbitrary_field'] == "some_value"
            assert 'created_at' in retrieved_task
            assert 'updated_at' in retrieved_task


def test_create_task_missing_required_field(client):
    """Test task creation with a missing required field."""
    task_data = {
        "userid": "testuser2",
        "date": "2023-01-02",
        "task_name": "Test Task 2",
        # "category": "Testing", # Missing
        "expected_hours": 3.0
    }
    response = client.post('/api/v1/tasks', json=task_data)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'category' in data['errors']
    assert "'category' is a required field." in data['errors']['category']

def test_create_task_incorrect_data_type(client):
    """Test task creation with incorrect data type for a field."""
    task_data = {
        "userid": "testuser3",
        "date": "2023-01-03",
        "task_name": "Test Task 3",
        "category": "Testing",
        "expected_hours": "not_a_float" # Incorrect type
    }
    response = client.post('/api/v1/tasks', json=task_data)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'expected_hours' in data['errors']
    assert "'expected_hours' must be of type float, but got str." in data['errors']['expected_hours']

def test_create_task_invalid_date_format(client):
    """Test task creation with an invalid date format."""
    task_data = {
        "userid": "testuser3",
        "date": "01-03-2023", # Incorrect format
        "task_name": "Test Task 3",
        "category": "Testing",
        "expected_hours": 4.0
    }
    response = client.post('/api/v1/tasks', json=task_data)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'date' in data['errors']
    assert "'date' must be in YYYY-MM-DD format." in data['errors']['date']

def test_create_task_arbitrary_field_not_string(client):
    """Test task creation with an arbitrary field that is not a string."""
    task_data = {
        "userid": "testuser4",
        "date": "2023-01-04",
        "task_name": "Test Task 4",
        "category": "Testing",
        "expected_hours": 1.0,
        "arbitrary_number": 123 # Should be string
    }
    response = client.post('/api/v1/tasks', json=task_data)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert data['message'] == "Arbitrary attribute 'arbitrary_number' must be a string."


def test_modify_task_success(client):
    """Test successful modification of an existing task."""
    # First, create a task to modify
    create_response = client.post('/api/v1/tasks', json={
        "userid": "moduser1", "date": "2023-02-01", "task_name": "Task to Modify",
        "category": "Modification", "expected_hours": 5.0
    })
    assert create_response.status_code == 201
    created_task_id = json.loads(create_response.data)['task_id']

    # Now, modify it
    modify_data = {
        "actual_hours": 4.5,
        "description": "Finished early.",
        "new_arbitrary_field": "new_value" # Add new arbitrary field
    }
    response = client.put(f'/api/v1/tasks/{created_task_id}', json=modify_data)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['message'] == 'Task updated successfully'
    assert data['task_id'] == created_task_id

    # Verify update in the mocked DB
    with patch('pymongo.MongoClient', new=MongoClient):
        with client.application.app_context():
            mongo_service = MongoService()
            retrieved_task = mongo_service.get_task(created_task_id)
            assert retrieved_task['actual_hours'] == 4.5
            assert retrieved_task['description'] == "Finished early."
            assert retrieved_task['new_arbitrary_field'] == "new_value"
            assert retrieved_task['userid'] == "moduser1" # Unchanged
            assert retrieved_task['updated_at'] > retrieved_task['created_at']


def test_modify_task_not_found(client):
    """Test modification of a non-existent task."""
    non_existent_id = "non-existent-task-id"
    modify_data = {"actual_hours": 1.0}
    response = client.put(f'/api/v1/tasks/{non_existent_id}', json=modify_data)
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert "not found" in data['message']

def test_modify_task_incorrect_data_type(client):
    """Test modification with incorrect data type for a field."""
    # Create a task first
    create_response = client.post('/api/v1/tasks', json={
        "userid": "moduser2", "date": "2023-02-02", "task_name": "Task for Bad Modify",
        "category": "Modification", "expected_hours": 6.0
    })
    assert create_response.status_code == 201
    created_task_id = json.loads(create_response.data)['task_id']

    # Try to modify with bad type
    modify_data = {"expected_hours": "should_be_float"}
    response = client.put(f'/api/v1/tasks/{created_task_id}', json=modify_data)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'expected_hours' in data['errors']
    assert "'expected_hours' must be of type float, but got str." in data['errors']['expected_hours']

def test_modify_task_arbitrary_field_not_string(client):
    """Test modification with an arbitrary field that is not a string."""
    # Create a task first
    create_response = client.post('/api/v1/tasks', json={
        "userid": "moduser3", "date": "2023-02-03", "task_name": "Task for Bad Arbitrary Modify",
        "category": "Modification", "expected_hours": 7.0
    })
    assert create_response.status_code == 201
    created_task_id = json.loads(create_response.data)['task_id']

    # Try to modify with bad arbitrary type
    modify_data = {"new_arbitrary_number": 456} # Should be string

