import httpx
import pytest

def test_unauthenticated_request_defaults_to_guest(creds):
    url = f"{creds['api_url']}/categories"
    resp = httpx.get(url, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('userid') == 'guest'
    assert 'Guests' in data.get('groups', [])
    assert 'Administrators' not in data.get('groups', [])

def test_invalid_bearer_token_defaults_to_guest(creds):
    url = f"{creds['api_url']}/categories"
    headers = {'Authorization': 'Bearer non_existent_token_xyz123'}
    resp = httpx.get(url, headers=headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('userid') == 'guest'
    assert 'Guests' in data.get('groups', [])
    assert 'Administrators' not in data.get('groups', [])

def test_malformed_auth_header_bearer_without_token_defaults_to_guest(creds):
    url = f"{creds['api_url']}/categories"
    headers = {'Authorization': 'Bearer'}
    resp = httpx.get(url, headers=headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('userid') == 'guest'

def test_malformed_auth_header_unsupported_scheme_defaults_to_guest(creds):
    url = f"{creds['api_url']}/categories"
    headers = {'Authorization': 'Digest dXNlcjpwYXNz'}
    resp = httpx.get(url, headers=headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('userid') == 'guest'

def test_authenticated_test_user_identity(creds, auth_headers):
    url = f"{creds['api_url']}/categories"
    resp = httpx.get(url, headers=auth_headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('userid') == creds['userid']
    groups = data.get('groups', [])
    assert 'ServiceAccounts' in groups
    # Critical security boundary: test user must NOT belong to admin or production human groups
    assert 'Administrators' not in groups
    assert 'Hunny Bunnies' not in groups

def test_alternate_test_user_identity(creds, alt_headers):
    url = f"{creds['api_url']}/categories"
    resp = httpx.get(url, headers=alt_headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('userid') == creds['alt_userid']
    groups = data.get('groups', [])
    assert 'ServiceAccounts' in groups
    assert 'Administrators' not in groups
    assert 'Hunny Bunnies' not in groups

def test_list_users_endpoint_contract(creds, auth_headers):
    url = f"{creds['api_url']}/users"
    resp = httpx.get(url, headers=auth_headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('userid') == creds['userid']
    # Scoped strictly to ServiceAccounts group members
    assert data.get('users') == ['service-agent', 'service-automation']

def test_group_tasks_isolation_enforces_tenant_boundary(creds, auth_headers):
    """
    Asserts that GET /tasks only returns tasks belonging to users in the caller's groups
    and never leaks tasks from production human users ('diederich@gmail.com', 'msdiederich@gmail.com').
    """
    url = f"{creds['api_url']}/tasks"
    resp = httpx.get(url, headers=auth_headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('status') == 'success'
    tasks = data.get('tasks', [])
    
    for task in tasks:
        task_owner = task.get('userid')
        assert task_owner not in ('diederich@gmail.com', 'msdiederich@gmail.com', 'dana', 'michelle'), (
            f"Security violation: task {task.get('task_id')} owned by '{task_owner}' leaked to '{creds['userid']}'"
        )

def test_service_account_login_success(creds):
    if not creds.get('password'):
        pytest.skip('TMTRACK_PASSWORD not configured')
    login_url = f"{creds['auth_api_url']}/login"
    resp = httpx.post(login_url, json={'username': creds['userid'], 'password': creds['password']}, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('authenticated') is True
    assert data.get('userid') == creds['userid']
    assert 'ServiceAccounts' in data.get('groups', [])
    assert 'tmtrack_session' in resp.cookies

def test_service_account_login_invalid_password(creds):
    login_url = f"{creds['auth_api_url']}/login"
    resp = httpx.post(login_url, json={'username': creds['userid'], 'password': 'wrong_password_xyz'}, timeout=10.0)
    assert resp.status_code == 401
    assert 'Invalid account name or password' in resp.json().get('error', '')

def test_basic_auth_valid_credentials(creds, basic_auth_headers):
    url = f"{creds['api_url']}/users"
    resp = httpx.get(url, headers=basic_auth_headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('userid') == creds['userid']
    assert 'ServiceAccounts' in data.get('groups', [])

def test_basic_auth_invalid_credentials_defaults_to_guest(creds):
    import base64
    url = f"{creds['api_url']}/users"
    bad_pair = f"{creds['userid']}:bad_password_xyz"
    bad_headers = {'Authorization': f'Basic {base64.b64encode(bad_pair.encode()).decode()}'}
    resp = httpx.get(url, headers=bad_headers, timeout=10.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('userid') == 'guest'
    assert 'Guests' in data.get('groups', [])
