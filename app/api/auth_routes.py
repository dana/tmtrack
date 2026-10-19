import datetime
import os
import secrets
import urllib.parse
from flask import Blueprint, jsonify, make_response, redirect, request, current_app
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
import requests

from app.auth import get_groups_from_userid, verify_user_credentials
from app.api.utils import get_auth_info_from_request
from app.services.mongo_service import MongoService

auth_bp = Blueprint('auth_bp', __name__)
mongo_service = MongoService()


def _is_request_secure():
    """Detects whether request was made over HTTPS directly or via reverse proxy."""
    if request.is_secure:
        return True
    return request.headers.get('X-Forwarded-Proto', '').lower() == 'https'


def _get_cookie_path():
    """Returns the base cookie path (default /tmtrack in prod, / in test/local)."""
    return os.environ.get('TMTRACK_COOKIE_PATH', '/tmtrack')


@auth_bp.route('/auth/google/login', methods=['GET'])
def google_login():
    """Initiates Google OAuth 2.0 authorization code flow."""
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    redirect_uri = os.environ.get(
        "GOOGLE_OAUTH_REDIRECT_URI",
        "https://diederich.ai/tmtrack/api/auth/google/callback"
    )
    scopes = os.environ.get("GOOGLE_OAUTH_SCOPES", "openid email profile")

    if not client_id:
        return jsonify({"error": "Google OAuth is not configured on this server"}), 500

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scopes,
        "state": state,
        "nonce": nonce,
        "access_type": "online",
        "prompt": "select_account",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    response = redirect(auth_url, code=303)
    is_secure = _is_request_secure()
    # Save state:nonce in a short-lived HTTP-only cookie for verification in callback
    response.set_cookie(
        key="tmtrack_oauth_state",
        value=f"{state}:{nonce}",
        max_age=600,
        httponly=True,
        secure=is_secure,
        samesite="Lax",
        path="/",
    )
    return response


@auth_bp.route('/auth/google/callback', methods=['GET'])
def google_callback():
    """Handles the OAuth 2.0 callback from Google."""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    if error:
        return jsonify({"error": f"Google authentication error: {error}"}), 400

    if not code or not state:
        return jsonify({"error": "Missing code or state parameter"}), 400

    # Retrieve and verify state & nonce from cookie
    state_cookie = request.cookies.get("tmtrack_oauth_state")
    if not state_cookie or ":" not in state_cookie:
        return jsonify({"error": "Missing or expired OAuth state cookie"}), 400

    expected_state, expected_nonce = state_cookie.split(":", 1)
    if not secrets.compare_digest(state, expected_state):
        return jsonify({"error": "OAuth state mismatch (potential CSRF)"}), 400

    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    redirect_uri = os.environ.get(
        "GOOGLE_OAUTH_REDIRECT_URI",
        "https://diederich.ai/tmtrack/api/auth/google/callback"
    )

    # 1. Exchange code for tokens
    try:
        token_resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
    except Exception as e:
        return jsonify({"error": f"Failed to contact Google token endpoint: {e}"}), 502

    if token_resp.status_code != 200:
        return jsonify({
            "error": "Failed to exchange authorization code",
            "details": token_resp.text
        }), 400

    token_data = token_resp.json()
    id_token_jwt = token_data.get("id_token")
    if not id_token_jwt:
        return jsonify({"error": "Google token response did not contain an id_token"}), 400

    # 2. Verify Google ID Token
    try:
        req = google_requests.Request()
        id_info = id_token.verify_oauth2_token(id_token_jwt, req, client_id)
        if id_info.get("nonce") != expected_nonce:
            return jsonify({"error": "OAuth nonce mismatch"}), 400
    except Exception as e:
        return jsonify({"error": f"Token verification failed: {e}"}), 400

    email = id_info.get("email", "").strip().lower()
    email_verified = id_info.get("email_verified", False)
    if not email or not email_verified:
        return jsonify({"error": "Google account email is missing or not verified"}), 403

    # 3. Whitelist check against user_authorization
    groups = get_groups_from_userid(email)
    if not groups or groups == ["Guests"]:
        return jsonify({
            "error": "Forbidden",
            "message": f"Account '{email}' is not authorized to access TMTrack."
        }), 403

    # 4. Create authenticated session in MongoDB
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
    name = id_info.get("name", email)
    google_sub = id_info.get("sub", "")

    mongo_service.create_session(
        session_id=session_id,
        userid=email,
        email=email,
        name=name,
        google_sub=google_sub,
        expires_at=expires_at,
    )

    # 5. Set session cookie and redirect to main UI
    target_redirect = os.environ.get("TMTRACK_UI_URL", "/tmtrack/")
    response = redirect(target_redirect, code=303)
    is_secure = _is_request_secure()
    cookie_path = _get_cookie_path()

    response.set_cookie(
        key="tmtrack_session",
        value=session_id,
        max_age=365 * 24 * 3600,
        httponly=True,
        secure=is_secure,
        samesite="Lax",
        path=cookie_path,
    )
    # Clear temporary state cookie
    response.delete_cookie("tmtrack_oauth_state", path="/")
    response.headers["Cache-Control"] = "no-store"
    return response


