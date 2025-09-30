from flask import Blueprint, request, jsonify
from ..services.mongo_service import MongoService
import bson # Import bson to handle ObjectId serialization

categories_bp = Blueprint('categories', __name__)
mongo_service = MongoService()

@categories_bp.route('/categories', methods=['GET'])
def get_categories():
    """
    Retrieves the single document containing the list of all categories.
    If no document exists, it returns a default empty list.
    """
    try:
        categories_doc = mongo_service.get_categories()
        if categories_doc:
            # MongoDB returns an _id field, which we don't want in the response.
            categories_doc.pop('_id', None)
            return jsonify(categories_doc), 200
        else:
            # Return a default structure if the document doesn't exist yet
            return jsonify({"categories": []}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to retrieve categories: {str(e)}"}), 500


@categories_bp.route('/categories', methods=['PUT'])
def update_categories():
    """
    Replaces the entire categories document with the provided data.
    The request body must be a JSON object with a single key "categories"
    that contains a list of strings.
    """
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    # Validation
    if 'categories' not in data:
        return jsonify({"status": "error", "message": "Request body must contain a 'categories' key."}), 400
    
    category_list = data['categories']
    if not isinstance(category_list, list):
        return jsonify({"status": "error", "message": "The 'categories' value must be a list."}), 400

    if not all(isinstance(item, str) for item in category_list):
        return jsonify({"status": "error", "message": "All items in the 'categories' list must be strings."}), 400

    try:
        result = mongo_service.update_categories(data)
        return jsonify({
            "status": "success",
            "message": "Categories updated successfully.",
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": str(result.upserted_id) if result.upserted_id else None
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to update categories: {str(e)}"}), 500
