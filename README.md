# tmtrack: Time Tracker REST API

`tmtrack` is a modern Flask-based REST API for tracking daily tasks. It connects to a MongoDB database to store task information, allowing users to create, modify, and manage their tasks.

## Features

*   **Task Creation:** Create new task entries with required and optional attributes.
*   **Task Modification:** Update existing task details based on `task_id`.
*   **MongoDB Integration:** Stores task data in a MongoDB database.
*   **API Validation:** Ensures data types and required fields are correct.
*   **UUID Generation:** Automatically assigns unique IDs to new tasks.
*   **File-Based Auth:** Simple, file-based authentication and authorization system.

## Technologies Used

*   Python 3.10+
*   Flask
*   PyMongo
*   MongoDB
*   Tox (for testing)
*   UWSGI (for deployment)

## Getting Started

### Prerequisites

*   Python 3.10+
*   **MongoDB installed and running on `localhost:27017`**
*   `pyenv` (recommended for managing Python versions, optional)

### MongoDB Installation on Ubuntu 24.04 (Noble Numbat)

Follow these steps to install MongoDB Community Edition on your Ubuntu 24.04 system. These instructions are adapted from the official MongoDB documentation.

1.  **Import the MongoDB GPG Key:**
    ```bash
    curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
       sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg \
       --dearmor
    ```

2.  **Create the List File for MongoDB:**
    ```bash
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
    ```

3.  **Reload Local Package Database:**
    ```bash
    sudo apt update
    ```

4.  **Install MongoDB Packages:**
    ```bash
    sudo apt install -y mongodb-org
    ```

5.  **Start MongoDB:**
    ```bash
    sudo systemctl start mongod
    ```

6.  **Verify MongoDB is Running:**
    ```bash
    sudo systemctl status mongod
    ```
    You should see `active (running)`.

7.  **Enable MongoDB to Start on Boot (Optional but recommended):**
    ```bash
    sudo systemctl enable mongod
    ```

### Application Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/tmtrack.git
    cd tmtrack
    ```

2.  **Set up a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application (with `flask run`)

1.  **Ensure MongoDB is running** (see "Start MongoDB" step above).

2.  **Set Flask environment variables:**
    ```bash
    export FLASK_APP=app/__init__.py
    export FLASK_ENV=development
    ```
    *   `FLASK_APP`: Tells Flask where your main application instance is.
    *   `FLASK_ENV`: Sets the environment (e.g., `development` enables debug mode).

3.  **Run the Flask development server:**
    ```bash
    flask run
    ```
    The API will be available at `http://127.0.0.1:5000`.

## Docker

This project includes a `Dockerfile` to build and run the application in a containerized environment.

### Prerequisites

*   Docker installed and running.

### Building the Docker Image

1.  **Build the image:**
    ```bash
    docker build -t tmtrack .
    ```

### Running the Docker Container

1.  **Run the container:**
    ```bash
    docker run -p 5000:5000 --network="host" tmtrack
    ```
    *   `-p 5000:5000`: Maps port 5000 on the host to port 5000 in the container.
    *   `--network="host"`: Connects the container to the host's network. This is necessary for the application to connect to the MongoDB instance running on `localhost`.

The API will be available at `http://127.0.0.1:5000`.

## Testing

The project uses `tox` for comprehensive testing against a **live MongoDB instance**.

1.  **Ensure MongoDB is running** (see "Start MongoDB" step above).
2.  **Install `tox`** (if not already installed via `pip install -r requirements.txt`):
    ```bash
    pip install tox
    ```
3.  **Run tests:**
    ```bash
    tox
    ```
    If you want to run `pytest` directly (after activating your virtual environment and installing `pytest`):
    ```bash
    pytest tests/
    ```

## Authentication and Authorization

This application uses a simple, file-based system for managing user access. On startup, the server reads two JSON files from the project's root directory. **Any changes to these files require a server restart to take effect.**

To make an authenticated request, the client must pass an `Authorization` header with a bearer token.

**Example Header:**
`Authorization: Bearer 730ea935edf1dd98eef8`

If a valid token is provided, all API responses will include `userid` and `groups` fields identifying the authenticated user. If no token or an invalid token is provided, the user is treated as `"guest"`.

### Authentication (`user_authentication.json`)

This file maps user authentication tokens to user IDs. To make an authenticated request, a client would typically pass their token in a request header (e.g., `Authorization: Bearer <token>`).

