# app/routes/auth_routes.py
# Authentication routes for PortWatch: login and logout.
#
# Security design decisions:
#   - Login errors always say "Invalid username or password." — never which
#     field was wrong, to prevent username enumeration.
#   - Inactive accounts get a separate, specific message so the admin knows
#     to reactivate the account (this is not a security leak since it doesn't
#     reveal anything about the password).
#   - Successful login redirects by role (admin → /admin/dashboard,
#     viewer → /viewer/dashboard).
#   - The ?next= parameter is validated to only allow relative, internal URLs,
#     preventing open-redirect attacks.
#   - Passwords are never logged or flashed.

from flask import (
    Blueprint, render_template, redirect, url_for, request,
)
from flask_login import login_user, logout_user, current_user

auth_bp = Blueprint("auth", __name__)


def _is_safe_next(next_url):
    """Return True only for relative URLs (no scheme = no external redirect)."""
    return next_url and next_url.startswith("/") and not next_url.startswith("//")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page. Redirects already-logged-in users to their dashboard."""
    # Already logged in — skip the form
    if current_user.is_authenticated:
        if current_user.role == "administrator":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("viewer.dashboard"))

    error = None

    if request.method == "GET":
        # Clear any leftover flash messages that accumulated before reaching the
        # login page (e.g. "Please sign in to continue." added by a decorator
        # before it was removed, or stale messages from a previous session).
        # Without this, those messages would survive in the session cookie and
        # appear on the dashboard AFTER the user successfully logs in, which is
        # confusing because by that point the action has already succeeded.
        from flask import get_flashed_messages
        get_flashed_messages()   # consume and discard — result is intentionally ignored

    if request.method == "POST":
        from app.mock_data.admin_users_mock import (
            get_user_by_username, check_user_password,
            PortWatchUser, update_last_login,
        )
        from app.mock_data.admin_audit_log_mock import add_audit_entry

        username_input = request.form.get("username", "").strip()
        password_input = request.form.get("password", "")
        remember       = bool(request.form.get("remember"))

        user_dict = get_user_by_username(username_input)

        if user_dict is None or not check_user_password(user_dict, password_input):
            # Generic message — never reveal whether username or password was wrong
            error = "Invalid username or password."
            add_audit_entry(
                "login_failed",
                user=username_input or "(empty)",
                target=username_input,
                detail=f"Failed login attempt for username '{username_input}'.",
                category="Security",
                result="failed",
            )

        elif user_dict["status"] != "active":
            error = "This account is inactive. Contact your administrator."
            add_audit_entry(
                "login_failed",
                user=username_input,
                target=username_input,
                detail=f"Login blocked: account @{username_input} is inactive.",
                category="Security",
                result="blocked",
            )

        else:
            # Success
            flask_user = PortWatchUser(user_dict)
            login_user(flask_user, remember=remember)
            update_last_login(user_dict["id"])

            add_audit_entry(
                "login_success",
                user=user_dict["username"],
                target=user_dict["username"],
                detail=f"@{user_dict['username']} signed in successfully.",
                category="Security",
                result="success",
            )

            # Safe next redirect
            next_url = request.args.get("next") or request.form.get("next")
            if _is_safe_next(next_url):
                return redirect(next_url)

            if user_dict["role"] == "administrator":
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("viewer.dashboard"))

    return render_template(
        "auth/login.html",
        error=error,
        next=request.args.get("next", ""),
    )


@auth_bp.route("/logout")
def logout():
    """Log the current user out, add an audit entry, and return to login."""
    if current_user.is_authenticated:
        from app.mock_data.admin_audit_log_mock import add_audit_entry
        add_audit_entry(
            "logout",
            user=current_user.username,
            target=current_user.username,
            detail=f"@{current_user.username} signed out.",
            category="Security",
            result="success",
        )
    logout_user()
    # No flash — the login page arrival is self-explanatory after clicking Sign Out
    return redirect(url_for("auth.login"))
