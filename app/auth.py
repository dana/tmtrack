import json
from pathlib import Path

# --- Data Structures ---
# These will be populated once when the module is first imported.
_token_to_userid_map = {}
_userid_to_groups_map = {}

# --- Helper function to load and process data ---
def _load_auth_data():
    """
    Loads authentication and authorization data from JSON files.
    This function is executed once when the module is loaded.
    It is intended for internal use only.
    """
    global _token_to_userid_map, _userid_to_groups_map
    
    # --- Load Authentication Data ---
    auth_file_path = Path(__file__).parent.parent / 'user_authentication.json'
    try:
        with open(auth_file_path, 'r') as f:
            auth_data = json.load(f)
            # Transform the list into a dictionary for efficient token lookups
            _token_to_userid_map = {
                item['auth_token']: item['userid'] for item in auth_data
            }
        print(f"Successfully loaded {_token_to_userid_map.keys().__len__()} user authentication tokens.")
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"WARNING: Could not load or parse user_authentication.json: {e}. Authentication will not work.")
        _token_to_userid_map = {}

    # --- Load Authorization Data ---
    authz_file_path = Path(__file__).parent.parent / 'user_authorization.json'
    try:
        with open(authz_file_path, 'r') as f:
            authz_data = json.load(f)
            # Transform the group-centric list into a user-centric dictionary for efficient lookups
            temp_map = {}
            for group in authz_data:
                group_name = group['group_name']
                for userid in group['userids']:
                    if userid not in temp_map:
                        temp_map[userid] = []
                    temp_map[userid].append(group_name)
            _userid_to_groups_map = temp_map
        print(f"Successfully loaded authorizations for {_userid_to_groups_map.keys().__len__()} users.")
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"WARNING: Could not load or parse user_authorization.json: {e}. Authorization will not work.")
        _userid_to_groups_map = {}


# --- Publicly accessible methods ---

def get_userid_from_token(auth_token: str | None) -> str:
    """
    Finds the userid associated with a given authentication token.

    This function looks up the token in the pre-loaded authentication data.
    The data is loaded from user_authentication.json only once at startup.

    Args:
        auth_token: The authentication token string to look up.

    Returns:
        The userid (e.g., "dana") if the token is found.
        The string "guest" if the token is None, empty, or not found.
    """
    if not auth_token:
        return "guest"
    return _token_to_userid_map.get(auth_token, "guest")


def get_groups_from_userid(userid: str | None) -> list[str]:
    """
    Retrieves the list of group names a user belongs to.

    This function looks up the userid in the pre-loaded authorization data.
    The data is loaded from user_authorization.json only once at startup.

    Args:
        userid: The userid string to look up.

    Returns:
        A list of group names (e.g., ["Hunny Bunnies", "Administrators"]) if the user is found.
        A list containing only "Guests" (i.e., ["Guests"]) if the userid is None, empty, or not found.
    """
    if not userid:
        return ["Guests"]
    # The .get() method with a default value is perfect for this.
    return _userid_to_groups_map.get(userid, ["Guests"])


# --- Main execution block for the module ---
# This code runs once when the Flask server imports this module.
_load_auth_data()
