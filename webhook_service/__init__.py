from flask import Flask
from .config import Config
from .database import db_session, init_db, shutdown_session
from .cache import init_cache
from .celery_app import celery_app

def create_app():
    """Flask application factory function."""
    app = Flask(__name__)
    app.config.from_object(Config)

    init_cache()
    from .api import api_bp
    app.register_blueprint(api_bp)

    # Add teardown context to close database sessions automatically after each request
    @app.teardown_appcontext
    def remove_session(exception=None):
        shutdown_session(exception)

    @app.route('/')
    def index():
        return "Webhook Delivery Service is running!"

    return app
