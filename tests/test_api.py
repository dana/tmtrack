# In tests/test_api.py

import pytest
from app import create_app
from app.services.mongo_service import MongoService
import json
import datetime
from pymongo.errors import ConnectionFailure

# Use a distinct test database and collection name
TEST_DB_NAME = "tmtrack_test_db"
TEST_TASKS_COLLECTION = "daily_tasks_test"
TEST_CATEGORIES_COLLECTION = "categories" # Use a consistent name, no need for _test

@pytest.fixture(scope='session', autouse=True)
def ensure_mongodb_running():
    """Ensures MongoDB is running before any tests are executed."""
    try:
        # Attempt to connect to MongoDB directly to check if it's running
        from pymongo import MongoClient
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=1000)
        client.admin.command('ping')
        print("\nMongoDB is running. Proceeding with tests.")
    except ConnectionFailure:
        pytest.fail("MongoDB not running. Please start MongoDB on localhost:27017 before running tests.")


@pytest.fixture(scope='function') # Changed scope to function to clear DB for each test
def app():
    """
    Fixture for creating a Flask app instance with test configuration.
    Clears the test database collection before each test function.
    """
    app = create_app()
    app.config.update({
        "TESTING": True,
        "MONGO_URI": "mongodb://localhost:27017/",
        "MONGO_DB_NAME": TEST_DB_NAME,
        "MONGO_COLLECTION_NAME": TEST_TASKS_COLLECTION
    })

    with app.app_context():
        mongo_service = MongoService()
        # Explicitly set db and collection names for the service instance used in fixture
        # to ensure it clears the correct test collection.
        mongo_service.db = mongo_service.client[TEST_DB_NAME]
        mongo_service.collection = mongo_service.db[TEST_TASKS_COLLECTION]
        mongo_service.clear_collection() # Clear before each test
        mongo_service.clear_categories_collection()
    yield app
    with app.app_context():
        mongo_service = MongoService()
        mongo_service.db = mongo_service.client[TEST_DB_NAME]
        mongo_service.collection = mongo_service.db[TEST_TASKS_COLLECTION]
        mongo_service.clear_collection() # Clear after each test
        mongo_service.clear_categories_collection()



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

    # Verify task exists in the real DB
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

    # Verify update in the real DB
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
    response = client.put(f'/api/v1/tasks/{created_task_id}', json=modify_data)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert data['message'] == "Arbitrary attribute 'new_arbitrary_number' must be a string."

