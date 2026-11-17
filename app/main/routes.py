from flask import render_template, jsonify, request, redirect, url_for, flash
from flask_login import current_user
from app.main import main_bp
from app.models.user import User
from app.models.blog import Post


@main_bp.route('/')
def index():
    """
    Renders the home page with published blog posts.
    Supports server-side pagination with 5 posts per page,
    preserving the existing hero section and feature cards.
    """
    page = request.args.get('page', 1, type=int)
    if not page or page < 1:
        page = 1
    per_page = 5

    pagination = Post.query.order_by(Post.created_at.desc(), Post.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    posts = pagination.items

    return render_template(
        'index.html',
        title='DIY Internship - Flask Setup & Blog Platform',
        app_name='FlaskStarter',
        posts=posts,
        pagination=pagination
    )


@main_bp.route('/profile/<username>')
def profile_redirect(username):
    """Redirect legacy or alternate /profile/<username> URLs to canonical /user/<username>."""
    return redirect(url_for('main.user_profile', username=username))


@main_bp.route('/user/<username>')
def user_profile(username):
    """
    Public user profile page.
    Displays username, registration date, total posts authored,
    and all blog posts written by this user with pagination.
    Gracefully handles nonexistent users without exposing private/sensitive data.
    """
    user = User.query.filter_by(username=username).first()
    if not user:
        return render_template(
            'errors/404.html',
            error_title='User Not Found',
            error_message=f"The user profile for '@{username}' does not exist or may have been removed."
        ), 404

    page = request.args.get('page', 1, type=int)
    if not page or page < 1:
        page = 1
    per_page = 5

    pagination = Post.query.filter_by(user_id=user.id).order_by(
        Post.created_at.desc(), Post.id.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    posts = pagination.items
    total_posts = user.posts.count()

    return render_template(
        'user_profile.html',
        profile_user=user,
        posts=posts,
        pagination=pagination,
        total_posts=total_posts
    )


@main_bp.route('/profile')
def my_profile():
    """
    Convenience shortcut to the authenticated user's public profile.
    Redirects guests to the login page.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.user_profile', username=current_user.username))
    flash('Please log in to view your profile.', 'info')
    return redirect(url_for('auth.login', next=url_for('main.my_profile')))


@main_bp.route('/health')
def health_check():
    """
    Simple health-check endpoint.
    Returns JSON status indicating the application is alive and healthy.
    """
    return jsonify({
        'status': 'healthy',
        'service': 'Flask Application',
        'message': 'Application is running properly'
    }), 200


@main_bp.app_errorhandler(404)
def page_not_found(e):
    """Graceful 404 error handler."""
    return render_template(
        'errors/404.html',
        error_title='Page Not Found',
        error_message='The requested page could not be found. Please check the URL or return to the home page.'
    ), 404


@main_bp.app_errorhandler(403)
def forbidden_access(e):
    """Graceful 403 error handler."""
    return render_template(
        'errors/403.html',
        error_title='Access Forbidden',
        error_message='You are not authorized to access or modify this resource. Only the post author has permission.'
    ), 403

