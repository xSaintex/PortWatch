# app/mock_data/admin_users_mock.py
# In-memory user accounts for PortWatch.
#
# IMPORTANT: Stored in memory only — resets when the server restarts.
# These functions will be replaced by a Flask-SQLAlchemy User model
# with the same field names so the rest of the app needs minimal changes.
#
# DEMO PASSWORDS (for testing only — never use in production):
#   admin   / Admin123!     — System Administrator (administrator role)
#   viewer  / Viewer123!    — Demo Viewer (viewer role)
#   All other mock users   — PortWatch123
#
# WHY PASSWORDS ARE HASHED:
#   If the database is ever stolen, the attacker gets only the hash, not
#   the real password. Werkzeug uses PBKDF2 + SHA-256 + a random salt,
#   so even identical passwords produce different hashes.

import threading
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

_lock    = threading.Lock()
USERS    = []
_next_id = 1

_DEMO_PASSWORD       = "PortWatch123"
_ADMIN_PASSWORD      = "Admin123!"
_VIEWER_PASSWORD     = "Viewer123!"


def _hash(password):
    return generate_password_hash(password)


# ================================================================== #
# USER CLASS (Flask-Login integration)
# ================================================================== #

class PortWatchUser(UserMixin):
    """
    Wraps a user dict so Flask-Login can manage authentication state.

    Flask-Login requires:
      get_id()       — unique string identifier
      is_authenticated — True for real users (UserMixin default)
      is_active       — from the user's status field
      is_anonymous    — False for real users (UserMixin default)
    """

    def __init__(self, user_dict):
        self._user = user_dict

    # ---- Flask-Login required ----

    def get_id(self):
        """Return the user id as a string (Flask-Login stores it in the session)."""
        return str(self._user["id"])

    @property
    def is_active(self):
        """Only active users are allowed to log in."""
        return self._user.get("status") == "active"

    # ---- Convenience proxies so templates can use current_user.full_name ----

    @property
    def id(self):
        return self._user["id"]

    @property
    def username(self):
        return self._user["username"]

    @property
    def full_name(self):
        return self._user["full_name"]

    @property
    def role(self):
        return self._user["role"]

    @property
    def status(self):
        return self._user["status"]

    @property
    def must_change_password(self):
        return self._user.get("must_change_password", False)

    @property
    def last_login(self):
        return self._user.get("last_login")

    @property
    def created_at(self):
        return self._user.get("created_at")

    def to_dict(self):
        """Return the underlying dict (used by existing code that expects a dict)."""
        return self._user

    # Allow dict-style access for backward compatibility with existing routes
    def __getitem__(self, key):
        return self._user[key]

    def get(self, key, default=None):
        return self._user.get(key, default)

    def __contains__(self, key):
        return key in self._user


def user_loader(user_id):
    """
    Flask-Login calls this to reload a user from the session on every request.
    Must return a PortWatchUser or None.
    Registered in app/__init__.py via login_manager.user_loader.
    """
    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return None
    user_dict = get_user(uid)
    if user_dict is None:
        return None
    return PortWatchUser(user_dict)


def get_current_user():
    """
    Return the currently logged-in user as a plain dict (for backward
    compatibility with routes that still use dict access).

    Now delegates to Flask-Login's current_user instead of always returning
    user id=1. Falls back to user id=1 only outside a request context
    (e.g. during seeding), which is safe because seeding happens at import time.
    """
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            return current_user.to_dict()
    except RuntimeError:
        pass  # outside app context (import time) — fall back to id=1
    return get_user(1)


# ================================================================== #
# READ FUNCTIONS
# ================================================================== #

def get_all_users():
    """Return all users sorted newest-first by created_at."""
    with _lock:
        return sorted(USERS, key=lambda u: u["created_at"], reverse=True)


def get_user(user_id):
    """Return a user dict by integer id, or None."""
    with _lock:
        for u in USERS:
            if u["id"] == user_id:
                return u
    return None


def get_user_by_username(username):
    """Return a user dict by username (case-insensitive), or None."""
    uname = (username or "").strip().lower()
    with _lock:
        for u in USERS:
            if u["username"].lower() == uname:
                return u
    return None


