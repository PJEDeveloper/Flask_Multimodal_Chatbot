# Blueprint for modular route grouping, render_template for serving HTML templates
from flask import Blueprint, render_template # type: ignore

# Create a Blueprint named "ui" for handling UI-related routes
ui_bp = Blueprint("ui", __name__)

# Route handler for serving the main UI page of the application
@ui_bp.route("/", methods=["GET"])
def index():
    """
    Serves the main UI page of the application.
    - This route responds to GET requests at the root URL ('/').
    - Renders and returns the 'index.html' template to the client browser.
    """
    return render_template("index.html")