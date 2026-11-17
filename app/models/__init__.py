"""
Models package.

Import models here so Alembic / Flask-Migrate and SQLAlchemy detect all tables.
"""

from app.models.user import User
from app.models.blog import Category, Tag, Post, post_tags, Comment

__all__ = ['User', 'Category', 'Tag', 'Post', 'post_tags', 'Comment']