@auth_bp.route('/auth/me', methods=['GET'])
def get_current_user():
    """Returns the current authenticated user's profile and groups."""
    userid, groups = get_auth_info_from_request()
    if not userid or userid == "guest":
        return jsonify({
            "authenticated": False,
            "userid": "guest",
            "groups": ["Guests"]
        }), 200

    name = userid
    session_id = request.cookies.get("tmtrack_session")
    if session_id:
        session = mongo_service.get_session(session_id)
        if session and session.get("name"):
            name = session["name"]

    return jsonify({
        "authenticated": True,
        "userid": userid,
        "email": userid if "@" in userid else None,
        "name": name,
        "groups": groups
    }), 200


@auth_bp.route('/auth/logout', methods=['GET', 'POST'])
def logout():
    """Clears the active session and logs out."""
    session_id = request.cookies.get("tmtrack_session")
    if session_id:
        mongo_service.delete_session(session_id)

    target_redirect = os.environ.get("TMTRACK_UI_URL", "/tmtrack/")
    response = redirect(target_redirect, code=303) if request.method == 'GET' else jsonify({"status": "logged_out"})
    cookie_path = _get_cookie_path()
    response.delete_cookie("tmtrack_session", path=cookie_path)
    response.headers["Cache-Control"] = "no-store"
    return response


@auth_bp.route("/auth/dev-login", methods=["GET"])
def dev_login():
    """
    Local development login bypass. Only enabled when FLASK_ENV=development or FLASK_DEBUG is enabled.
    Sets a local session cookie for the requested userid (defaults to diederich@gmail.com).
    """
    if os.environ.get("FLASK_ENV") != "development" and os.environ.get("FLASK_DEBUG") not in ("1", "true", "True"):
        return jsonify({"error": "Dev login is only available in development mode"}), 403

    userid = request.args.get("userid", "diederich@gmail.com")
    session_id = secrets.token_urlsafe(32)
    mongo_service.create_session(
        session_id=session_id,
        userid=userid,
        email=userid,
        name=userid.split("@")[0].title()
    )

    cookie_path = _get_cookie_path()
    target_next = request.args.get("next", "/")
    resp = redirect(target_next, code=303)
    resp.set_cookie(
        "tmtrack_session",
        session_id,
        max_age=7 * 24 * 3600,
        secure=_is_request_secure(),
        httponly=True,
        samesite="Lax",
        path=cookie_path
    )
    return resp


@auth_bp.route("/auth/login", methods=["POST"])
def password_login():
    """
    Authenticates a user or service account using account name and password.
    Accepts JSON body ({"username": "...", "password": "..."}) or Form POST.
    Falls back to HTTP Basic Auth if credentials are not in request body.
    Sets the "tmtrack_session" cookie on success and returns session info or redirects.
    """
    data = request.get_json(silent=True) or {}
    username = (
        data.get("username")
        or data.get("userid")
        or request.form.get("username")
        or request.form.get("userid")
    )
    password = data.get("password") or request.form.get("password")

    # Fall back to HTTP Basic Auth if credentials not present in body
    if (not username or not password) and request.authorization:
        username = request.authorization.username
        password = request.authorization.password

    if not username or not password:
        return jsonify({"error": "Account name and password are required"}), 400

    username = username.strip()
    if not verify_user_credentials(username, password):
        return jsonify({"error": "Invalid account name or password"}), 401

    groups = get_groups_from_userid(username)
    if not groups or groups == ["Guests"]:
        return jsonify({
            "error": "Forbidden",
            "message": f"Account '{username}' is not authorized to access TMTrack."
        }), 403

    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
    mongo_service.create_session(
        session_id=session_id,
        userid=username,
        email=username if "@" in username else None,
        name=username,
        expires_at=expires_at,
    )

    target_redirect = request.args.get("next") or (request.form.get("next") if request.form else None)
    cookie_path = _get_cookie_path()
    is_secure = _is_request_secure()

    if target_redirect:
        response = redirect(target_redirect, code=303)
    else:
        response = make_response(jsonify({
            "authenticated": True,
            "userid": username,
            "name": username,
            "groups": groups,
            "session_id": session_id,
        }), 200)

    response.set_cookie(
        key="tmtrack_session",
        value=session_id,
        max_age=365 * 24 * 3600,
        httponly=True,
        secure=is_secure,
        samesite="Lax",
        path=cookie_path,
    )
    response.headers["Cache-Control"] = "no-store"
    return response
