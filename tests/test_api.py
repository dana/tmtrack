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
    app = create_app()
    app.config.update({
        "TESTING": True,
        "MONGO_URI": "mongodb://localhost:27017/",
        "MONGO_DB_NAME": TEST_DB_NAME,
        "MONGO_COLLECTION_NAME": TEST_TASKS_COLLECTION
    })
    with app.app_context():
        mongo_service = MongoService()
        mongo_service.db = mongo_service.client[TEST_DB_NAME]
        mongo_service.collection = mongo_service.db[TEST_TASKS_COLLECTION]
        mongo_service.clear_collection()
        mongo_service.clear_categories_collection()
    yield app
    with app.app_context():
        mongo_service = MongoService()
        mongo_service.db = mongo_service.client[TEST_DB_NAME]
        mongo_service.collection = mongo_service.db[TEST_TASKS_COLLECTION]
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
