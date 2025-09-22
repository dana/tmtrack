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
*   MongoDB installed and running on `localhost:27017`

    To install MongoDB on Ubuntu 24.04, follow the official MongoDB documentation: [https://www.mongodb.com/docs/manual/administration/install-on-linux/](https://www.mongodb.com/docs/manual/administration/install-on-linux/)

*   `pyenv` (recommended for managing Python versions)

### Installation

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

### Running the Application

1.  **Ensure MongoDB is running:**
    ```bash
    sudo systemctl start mongod
    ```
    (Or whatever command your OS uses to start MongoDB)

2.  **Run the Flask development server:**
    ```bash
    export FLASK_APP=app/__init__.py
    export FLASK_ENV=development
    flask run
    ```
    The API will be available at `http://127.0.0.1:5000`.

### Testing

The project uses `tox` for comprehensive testing.

1.  **Install `tox`:**
    ```bash
    pip install tox
    ```

2.  **Run tests:**
    ```bash
    tox
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


Successful Response (201 Created):


{
    "message": "Task created successfully",
    "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "status": "success"
}

2. Modify an Existing Task
URL: /api/v1/tasks/<task_id>
Method: PUT
Content-Type: application/json
Request Body Example:


{
    "expected_hours": 9.0,
    "actual_hours": 8.5,
    "description": "Adjusted hours based on new requirements."
}

Successful Response (200 OK):


{
    "message": "Task updated successfully",
    "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "status": "success"
}

Contributing
Please read CONTRIBUTING.md for details on our code of conduct, and the process for submitting pull requests to us.
License
This project is licensed under the MIT License - see the LICENSE file for details.
Contact
For any questions or suggestions, please open an issue on GitHub.



