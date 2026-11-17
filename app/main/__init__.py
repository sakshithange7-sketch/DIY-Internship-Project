from flask import Blueprint

# Define the 'main' blueprint
main_bp = Blueprint('main', __name__)

# Import routes at the bottom to avoid circular import issues
from app.main import routes
