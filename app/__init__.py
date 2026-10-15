from flask import Flask, jsonify
from flask_cors import CORS
from .api.categories import categories_bp
from .api.tasks import tasks_bp
from .api.auth_routes import auth_bp
from .config import Config

def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True)
    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(tasks_bp, url_prefix='/api/v1')
    app.register_blueprint(categories_bp, url_prefix='/api/v1')

    # Register auth blueprint at both /api and /api/v1 for flexible routing
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api/v1', name='auth_bp_v1')

    @app.route('/')
    def index():
        return jsonify({"message": "Welcome to tmtrack API v1"})

    return app
