import datetime
import json
from unittest.mock import patch, MagicMock
import pytest
from app.services.mongo_service import MongoService


@pytest.fixture
def mongo_svc(app):
    with app.app_context():
        svc = MongoService()
        svc.clear_sessions_collection()
        yield svc
        svc.clear_sessions_collection()


def test_google_login_redirect(client, monkeypatch):
    """Test login route redirects to accounts.google.com with state and nonce cookies."""
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "https://diederich.ai/tmtrack/api/auth/google/callback")
    monkeypatch.setenv("GOOGLE_OAUTH_SCOPES", "openid email profile")

    response = client.get('/api/auth/google/login')
    assert response.status_code == 303
    assert "https://accounts.google.com/o/oauth2/v2/auth" in response.headers["Location"]
    assert "client_id=test-client-id" in response.headers["Location"]
    assert "tmtrack_oauth_state" in response.headers.get("Set-Cookie", "")


def test_google_login_not_configured(client, monkeypatch):
    """Test login route returns 500 when client ID is not set."""
    monkeypatch.delenv("GOOGLE_OAUTH_CLIENT_ID", raising=False)
    response = client.get('/api/auth/google/login')
    assert response.status_code == 500
    assert "not configured" in response.get_json()["error"]


def test_google_callback_missing_params(client):
    """Test callback fails when code or state is missing."""
    resp = client.get('/api/auth/google/callback')
    assert resp.status_code == 400


def test_google_callback_state_mismatch(client):
    """Test callback rejects request with state mismatch."""
    client.set_cookie('tmtrack_oauth_state', 'expected_state:expected_nonce', domain='localhost', path='/')
    resp = client.get('/api/auth/google/callback?code=fake_code&state=wrong_state')
    assert resp.status_code == 400
    assert "mismatch" in resp.get_json()["error"]


def test_google_callback_success(client, mongo_svc, monkeypatch):
    """Test successful Google OAuth token exchange and session creation."""
    client_id = "test-client-id.apps.googleusercontent.com"
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", client_id)
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "https://diederich.ai/tmtrack/api/auth/google/callback")

    state = "valid_state_123"
    nonce = "valid_nonce_456"
    client.set_cookie('tmtrack_oauth_state', f"{state}:{nonce}", domain='localhost', path='/')

    # Mock token exchange
    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"id_token": "mocked.jwt.token"}

    # Mock id_token verification
    mock_id_info = {
        "sub": "google-10928374",
        "email": "diederich@gmail.com",
        "email_verified": True,
        "name": "Dana Diederich",
        "nonce": nonce,
    }

    with patch("requests.post", return_value=mock_token_resp), \
         patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        
        response = client.get(f'/api/auth/google/callback?code=google_auth_code_xyz&state={state}')
        assert response.status_code == 303
        assert response.headers["Location"] == "/tmtrack/"
        assert "tmtrack_session=" in response.headers.get("Set-Cookie", "")

        # Verify session is persisted in MongoDB
        cookies = response.headers.getlist("Set-Cookie")
        session_cookie = [c for c in cookies if c.startswith("tmtrack_session=")][0]
        session_id = session_cookie.split(";")[0].split("=")[1]
        
        saved_session = mongo_svc.get_session(session_id)
        assert saved_session is not None
        assert saved_session["userid"] == "diederich@gmail.com"
        assert saved_session["email"] == "diederich@gmail.com"
        assert saved_session["name"] == "Dana Diederich"


def test_google_callback_unauthorized_email(client, mongo_svc, monkeypatch):
    """Test callback rejects verified Google emails that are not in the whitelist."""
    client_id = "test-client-id.apps.googleusercontent.com"
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", client_id)
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "test-secret")

    state = "state_unauth"
    nonce = "nonce_unauth"
    client.set_cookie('tmtrack_oauth_state', f"{state}:{nonce}", domain='localhost', path='/')

    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"id_token": "mocked.jwt.token"}

    mock_id_info = {
        "sub": "stranger-999",
        "email": "unauthorized_stranger@gmail.com",
        "email_verified": True,
        "name": "Stranger",
        "nonce": nonce,
    }

    with patch("requests.post", return_value=mock_token_resp), \
         patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        
        response = client.get(f'/api/auth/google/callback?code=code_stranger&state={state}')
        assert response.status_code == 403
        data = response.get_json()
        assert data["error"] == "Forbidden"
        assert "not authorized" in data["message"]


def test_me_endpoint_unauthenticated(client):
    """Test /auth/me returns guest when no auth is provided."""
    resp = client.get('/api/auth/me')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["authenticated"] is False
    assert data["userid"] == "guest"


