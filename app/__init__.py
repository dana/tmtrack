from flask import Flask, jsonify
from flask_cors import CORS
# Import the new blueprint
from .api.categories import categories_bp
from .api.tasks import tasks_bp
from .config import Config

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(tasks_bp, url_prefix='/api/v1')
    # Register the new categories blueprint
    app.register_blueprint(categories_bp, url_prefix='/api/v1')

    @app.route('/')
    def index():
        return jsonify({"message": "Welcome to tmtrack API v1"})

    return app
