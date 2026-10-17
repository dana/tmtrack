import datetime
from flask import request
from app.auth import get_userid_from_token, get_groups_from_userid, verify_user_credentials
from app.services.mongo_service import MongoService

mongo_service = MongoService()

def get_auth_info_from_request():
    """
    Resolves authenticated identity and group memberships from the current request.
    
    Resolution order:
    1. "tmtrack_session" cookie validated against MongoDB tmtrack_sessions.
    2. "Authorization: Bearer <token>" header looked up in user_authentication.json.
    3. "Authorization: Basic <base64>" header verified against user credentials.
    4. Defaults to "guest" and ["Guests"] if unauthenticated or session invalid.

    Returns:
        A tuple containing (userid: str, groups: list[str]).
    """
    # 1. Cookie-based Google OAuth / Service Account session
    session_id = request.cookies.get("tmtrack_session")
    if session_id:
        try:
            session = mongo_service.get_session(session_id)
            if session and session.get("userid"):
                expires_at = session.get("expires_at")
                # If expires_at is timezone-naive, treat as UTC
                if expires_at and expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
                now = datetime.datetime.now(datetime.timezone.utc)
                if not expires_at or expires_at > now:
                    userid = session["userid"]
                    groups = get_groups_from_userid(userid)
                    return userid, groups
        except Exception as e:
            print(f"Warning: Failed to validate tmtrack_session: {e}")

    # 2. Bearer token (static service accounts / test tokens)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[-1]
        if token:
            userid = get_userid_from_token(token)
            if userid and userid != "guest":
                groups = get_groups_from_userid(userid)
                return userid, groups

    # 3. HTTP Basic Auth (service accounts / API clients)
    if request.authorization and request.authorization.username and request.authorization.password:
        u = request.authorization.username.strip()
        p = request.authorization.password
        if verify_user_credentials(u, p):
            groups = get_groups_from_userid(u)
            if groups and groups != ["Guests"]:
                return u, groups

    return "guest", ["Guests"]
