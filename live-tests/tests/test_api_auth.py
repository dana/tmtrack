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

def test_malformed_auth_header_bearer_without_token_defaults_to_guest(creds):
    url = f"{creds['api_url']}/categories"
    headers = {"Authorization": "Bearer"}
    resp = httpx.get(url, headers=headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("userid") == "guest"

def test_malformed_auth_header_unsupported_scheme_defaults_to_guest(creds):
    url = f"{creds['api_url']}/categories"
    headers = {"Authorization": "Basic dXNlcjpwYXNz"}
    resp = httpx.get(url, headers=headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("userid") == "guest"

def test_authenticated_test_user_identity(creds, auth_headers):
    url = f"{creds['api_url']}/categories"
    resp = httpx.get(url, headers=auth_headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("userid") == creds["userid"]
    groups = data.get("groups", [])
    assert "Guests" in groups
    assert "The Odd Squad" in groups
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

def test_list_users_endpoint_contract(creds, auth_headers):
    url = f"{creds['api_url']}/users"
    resp = httpx.get(url, headers=auth_headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("userid") == creds["userid"]
    # Backend explicitly returns allowed_users = ["dana", "michelle"]
    assert data.get("users") == ["dana", "michelle"]

def test_group_tasks_isolation_enforces_tenant_boundary(creds, auth_headers):
    """
    Asserts that GET /tasks only returns tasks belonging to users in the caller's groups
    and never leaks tasks from production users ('dana', 'michelle').
    """
    url = f"{creds['api_url']}/tasks"
    resp = httpx.get(url, headers=auth_headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "success"
    tasks = data.get("tasks", [])
    
    # Allowed userids for TemporaryHero groups: guest, TemporaryHero, WanderingPixel, JustBrowsing, EphemeralEnigma
    for task in tasks:
        task_owner = task.get("userid")
        assert task_owner not in ("dana", "michelle"), (
            f"Security violation: task {task.get('task_id')} owned by '{task_owner}' leaked to '{creds['userid']}'"
        )
