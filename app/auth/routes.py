import re
from urllib.parse import urlparse
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.auth import auth_bp

# Regex pattern for email format validation
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


@auth_bp.route('/register', methods=['GET', 'POST'])
@auth_bp.route('/auth/register', methods=['GET', 'POST'])
def register():
    """
    User registration route.
    Validates form data, checks for existing usernames/emails,
    hashes passwords, and creates new User records.
    """
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Basic presence validation
        if not username or not email or not password or not confirm_password:
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html', username=username, email=email)

        # Username length & character validation
        if len(username) < 3 or len(username) > 80:
            flash('Username must be between 3 and 80 characters long.', 'danger')
            return render_template('auth/register.html', username=username, email=email)

        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            flash('Username may only contain letters, numbers, dots, hyphens, and underscores.', 'danger')
            return render_template('auth/register.html', username=username, email=email)

        # Email format validation
        if not EMAIL_REGEX.match(email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('auth/register.html', username=username, email=email)

        # Password complexity / length check
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register.html', username=username, email=email)

        # Password confirmation check
        if password != confirm_password:
            flash('Passwords do not match. Please re-enter.', 'danger')
            return render_template('auth/register.html', username=username, email=email)

        # Duplicate username check
        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Please choose a different one.', 'danger')
            return render_template('auth/register.html', username=username, email=email)

        # Duplicate email check
        if User.query.filter_by(email=email).first():
            flash('Email address is already registered. Please log in or use a different email.', 'danger')
            return render_template('auth/register.html', username=username, email=email)

        # Create user with hashed password
        new_user = User(username=username, email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_bp.route('/auth/login', methods=['GET', 'POST'])
def login():
    """
    User login route.
    Authenticates user credentials, manages user session via Flask-Login,
    and handles secure 'next' redirects.
    """
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        login_identifier = request.form.get('login_identifier', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not login_identifier or not password:
            flash('Please provide both username/email and password.', 'danger')
            return render_template('auth/login.html', login_identifier=login_identifier)

        # Allow login using either username or email
        user = User.query.filter(
            (User.username == login_identifier) | (User.email == login_identifier.lower())
        ).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.username}!', 'success')

            # Handle safe redirection (prevent open redirect vulnerabilities)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('auth.dashboard')
            return redirect(next_page)

        flash('Invalid username/email or password. Please try again.', 'danger')
        return render_template('auth/login.html', login_identifier=login_identifier)

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@auth_bp.route('/auth/logout')
@login_required
def logout():
    """
    User logout route.
    Terminates the authenticated user session.
    """
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/dashboard')
@auth_bp.route('/auth/dashboard')
@login_required
def dashboard():
    """
    Protected dashboard route.
    Accessible only to authenticated users via Flask-Login.
    """
    return render_template('auth/dashboard.html', user=current_user)