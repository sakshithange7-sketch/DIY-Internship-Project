import re
from datetime import datetime, timezone
from app.extensions import db


# Association table for Many-to-Many relationship between Post and Tag
post_tags = db.Table(
    'post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)


class Category(db.Model):
    """
    Category model for grouping related blog posts.
    One-to-Many relationship with Post.
    """
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # One-to-Many relationship with Post
    posts = db.relationship('Post', backref='category', lazy='dynamic', cascade='all')

    @staticmethod
    def slugify(name):
        """Generate a clean URL-friendly slug from name."""
        clean = re.sub(r'[^\w\s-]', '', name).strip().lower()
        return re.sub(r'[-\s]+', '-', clean) or 'category'

    def __repr__(self):
        return f'<Category {self.name}>'


class Tag(db.Model):
    """
    Tag model for labeling blog posts.
    Many-to-Many relationship with Post.
    """
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)

    # Many-to-Many relationship with Post
    posts = db.relationship('Post', secondary=post_tags, back_populates='tags', lazy='dynamic')

    @staticmethod
    def slugify(name):
        """Generate a clean URL-friendly slug from tag name."""
        clean = re.sub(r'[^\w\s-]', '', name).strip().lower()
        return re.sub(r'[-\s]+', '-', clean) or 'tag'

    def __repr__(self):
        return f'<Tag {self.name}>'


class Post(db.Model):
    """
    Post model representing blog entries.
    Linked to User (author), Category, and Tags.
    """
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)

    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False, index=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Many-to-Many relationship with Tag
    tags = db.relationship('Tag', secondary=post_tags, back_populates='posts', lazy='joined')

    @property
    def excerpt(self):
        """
        Returns a plain-text preview of the post content without HTML/markdown tags.
        """
        # Strip simple HTML tags
        clean_text = re.sub(r'<[^>]*>', '', self.content or '')
        # Strip markdown syntax symbols like #, *, `
        clean_text = re.sub(r'[#*`_>~]', '', clean_text)
        clean_text = ' '.join(clean_text.split())
        if len(clean_text) > 160:
            return clean_text[:157] + '...'
        return clean_text

    @property
    def tag_names_str(self):
        """Comma-separated list of tag names."""
        return ', '.join(t.name for t in self.tags)

    @classmethod
    def generate_unique_slug(cls, title, post_id=None):
        """
        Generate a unique slug based on post title.
        If a slug already exists for another post, appends an incremented suffix.
        """
        base_slug = re.sub(r'[^\w\s-]', '', title).strip().lower()
        base_slug = re.sub(r'[-\s]+', '-', base_slug) or 'post'

        slug = base_slug
        counter = 1
        while True:
            existing = cls.query.filter_by(slug=slug).first()
            if not existing or (post_id and existing.id == post_id):
                return slug
            slug = f"{base_slug}-{counter}"
            counter += 1

    def __repr__(self):
        return f'<Post {self.title}>'
