"""Flask web application for GPT-5 MongoDB AI Agent interface."""
import os
from flask import Flask, send_from_directory, session
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables
load_dotenv()

# Import route initializers
from routes.auth import init_auth_routes
from routes.chat import init_chat_routes


def create_app():
    """Create and configure Flask application.

    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__, static_folder='static', static_url_path='')

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Enable CORS
    CORS(app, supports_credentials=True)

    # MongoDB connection
    mongo_uri = os.getenv('MONGODB_URI', 'mongodb://mongodb:27017/')
    mongo_client = MongoClient(mongo_uri)
    db = mongo_client.government_procurement

    # Initialize routes
    app.register_blueprint(init_auth_routes(db))
    app.register_blueprint(init_chat_routes(db))

    @app.route('/')
    def index():
        """Serve the main application page."""
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/health')
    def health():
        """Health check endpoint.

        Returns:
            JSON response with health status
        """
        try:
            # Check MongoDB connection
            mongo_client.admin.command('ping')
            return {
                "status": "healthy",
                "services": {
                    "mongodb": "connected",
                    "flask": "running"
                }
            }, 200
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }, 500

    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 errors by serving index.html for client-side routing."""
        return send_from_directory(app.static_folder, 'index.html')

    @app.errorhandler(500)
    def internal_error(e):
        """Handle 500 errors."""
        return {
            "success": False,
            "error": "Internal server error"
        }, 500

    # Make session permanent by default
    @app.before_request
    def make_session_permanent():
        session.permanent = True

    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.getenv('FLASK_ENV') != 'production'
    )
