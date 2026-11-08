# app/mock_data/admin_audit_log_mock.py
# In-memory audit log for PortWatch administrator actions.
# Stored in memory only — resets when the server restarts.
# Will be replaced by a database table with the same add_audit_entry() interface.
#
# WHY THE AUDIT LOG IS READ-ONLY IN THE UI:
#   Audit log entries are security evidence. Modifying or deleting them would
#   undermine accountability — if a suspicious action was logged, the admin
#   responsible could cover their tracks. Even "admin" users must not be
#   able to clear the log. A future version may support "archiving" old
#   entries (with a separate admin approval), but never silent deletion.
#
# ENTRY FIELDS:
#   id          — auto-increment integer
#   timestamp   — datetime
#   username    — who performed the action (stored as text so it remains
#                 readable even after the user account is deleted)
#   ip_address  — request.remote_addr at the time of the action (or "—")
#   action      — short action code, e.g. "scan_started"
#   category    — one of: Scans, Findings, Devices, Allowlist, Users,
#                 Reports, Security
#   target      — what was acted on (e.g. a device name, scan ID, or username)
#   detail      — human-readable description
#   result      — "success", "blocked", or "failed"

import threading
from datetime import datetime, timedelta

_lock    = threading.Lock()
ENTRIES  = []
_next_id = 1


# ================================================================== #
# ACTION → CATEGORY + DEFAULT RESULT MAP
# ================================================================== #
# This maps action codes to their category and default result so callers
# only need to pass the action code in the most common case.
_ACTION_META = {
    # ---- Scans ----
    "scan_started":           ("Scans",     "success"),
    "scan_completed":         ("Scans",     "success"),
    "scan_failed":            ("Scans",     "failed"),
    # ---- Findings ----
    "finding_acknowledged":   ("Findings",  "success"),
    # ---- Devices ----
    "device_added":           ("Devices",   "success"),
    "device_updated":         ("Devices",   "success"),
    "device_deleted":         ("Devices",   "success"),
    "device_activated":       ("Devices",   "success"),
    "device_deactivated":     ("Devices",   "success"),
    # ---- Allowlist ----
    "allowlist_entry_added":  ("Allowlist", "success"),
    "allowlist_entry_updated":("Allowlist", "success"),
    "allowlist_entry_removed":("Allowlist", "success"),
    "allowlist_copied":       ("Allowlist", "success"),
    # ---- Users ----
    "user_created":           ("Users",     "success"),
    "user_updated":           ("Users",     "success"),
    "user_role_changed":      ("Users",     "success"),
    "user_activated":         ("Users",     "success"),
    "user_deactivated":       ("Users",     "success"),
    "user_password_reset":    ("Users",     "success"),
    "user_deleted":           ("Users",     "success"),
    "password_changed":       ("Users",     "success"),
    # ---- Reports ----
    "report_exported":        ("Reports",   "success"),
    # ---- Security (blocked / suspicious) ----
    "scan_blocked":           ("Security",  "blocked"),
    "user_action_blocked":    ("Security",  "blocked"),
    "login_failed":           ("Security",  "failed"),
    "access_denied":          ("Security",  "blocked"),
    "login_success":          ("Security",  "success"),
    "logout":                 ("Security",  "success"),
    "password_change_failed": ("Security",  "blocked"),
}

_READABLE_LABELS = {
    "scan_started":           "Scan started",
    "scan_completed":         "Scan completed",
    "scan_failed":            "Scan failed",
    "finding_acknowledged":   "Finding acknowledged",
    "device_added":           "Device added",
    "device_updated":         "Device updated",
    "device_deleted":         "Device deleted",
    "device_activated":       "Device activated",
    "device_deactivated":     "Device deactivated",
    "allowlist_entry_added":  "Allowlist entry added",
    "allowlist_entry_updated":"Allowlist entry updated",
    "allowlist_entry_removed":"Allowlist entry removed",
    "allowlist_copied":       "Allowlist copied",
    "user_created":           "User created",
    "user_updated":           "User updated",
    "user_role_changed":      "Role changed",
    "user_activated":         "User activated",
    "user_deactivated":       "User deactivated",
    "user_password_reset":    "Password reset",
    "user_deleted":           "User deleted",
    "password_changed":       "Password changed",
    "report_exported":        "Report exported",
    "scan_blocked":           "Scan blocked",
    "user_action_blocked":    "Action blocked",
    "login_failed":           "Login failed",
    "access_denied":          "Access denied",
    "login_success":          "Login",
    "logout":                 "Logout",
    "password_change_failed": "Password change failed",
}


