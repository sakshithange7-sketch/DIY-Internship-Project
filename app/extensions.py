"""
Extensions module.

Instantiates Flask extensions without binding them to a specific app.
This decouples extension creation from app creation, avoiding circular imports.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Database ORM instance
db = SQLAlchemy()

# Migration engine instance
migrate = Migrate()

# Authentication and session management instance
login_manager = LoginManager()
