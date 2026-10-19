from werkzeug.security import generate_password_hash
import json
import pytest
from app import auth

SAMPLE_AUTH_DATA = [
    {"userid": "dana", "auth_token": "token_dana"},
    {"userid": "michelle", "auth_token": "token_michelle"},
    {"userid": "service-test", "password": "plain-password", "password_hash": generate_password_hash("hash-password"), "auth_token": "token-as-pwd"}
]
SAMPLE_AUTHZ_DATA = [
    {"group_name": "Group A", "userids": ["dana", "michelle"]},
    {"group_name": "Group B", "userids": ["dana"]},
    {"group_name": "Guests", "userids": ["guest"]}
]

@pytest.fixture
def setup_auth_files(tmp_path, monkeypatch):
    """
    A pytest fixture to create temporary auth/authz files and load them.
    Ensures tests are isolated from real JSON files and restores state on teardown.
    """
    auth_file = tmp_path / "user_authentication.json"
    authz_file = tmp_path / "user_authorization.json"

    with open(auth_file, "w") as f:
        json.dump(SAMPLE_AUTH_DATA, f)

    with open(authz_file, "w") as f:
        json.dump(SAMPLE_AUTHZ_DATA, f)

    monkeypatch.setattr(auth.Path, "parent", tmp_path, raising=False)

    import importlib
    importlib.reload(auth)

    yield

    # Monkeypatch undoes automatically when leaving fixture; reload auth to restore original repo data
    monkeypatch.undo()
    importlib.reload(auth)


# --- Tests for get_userid_from_token ---

def test_get_userid_from_token_valid(setup_auth_files):
    """Test retrieving a userid with a valid, known token."""
    assert auth.get_userid_from_token("token_dana") == "dana"
    assert auth.get_userid_from_token("token_michelle") == "michelle"

def test_get_userid_from_token_invalid(setup_auth_files):
    """Test that an unknown token returns 'guest'."""
    assert auth.get_userid_from_token("invalid_token") == "guest"

def test_get_userid_from_token_none(setup_auth_files):
    """Test that a None token returns 'guest'."""
    assert auth.get_userid_from_token(None) == "guest"

def test_get_userid_from_token_empty_string(setup_auth_files):
    """Test that an empty string token returns 'guest'."""
    assert auth.get_userid_from_token("") == "guest"


# --- Tests for get_groups_from_userid ---

def test_get_groups_from_userid_multiple_groups(setup_auth_files):
    """Test retrieving groups for a user in multiple groups."""
    groups = auth.get_groups_from_userid("dana")
    assert set(groups) == {"Group A", "Group B"}

def test_get_groups_from_userid_single_group(setup_auth_files):
    """Test retrieving groups for a user in a single group."""
    groups = auth.get_groups_from_userid("michelle")
    assert set(groups) == {"Group A"}

def test_get_groups_from_userid_guest(setup_auth_files):
    """Test retrieving groups for the 'guest' user."""
    groups = auth.get_groups_from_userid("guest")
    assert set(groups) == {"Guests"}

def test_get_groups_from_userid_unknown_user(setup_auth_files):
    """Test that an unknown userid returns the default 'Guests' list."""
    groups = auth.get_groups_from_userid("unknown_user")
    assert groups == ["Guests"]

def test_get_groups_from_userid_none_or_empty(setup_auth_files):
    """Test that a None or empty userid returns the 'Guests' list."""
    assert auth.get_groups_from_userid(None) == ["Guests"]
    assert auth.get_groups_from_userid("") == ["Guests"]


# --- Tests for verify_user_credentials ---

def test_verify_user_credentials_hashed_password(setup_auth_files):
    assert auth.verify_user_credentials("service-test", "hash-password") is True

def test_verify_user_credentials_plaintext_password(setup_auth_files):
    assert auth.verify_user_credentials("service-test", "plain-password") is True

def test_verify_user_credentials_auth_token_fallback(setup_auth_files):
    assert auth.verify_user_credentials("service-test", "token-as-pwd") is True

def test_verify_user_credentials_invalid_password(setup_auth_files):
    assert auth.verify_user_credentials("service-test", "wrong-password") is False

def test_verify_user_credentials_unknown_user(setup_auth_files):
    assert auth.verify_user_credentials("nonexistent-user", "password") is False

def test_verify_user_credentials_empty(setup_auth_files):
    assert auth.verify_user_credentials("", "") is False
    assert auth.verify_user_credentials("service-test", "") is False
    assert auth.verify_user_credentials(None, "hash-password") is False
