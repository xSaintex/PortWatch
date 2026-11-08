# app/mock_data/admin_devices_mock.py
# Sample (fake) device data shared across the Device Registry page and Dashboard.
#
# IMPORTANT: Changes here are stored in memory only and reset when the
# server restarts. These functions (add_device, update_device, etc.) will
# be replaced by database functions with the same names later — the rest
# of the app will not need to change because the function signatures stay the same.
#
# CIRCULAR IMPORT NOTE:
#   This file imports count_entries() from admin_allowlist_mock.py to
#   calculate allowlisted_port_count dynamically. To avoid a circular
#   import, admin_allowlist_mock.py must NOT import from this file.
#   The dependency is one-way: devices → allowlist. Keeping it one-way
#   also mirrors the real database structure (allowlist rows reference
#   devices via a foreign key, not the other way around).
#
#   Similarly, last_scanned and last_highest_risk are NOT stored here.
#   They are looked up live from admin_scans_mock.py via _inject_scan_info().
#   admin_scans_mock imports from admin_allowlist_mock and mock_nmap_scanner,
#   but NOT from this file — so the import chain is acyclic:
#     admin_devices_mock → admin_allowlist_mock (count_entries)
#     admin_devices_mock → admin_scans_mock (get_latest_scan_for_device)
#     admin_scans_mock   → admin_allowlist_mock, mock_nmap_scanner, scan_classifier
#
# TODO: Replace all functions here with real SQLAlchemy database queries
#       once Flask-SQLAlchemy and the device model are implemented.

from datetime import datetime


