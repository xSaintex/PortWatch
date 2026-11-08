# run.py
# Entry point for the PortWatch application.
# Run this file from the terminal to start the Flask development server.
# Usage: python run.py

from app import create_app

# Create the Flask app using the app factory
app = create_app()

if __name__ == "__main__":
    # debug=True enables auto-reload when you save files and shows error details
    app.run(debug=True)
