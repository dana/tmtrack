from flask import Flask, jsonify
from .api.tasks import tasks_bp
from .config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(tasks_bp, url_prefix='/api/v1')

    @app.route('/')
    def index():
        return jsonify({"message": "Welcome to tmtrack API v1"})

    return app
