# app/utils/user_validators.py
# Server-side validation helpers for user accounts.
# These are REAL rules that will continue to apply once Flask-Login is added.
# Keeping them here (not in the route) means the same rules apply to both
# the web form and any future API.

import re


def validate_full_name(name):
    """
    Validate a user's full name.
    Returns an error string, or None if valid.
    """
    if not name or not name.strip():
        return "Full name is required."
    n = name.strip()
    if len(n) < 2:
        return "Full name must be at least 2 characters."
    if len(n) > 60:
        return "Full name must be 60 characters or fewer."
    # Allow letters (including Unicode for Filipino names), spaces, periods, hyphens, apostrophes
    if not re.match(r"^[\w\s.\-']+$", n, re.UNICODE):
        return "Full name may only contain letters, spaces, periods, hyphens, and apostrophes."
    return None


def validate_username(username, existing_users, editing_user_id=None):
    """
    Validate a username for Add mode (editing_user_id=None) or Edit mode.
    Returns an error string, or None if valid.

    Args:
        username       (str):        The submitted username.
        existing_users (list):       All user dicts to check uniqueness against.
        editing_user_id (int|None):  Skip uniqueness check for this user's own record.
    """
    if not username or not username.strip():
        return "Username is required."
    u = username.strip().lower()
    if len(u) < 3:
        return "Username must be at least 3 characters."
    if len(u) > 20:
        return "Username must be 20 characters or fewer."
    if not re.match(r'^[a-z][a-z0-9_.]*$', u):
        return (
            "Username must start with a letter and may only contain "
            "lowercase letters, numbers, underscores, or periods."
        )
    # Uniqueness (case-insensitive)
    for user in existing_users:
        if user["username"].lower() == u and user["id"] != editing_user_id:
            return "This username is already taken."
    return None


def validate_password(password, confirm=None):
    """
    Validate a new password (and optionally its confirmation).
    Returns an error string, or None if valid.
    """
    if not password:
        return "Password is required."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > 64:
        return "Password must be 64 characters or fewer."
    if not re.search(r'[a-zA-Z]', password):
        return "Password must contain at least one letter."
    if not re.search(r'[0-9]', password):
        return "Password must contain at least one number."
    if confirm is not None and password != confirm:
        return "Passwords do not match."
    return None


def validate_role(role):
    """Validate that role is one of the allowed values."""
    if role not in ("administrator", "viewer"):
        return "Role must be either 'administrator' or 'viewer'."
    return None
