# config.py
# Application configuration settings for PortWatch.
# Centralises settings like the secret key and debug mode so they are
# easy to find and change without hunting through the codebase.

class Config:
    # SECRET_KEY is used by Flask to sign session cookies.
    # IMPORTANT: Replace this placeholder with a long random string before
    # deploying to a real server. Never commit a real secret key to version control.
    SECRET_KEY = "replace-this-with-a-real-secret-key"

    # DEBUG mode shows detailed error pages and auto-reloads on file changes.
    # Set to False in production.
    DEBUG = True

    # Session cookie security — prevents JavaScript from reading the session cookie,
    # which protects against XSS-based session hijacking.
    SESSION_COOKIE_HTTPONLY = True

    # ------------------------------------------------------------------ #
    # SCAN SETTINGS
    # ------------------------------------------------------------------ #

    # How many TCP ports the scanner checks by default (Nmap --top-ports).
    SCAN_DEFAULT_TOP_PORTS = 1000

    # How many seconds the MOCK scanner sleeps to simulate scanning one device.
    # This makes the progress page feel realistic without running real Nmap.
    # Remove once real Nmap is connected.
    MOCK_SCAN_DURATION_SECONDS = 8
