import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app(test_config=None):
    """
    Application factory function to create and configure the Flask app
    """
    # Initialize Flask application
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))
    CORS(app, supports_credentials=True)  # Enable credential support for CORS
    
    # Import and register blueprints
    from app.routes.auth import auth_bp
    from app.routes.agent import agent_bp
    from app.routes.twitter import twitter_bp
    from app.routes.dashboard import dashboard_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(twitter_bp)
    app.register_blueprint(dashboard_bp)
    
    # Register function to close database connection when application shuts down
    from app.utils.db import close_db
    
    @app.teardown_appcontext
    def shutdown_db_connection(exception=None):
        """Close database connection when application context ends"""
        close_db()
    
    # Root route
    @app.route('/', methods=['GET'])
    def index():
        """
        API home page
        """
        from flask import jsonify
        return jsonify({
            "status": "success",
            "message": "CryptoBunny API is running",
            "version": "1.0.0",
        })
    
    return app 