The file format is a list of objects, each with a `userid` and an `auth_token`:
```json
[
    {
        "userid": "dana",
        "auth_token": "730ea935edf1dd98eef8"
    },
    {
        "userid": "michelle",
        "auth_token": "330829f6cb0b17ff21f5"
    }
]

Within the application, you can get a user's ID from a token by calling a helper method:

from app.auth import get_userid_from_token

# Example usage within a Flask route:
# auth_header = request.headers.get('Authorization')
# token = auth_header.split(" ") if auth_header else None
# current_user_id = get_userid_from_token(token)  # Returns "dana" or "guest"

Authorization (user_authorization.json)
This file maps groups to lists of user IDs. It defines "who is in what group."
The file format is a list of group objects:


[
    {
        "group_name": "Hunny Bunnies",
        "userids": ["dana", "michelle"]
    },
    {
        "group_name": "Administrators",
        "userids": ["dana"]
    },
    {
        "group_name": "Guests",
        "userids": ["guest"]
    }
]
Within the application, you can get a user's group memberships from their user ID:

from app.auth import get_groups_from_userid

# Example usage:
# dana_groups = get_groups_from_userid("dana") 
# # Returns ['Hunny Bunnies', 'Administrators']
#
# guest_groups = get_groups_from_userid("some_unknown_user") 
# # Returns ['Guests']

API Endpoints
1. Create a New Task
URL: /api/v1/tasks
Method: POST
Content-Type: application/json
Successful Response (201 Created):


{
    "userid": "dana",
    "groups": ["Hunny Bunnies", "Administrators"],
    "status": "success",
    "message": "Task created successfully",
    "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
}

Curl Example (Create):


curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 730ea935edf1dd98eef8" \
  -d '{
    "userid": "curluser1",
    "date": "2023-10-27",
    "task_name": "Review documentation",
    "category": "Documentation",
    "expected_hours": 2.0
}' http://127.0.0.1:5000/api/v1/tasks

2. Modify an Existing Task
URL: /api/v1/tasks/<task_id>
Method: PUT
Content-Type: application/json
Successful Response (200 OK):


{
    "userid": "michelle",
    "groups": ["Hunny Bunnies"],
    "status": "success",
    "message": "Task updated successfully",
    "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
}


Curl Example (Modify):


curl -X PUT \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 330829f6cb0b17ff21f5" \
  -d '{"actual_hours": 2.5}' \
  http://127.0.0.1:5000/api/v1/tasks/YOUR_TASK_ID

3. Get a Single Task
URL: /api/v1/tasks/<task_id>
Method: GET
Successful Response (200 OK):


{
    "userid": "guest",
    "groups": ["Guests"],
    "status": "success",
    "task": {
        "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
        "userid": "curluser1",
        "date": "2023-10-27",
        "task_name": "Review documentation",
        "category": "Documentation",
        "expected_hours": 2.0,
        "created_at": "...",
        "updated_at": "..."
    }
}

Curl Example (Get Single as Guest):
code
Bash
curl http://127.0.0.1:5000/api/v1/tasks/YOUR_TASK_ID
4. Get All Tasks
URL: /api/v1/tasks
Method: GET
Curl Example (Get All):
code
Bash
curl -H "Authorization: Bearer 730ea935edf1dd98eef8" http://127.0.0.1:5000/api/v1/tasks
5. Get Users
URL: /api/v1/users
Method: GET
Successful Response (200 OK):
code
JSON
{
    "userid": "dana",
    "groups": ["Hunny Bunnies", "Administrators"],
    "users": ["dana", "michelle"]
}
Curl Example (Get Users):
code
Bash
curl -H "Authorization: Bearer 730ea935edf1dd98eef8" http://127.0.0.1:5000/api/v1/users
6. Get Categories
URL: /api/v1/categories
Method: GET
Successful Response (200 OK):
code
JSON
{
    "userid": "dana",
    "groups": ["Hunny Bunnies", "Administrators"],
    "categories": [
        "work",
        "personal",
        "billing"
    ]
}
Curl Example (Get Categories):
code
Bash
curl -H "Authorization: Bearer 730ea935edf1dd98eef8" http://127.0.0.1:5000/api/v1/categories
7. Update Categories
URL: /api/v1/categories
Method: PUT
Curl Example (Update Categories):
code
Bash
curl -X PUT \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 730ea935edf1dd98eef8" \
  -d '{"categories": ["work", "new category"]}' \
  http://127.0.0.1:5000/api/v1/categories
Contributing
Please read CONTRIBUTING.md for details on our code of conduct, and the process for submitting pull requests to us.
License
This project is licensed under the MIT License - see the LICENSE file for details.
Contact
For any questions or suggestions, please open an issue on GitHub.


