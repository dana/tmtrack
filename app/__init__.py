from flask import Flask, jsonify
from flask_cors import CORS  # 1. Import CORS
from .api.tasks import tasks_bp
from .config import Config

def create_app():
    app = Flask(__name__)

    # 2. Initialize CORS on the app instance.
    # This will add the required Access-Control-Allow-Origin header
    # to all responses from the application.
    CORS(app)

    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(tasks_bp, url_prefix='/api/v1')

    @app.route('/')
    def index():
        return jsonify({"message": "Welcome to tmtrack API v1"})

    return app
