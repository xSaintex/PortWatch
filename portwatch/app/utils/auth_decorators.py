# app/utils/auth_decorators.py
# Route protection decorators for PortWatch.
#
# admin_required  — must be logged in AND have role "administrator"
# viewer_required — must be logged in AND have role "viewer" or "administrator"
#
# Unauthenticated users are sent to /login.
# A viewer trying to reach an admin page gets a flash + redirect to their dashboard.
# An admin trying to reach a viewer page is redirected to the admin dashboard.

from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user


def admin_required(f):
    """
    Decorator for administrator-only routes.
    Redirects to /login if not authenticated.
    Redirects to /viewer/dashboard (with a flash + audit log) if a Viewer tries.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1. Not logged in at all — redirect silently; the login page is self-explanatory
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))

        # 2. Logged in as a Viewer — access denied
        if current_user.role != "administrator":
            from app.mock_data.admin_audit_log_mock import add_audit_entry
            add_audit_entry(
                "access_denied",
                user=current_user.username,
                target=request.path,
                detail=f"Viewer @{current_user.username} tried to access admin page: {request.path}",
                category="Security",
                result="blocked",
            )
            flash("You don't have permission to access that page.", "error")
            return redirect(url_for("viewer.dashboard"))

        return f(*args, **kwargs)
    return decorated


def viewer_required(f):
    """
    Decorator for viewer (and admin) routes.
    Redirects to /login if not authenticated.
    Redirects admins opening a /viewer page to /admin/dashboard.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            # Redirect silently — the login page is self-explanatory
            return redirect(url_for("auth.login", next=request.path))

        # Admins shouldn't be navigating viewer pages
        if current_user.role == "administrator":
            return redirect(url_for("admin.dashboard"))

        return f(*args, **kwargs)
    return decorated
