# app/__init__.py
# App factory for PortWatch.
# The create_app() function builds and configures the Flask application,
# then registers each Blueprint (group of routes) so Flask knows about them.

from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load settings from config.py
    app.config.from_object("config.Config")

    # ------------------------------------------------------------------ #
    # Flask-Login setup
    # ------------------------------------------------------------------ #
    login_manager = LoginManager()
    login_manager.init_app(app)

    # Where Flask-Login sends unauthenticated users
    login_manager.login_view = "auth.login"
    # No flash message — the login page itself is clear enough without a banner.
    # Setting to None prevents Flask-Login's own "Please log in" message from
    # appearing on the dashboard after the user signs in.
    login_manager.login_message = None

    from app.mock_data.admin_users_mock import user_loader as _user_loader
    login_manager.user_loader(_user_loader)

    # ------------------------------------------------------------------ #
    # Jinja globals — functions and objects available in ALL templates
    # ------------------------------------------------------------------ #
    from app.mock_data.admin_users_mock import get_current_user as _get_current_user
    app.jinja_env.globals["get_current_user"] = _get_current_user
    # Make Flask-Login's current_user available as a Jinja global too
    app.jinja_env.globals["current_user"] = current_user

    # ------------------------------------------------------------------ #
    # Register Blueprints
    # ------------------------------------------------------------------ #
    from .routes.auth_routes   import auth_bp
    from .routes.admin_routes  import admin_bp, root_bp
    from .routes.viewer_routes import viewer_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(root_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(viewer_bp)

    return app
