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

... (This section remains unchanged) ...

## Running the Application (with `flask run`)

... (This section remains unchanged) ...

## Authentication and Authorization

This application uses a simple, file-based system for managing user access. On startup, the server reads two JSON files from the project's root directory. **Any changes to these files require a server restart to take effect.**

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
code
Python
from app.auth import get_userid_from_token

# Example usage within a Flask route:
# auth_header = request.headers.get('Authorization')
# token = auth_header.split(" ") if auth_header else None
# current_user_id = get_userid_from_token(token)  # Returns "dana" or "guest"
Authorization (user_authorization.json)
This file maps groups to lists of user IDs. It defines "who is in what group."
The file format is a list of group objects:
code
JSON
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
code
Python
from app.auth import get_groups_from_userid

# Example usage:
# dana_groups = get_groups_from_userid("dana") 
# # Returns ['Hunny Bunnies', 'Administrators']
#
# guest_groups = get_groups_from_userid("some_unknown_user") 
# # Returns ['Guests']

### API Endpoints

#### 1. Create a New Task

*   **URL:** `/api/v1/tasks`
*   **Method:** `POST`
*   **Content-Type:** `application/json`

**Request Body Example:**

```json
{
    "userid": "user123",
    "date": "2023-10-27",
    "task_name": "Develop REST API",
    "category": "Development",
    "expected_hours": 8.0,
    "actual_hours": 7.5,
    "description": "Implement the Flask API for task management.",
    "project_code": "TMTRACK-FLASK"
}
```

Successful Response (201 Created):
```json
{
    "message": "Task created successfully",
    "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "status": "success"
}
```


Curl Example (Create):
```json
curl -X POST -H "Content-Type: application/json" -d '{
    "userid": "curluser1",
    "date": "2023-10-27",
    "task_name": "Review documentation",
    "category": "Documentation",
    "expected_hours": 2.0,
    "description": "Review the updated README.md"
}' http://127.0.0.1:5000/api/v1/tasks
```


2. Modify an Existing Task
URL: /api/v1/tasks/<task_id>
Method: PUT
Content-Type: application/json
Request Body Example:
```json
{
    "expected_hours": 9.0,
    "actual_hours": 8.5,
    "description": "Adjusted hours based on new requirements."
}
```

Successful Response (200 OK):
```json
{
    "message": "Task updated successfully",
    "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "status": "success"
}
```


Curl Example (Modify):
First, create a task and get its task_id (from the create curl output). Let's assume YOUR_TASK_ID is a1b2c3d4-e5f6-7890-1234-567890abcdef.
```bash
curl -X PUT -H "Content-Type: application/json" -d '{
    "actual_hours": 2.5,
    "notes": "Completed faster than expected."
}' http://127.0.0.1:5000/api/v1/tasks/a1b2c3d4-e5f6-7890-1234-567890abcdef
```

3. Get a Single Task
URL: /api/v1/tasks/<task_id>
Method: GET
Curl Example (Get Single):
```bash
curl http://127.0.0.1:5000/api/v1/tasks/a1b2c3d4-e5f6-7890-1234-567890abcdef
```

4. Get All Tasks
URL: /api/v1/tasks
Method: GET
Curl Example (Get All):
```bash
curl http://127.0.0.1:5000/api/v1/tasks
```

5. Get Categories

*   **URL:** `/api/v1/categories`
*   **Method:** `GET`

**Successful Response (200 OK):**

```json
{
    "categories": [
        "work",
        "personal",
        "billing"
    ]
}


Contributing
Please read CONTRIBUTING.md for details on our code of conduct, and the process for submitting pull requests to us.
License
This project is licensed under the MIT License - see the LICENSE file for details.
Contact
For any questions or suggestions, please open an issue on GitHub.

