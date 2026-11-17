"""
Models package.

Import models here so Alembic / Flask-Migrate and SQLAlchemy detect all tables.
"""

from app.models.user import User

__all__ = ['User']