def count_active_admins():
    """Return the number of active administrator accounts."""
    with _lock:
        return sum(
            1 for u in USERS
            if u["role"] == "administrator" and u["status"] == "active"
        )


def check_user_password(user, password):
    """
    Return True if the given plain-text password matches the user's hash.
    'user' may be a dict or a PortWatchUser instance.
    """
    if not user or not password:
        return False
    if isinstance(user, PortWatchUser):
        user = user.to_dict()
    return check_password_hash(user["password_hash"], password)


def update_last_login(user_id):
    """Set a user's last_login to now. Called on successful login."""
    user = get_user(user_id)
    if user:
        with _lock:
            user["last_login"] = datetime.now()


# ================================================================== #
# WRITE FUNCTIONS  (in-memory only — reset on server restart)
# ================================================================== #

def add_user(data):
    """Create a new user account."""
    global _next_id
    new_user = {
        "id":                   _next_id,
        "username":             data["username"].strip().lower(),
        "full_name":            data["full_name"].strip(),
        "role":                 data["role"].lower(),
        "status":               data.get("status", "active"),
        "password_hash":        generate_password_hash(data["password"]),
        "must_change_password": data.get("must_change_password", False),
        "created_at":           datetime.now(),
        "last_login":           None,
    }
    with _lock:
        USERS.append(new_user)
        _next_id += 1
    return new_user


def update_user(user_id, data):
    """Update a user's editable profile fields (not password)."""
    user = get_user(user_id)
    if not user:
        return None
    with _lock:
        user["full_name"] = data["full_name"].strip()
        user["role"]      = data["role"].lower()
        user["status"]    = data.get("status", user["status"])
    return user


def reset_password(user_id, new_password, must_change=False):
    """Reset a user's password (stores only the hash)."""
    user = get_user(user_id)
    if not user:
        return None
    with _lock:
        user["password_hash"]        = generate_password_hash(new_password)
        user["must_change_password"] = must_change
    return user


def toggle_user_status(user_id):
    """Flip a user's status between 'active' and 'inactive'."""
    user = get_user(user_id)
    if not user:
        return None
    with _lock:
        user["status"] = "inactive" if user["status"] == "active" else "active"
    return user["username"], user["status"]


def delete_user(user_id):
    """Remove a user from the in-memory list."""
    user = get_user(user_id)
    if not user:
        return None
    with _lock:
        USERS[:] = [u for u in USERS if u["id"] != user_id]
    return user


# ================================================================== #
# SEED DATA
# ================================================================== #

