import pytest
from app import create_app
from app.services.mongo_service import MongoService
import json
from pymongo.errors import ConnectionFailure

# --- Constants for testing ---
TEST_DB_NAME = "tmtrack_test_db"
TEST_TASKS_COLLECTION = "daily_tasks_test"
TEST_CATEGORIES_COLLECTION = "categories"

# Use tokens from user_authentication.json
DANA_TOKEN = "730ea935edf1dd98eef8"
MICHELLE_TOKEN = "330829f6cb0b17ff21f5"
DANA_HEADERS = {"Authorization": f"Bearer {DANA_TOKEN}"}
MICHELLE_HEADERS = {"Authorization": f"Bearer {MICHELLE_TOKEN}"}
DANA_GROUPS = {"Hunny Bunnies", "Administrators"}
MICHELLE_GROUPS = {"Hunny Bunnies"}


# --- Fixtures (ensure_mongodb_running and app fixtures remain the same) ---
@pytest.fixture(scope='session', autouse=True)
def ensure_mongodb_running():
    try:
        from pymongo import MongoClient
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=1000)
        client.admin.command('ping')
    except ConnectionFailure:
        pytest.fail("MongoDB not running. Please start it before running tests.")

@pytest.fixture(scope='function')
def app():
    """
    Creates a Flask app instance for testing, configured for the test database.
    It also ensures the test database collections are cleared before and after
    each test.
    """
    app = create_app()
    app.config.update({
        "TESTING": True,
        "MONGO_URI": "mongodb://localhost:27017/",
        "MONGO_DB_NAME": TEST_DB_NAME,
        "MONGO_COLLECTION_NAME": TEST_TASKS_COLLECTION
    })

    with app.app_context():
        # The first call to MongoService will establish a connection.
        mongo_service = MongoService()
        # Clear collections to ensure a clean state for the test.
        mongo_service.clear_collection()
        mongo_service.clear_categories_collection()

    yield app

    # Teardown: runs after the test has completed.
    with app.app_context():
        mongo_service = MongoService()
        mongo_service.clear_collection()
        mongo_service.clear_categories_collection()

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def runner(app):
    return app.test_cli_runner()

# --- Helper for auth assertions ---
def assert_auth_info(data, expected_userid="guest", expected_groups=None):
    if expected_groups is None:
        expected_groups = ["Guests"]
    assert 'userid' in data and data['userid'] == expected_userid
    assert 'groups' in data and set(data['groups']) == set(expected_groups)


# --- Updated Test Cases ---

def test_create_task_success(client):
    """Test successful task creation with authentication."""
    task_data = {
        "userid": "testuser1", "date": "2023-01-01", "task_name": "Test Task 1",
        "category": "Testing", "expected_hours": 2.5
    }
    response = client.post('/api/v1/tasks', json=task_data, headers=DANA_HEADERS)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert_auth_info(data, "dana", DANA_GROUPS)
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
    assert_auth_info(data) # Asserts guest user
    assert data['status'] == 'success'

def test_modify_task_success(client):
    """Test successful modification of an existing task with auth."""
    create_response = client.post('/api/v1/tasks', json={
        "userid": "moduser1", "date": "2023-02-01", "task_name": "Task to Modify",
        "category": "Modification", "expected_hours": 5.0
    }, headers=DANA_HEADERS)
    created_task_id = json.loads(create_response.data)['task_id']

    modify_data = {"actual_hours": 4.5}
    response = client.put(f'/api/v1/tasks/{created_task_id}', json=modify_data, headers=MICHELLE_HEADERS)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert_auth_info(data, "michelle", MICHELLE_GROUPS)
    assert data['status'] == 'success'

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
    assert_auth_info(data, "dana", DANA_GROUPS)
    assert data['status'] == 'success'
    assert data['task']['task_id'] == created_task_id

def test_get_all_tasks_as_guest(client):
    """Test retrieving all tasks as a guest."""
    response = client.get('/api/v1/tasks') # No headers
    assert response.status_code == 200
    data = json.loads(response.data)
    assert_auth_info(data)
    assert data['status'] == 'success'

