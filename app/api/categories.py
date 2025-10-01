from flask import Blueprint, request, jsonify
from ..services.mongo_service import MongoService
from .utils import get_auth_info_from_request # Import the new utility
import bson

categories_bp = Blueprint('categories', __name__)
mongo_service = MongoService()

@categories_bp.route('/categories', methods=['GET'])
def get_categories():
    """
    Retrieves the single document containing the list of all categories.
    If no document exists, it returns a default empty list.
    """
    userid, groups = get_auth_info_from_request()
    auth_info = {"userid": userid, "groups": groups}

    try:
        categories_doc = mongo_service.get_categories()
        if categories_doc:
            categories_doc.pop('_id', None)
            return jsonify({**auth_info, **categories_doc}), 200
        else:
            return jsonify({**auth_info, "categories": []}), 200
    except Exception as e:
        error_response = {"status": "error", "message": f"Failed to retrieve categories: {str(e)}"}
        return jsonify({**auth_info, **error_response}), 500


@categories_bp.route('/categories', methods=['PUT'])
def update_categories():
    """
    Replaces the entire categories document with the provided data.
    The request body must be a JSON object with a single key "categories"
    that contains a list of strings.
    """
    userid, groups = get_auth_info_from_request()
    auth_info = {"userid": userid, "groups": groups}

    data = request.get_json()
    if not data:
        error_response = {"status": "error", "message": "Request must be JSON"}
        return jsonify({**auth_info, **error_response}), 400

    # Validation
    if 'categories' not in data:
        error_response = {"status": "error", "message": "Request body must contain a 'categories' key."}
        return jsonify({**auth_info, **error_response}), 400
    
    category_list = data['categories']
    if not isinstance(category_list, list):
        error_response = {"status": "error", "message": "The 'categories' value must be a list."}
        return jsonify({**auth_info, **error_response}), 400

    if not all(isinstance(item, str) for item in category_list):
        error_response = {"status": "error", "message": "All items in the 'categories' list must be strings."}
        return jsonify({**auth_info, **error_response}), 400

    try:
        result = mongo_service.update_categories(data)
        success_response = {
            "status": "success",
            "message": "Categories updated successfully.",
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": str(result.upserted_id) if result.upserted_id else None
        }
        return jsonify({**auth_info, **success_response}), 200
    except Exception as e:
        error_response = {"status": "error", "message": f"Failed to update categories: {str(e)}"}
        return jsonify({**auth_info, **error_response}), 500