def _seed():
    """Create all mock users at startup."""
    global _next_id

    seed_data = [
        # ---- Primary demo accounts (individual passwords) ----
        {
            "id":           1,
            "username":     "admin",
            "full_name":    "System Administrator",
            "role":         "administrator",
            "status":       "active",
            "password":     _ADMIN_PASSWORD,   # Admin123!
            "last_login":   datetime(2026, 11, 5, 8, 30),
            "created_at":   datetime(2026, 9, 1, 8, 0),
            "must_change_password": False,
        },
        # Demo Viewer — easy login for testing
        {
            "id":           15,
            "username":     "viewer",
            "full_name":    "Demo Viewer",
            "role":         "viewer",
            "status":       "active",
            "password":     _VIEWER_PASSWORD,  # Viewer123!
            "last_login":   None,
            "created_at":   datetime(2026, 9, 1, 8, 1),
            "must_change_password": False,
        },
        # ---- Other administrators (PortWatch123) ----
        {
            "id":           2,
            "username":     "kdeleon",
            "full_name":    "Karl De Leon",
            "role":         "administrator",
            "status":       "active",
            "password":     _DEMO_PASSWORD,
            "last_login":   datetime(2026, 11, 4, 14, 15),
            "created_at":   datetime(2026, 9, 1, 8, 5),
            "must_change_password": False,
        },
        {
            "id":           3,
            "username":     "mreyes",
            "full_name":    "Maria Reyes",
            "role":         "administrator",
            "status":       "active",
            "password":     _DEMO_PASSWORD,
            "last_login":   datetime(2026, 11, 3, 10, 0),
            "created_at":   datetime(2026, 9, 2, 9, 0),
            "must_change_password": False,
        },
        {
            "id":           4,
            "username":     "rbautista",
            "full_name":    "Rodel Bautista",
            "role":         "administrator",
            "status":       "inactive",
            "password":     _DEMO_PASSWORD,
            "last_login":   datetime(2026, 10, 15, 11, 0),
            "created_at":   datetime(2026, 9, 3, 9, 0),
            "must_change_password": False,
        },
        # ---- Viewers (PortWatch123) ----
        {
            "id":           5,  "username": "jdelacruz",  "full_name": "Jose Dela Cruz",
            "role": "viewer",   "status": "active",       "password": _DEMO_PASSWORD,
            "last_login": datetime(2026, 11, 1, 7, 45),   "created_at": datetime(2026, 9, 5, 10, 0),
            "must_change_password": False,
        },
        {
            "id":           6,  "username": "asonido",    "full_name": "Ana Sonido",
            "role": "viewer",   "status": "active",       "password": _DEMO_PASSWORD,
            "last_login": datetime(2026, 10, 30, 13, 0),  "created_at": datetime(2026, 9, 5, 10, 30),
            "must_change_password": False,
        },
        {
            "id":           7,  "username": "bmagno",     "full_name": "Benjamin Magno",
            "role": "viewer",   "status": "active",       "password": _DEMO_PASSWORD,
            "last_login": datetime(2026, 10, 28, 9, 0),   "created_at": datetime(2026, 9, 8, 11, 0),
            "must_change_password": False,
        },
        {
            "id":           8,  "username": "cvillanueva","full_name": "Cynthia Villanueva",
            "role": "viewer",   "status": "active",       "password": _DEMO_PASSWORD,
            "last_login": datetime(2026, 10, 25, 8, 30),  "created_at": datetime(2026, 9, 10, 9, 0),
            "must_change_password": True,
        },
        {
            "id":           9,  "username": "dcastillo",  "full_name": "Diego Castillo",
            "role": "viewer",   "status": "active",       "password": _DEMO_PASSWORD,
            "last_login": None,                            "created_at": datetime(2026, 9, 12, 14, 0),
            "must_change_password": False,
        },
        {
            "id":           10, "username": "ementicio",  "full_name": "Elena Menticio",
            "role": "viewer",   "status": "active",       "password": _DEMO_PASSWORD,
            "last_login": datetime(2026, 10, 20, 10, 0),  "created_at": datetime(2026, 9, 15, 8, 0),
            "must_change_password": False,
        },
        {
            "id":           11, "username": "fnavarro",   "full_name": "Fernando Navarro",
            "role": "viewer",   "status": "inactive",     "password": _DEMO_PASSWORD,
            "last_login": datetime(2026, 10, 1, 8, 0),    "created_at": datetime(2026, 9, 18, 9, 30),
            "must_change_password": False,
        },
        {
            "id":           12, "username": "gcabrera",   "full_name": "Grace Cabrera",
            "role": "viewer",   "status": "active",       "password": _DEMO_PASSWORD,
            "last_login": datetime(2026, 10, 22, 11, 30), "created_at": datetime(2026, 9, 20, 10, 0),
            "must_change_password": False,
        },
        {
            "id":           13, "username": "hmendoza",   "full_name": "Hernando Mendoza",
            "role": "viewer",   "status": "active",       "password": _DEMO_PASSWORD,
            "last_login": None,                            "created_at": datetime(2026, 10, 1, 14, 0),
            "must_change_password": False,
        },
        {
            "id":           14, "username": "isantiago",  "full_name": "Irene Santiago",
            "role": "viewer",   "status": "active",       "password": _DEMO_PASSWORD,
            "last_login": datetime(2026, 10, 31, 16, 0),  "created_at": datetime(2026, 10, 5, 11, 0),
            "must_change_password": False,
        },
    ]

    with _lock:
        for d in seed_data:
            pw = d.pop("password")
            d["password_hash"] = _hash(pw)
            USERS.append(d)
        _next_id = max(d["id"] for d in USERS) + 1


_seed()
