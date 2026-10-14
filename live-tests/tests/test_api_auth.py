import httpx
import pytest

def test_unauthenticated_request_defaults_to_guest(creds):
    url = f"{creds['api_url']}/categories"
    resp = httpx.get(url, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("userid") == "guest"
    assert "Guests" in data.get("groups", [])
    assert "Administrators" not in data.get("groups", [])

def test_invalid_bearer_token_defaults_to_guest(creds):
    url = f"{creds['api_url']}/categories"
    headers = {"Authorization": "Bearer non_existent_token_xyz123"}
    resp = httpx.get(url, headers=headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("userid") == "guest"
    assert "Guests" in data.get("groups", [])
    assert "Administrators" not in data.get("groups", [])

def test_authenticated_test_user_identity(creds, auth_headers):
    url = f"{creds['api_url']}/categories"
    resp = httpx.get(url, headers=auth_headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("userid") == creds["userid"]
    groups = data.get("groups", [])
    assert "Guests" in groups
    assert "The Odd Squad" in groups
    assert "Very Hard Workers Doing Very Serious Work" in groups
    # Critical security boundary: test user must NOT belong to admin or production user groups
    assert "Administrators" not in groups
    assert "Hunny Bunnies" not in groups

def test_alternate_test_user_identity(creds, alt_headers):
    url = f"{creds['api_url']}/categories"
    resp = httpx.get(url, headers=alt_headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("userid") == creds["alt_userid"]
    groups = data.get("groups", [])
    assert "Guests" in groups
    assert "A Wrinkle in Time" in groups
    assert "Administrators" not in groups

def test_list_users_endpoint(creds, auth_headers):
    url = f"{creds['api_url']}/users"
    resp = httpx.get(url, headers=auth_headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("userid") == creds["userid"]
    assert isinstance(data.get("users"), list)
