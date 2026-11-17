import re
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError


class PostForm(FlaskForm):
    """
    Form for creating and editing blog posts.
    """
    title = StringField(
        'Post Title',
        validators=[
            DataRequired(message='Post title is required.'),
            Length(min=3, max=200, message='Title must be between 3 and 200 characters long.')
        ],
        render_kw={'placeholder': 'Enter an engaging title...', 'class': 'form-control'}
    )

    slug = StringField(
        'Custom Slug (Optional)',
        validators=[
            Optional(),
            Length(max=220, message='Slug cannot exceed 220 characters.')
        ],
        render_kw={
            'placeholder': 'leave-blank-to-auto-generate-from-title',
            'class': 'form-control'
        }
    )

    category_id = SelectField(
        'Category',
        coerce=int,
        validators=[DataRequired(message='Please select a valid category.')],
        render_kw={'class': 'form-control form-select'}
    )

    tags = StringField(
        'Tags (comma-separated)',
        validators=[
            Optional(),
            Length(max=200, message='Tags cannot exceed 200 characters.')
        ],
        render_kw={'placeholder': 'flask, python, web development', 'class': 'form-control'}
    )

    content = TextAreaField(
        'Post Content',
        validators=[
            DataRequired(message='Post content is required.'),
            Length(min=10, message='Content must be at least 10 characters long.')
        ],
        render_kw={
            'placeholder': 'Write your post content here...',
            'rows': 12,
            'class': 'form-control rich-editor'
        }
    )

    submit = SubmitField('Publish Post', render_kw={'class': 'btn btn-primary'})

    def validate_slug(self, field):
        """Validate that custom slug has only lowercase letters, digits, and hyphens."""
        if field.data:
            clean_slug = field.data.strip().lower()
            if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', clean_slug):
                raise ValidationError('Slug may only contain lowercase alphanumeric characters and single hyphens.')

    def validate_content(self, field):
        """Validate that content is not just empty whitespace or blank HTML tags."""
        if field.data:
            clean_text = re.sub(r'<[^>]*>', '', field.data).strip()
            if len(clean_text) < 5:
                raise ValidationError('Content must contain meaningful text (at least 5 characters).')


class CategoryForm(FlaskForm):
    """
    Form for adding a new blog category.
    """
    name = StringField(
        'Category Name',
        validators=[
            DataRequired(message='Category name is required.'),
            Length(min=2, max=80, message='Category name must be between 2 and 80 characters.')
        ],
        render_kw={'placeholder': 'e.g. Technology', 'class': 'form-control'}
    )

    description = StringField(
        'Description (Optional)',
        validators=[
            Optional(),
            Length(max=255, message='Description cannot exceed 255 characters.')
        ],
        render_kw={'placeholder': 'Brief description of this category...', 'class': 'form-control'}
    )

    submit = SubmitField('Create Category', render_kw={'class': 'btn btn-secondary'})