def test_get_task_success(client):
    """Test retrieving a single task."""
    create_response = client.post('/api/v1/tasks', json={
        "userid": "getuser1", "date": "2023-03-01", "task_name": "Task to Get",
        "category": "Retrieve", "expected_hours": 1.0
    })
    assert create_response.status_code == 201
    created_task_id = json.loads(create_response.data)['task_id']

    response = client.get(f'/api/v1/tasks/{created_task_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['task']['task_id'] == created_task_id
    assert data['task']['userid'] == 'getuser1'

def test_get_task_not_found(client):
    """Test retrieving a non-existent task."""
    response = client.get(f'/api/v1/tasks/non-existent-task')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'not found' in data['message']

def test_get_all_tasks(client):
    """Test retrieving all tasks."""
    client.post('/api/v1/tasks', json={"userid": "listuser1", "date": "2023-04-01", "task_name": "List Task 1", "category": "List", "expected_hours": 1.0})
    client.post('/api/v1/tasks', json={"userid": "listuser2", "date": "2023-04-02", "task_name": "List Task 2", "category": "List", "expected_hours": 2.0})

    response = client.get('/api/v1/tasks')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert len(data['tasks']) >= 2 # Might be more if previous tests failed to clear cleanly, but the fixture should handle it.
    userids = [t['userid'] for t in data['tasks']]
    assert 'listuser1' in userids
    assert 'listuser2' in userids
# In tests/test_api.py

def test_create_task_does_not_fail_on_internal_datetime_fields(client):
    """
    Test that a valid task creation does not fail validation due to
    internally added datetime fields like 'created_at' and 'updated_at'.
    This test specifically captures the bug where internal fields were
    incorrectly validated as arbitrary string attributes.
    """
    task_data = {
        "userid": "internal_field_user",
        "date": "2024-01-01",
        "task_name": "Test Internal Fields",
        "category": "Bugfix",
        "expected_hours": 1.0,
        "description": "This task should be created without errors."
    }
    response = client.post('/api/v1/tasks', json=task_data)

    # Before the fix, this would be a 400 error. After the fix, it should be 201.
    assert response.status_code == 201, f"Expected status 201, but got {response.status_code}. Response data: {response.data.decode()}"

    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'task_id' in data


def test_modify_task_does_not_fail_on_internal_datetime_fields(client):
    """
    Test that a valid task modification does not fail validation due to
    the internally added 'updated_at' datetime field.
    """
    # First, create a task to modify
    create_response = client.post('/api/v1/tasks', json={
        "userid": "internal_modify_user",
        "date": "2024-01-02",
        "task_name": "Task for Internal Field Modify",
        "category": "Bugfix",
        "expected_hours": 2.0
    })
    assert create_response.status_code == 201
    task_id = json.loads(create_response.data)['task_id']

    # Now, modify it with valid data
    modify_data = {"description": "Updated description."}
    response = client.put(f'/api/v1/tasks/{task_id}', json=modify_data)

    # Before the fix, this would also be a 400 error. After the fix, it should be 200.
    assert response.status_code == 200, f"Expected status 200, but got {response.status_code}. Response data: {response.data.decode()}"
    data = json.loads(response.data)
    assert data['status'] == 'success'

def test_modify_task_without_task_id_in_body_succeeds(client):
    """
    Test that modifying a task succeeds when the task_id is only in the URL
    and not in the request body, which is the correct REST pattern.
    This captures the bug where validation incorrectly required task_id in the body.
    """
    # First, create a task to get a valid ID
    create_response = client.post('/api/v1/tasks', json={
        "userid": "no_body_id_user",
        "date": "2024-02-01",
        "task_name": "Test No Body ID",
        "category": "Bugfix",
        "expected_hours": 3.0
    })
    assert create_response.status_code == 201
    task_id = json.loads(create_response.data)['task_id']

    # Now, modify it without task_id in the JSON payload
    modify_data = {"description": "This update should work."}
    response = client.put(f'/api/v1/tasks/{task_id}', json=modify_data)

    # Before the fix, this will be 400. After, it should be 200.
    assert response.status_code == 200, f"Expected status 200, but got {response.status_code}. Response data: {response.data.decode()}"
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['message'] == 'Task updated successfully'

    # Verify the change in the database
    with client.application.app_context():
        mongo_service = MongoService()
        retrieved_task = mongo_service.get_task(task_id)
        assert retrieved_task['description'] == "This update should work."


def test_list_users(client):
    """Test the list_users endpoint to ensure it returns the correct users."""
    response = client.get('/api/v1/users')
    
    # 1. Check for a successful HTTP status code
    assert response.status_code == 200
    
    data = json.loads(response.data)
    
    # 2. Check that the top-level JSON key is 'users'
    assert 'users' in data
    
    # 3. Check that the value associated with 'users' is a list
    assert isinstance(data['users'], list)
    
    # 4. Check that the list contains the exact expected users
    # Using a set comparison is robust and ignores the order of elements.
    expected_users = {"dana", "michelle"}
    assert set(data['users']) == expected_users
    
    # 5. Check that there are no extra users
    assert len(data['users']) == 2


def test_get_categories_when_empty(client):
    """Test GET /categories when no document exists; should return a default empty list."""
    response = client.get('/api/v1/categories')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == {"categories": []}

def test_put_and_get_categories(client):
    """Test successfully setting categories with PUT and then retrieving them with GET."""
    # 1. PUT a new list of categories
    put_payload = {"categories": ["work", "personal", "billing"]}
    put_response = client.put('/api/v1/categories', json=put_payload)
    assert put_response.status_code == 200
    put_data = json.loads(put_response.data)
    assert put_data['status'] == 'success'

    # 2. GET the categories to verify they were saved
    get_response = client.get('/api/v1/categories')
    assert get_response.status_code == 200
    get_data = json.loads(get_response.data)
    assert get_data == put_payload

def test_put_categories_overwrite(client):
    """Test that a second PUT request overwrites the existing categories document."""
    # First PUT
    client.put('/api/v1/categories', json={"categories": ["initial", "list"]})

    # Second PUT with new data
    new_payload = {"categories": ["final list only"]}
    put_response = client.put('/api/v1/categories', json=new_payload)
    assert put_response.status_code == 200

    # GET to confirm the data was overwritten
    get_response = client.get('/api/v1/categories')
    assert get_response.status_code == 200
    get_data = json.loads(get_response.data)
    assert get_data == new_payload

def test_put_categories_invalid_payloads(client):
    """Test various invalid payloads for the PUT /categories endpoint."""
    # Case 1: Incorrect top-level key
    bad_payload_1 = {"cats": ["a", "b"]}
    response1 = client.put('/api/v1/categories', json=bad_payload_1)
    assert response1.status_code == 400
    assert "must contain a 'categories' key" in response1.data.decode()

    # Case 2: Value is not a list
    bad_payload_2 = {"categories": "just a string"}
    response2 = client.put('/api/v1/categories', json=bad_payload_2)
    assert response2.status_code == 400
    assert "must be a list" in response2.data.decode()

    # Case 3: List contains non-string items
    bad_payload_3 = {"categories": ["ok", "fine", 123, "not fine"]}
    response3 = client.put('/api/v1/categories', json=bad_payload_3)
    assert response3.status_code == 400
    assert "must be strings" in response3.data.decode()

