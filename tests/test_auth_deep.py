import json
import pytest
from app import auth
from app.api.utils import get_auth_info_from_request


def test_get_userids_in_groups():
    """Test resolving multiple groups to a unique set of user IDs."""
    users = auth.get_userids_in_groups(["Hunny Bunnies", "Administrators"])
    assert "diederich@gmail.com" in users
    assert "msdiederich@gmail.com" in users


def test_get_userids_in_empty_groups():
    """Empty group list returns an empty set."""
    assert auth.get_userids_in_groups([]) == set()
    assert auth.get_userids_in_groups(["NonExistentGroup"]) == set()


def test_get_auth_info_from_request_with_valid_bearer(app):
    """Request with valid Authorization: Bearer <token> resolves userid and groups."""
    with app.test_request_context(headers={"Authorization": "Bearer 730ea935edf1dd98eef8"}):
        userid, groups = get_auth_info_from_request()
        assert userid == "diederich@gmail.com"
        assert "Administrators" in groups


def test_get_auth_info_from_request_missing_header(app):
    """Request without Authorization header defaults to guest."""
    with app.test_request_context():
        userid, groups = get_auth_info_from_request()
        assert userid == "guest"
        assert "Guests" in groups


def test_get_auth_info_from_request_malformed_header(app):
    """Request with malformed Authorization header defaults to guest."""
    with app.test_request_context(headers={"Authorization": "NotBearer 12345"}):
        userid, groups = get_auth_info_from_request()
        assert userid == "guest"


def test_get_auth_info_from_request_empty_token(app):
    """Request with 'Bearer ' and no token defaults to guest."""
    with app.test_request_context(headers={"Authorization": "Bearer "}):
        userid, groups = get_auth_info_from_request()
        assert userid == "guest"


def test_auth_missing_files_fallback(tmp_path, monkeypatch, capsys):
    """When auth files are missing, _load_auth_data falls back to empty maps."""
    import importlib
    monkeypatch.setattr(auth.Path, "parent", tmp_path, raising=False)
    importlib.reload(auth)
    
    assert auth._token_to_userid_map == {}
    assert auth._userid_to_groups_map == {}
    assert auth.get_userid_from_token("any_token") == "guest"
    assert auth.get_groups_from_userid("any_user") == ["Guests"]
    
    # Restore
    monkeypatch.undo()
    importlib.reload(auth)
