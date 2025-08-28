# Import the application factory function from the app module
from app import create_app
import os

# Create an instance of the Flask application using the factory function
app = create_app()

@app.route("/health", methods=["GET"])
def health_check():
    return {"status": "ok"}, 200


# Run the application if this file is executed directly
if __name__ == "__main__":
    # Start the Flask development server
    # host="0.0.0.0" makes the app accessible on the network
    # port=5000 specifies the port number
    # debug=True enables hot reload and debug mode (**not for production**)
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5001, debug=debug)