# ------------------------------------------------------------------ #
# DEVICE LIST — 20 realistic lab devices
#
# Keys stored in DEVICES (static):
#   id, name, ip_address, lab_location, device_type, notes,
#   status, last_scanned, last_highest_risk, created_at
#
# allowlisted_port_count is NOT stored here. It is calculated live
# by injecting count_entries(device_id) from admin_allowlist_mock.py
# so Device Registry, Dashboard, and Allowlist page always agree.
# ------------------------------------------------------------------ #
DEVICES = [
    # ---- Computer Lab 1 (6 workstations) ----
    {"id": 1,  "name": "LAB1-PC01",     "ip_address": "192.168.10.11", "lab_location": "Computer Lab 1", "device_type": "Workstation",    "notes": "Student workstation, row 1 seat 1.",                      "status": "active",   "last_scanned": datetime(2026, 10, 31, 11, 5),  "last_highest_risk": "None", "created_at": datetime(2026, 10, 1, 8, 0)},
    {"id": 2,  "name": "LAB1-PC02",     "ip_address": "192.168.10.12", "lab_location": "Computer Lab 1", "device_type": "Workstation",    "notes": "Student workstation, row 1 seat 2.",                      "status": "active",   "last_scanned": datetime(2026, 10, 29, 10, 0),  "last_highest_risk": "Low",  "created_at": datetime(2026, 10, 1, 8, 5)},
    {"id": 3,  "name": "LAB1-PC03",     "ip_address": "192.168.10.13", "lab_location": "Computer Lab 1", "device_type": "Workstation",    "notes": "Student workstation, row 2 seat 1.",                      "status": "active",   "last_scanned": datetime(2026, 10, 31, 14, 42), "last_highest_risk": "Medium","created_at": datetime(2026, 10, 1, 8, 10)},
    {"id": 4,  "name": "LAB1-PC04",     "ip_address": "192.168.10.14", "lab_location": "Computer Lab 1", "device_type": "Workstation",    "notes": "Student workstation, row 2 seat 2.",                      "status": "inactive", "last_scanned": datetime(2026, 10, 20, 9, 30),  "last_highest_risk": "Low",  "created_at": datetime(2026, 10, 1, 8, 15)},
    {"id": 5,  "name": "LAB1-PC05",     "ip_address": "192.168.10.15", "lab_location": "Computer Lab 1", "device_type": "Workstation",    "notes": "Student workstation, row 3 seat 1.",                      "status": "active",   "last_scanned": datetime(2026, 10, 28, 9, 0),   "last_highest_risk": "None", "created_at": datetime(2026, 10, 1, 8, 20)},
    {"id": 6,  "name": "LAB1-PC06",     "ip_address": "192.168.10.16", "lab_location": "Computer Lab 1", "device_type": "Workstation",    "notes": "Instructor PC — has file sharing enabled for class demos.","status": "active",   "last_scanned": datetime(2026, 10, 27, 15, 0),  "last_highest_risk": "Low",  "created_at": datetime(2026, 10, 1, 8, 25)},
    # ---- Computer Lab 2 (6 workstations + 2 servers) ----
    {"id": 7,  "name": "LAB2-PC01",     "ip_address": "192.168.10.21", "lab_location": "Computer Lab 2", "device_type": "Workstation",    "notes": "Student workstation.",                                    "status": "active",   "last_scanned": datetime(2026, 10, 30, 16, 20), "last_highest_risk": "Low",  "created_at": datetime(2026, 10, 3, 9, 0)},
    {"id": 8,  "name": "LAB2-PC02",     "ip_address": "192.168.10.22", "lab_location": "Computer Lab 2", "device_type": "Workstation",    "notes": "Student workstation.",                                    "status": "active",   "last_scanned": datetime(2026, 10, 30, 16, 20), "last_highest_risk": "Medium","created_at": datetime(2026, 10, 3, 9, 5)},
    {"id": 9,  "name": "LAB2-PC03",     "ip_address": "192.168.10.23", "lab_location": "Computer Lab 2", "device_type": "Workstation",    "notes": "Student workstation.",                                    "status": "inactive", "last_scanned": datetime(2026, 10, 15, 10, 0),  "last_highest_risk": "High", "created_at": datetime(2026, 10, 3, 9, 10)},
    {"id": 10, "name": "LAB2-PC04",     "ip_address": "192.168.10.24", "lab_location": "Computer Lab 2", "device_type": "Workstation",    "notes": "Student workstation.",                                    "status": "active",   "last_scanned": datetime(2026, 10, 29, 14, 0),  "last_highest_risk": "None", "created_at": datetime(2026, 10, 3, 9, 15)},
    {"id": 11, "name": "LAB2-PC05",     "ip_address": "192.168.10.25", "lab_location": "Computer Lab 2", "device_type": "Workstation",    "notes": "Student workstation.",                                    "status": "active",   "last_scanned": None,                           "last_highest_risk": None,   "created_at": datetime(2026, 10, 3, 9, 20)},
    {"id": 12, "name": "LAB2-PC06",     "ip_address": "192.168.10.26", "lab_location": "Computer Lab 2", "device_type": "Workstation",    "notes": "Student workstation.",                                    "status": "active",   "last_scanned": None,                           "last_highest_risk": None,   "created_at": datetime(2026, 10, 3, 9, 25)},
    {"id": 13, "name": "LAB2-SERVER01", "ip_address": "192.168.10.30", "lab_location": "Computer Lab 2", "device_type": "Server",         "notes": "Main file and print server for Lab 2. Handle with care.", "status": "active",   "last_scanned": datetime(2026, 11, 1, 9, 15),   "last_highest_risk": "High", "created_at": datetime(2026, 10, 5, 14, 0)},
    {"id": 14, "name": "LAB2-SERVER02", "ip_address": "192.168.10.31", "lab_location": "Computer Lab 2", "device_type": "Server",         "notes": "Backup server.",                                          "status": "active",   "last_scanned": datetime(2026, 10, 30, 9, 0),   "last_highest_risk": "High", "created_at": datetime(2026, 10, 5, 14, 30)},
    # ---- Computer Lab 3 (4 workstations) ----
    {"id": 15, "name": "LAB3-PC01",     "ip_address": "192.168.20.11", "lab_location": "Computer Lab 3", "device_type": "Workstation",    "notes": "Student workstation.",                                    "status": "active",   "last_scanned": datetime(2026, 10, 28, 11, 0),  "last_highest_risk": "None", "created_at": datetime(2026, 10, 8, 10, 0)},
    {"id": 16, "name": "LAB3-PC02",     "ip_address": "192.168.20.12", "lab_location": "Computer Lab 3", "device_type": "Workstation",    "notes": "Student workstation.",                                    "status": "active",   "last_scanned": datetime(2026, 10, 28, 11, 0),  "last_highest_risk": "Low",  "created_at": datetime(2026, 10, 8, 10, 5)},
    {"id": 17, "name": "LAB3-PC03",     "ip_address": "192.168.20.13", "lab_location": "Computer Lab 3", "device_type": "Workstation",    "notes": "Student workstation.",                                    "status": "active",   "last_scanned": None,                           "last_highest_risk": None,   "created_at": datetime(2026, 10, 8, 10, 10)},
    {"id": 18, "name": "LAB3-PC04",     "ip_address": "192.168.20.14", "lab_location": "Computer Lab 3", "device_type": "Workstation",    "notes": "Student workstation.",                                    "status": "active",   "last_scanned": datetime(2026, 10, 26, 9, 0),   "last_highest_risk": "Medium","created_at": datetime(2026, 10, 8, 10, 15)},
    # ---- Server Room ----
    {"id": 19, "name": "LAB3-SWITCH01", "ip_address": "192.168.20.1",  "lab_location": "Server Room",    "device_type": "Network Device", "notes": "Core managed switch for the server room.",               "status": "active",   "last_scanned": datetime(2026, 10, 25, 8, 0),   "last_highest_risk": "Medium","created_at": datetime(2026, 10, 10, 11, 0)},
    {"id": 20, "name": "LAB3-SERVER01", "ip_address": "192.168.20.30", "lab_location": "Server Room",    "device_type": "Server",         "notes": "Network storage server.",                                 "status": "active",   "last_scanned": datetime(2026, 10, 24, 14, 0),  "last_highest_risk": "Low",  "created_at": datetime(2026, 10, 10, 11, 30)},
]

# Keep track of the highest id used so add_device() assigns the next one correctly
_next_id = max(d["id"] for d in DEVICES) + 1


