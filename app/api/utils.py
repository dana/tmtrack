from flask import request
from app.auth import get_userid_from_token, get_groups_from_userid

def get_auth_info_from_request():
    """
    Parses the 'Authorization: Bearer <token>' header from the current request
    and returns the corresponding userid and group memberships.

    Returns:
        A tuple containing (userid: str, groups: list[str]).
        Defaults to "guest" and ["Guests"] if the token is missing or invalid.
    """
    auth_header = request.headers.get('Authorization')
    token = None
    if auth_header and auth_header.startswith('Bearer '):
        # Split 'Bearer <token>' and get the token part
        token = auth_header.split(' ')[-1]
    
    userid = get_userid_from_token(token)
    groups = get_groups_from_userid(userid)
    
    return userid, groups
