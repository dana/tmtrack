import json
import pytest
from app import auth

# Define sample data for testing
SAMPLE_AUTH_DATA = [
    {"userid": "dana", "auth_token": "token_dana"},
    {"userid": "michelle", "auth_token": "token_michelle"}
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
    This ensures tests are isolated from the real JSON files and are repeatable.
    """
    # Create temporary files
    auth_file = tmp_path / "user_authentication.json"
    authz_file = tmp_path / "user_authorization.json"
    
    with open(auth_file, "w") as f:
        json.dump(SAMPLE_AUTH_DATA, f)
        
    with open(authz_file, "w") as f:
        json.dump(SAMPLE_AUTHZ_DATA, f)

    # Use monkeypatch to make the auth module look for files in our temp directory
    # The Path object in auth.py is relative to `__file__`, so we patch its parent's parent
    monkeypatch.setattr(auth.Path, "parent", tmp_path, raising=False)

    # Reload the auth module to force it to re-run _load_auth_data()
    # This is a bit of a trick, but essential for testing module-level logic
    import importlib
    importlib.reload(auth)
    
    yield
    
    # Teardown: Reload the auth module again without the patch to restore state
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
    # Use set comparison to be order-independent
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
