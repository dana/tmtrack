import atexit
import os
import shutil
import subprocess
import time
import pytest
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from app import create_app
from app.auth import get_groups_from_userid
from app.services.mongo_service import MongoService

TEST_DB_NAME = "tmtrack_test_db"
TEST_TASKS_COLLECTION = "daily_tasks_test"
TEST_CATEGORIES_COLLECTION = "categories"

CONTAINER_NAME = "tmtrack-test-mongo"

DANA_TOKEN = "730ea935edf1dd98eef8"
MICHELLE_TOKEN = "330829f6cb0b17ff21f5"
DANA_HEADERS = {"Authorization": f"Bearer {DANA_TOKEN}"}
MICHELLE_HEADERS = {"Authorization": f"Bearer {MICHELLE_TOKEN}"}
DANA_GROUPS = {"Hunny Bunnies", "Administrators"}
MICHELLE_GROUPS = {"Hunny Bunnies"}


def is_mongo_ready(uri: str) -> bool:
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=1000)
        client.admin.command("ping")
        client.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def mongodb_uri():
    default_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")

    if is_mongo_ready(default_uri):
        yield default_uri
        return

    # Not running, attempt to start via Docker
    docker_bin = shutil.which("docker")
    if not docker_bin:
        pytest.fail("MongoDB is not running and docker is not available in PATH.")

    # Determine if docker requires sudo (e.g. if user is not in active docker group)
    docker_cmd = [docker_bin]
    test_run = subprocess.run([docker_bin, "ps"], capture_output=True)
    if test_run.returncode != 0 and b"permission denied" in test_run.stderr.lower():
        sudo_bin = shutil.which("sudo")
        if sudo_bin:
            sudo_run = subprocess.run([sudo_bin, "-n", docker_bin, "ps"], capture_output=True)
            if sudo_run.returncode == 0:
                docker_cmd = [sudo_bin, "-n", docker_bin]

    # Stop any leftover container with the same name
    subprocess.run(docker_cmd + ["rm", "-f", CONTAINER_NAME], capture_output=True)

    # Start container
    cmd = docker_cmd + [
        "run", "-d", "--rm",
        "-p", "27017:27017",
        "--name", CONTAINER_NAME,
        "mongo:7"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(f"Failed to start MongoDB Docker container: {res.stderr}")

    def _cleanup():
        subprocess.run(docker_cmd + ["stop", CONTAINER_NAME], capture_output=True)

    atexit.register(_cleanup)

    # Wait for MongoDB to become ready
    ready = False
    for _ in range(30):
        if is_mongo_ready(default_uri):
            ready = True
            break
        time.sleep(0.5)

    if not ready:
        _cleanup()
        pytest.fail("MongoDB container started but did not respond to ping within 15 seconds.")

    yield default_uri

    _cleanup()


@pytest.fixture(scope="session", autouse=True)
def ensure_mongodb_running(mongodb_uri):
    """Session fixture to ensure MongoDB is running before any tests execute."""
    return mongodb_uri


@pytest.fixture(scope="function")
def app(mongodb_uri):
    """
    Creates a Flask app instance for testing, configured for the test database.
    Ensures the test collections are cleared before and after each test.
    """
    flask_app = create_app()
    flask_app.config.update({
        "TESTING": True,
        "MONGO_URI": mongodb_uri,
        "MONGO_DB_NAME": TEST_DB_NAME,
        "MONGO_COLLECTION_NAME": TEST_TASKS_COLLECTION,
    })

    with flask_app.app_context():
        mongo_service = MongoService()
        mongo_service.clear_collection()
        mongo_service.clear_categories_collection()

    yield flask_app

    with flask_app.app_context():
        mongo_service = MongoService()
        mongo_service.clear_collection()
        mongo_service.clear_categories_collection()


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    return app.test_cli_runner()


def assert_auth_info(data, expected_userid="guest", expected_groups=None):
    """Helper to assert presence and correctness of auth metadata in responses."""
    if expected_groups is None:
        expected_groups = get_groups_from_userid(expected_userid)
    assert "userid" in data and data["userid"] == expected_userid
    assert "groups" in data and set(data["groups"]) == set(expected_groups)
