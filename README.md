# tmtrack: Time Tracker REST API

`tmtrack` is a modern Flask-based REST API for tracking daily tasks. It connects to a MongoDB database to store task information, allowing users to create, modify, and manage their tasks.

## Features

*   **Task Creation:** Create new task entries with required and optional attributes.
*   **Task Modification:** Update existing task details based on `task_id`.
*   **MongoDB Integration:** Stores task data in a MongoDB database.
*   **API Validation:** Ensures data types and required fields are correct.
*   **UUID Generation:** Automatically assigns unique IDs to new tasks.

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

### Running the Application (with `flask run`)

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

### Testing

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

