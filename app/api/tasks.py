from flask import Blueprint, request, jsonify
from uuid import uuid4
import datetime
from ..services.mongo_service import MongoService
from .utils import get_auth_info_from_request # Import the new utility
from ..auth import get_userids_in_groups

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
            elif field == "date" and isinstance(value, str):
                try:
                    datetime.datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    errors[field] = f"'{field}' must be in YYYY-MM-DD format."
    return errors

@tasks_bp.route('/happy', methods=['GET'])
def happy_check():
    return jsonify({"status": "ok"}), 200

@tasks_bp.route('/users', methods=['GET'])
def list_users():
    """Returns the list of allowed userids based on group memberships."""
    userid, groups = get_auth_info_from_request()
    auth_info = {"userid": userid, "groups": groups}
    
    users = get_userids_in_groups(groups)
    allowed_users = sorted(list(users)) if users else ["guest"]
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

    target_userid = data.get('userid')
    if userid != 'guest' and target_userid != userid and 'Administrators' not in groups and 'ServiceAccounts' not in groups:
        return jsonify({**auth_info, "status": "error", "message": "Forbidden: You are not authorized to create tasks for another user"}), 403

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

    task = mongo_service.get_task(task_id)
    if not task:
        return jsonify({**auth_info, "status": "error", "message": f"Task with task_id '{task_id}' not found"}), 404

    # Authorization check: only the owner or an Administrator can modify the task
    if task.get('userid') != userid and 'Administrators' not in groups:
        return jsonify({**auth_info, "status": "error", "message": "Forbidden: You are not authorized to modify this task"}), 403

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
            userids_in_my_groups = get_userids_in_groups(groups)
            if task.get('userid') not in userids_in_my_groups and 'Administrators' not in groups:
                return jsonify({**auth_info, "status": "error", "message": "Forbidden: You are not authorized to view this task"}), 403
            if '_id' in task:
                task['_id'] = str(task['_id'])
            return jsonify({**auth_info, "status": "success", "task": task}), 200
        return jsonify({**auth_info, "status": "error", "message": "Task not found"}), 404
    except Exception as e:
        return jsonify({**auth_info, "status": "error", "message": f"Failed to retrieve task: {str(e)}"}), 500

@tasks_bp.route('/tasks/<string:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Deletes a single task by its task_id, with authorization check."""
    userid, groups = get_auth_info_from_request()
    auth_info = {"userid": userid, "groups": groups}

    try:
        task = mongo_service.get_task(task_id)
        if not task:
            return jsonify({**auth_info, "status": "error", "message": "Task not found"}), 404

        # Authorization check: only the owner or an Administrator can delete the task
        if task.get('userid') != userid and 'Administrators' not in groups:
            return jsonify({**auth_info, "status": "error", "message": "Forbidden: You are not authorized to delete this task"}), 403

        deleted_count = mongo_service.delete_task(task_id)
        if deleted_count > 0:
            return jsonify({**auth_info, "status": "success", "message": "Task deleted successfully"}), 200
        else:
            return jsonify({**auth_info, "status": "error", "message": "Task not found or already deleted"}), 404
    except Exception as e:
        return jsonify({**auth_info, "status": "error", "message": f"Failed to delete task: {str(e)}"}), 500


from ..auth import get_userids_in_groups

@tasks_bp.route('/days', methods=['GET'])
def get_days():
    """
    Retrieves daily summary metadata (task counts, total hours, incomplete counts)
    for a user, optionally scoped to a date range.
    """
    userid, groups = get_auth_info_from_request()
    auth_info = {"userid": userid, "groups": groups}

    userids_in_my_groups = get_userids_in_groups(groups)
    target_userid = request.args.get('userid', userid)

    if target_userid not in userids_in_my_groups and 'Administrators' not in groups:
        return jsonify({**auth_info, "status": "error", "message": f"Forbidden: Not authorized to view days for user '{target_userid}'"}), 403

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    try:
        summary = mongo_service.get_days_summary(
            userid=target_userid,
            start_date=start_date,
            end_date=end_date
        )
        return jsonify({**auth_info, "status": "success", **summary}), 200
    except Exception as e:
        return jsonify({**auth_info, "status": "error", "message": f"Failed to retrieve days summary: {str(e)}"}), 500


@tasks_bp.route('/tasks', methods=['GET'])
def get_all_tasks():
    """
    Retrieves tasks based on group memberships and optional query filters:
    - userid: filter by a specific user (must be in shared groups)
    - date: exact single date (YYYY-MM-DD)
    - start_date / end_date: date range (inclusive)
    """
    userid, groups = get_auth_info_from_request()
    auth_info = {"userid": userid, "groups": groups}

    try:
        userids_in_my_groups = get_userids_in_groups(groups)
        filter_userid = request.args.get('userid')

        if filter_userid:
            if filter_userid not in userids_in_my_groups and 'Administrators' not in groups:
                return jsonify({**auth_info, "status": "error", "message": f"Forbidden: Not authorized to view tasks for user '{filter_userid}'"}), 403
            target_userids = [filter_userid]
        else:
            target_userids = list(userids_in_my_groups) if userids_in_my_groups else [userid]

        date = request.args.get('date')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        tasks = mongo_service.get_all_tasks(
            userids=target_userids,
            date=date,
            start_date=start_date,
            end_date=end_date
        )

        for task in tasks:
            if '_id' in task:
                task['_id'] = str(task['_id'])
        return jsonify({**auth_info, "status": "success", "tasks": tasks}), 200
    except Exception as e:
        return jsonify({**auth_info, "status": "error", "message": f"Failed to retrieve tasks: {str(e)}"}), 500
