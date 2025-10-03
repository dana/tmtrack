from flask import Blueprint, request, jsonify
from uuid import uuid4
import datetime
from ..services.mongo_service import MongoService
from .utils import get_auth_info_from_request # Import the new utility

tasks_bp = Blueprint('tasks', __name__)
mongo_service = MongoService()

# ... (TASK_FIELDS, INTERNAL_FIELDS, validate_task_data remain unchanged) ...
TASK_FIELDS = {
    "task_id": {"type": str, "required": True},
    "userid": {"type": str, "required": True},
    "date": {"type": str, "required": True},
    "task_name": {"type": str, "required": True},
    "category": {"type": str, "required": True},
    "expected_hours": {"type": float, "required": True},
    "actual_hours": {"type": float, "required": False},
    "description": {"type": str, "required": False}
}
INTERNAL_FIELDS = {'created_at', 'updated_at'}

def validate_task_data(data, is_create=True):
    errors = {}
    for field, specs in TASK_FIELDS.items():
        if is_create and specs["required"] and field not in data:
            if field != "task_id":
                errors[field] = f"'{field}' is a required field."
            continue
        if field in data:
            value = data[field]
            expected_type = specs["type"]
            if not isinstance(value, expected_type):
                errors[field] = f"'{field}' must be of type {expected_type.__name__}, but got {type(value).__name__}."
            if field == "date" and expected_type == str:
                try:
                    datetime.datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    errors[field] = f"'{field}' must be in YYYY-MM-DD format."
    return errors

@tasks_bp.route('/users', methods=['GET'])
def list_users():
    """Returns a static list of allowed userids."""
    userid, groups = get_auth_info_from_request()
    auth_info = {"userid": userid, "groups": groups}
    
    allowed_users = ["dana", "michelle"]
    return jsonify({**auth_info, "users": allowed_users}), 200

@tasks_bp.route('/tasks', methods=['POST'])
def create_task():
    """Creates a new task document in MongoDB."""
    userid, groups = get_auth_info_from_request()
    auth_info = {"userid": userid, "groups": groups}

    data = request.get_json()
    if not data:
        return jsonify({**auth_info, "status": "error", "message": "Request must be JSON"}), 400

    validation_errors = validate_task_data(data, is_create=True)
    if validation_errors:
        return jsonify({**auth_info, "status": "error", "message": "Validation failed", "errors": validation_errors}), 400

    task_id = str(uuid4())
    data['task_id'] = task_id
    data['created_at'] = datetime.datetime.now(datetime.timezone.utc)
    data['updated_at'] = datetime.datetime.now(datetime.timezone.utc)

    for key, value in data.items():
        if key not in TASK_FIELDS and key not in INTERNAL_FIELDS and not isinstance(value, str):
            return jsonify({**auth_info, "status": "error", "message": f"Arbitrary attribute '{key}' must be a string."}), 400

    try:
        mongo_service.insert_task(data)
        success_response = {
            "status": "success",
            "message": "Task created successfully",
            "task_id": task_id
        }
        return jsonify({**auth_info, **success_response}), 201
    except Exception as e:
        return jsonify({**auth_info, "status": "error", "message": f"Failed to create task: {str(e)}"}), 500

@tasks_bp.route('/tasks/<string:task_id>', methods=['PUT'])
def modify_task(task_id):
    """Modifies an existing task document in MongoDB."""
    userid, groups = get_auth_info_from_request()
    auth_info = {"userid": userid, "groups": groups}

    data = request.get_json()
    if not data:
        return jsonify({**auth_info, "status": "error", "message": "Request must be JSON"}), 400

    if 'task_id' in data:
        del data['task_id']

    validation_errors = validate_task_data(data, is_create=False)
    if validation_errors:
        return jsonify({**auth_info, "status": "error", "message": "Validation failed", "errors": validation_errors}), 400

    data['updated_at'] = datetime.datetime.now(datetime.timezone.utc)

    for key, value in data.items():
        if key not in TASK_FIELDS and key not in INTERNAL_FIELDS and not isinstance(value, str):
            return jsonify({**auth_info, "status": "error", "message": f"Arbitrary attribute '{key}' must be a string."}), 400

    try:
        modified_count = mongo_service.update_task(task_id, data)
        if modified_count == 0:
            return jsonify({**auth_info, "status": "error", "message": f"Task with task_id '{task_id}' not found or no changes made."}), 404
        
        success_response = {
            "status": "success",
            "message": "Task updated successfully",
            "task_id": task_id
        }
        return jsonify({**auth_info, **success_response}), 200
    except Exception as e:
        return jsonify({**auth_info, "status": "error", "message": f"Failed to update task: {str(e)}"}), 500

@tasks_bp.route('/tasks/<string:task_id>', methods=['GET'])
def get_task(task_id):
    """Retrieves a single task by its task_id."""
    userid, groups = get_auth_info_from_request()
    auth_info = {"userid": userid, "groups": groups}

    try:
        task = mongo_service.get_task(task_id)
        if task:
            if '_id' in task:
                task['_id'] = str(task['_id'])
            return jsonify({**auth_info, "status": "success", "task": task}), 200
        return jsonify({**auth_info, "status": "error", "message": "Task not found"}), 404
    except Exception as e:
        return jsonify({**auth_info, "status": "error", "message": f"Failed to retrieve task: {str(e)}"}), 500

from ..auth import get_userids_in_groups

@tasks_bp.route('/tasks', methods=['GET'])
def get_all_tasks():
    """
    Retrieves tasks based on the authenticated user's group memberships.

    This endpoint returns a list of tasks for all users who are in the same
    groups as the authenticated user. For example, if the authenticated user
    'dana' is in "Group A", this route will return tasks for all users in
    "Group A". The 'guest' user will only see tasks associated with the
    'guest' userid.

    Returns:
        A JSON response containing the list of tasks.
    """
    userid, groups = get_auth_info_from_request()
    auth_info = {"userid": userid, "groups": groups}

    try:
        # Get the unique set of userids from all of the groups the
        # authenticated user is in.
        userids_in_my_groups = get_userids_in_groups(groups)
        
        # Fetch tasks for only those userids
        tasks = mongo_service.get_all_tasks(userids=list(userids_in_my_groups))
        
        for task in tasks:
            if '_id' in task:
                task['_id'] = str(task['_id'])
        return jsonify({**auth_info, "status": "success", "tasks": tasks}), 200
    except Exception as e:
        return jsonify({**auth_info, "status": "error", "message": f"Failed to retrieve tasks: {str(e)}"}), 500
