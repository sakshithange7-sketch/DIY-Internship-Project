from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    """
    User model for authentication and session management.
    Inherits from UserMixin to integrate seamlessly with Flask-Login.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # One-to-Many relationship with Post
    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete-orphan')

    # One-to-Many relationship with Comment (cascade delete)
    comments = db.relationship(
        'Comment',
        back_populates='author',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    @property
    def authored_posts(self):
        """Returns all posts authored by this user, ordered by creation date descending."""
        from app.models.blog import Post
        return self.posts.order_by(Post.created_at.desc()).all()

    def set_password(self, password):
        """Hash and store the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check the hashed password against the provided plain-text password."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'