def _inject_counts(device_or_list):
    """
    Add live-calculated allowlisted_port_count, last_scanned, and
    last_highest_risk to one device dict or a list of device dicts.

    All three fields are computed from other mocks so they stay in sync
    without any manual updating.

    Imports are lazy (inside the function) to avoid circular imports.
    """
    from app.mock_data.admin_allowlist_mock import count_entries
    from app.mock_data.admin_scans_mock import get_latest_scan_for_device

    def _enrich(d):
        d2 = dict(d)
        d2["allowlisted_port_count"] = count_entries(d["id"])
        latest = get_latest_scan_for_device(d["id"])
        if latest:
            d2["last_scanned"]      = latest["finished_at"]
            d2["last_highest_risk"] = latest["summary"].get("highest_risk", "None")
        else:
            d2["last_scanned"]      = None
            d2["last_highest_risk"] = None
        return d2

    if isinstance(device_or_list, list):
        return [_enrich(d) for d in device_or_list]
    else:
        return _enrich(device_or_list)


# ================================================================== #
# READ FUNCTIONS
# ================================================================== #

def get_all_devices():
    """
    Return all devices sorted newest-first by created_at.
    allowlisted_port_count is injected live from admin_allowlist_mock.
    Later this becomes ORDER BY created_at DESC in the database query.
    """
    sorted_devices = sorted(DEVICES, key=lambda d: d["created_at"], reverse=True)
    return _inject_counts(sorted_devices)


def get_device_by_id(device_id):
    """
    Find and return a single device dict (with live allowlisted_port_count).
    Returns None if not found.
    """
    for device in DEVICES:
        if device["id"] == device_id:
            return _inject_counts(device)
    return None


def get_device_summary():
    """
    Return totals for the Device Registry stat strip and Dashboard card.
    never_scanned is computed live from the scan history.

    Returns:
        dict: total, active, inactive, never_scanned counts.
    """
    from app.mock_data.admin_scans_mock import get_latest_scan_for_device
    return {
        "total":          len(DEVICES),
        "active":         sum(1 for d in DEVICES if d["status"] == "active"),
        "inactive":       sum(1 for d in DEVICES if d["status"] == "inactive"),
        "never_scanned":  sum(
            1 for d in DEVICES if get_latest_scan_for_device(d["id"]) is None
        ),
    }


def get_lab_locations():
    """
    Return a sorted list of unique lab/location names.
    Used in the Lab filter dropdown and the Add/Edit form datalist.
    """
    return sorted(set(d["lab_location"] for d in DEVICES))


# ================================================================== #
# WRITE FUNCTIONS  (in-memory only — reset on server restart)
# ================================================================== #

def add_device(data):
    """
    Add a new device to the in-memory list.
    Assigns the next available id and stamps created_at with the current time
    so the device sorts to the top of get_all_devices() immediately.

    Args:
        data (dict): Keys: name, ip_address, lab_location, device_type,
                     notes, status.

    Returns:
        dict: The newly created device dict (including the assigned id).
    """
    global _next_id

    new_device = {
        "id":                    _next_id,
        "name":                  data["name"],
        "ip_address":            data["ip_address"],
        "lab_location":          data["lab_location"],
        "device_type":           data["device_type"],
        "notes":                 data.get("notes", ""),
        "status":                data.get("status", "active"),
        # New devices start with no scan history
        "last_scanned":          None,
        "last_highest_risk":     None,
        # Stamp the current time so this device sorts first (newest first)
        "created_at":            datetime.now(),
    }

    DEVICES.append(new_device)
    _next_id += 1
    return _inject_counts(new_device)


def update_device(device_id, data):
    """
    Update an existing device's editable fields in memory.
    created_at is intentionally NOT updated — editing a device must not
    move it to the top of the list.

    Args:
        device_id (int): Id of the device to update.
        data (dict): Keys: name, ip_address, lab_location, device_type,
                     notes, status.

    Returns:
        dict or None: The updated device dict, or None if not found.
    """
    device = get_device_by_id(device_id)
    if not device:
        return None

    device["name"]         = data["name"]
    device["ip_address"]   = data["ip_address"]
    device["lab_location"] = data["lab_location"]
    device["device_type"]  = data["device_type"]
    device["notes"]        = data.get("notes", "")
    device["status"]       = data.get("status", device["status"])
    # created_at is deliberately left unchanged
    return device


def delete_device(device_id):
    """
    Remove a device from the in-memory list by id.

    Returns:
        str or None: The deleted device's name, or None if not found.
    """
    device = get_device_by_id(device_id)
    if not device:
        return None

    name = device["name"]
    DEVICES[:] = [d for d in DEVICES if d["id"] != device_id]
    return name


def toggle_device_status(device_id):
    """
    Flip a device's status between "active" and "inactive".

    Returns:
        tuple (str, str) or None: (device_name, new_status), or None if not found.
    """
    device = get_device_by_id(device_id)
    if not device:
        return None

    device["status"] = "inactive" if device["status"] == "active" else "active"
    return device["name"], device["status"]