def get_action_label(action):
    """Return a human-readable label for an action code."""
    return _READABLE_LABELS.get(action, action.replace("_", " ").title())


def get_category(action):
    """Return the category for an action code."""
    return _ACTION_META.get(action, ("Security", "success"))[0]


def get_default_result(action):
    """Return the default result for an action code."""
    return _ACTION_META.get(action, ("Security", "success"))[1]


# ================================================================== #
# WRITE
# ================================================================== #

def add_audit_entry(action, user="Admin", target=None, detail=None,
                    ip_address=None, result=None, category=None):
    """
    Record an action in the audit log.

    Args:
        action     (str):       Short action code, e.g. "scan_blocked".
        user       (str):       Username of the actor (stored as text).
        target     (str):       What was acted on (device name, scan ID, …).
        detail     (str):       Human-readable description.
        ip_address (str|None):  Request IP. If None, tries request.remote_addr.
        result     (str|None):  "success", "blocked", or "failed".
                                Defaults from _ACTION_META.
        category   (str|None):  Override the auto-derived category.

    Returns:
        dict: The new audit entry.
    """
    global _next_id

    # Try to get the request IP automatically (will be None outside a request)
    if ip_address is None:
        try:
            from flask import request as _req
            ip_address = _req.remote_addr or "—"
        except RuntimeError:
            ip_address = "—"

    derived_category = category or get_category(action)
    derived_result   = result   or get_default_result(action)

    entry = {
        "id":         _next_id,
        "timestamp":  datetime.now(),
        "username":   user,
        "ip_address": ip_address or "—",
        "action":     action,
        "label":      get_action_label(action),
        "category":   derived_category,
        "target":     target or "",
        "detail":     detail or "",
        "result":     derived_result,
    }

    with _lock:
        ENTRIES.append(entry)
        _next_id += 1

    return entry


# ================================================================== #
# READ
# ================================================================== #

def get_all_entries():
    """Return all audit entries, newest first."""
    with _lock:
        return sorted(ENTRIES, key=lambda e: e["timestamp"], reverse=True)


def get_recent_audit_entries(limit=50):
    """Return the most recent audit entries, newest first."""
    with _lock:
        return sorted(ENTRIES, key=lambda e: e["timestamp"], reverse=True)[:limit]


def get_all_categories():
    """Return the fixed list of category names for the filter dropdown."""
    return ["Scans", "Findings", "Devices", "Allowlist", "Users", "Reports", "Security"]


def get_all_usernames():
    """Return sorted unique usernames present in the log."""
    with _lock:
        return sorted(set(e["username"] for e in ENTRIES))


# ================================================================== #
# SEED DATA — ~45 realistic entries over the last 6 weeks
# ================================================================== #

