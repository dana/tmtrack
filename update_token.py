
import argparse
import json

def update_auth_token(new_token_part):
    """
    Reads user_authentication.json, appends a string to the auth_token,
    and writes the updated JSON back to the file.
    """
    try:
        with open('user_authentication.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: user_authentication.json not found.")
        return
    except json.JSONDecodeError:
        print("Error: Could not decode JSON from user_authentication.json.")
        return

    if not isinstance(data, list):
        print("Error: user_authentication.json is not a list of users.")
        return

    for user in data:
        if 'auth_token' in user and isinstance(user['auth_token'], str):
            user['auth_token'] += new_token_part
        else:
            print(f"Warning: 'auth_token' not found or not a string for user {user.get('userid', '(unknown)')}.")


    with open('user_authentication.json', 'w') as f:
        json.dump(data, f, indent=4)

    print(f"Successfully updated auth_token in user_authentication.json.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Append a string to the auth_token in user_authentication.json.'
    )
    parser.add_argument(
        'token_part',
        type=str,
        help='The string to append to the auth_token.'
    )
    args = parser.parse_args()
    update_auth_token(args.token_part)