def test_me_endpoint_session_cookie(client, mongo_svc):
    """Test /auth/me returns user details when session cookie is provided."""
    session_id = "test_active_session_123"
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
    mongo_svc.create_session(
        session_id=session_id,
        userid="diederich@gmail.com",
        email="diederich@gmail.com",
        name="Dana Diederich",
        expires_at=expires_at
    )

    client.set_cookie('tmtrack_session', session_id, domain='localhost', path='/')
    resp = client.get('/api/auth/me')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["authenticated"] is True
    assert data["userid"] == "diederich@gmail.com"
    assert data["name"] == "Dana Diederich"
    assert "Administrators" in data["groups"]


def test_me_endpoint_bearer_token(client):
    """Test /auth/me returns user details when Bearer token is provided."""
    resp = client.get('/api/auth/me', headers={"Authorization": "Bearer 730ea935edf1dd98eef8"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["authenticated"] is True
    assert data["userid"] == "diederich@gmail.com"
    assert "Hunny Bunnies" in data["groups"]


def test_logout(client, mongo_svc):
    """Test logout removes session and clears cookie."""
    session_id = "test_session_to_delete"
    mongo_svc.create_session(
        session_id=session_id,
        userid="diederich@gmail.com",
        email="diederich@gmail.com"
    )

    client.set_cookie('tmtrack_session', session_id, domain='localhost', path='/')
    resp = client.post('/api/auth/logout')
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "logged_out"
    assert mongo_svc.get_session(session_id) is None


def test_dev_login_disabled_by_default(client, monkeypatch):
    """Test dev-login returns 403 when not in development mode."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("FLASK_DEBUG", raising=False)
    resp = client.get("/api/auth/dev-login?userid=diederich@gmail.com")
    assert resp.status_code == 403


def test_dev_login_success(client, monkeypatch, mongo_svc):
    """Test dev-login creates session and sets cookie when FLASK_DEBUG is enabled."""
    monkeypatch.setenv("FLASK_DEBUG", "1")
    resp = client.get("/api/auth/dev-login?userid=diederich@gmail.com&next=/tasks")
    assert resp.status_code == 303
    assert resp.headers["Location"] == "/tasks"
    assert "tmtrack_session" in resp.headers.get("Set-Cookie", "")


def test_password_login_success_json(client, mongo_svc):
    resp = client.post("/api/auth/login", json={
        "username": "service-agent",
        "password": "svc-tmtrack-b7ad2fad77801a35"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["authenticated"] is True
    assert data["userid"] == "service-agent"
    assert "ServiceAccounts" in data["groups"]
    assert "tmtrack_session" in resp.headers.get("Set-Cookie", "")


def test_password_login_success_form_with_redirect(client, mongo_svc):
    resp = client.post("/api/auth/login", data={
        "username": "service-agent",
        "password": "svc-tmtrack-b7ad2fad77801a35",
        "next": "/tmtrack/"
    })
    assert resp.status_code == 303
    assert resp.headers["Location"] == "/tmtrack/"
    assert "tmtrack_session" in resp.headers.get("Set-Cookie", "")


def test_password_login_invalid_password(client):
    resp = client.post("/api/auth/login", json={
        "username": "service-agent",
        "password": "wrong-password"
    })
    assert resp.status_code == 401
    assert "Invalid" in resp.get_json()["error"]


def test_password_login_missing_fields(client):
    resp = client.post("/api/auth/login", json={"username": "service-agent"})
    assert resp.status_code == 400


def test_password_login_basic_auth(client):
    import base64
    creds = base64.b64encode(b"service-agent:svc-tmtrack-b7ad2fad77801a35").decode()
    resp = client.get("/api/v1/users", headers={"Authorization": f"Basic {creds}"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["userid"] == "service-agent"
    assert "ServiceAccounts" in data["groups"]


def test_service_account_visibility_isolation(client, mongo_svc):
    # 1. Dana logs in
    session_dana = "session_dana_test"
    mongo_svc.create_session(session_id=session_dana, userid="diederich@gmail.com", email="diederich@gmail.com")
    client.set_cookie("tmtrack_session", session_dana, domain="localhost", path="/")
    resp_dana = client.get("/api/v1/users")
    assert resp_dana.status_code == 200
    users_dana = resp_dana.get_json()["users"]
    assert "diederich@gmail.com" in users_dana
    assert "service-agent" not in users_dana
    assert "service-automation" not in users_dana

    # 2. Service agent logs in
    session_svc = "session_svc_test"
    mongo_svc.create_session(session_id=session_svc, userid="service-agent", email="service-agent")
    client.set_cookie("tmtrack_session", session_svc, domain="localhost", path="/")
    resp_svc = client.get("/api/v1/users")
    assert resp_svc.status_code == 200
    users_svc = resp_svc.get_json()["users"]
    assert "service-agent" in users_svc
    assert "diederich@gmail.com" not in users_svc
