# Core Flask class for creating the application
from flask import Flask  

# Chat-related API routes
from app.routes.chat_routes import chat_bp    

# Clear/reset-related routes
from app.routes.clear_routes import clear_bp  

# UI rendering routes
from app.routes.ui_routes import ui_bp        

# Python logging for monitoring and debugging
import logging  

# OS operations for directory and file handling
import os  

# For structured JSON error responses
from flask import jsonify  

# Pre-configured logger instance from config
from config import logger  

def create_app():
    """
    Application factory function for creating and configuring the Flask app.
    Uses the factory pattern for scalability and testability.
    
    Steps:
    - Initialize Flask app.
    - Register blueprints for modular routing.
    - Add a global error handler for exceptions.
    
    Returns:
        Flask app instance.
    """
    app = Flask(__name__)

    # Register blueprints for modular organization
    app.register_blueprint(ui_bp)    # UI routes for rendering HTML pages
    app.register_blueprint(chat_bp)  # Chat endpoints (text/image/audio)
    app.register_blueprint(clear_bp) # Routes for clearing state/media

    # Global error handler to capture unhandled exceptions
    @app.errorhandler(Exception)
    def handle_exception(e):
        """
        Handles any unhandled exceptions across the app.
        Logs the error and returns a structured JSON response.
        """
        logger.error(f"Unhandled Exception: {e}", exc_info=True)
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

    return app

# Directory for storing log files
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Configure root logger with file and console handlers
logging.basicConfig(
    level=logging.INFO,  # Log level (INFO = general runtime info)
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",  # Log format with timestamp
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "app.log")),  # Save logs to file
        logging.StreamHandler()  # Print logs to console
    ]
)

# Get logger instance for this module
logger = logging.getLogger(__name__)
logger.info("Logging initialized.")
