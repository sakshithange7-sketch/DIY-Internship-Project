import os
from app import create_app

# Determine configuration environment (defaults to development)
env_config = os.environ.get('FLASK_CONFIG', 'development')
app = create_app(env_config)

if __name__ == '__main__':
    # Run development server on port 5000
    app.run(host='127.0.0.1', port=5000, debug=True)