def _seed():
    """Populate the log with realistic historical entries at startup."""
    now = datetime.now()

    def ago(days=0, hours=0, minutes=0):
        return now - timedelta(days=days, hours=hours, minutes=minutes)

    # Each tuple: (days, hours, action, user, target, detail, ip, result, category)
    # Use None for result/category to auto-derive from action.
    seed = [
        # ── Security — blocked scan attempts ───────────────────────────────
        (0,  2, 0, "scan_blocked",     "admin",  "8.8.8.8",
         "Scan blocked: 8.8.8.8 is a public IP. Only private lab devices can be scanned.",
         "192.168.10.1", None, None),
        (1,  5, 0, "scan_blocked",     "admin",  "192.168.50.99",
         "Scan blocked: 192.168.50.99 is not registered in the Device Registry.",
         "192.168.10.1", None, None),
        (3, 14, 0, "scan_blocked",     "kdeleon","LAB1-PC04",
         "Scan blocked: LAB1-PC04 (192.168.10.14) is inactive.",
         "192.168.10.5", None, None),
        (7,  9, 0, "scan_blocked",     "mreyes", "192.168.50.1",
         "Scan blocked: 192.168.50.1 is not in the Device Registry.",
         "192.168.10.3", None, None),
        (10, 8, 0, "scan_blocked",     "admin",  "203.0.113.5",
         "Scan blocked: 203.0.113.5 is a public IP address.",
         "192.168.10.1", None, None),
        (14, 7, 0, "scan_blocked",     "kdeleon","LAB2-PC03",
         "Scan blocked: LAB2-PC03 (192.168.10.23) is inactive.",
         "192.168.10.5", None, None),
        (21, 6, 0, "scan_blocked",     "admin",  "172.217.0.0",
         "Scan blocked: 172.217.0.0 is a public IP address.",
         "192.168.10.1", None, None),
        (28, 5, 0, "scan_blocked",     "admin",  "10.0.0.999",
         "Scan blocked: 10.0.0.999 is not a valid IP address.",
         "192.168.10.1", None, None),

        # ── Security — user action blocked ─────────────────────────────────
        (2,  3, 0, "user_action_blocked","admin","admin",
         "Blocked: cannot delete own account.",
         "192.168.10.1", None, None),
        (5, 11, 0, "user_action_blocked","kdeleon","mreyes",
         "Blocked: would remove last active administrator.",
         "192.168.10.5", None, None),

        # ── Scans ─────────────────────────────────────────────────────────
        (0,  9,  0, "scan_started",   "admin",  "LAB2-SERVER01",
         "Scan started for 1 device(s), port spec: top1000.", "192.168.10.1", None, None),
        (0,  9, 12, "scan_completed", "admin",  "LAB2-SERVER01",
         "Scan completed: 1 device(s), 7 open ports, 3 flagged, highest risk: High.",
         "192.168.10.1", None, None),
        (1,  16, 0, "scan_started",   "kdeleon","LAB2-SERVER02",
         "Scan started for 1 device(s), port spec: top1000.", "192.168.10.5", None, None),
        (1,  16,11, "scan_completed", "kdeleon","LAB2-SERVER02",
         "Scan completed: 1 device(s), 6 open ports, 2 flagged, highest risk: High.",
         "192.168.10.5", None, None),
        (3,  11, 0, "scan_started",   "mreyes", "LAB2-SERVER01",
         "Scan started for 1 device(s), port spec: 22,80,443,3306,3389.",
         "192.168.10.3", None, None),
        (3,  11, 5, "scan_completed", "mreyes", "LAB2-SERVER01",
         "Scan completed: 1 device(s), 5 open ports, 2 flagged, highest risk: High.",
         "192.168.10.3", None, None),
        (5,  10, 0, "scan_started",   "admin",  "BATCH-20261028",
         "Scan started for 6 device(s), port spec: top1000.", "192.168.10.1", None, None),
        (5,  10, 54,"scan_completed", "admin",  "BATCH-20261028",
         "Scan completed: 6 device(s), 22 open ports, 8 flagged, highest risk: Medium.",
         "192.168.10.1", None, None),
        (12, 10, 0, "scan_started",   "kdeleon","LAB3-SWITCH01",
         "Scan started for 1 device(s), port spec: top1000.", "192.168.10.5", None, None),
        (12, 10, 9, "scan_completed", "kdeleon","LAB3-SWITCH01",
         "Scan completed: 1 device(s), 4 open ports, 1 flagged, highest risk: Medium.",
         "192.168.10.5", None, None),

        # ── Findings ─────────────────────────────────────────────────────
        (0,  8, 0, "finding_acknowledged","admin","SCN-00001",
         "Finding 2 in scan SCN-00001 acknowledged by admin.",
         "192.168.10.1", None, None),
        (1, 15, 0, "finding_acknowledged","mreyes","SCN-00005",
         "All 2 finding(s) in scan SCN-00005 acknowledged by mreyes.",
         "192.168.10.3", None, None),

        # ── Devices ──────────────────────────────────────────────────────
        (4, 13, 0, "device_added",    "admin",  "LAB3-PC05",
         "New device LAB3-PC05 (192.168.20.15) added to Computer Lab 3.",
         "192.168.10.1", None, None),
        (6, 12, 0, "device_updated",  "kdeleon","LAB1-PC06",
         "LAB1-PC06 notes updated.", "192.168.10.5", None, None),
        (8,  9, 0, "device_deactivated","admin","LAB2-PC03",
         "LAB2-PC03 deactivated — pending OS reinstall.",
         "192.168.10.1", None, None),
        (15, 8, 0, "device_activated","mreyes", "LAB1-PC04",
         "LAB1-PC04 reactivated after hardware repair.",
         "192.168.10.3", None, None),
        (20, 7, 0, "device_deleted",  "admin",  "LAB1-OLD01",
         "Device 'LAB1-OLD01' deleted from registry.",
         "192.168.10.1", None, None),

        # ── Allowlist ────────────────────────────────────────────────────
        (2,  6, 0, "allowlist_entry_added","kdeleon","LAB2-SERVER01",
         "Port 25/tcp (smtp) added to LAB2-SERVER01's allowlist.",
         "192.168.10.5", None, None),
        (4, 11, 0, "allowlist_entry_removed","admin","LAB2-SERVER01",
         "Port 8080/tcp (http-proxy) removed from LAB2-SERVER01's allowlist.",
         "192.168.10.1", None, None),
        (9,  8, 0, "allowlist_entry_updated","mreyes","LAB2-PC01",
         "Port 3389/tcp (ms-wbt-server) notes updated on LAB2-PC01.",
         "192.168.10.3", None, None),
        (11, 9, 0, "allowlist_copied","admin","LAB2-PC05",
         "Copied 3 entries from LAB1-PC01 to LAB2-PC05 (merge mode).",
         "192.168.10.1", None, None),
        (18, 7, 0, "allowlist_entry_added","kdeleon","LAB3-SWITCH01",
         "Port 161/udp (snmp) added to LAB3-SWITCH01's allowlist.",
         "192.168.10.5", None, None),

        # ── Users ────────────────────────────────────────────────────────
        (1,  4, 0, "user_created",    "admin",  "isantiago",
         "New viewer account created for 'Irene Santiago' (@isantiago).",
         "192.168.10.1", None, None),
        (3,  5, 0, "user_password_reset","admin","jdelacruz",
         "Password reset for @jdelacruz.", "192.168.10.1", None, None),
        (6, 10, 0, "user_role_changed","admin", "bmagno",
         "Role changed from administrator to viewer.",
         "192.168.10.1", None, None),
        (8,  8, 0, "user_deactivated","admin",  "fnavarro",
         "@fnavarro deactivated.", "192.168.10.1", None, None),
        (13, 6, 0, "user_activated",  "admin",  "cvillanueva",
         "@cvillanueva activated.", "192.168.10.1", None, None),
        (17, 5, 0, "user_updated",    "admin",  "ementicio",
         "Profile updated for @ementicio.", "192.168.10.1", None, None),
        (25, 9, 0, "user_created",    "admin",  "hmendoza",
         "New viewer account created for 'Hernando Mendoza' (@hmendoza).",
         "192.168.10.1", None, None),

        # ── Reports ──────────────────────────────────────────────────────
        (0,  7, 0, "report_exported", "admin",  "SCN-00001",
         "PDF report exported for scan SCN-00001 by Admin.",
         "192.168.10.1", None, None),
        (2, 10, 0, "report_exported", "kdeleon","history",
         "CSV export: 15 rows. Filters: risk=High.",
         "192.168.10.5", None, None),
        (5,  8, 0, "report_exported", "mreyes", "SCN-00005",
         "PDF report exported for scan SCN-00005 by mreyes.",
         "192.168.10.3", None, None),
        (10, 7, 0, "report_exported", "admin",  "history",
         "CSV export: 37 rows. Filters: none.",
         "192.168.10.1", None, None),

        # ── Scan failures ─────────────────────────────────────────────
        (16, 8, 0, "scan_failed",     "kdeleon","LAB3-PC04",
         "Scan job failed: Nmap process timed out after 120 s.",
         "192.168.10.5", "failed", None),
        (30, 6, 0, "scan_failed",     "admin",  "LAB2-SERVER01",
         "Scan job failed: Permission denied on socket.",
         "192.168.10.1", "failed", None),
    ]

    for (days, hours, minutes, action, user, target, detail, ip, result, category) in seed:
        ts = ago(days, hours, minutes)
        _add_raw(action, user, target, detail, ip, result, category, ts)


def _add_raw(action, user, target, detail, ip, result, category, timestamp):
    """Internal: add a pre-dated entry (used by seeding only)."""
    global _next_id

    derived_category = category or get_category(action)
    derived_result   = result   or get_default_result(action)

    entry = {
        "id":         _next_id,
        "timestamp":  timestamp,
        "username":   user,
        "ip_address": ip or "—",
        "action":     action,
        "label":      get_action_label(action),
        "category":   derived_category,
        "target":     target or "",
        "detail":     detail or "",
        "result":     derived_result,
    }

    with _lock:
        ENTRIES.append(entry)
        _next_id += 1

    return entry


_seed()
