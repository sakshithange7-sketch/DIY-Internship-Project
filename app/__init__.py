import os
from flask import Flask
from config import config_by_name
from app.extensions import db, migrate, login_manager


def create_app(config_name=None):
    """
    Application Factory Pattern.
    Creates, configures, and returns a Flask application instance.
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)

    # Load configuration object from config.py
    app.config.from_object(config_by_name[config_name])

    # Ensure the instance directory exists (required for SQLite stored in instance/)
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize extensions with the current application instance
    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)

    # Configure Flask-Login session management
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'

    # Flask-Login user loader callback
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return db.session.get(User, int(user_id))

    # Import models so Flask-Migrate and SQLAlchemy register them
    from app import models

    # Register Blueprints
    from app.main import main_bp
    from app.auth import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)

    return app
