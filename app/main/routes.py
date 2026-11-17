from flask import render_template, jsonify
from app.main import main_bp


@main_bp.route('/')
def index():
    """
    Renders the home page using Jinja2 templates.
    """
    return render_template(
        'index.html',
        title='DIY Internship - Flask Setup',
        app_name='FlaskStarter'
    )


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