def test_get_all_tasks_with_auth_and_filtering(client):
    """
    Test that GET /tasks returns only tasks for users in the same groups
    as the authenticated user.
    """
    # Create tasks for different users
    client.post('/api/v1/tasks', json={
        "userid": "dana", "date": "2023-04-01", "task_name": "Dana's Task",
        "category": "Work", "expected_hours": 8.0
    }, headers=DANA_HEADERS)
    client.post('/api/v1/tasks', json={
        "userid": "michelle", "date": "2023-04-01", "task_name": "Michelle's Task",
        "category": "Work", "expected_hours": 7.5
    }, headers=MICHELLE_HEADERS)
    client.post('/api/v1/tasks', json={
        "userid": "guest", "date": "2023-04-01", "task_name": "Guest's Task",
        "category": "Personal", "expected_hours": 1.0
    }) # No headers for guest

    # --- Test as dana (should see dana's and michelle's tasks) ---
    # Dana is in "Hunny Bunnies" and "Administrators".
    # Michelle is in "Hunny Bunnies".
    # So, Dana should see tasks from all users in both groups.
    response_dana = client.get('/api/v1/tasks', headers=DANA_HEADERS)
    assert response_dana.status_code == 200
    data_dana = json.loads(response_dana.data)
    assert_auth_info(data_dana, "dana", DANA_GROUPS)
    assert len(data_dana['tasks']) == 2
    userids_seen_by_dana = {t['userid'] for t in data_dana['tasks']}
    assert userids_seen_by_dana == {"dana", "michelle"}

    # --- Test as michelle (should see dana's and michelle's tasks) ---
    # Michelle is only in "Hunny Bunnies".
    # Dana is also in "Hunny Bunnies".
    # So, Michelle should see tasks from all users in that group.
    response_michelle = client.get('/api/v1/tasks', headers=MICHELLE_HEADERS)
    assert response_michelle.status_code == 200
    data_michelle = json.loads(response_michelle.data)
    assert_auth_info(data_michelle, "michelle", MICHELLE_GROUPS)
    assert len(data_michelle['tasks']) == 2
    userids_seen_by_michelle = {t['userid'] for t in data_michelle['tasks']}
    assert userids_seen_by_michelle == {"dana", "michelle"}

    # --- Test as guest (should only see guest's task) ---
    response_guest = client.get('/api/v1/tasks') # No headers
    assert response_guest.status_code == 200
    data_guest = json.loads(response_guest.data)
    assert_auth_info(data_guest)
    assert len(data_guest['tasks']) == 1
    assert data_guest['tasks'][0]['userid'] == 'guest'

def test_list_users_with_auth(client):
    """Test the list_users endpoint with authentication."""
    response = client.get('/api/v1/users', headers=MICHELLE_HEADERS)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert_auth_info(data, "michelle", MICHELLE_GROUPS)
    assert set(data['users']) == {"dana", "michelle"}

def test_put_and_get_categories_with_auth(client):
    """Test PUT and GET categories with authentication."""
    # PUT as an admin (dana)
    put_payload = {"categories": ["work", "personal"]}
    put_response = client.put('/api/v1/categories', json=put_payload, headers=DANA_HEADERS)
    assert put_response.status_code == 200
    put_data = json.loads(put_response.data)
    assert_auth_info(put_data, "dana", DANA_GROUPS)
    assert put_data['status'] == 'success'

    # GET as another user (michelle)
    get_response = client.get('/api/v1/categories', headers=MICHELLE_HEADERS)
    assert get_response.status_code == 200
    get_data = json.loads(get_response.data)
    assert_auth_info(get_data, "michelle", MICHELLE_GROUPS)
    assert get_data['categories'] == ["work", "personal"]

def test_get_categories_as_guest(client):
    """Test GET /categories as a guest."""
    response = client.get('/api/v1/categories') # No headers
    assert response.status_code == 200
    data = json.loads(response.data)
    assert_auth_info(data)
    assert data['categories'] == []

# ... (It's good practice to keep the negative test cases as well, they don't need auth headers)
def test_create_task_missing_required_field(client):
    task_data = {"userid": "testuser2", "task_name": "Test Task 2"}
    response = client.post('/api/v1/tasks', json=task_data)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert_auth_info(data) # Even errors should return auth info
    assert data['status'] == 'error'
