# app/mock_data/admin_allowlist_mock.py
# In-memory mock data for allowlist entries.
#
# IMPORTANT: Stored in memory only, resets when the server restarts.
# These functions will be replaced by database functions with the same
# names later — the rest of the app will not need to change.
#
# CIRCULAR IMPORT NOTE:
#   This file does NOT import from admin_devices_mock.py.
#   admin_devices_mock.py calls count_entries() from THIS file to
#   calculate allowlisted_port_count dynamically. The dependency is
#   one-way only (devices → allowlist), which avoids a circular import.
#
# TODO: Replace all functions here with real SQLAlchemy database queries
#       once Flask-SQLAlchemy is set up.

from datetime import datetime


# ------------------------------------------------------------------ #
# ENTRY LIST
#
# Keys:
#   id            — unique integer id (auto-assigned by add_entry)
#   device_id     — foreign key to the device this entry belongs to
#   port          — integer port number (1–65535)
#   protocol      — "tcp" or "udp"
#   service       — Nmap service name string (e.g. "ssh", "http")
#   expected_open — bool: if True, flag as Missing when port is closed
#   notes         — optional free text (max 200 chars)
#   created_at    — datetime when this entry was added
# ------------------------------------------------------------------ #

ENTRIES = [
    # ---------------------------------------------------------------- #
    # LAB1-PC01 (id=1) — Standard student workstation: 3 entries
    # ---------------------------------------------------------------- #
    {"id": 101, "device_id": 1, "port": 135, "protocol": "tcp", "service": "msrpc",         "expected_open": True,  "notes": "Required for Windows RPC.",              "created_at": datetime(2026, 10, 2, 9, 0)},
    {"id": 102, "device_id": 1, "port": 139, "protocol": "tcp", "service": "netbios-ssn",   "expected_open": True,  "notes": "Windows file sharing.",                  "created_at": datetime(2026, 10, 2, 9, 1)},
    {"id": 103, "device_id": 1, "port": 445, "protocol": "tcp", "service": "microsoft-ds",  "expected_open": True,  "notes": "SMB — shared drives for student files.",  "created_at": datetime(2026, 10, 2, 9, 2)},

    # ---------------------------------------------------------------- #
    # LAB1-PC02 (id=2) — 3 entries (same as PC01)
    # ---------------------------------------------------------------- #
    {"id": 201, "device_id": 2, "port": 135, "protocol": "tcp", "service": "msrpc",         "expected_open": True,  "notes": "Required for Windows RPC.",              "created_at": datetime(2026, 10, 2, 9, 10)},
    {"id": 202, "device_id": 2, "port": 139, "protocol": "tcp", "service": "netbios-ssn",   "expected_open": True,  "notes": "Windows file sharing.",                  "created_at": datetime(2026, 10, 2, 9, 11)},
    {"id": 203, "device_id": 2, "port": 445, "protocol": "tcp", "service": "microsoft-ds",  "expected_open": True,  "notes": "SMB — shared drives.",                   "created_at": datetime(2026, 10, 2, 9, 12)},

    # ---------------------------------------------------------------- #
    # LAB1-PC03 (id=3) — 3 entries
    # ---------------------------------------------------------------- #
    {"id": 301, "device_id": 3, "port": 135, "protocol": "tcp", "service": "msrpc",         "expected_open": True,  "notes": "Required for Windows RPC.",              "created_at": datetime(2026, 10, 2, 9, 20)},
    {"id": 302, "device_id": 3, "port": 139, "protocol": "tcp", "service": "netbios-ssn",   "expected_open": True,  "notes": "Windows file sharing.",                  "created_at": datetime(2026, 10, 2, 9, 21)},
    {"id": 303, "device_id": 3, "port": 445, "protocol": "tcp", "service": "microsoft-ds",  "expected_open": True,  "notes": "SMB — shared drives.",                   "created_at": datetime(2026, 10, 2, 9, 22)},

    # ---------------------------------------------------------------- #
    # LAB1-PC04 (id=4) — 3 entries (inactive device)
    # ---------------------------------------------------------------- #
    {"id": 401, "device_id": 4, "port": 135, "protocol": "tcp", "service": "msrpc",         "expected_open": True,  "notes": "Required for Windows RPC.",              "created_at": datetime(2026, 10, 2, 9, 30)},
    {"id": 402, "device_id": 4, "port": 139, "protocol": "tcp", "service": "netbios-ssn",   "expected_open": True,  "notes": "Windows file sharing.",                  "created_at": datetime(2026, 10, 2, 9, 31)},
    {"id": 403, "device_id": 4, "port": 445, "protocol": "tcp", "service": "microsoft-ds",  "expected_open": True,  "notes": "SMB — shared drives.",                   "created_at": datetime(2026, 10, 2, 9, 32)},

    # ---------------------------------------------------------------- #
    # LAB1-PC05 (id=5) — 3 entries
    # ---------------------------------------------------------------- #
    {"id": 501, "device_id": 5, "port": 135, "protocol": "tcp", "service": "msrpc",         "expected_open": True,  "notes": "Required for Windows RPC.",              "created_at": datetime(2026, 10, 2, 9, 40)},
    {"id": 502, "device_id": 5, "port": 139, "protocol": "tcp", "service": "netbios-ssn",   "expected_open": True,  "notes": "Windows file sharing.",                  "created_at": datetime(2026, 10, 2, 9, 41)},
    {"id": 503, "device_id": 5, "port": 445, "protocol": "tcp", "service": "microsoft-ds",  "expected_open": True,  "notes": "SMB — shared drives.",                   "created_at": datetime(2026, 10, 2, 9, 42)},

    # ---------------------------------------------------------------- #
    # LAB1-PC06 (id=6) — Instructor PC: 5 entries (includes RDP)
    # ---------------------------------------------------------------- #
    {"id": 601, "device_id": 6, "port": 135,  "protocol": "tcp", "service": "msrpc",        "expected_open": True,  "notes": "Required for Windows RPC.",                          "created_at": datetime(2026, 10, 2, 10, 0)},
    {"id": 602, "device_id": 6, "port": 139,  "protocol": "tcp", "service": "netbios-ssn",  "expected_open": True,  "notes": "Windows file sharing.",                              "created_at": datetime(2026, 10, 2, 10, 1)},
    {"id": 603, "device_id": 6, "port": 445,  "protocol": "tcp", "service": "microsoft-ds", "expected_open": True,  "notes": "SMB — class file sharing for demos.",                "created_at": datetime(2026, 10, 2, 10, 2)},
    {"id": 604, "device_id": 6, "port": 3389, "protocol": "tcp", "service": "ms-wbt-server","expected_open": True,  "notes": "RDP — IT staff access for software installation.",   "created_at": datetime(2026, 10, 2, 10, 3)},
    {"id": 605, "device_id": 6, "port": 8080, "protocol": "tcp", "service": "http-proxy",   "expected_open": False, "notes": "Dev server for class demos (not always running).",   "created_at": datetime(2026, 10, 2, 10, 4)},

    # ---------------------------------------------------------------- #
    # LAB2-PC01 (id=7) — 4 entries (includes RDP)
    # ---------------------------------------------------------------- #
    {"id": 701, "device_id": 7, "port": 135,  "protocol": "tcp", "service": "msrpc",        "expected_open": True,  "notes": "Required for Windows RPC.",                        "created_at": datetime(2026, 10, 4, 9, 0)},
    {"id": 702, "device_id": 7, "port": 139,  "protocol": "tcp", "service": "netbios-ssn",  "expected_open": True,  "notes": "Windows file sharing.",                            "created_at": datetime(2026, 10, 4, 9, 1)},
    {"id": 703, "device_id": 7, "port": 445,  "protocol": "tcp", "service": "microsoft-ds", "expected_open": True,  "notes": "SMB — shared drives.",                             "created_at": datetime(2026, 10, 4, 9, 2)},
    {"id": 704, "device_id": 7, "port": 3389, "protocol": "tcp", "service": "ms-wbt-server","expected_open": False, "notes": "RDP — only used occasionally by IT.",               "created_at": datetime(2026, 10, 4, 9, 3)},

    # ---------------------------------------------------------------- #
    # LAB2-PC02 (id=8) — 4 entries
    # ---------------------------------------------------------------- #
    {"id": 801, "device_id": 8, "port": 135,  "protocol": "tcp", "service": "msrpc",        "expected_open": True,  "notes": "Required for Windows RPC.",  "created_at": datetime(2026, 10, 4, 9, 10)},
    {"id": 802, "device_id": 8, "port": 139,  "protocol": "tcp", "service": "netbios-ssn",  "expected_open": True,  "notes": "Windows file sharing.",      "created_at": datetime(2026, 10, 4, 9, 11)},
    {"id": 803, "device_id": 8, "port": 445,  "protocol": "tcp", "service": "microsoft-ds", "expected_open": True,  "notes": "SMB — shared drives.",       "created_at": datetime(2026, 10, 4, 9, 12)},
    {"id": 804, "device_id": 8, "port": 3389, "protocol": "tcp", "service": "ms-wbt-server","expected_open": False, "notes": "RDP — IT access only.",       "created_at": datetime(2026, 10, 4, 9, 13)},

    # ---------------------------------------------------------------- #
    # LAB2-PC03 (id=9) — 4 entries (inactive device)
    # ---------------------------------------------------------------- #
    {"id": 901, "device_id": 9, "port": 135,  "protocol": "tcp", "service": "msrpc",        "expected_open": True, "notes": "Required for Windows RPC.",   "created_at": datetime(2026, 10, 4, 9, 20)},
    {"id": 902, "device_id": 9, "port": 139,  "protocol": "tcp", "service": "netbios-ssn",  "expected_open": True, "notes": "Windows file sharing.",       "created_at": datetime(2026, 10, 4, 9, 21)},
    {"id": 903, "device_id": 9, "port": 445,  "protocol": "tcp", "service": "microsoft-ds", "expected_open": True, "notes": "SMB — shared drives.",        "created_at": datetime(2026, 10, 4, 9, 22)},
    {"id": 904, "device_id": 9, "port": 3389, "protocol": "tcp", "service": "ms-wbt-server","expected_open": True, "notes": "RDP — IT access only.",        "created_at": datetime(2026, 10, 4, 9, 23)},

    # ---------------------------------------------------------------- #
    # LAB2-PC04 (id=10) — 4 entries
    # ---------------------------------------------------------------- #
    {"id": 1001, "device_id": 10, "port": 135,  "protocol": "tcp", "service": "msrpc",        "expected_open": True,  "notes": "Required for Windows RPC.",  "created_at": datetime(2026, 10, 4, 9, 30)},
    {"id": 1002, "device_id": 10, "port": 139,  "protocol": "tcp", "service": "netbios-ssn",  "expected_open": True,  "notes": "Windows file sharing.",      "created_at": datetime(2026, 10, 4, 9, 31)},
    {"id": 1003, "device_id": 10, "port": 445,  "protocol": "tcp", "service": "microsoft-ds", "expected_open": True,  "notes": "SMB — shared drives.",       "created_at": datetime(2026, 10, 4, 9, 32)},
    {"id": 1004, "device_id": 10, "port": 3389, "protocol": "tcp", "service": "ms-wbt-server","expected_open": False, "notes": "RDP — IT access only.",       "created_at": datetime(2026, 10, 4, 9, 33)},

    # ---------------------------------------------------------------- #
    # LAB2-PC05 (id=11) — 0 entries (never configured)
    # ---------------------------------------------------------------- #
    # (no entries — device shows "None set" in the registry)

    # ---------------------------------------------------------------- #
    # LAB2-PC06 (id=12) — 0 entries (never configured)
    # ---------------------------------------------------------------- #
    # (no entries — device shows "None set" in the registry)

    # ---------------------------------------------------------------- #
    # LAB2-SERVER01 (id=13) — 9 entries (web + db + admin)
    # Intentionally 9+ so the Manage view shows 2 pages (8 per page).
    # ---------------------------------------------------------------- #
    {"id": 1301, "device_id": 13, "port": 22,   "protocol": "tcp", "service": "ssh",          "expected_open": True,  "notes": "SSH — admin access.",                        "created_at": datetime(2026, 10, 6, 10, 0)},
    {"id": 1302, "device_id": 13, "port": 80,   "protocol": "tcp", "service": "http",         "expected_open": True,  "notes": "HTTP — web service.",                        "created_at": datetime(2026, 10, 6, 10, 1)},
    {"id": 1303, "device_id": 13, "port": 443,  "protocol": "tcp", "service": "https",        "expected_open": True,  "notes": "HTTPS — encrypted web service.",             "created_at": datetime(2026, 10, 6, 10, 2)},
    {"id": 1304, "device_id": 13, "port": 3306, "protocol": "tcp", "service": "mysql",        "expected_open": True,  "notes": "MySQL — class database.",                    "created_at": datetime(2026, 10, 6, 10, 3)},
    {"id": 1305, "device_id": 13, "port": 445,  "protocol": "tcp", "service": "microsoft-ds", "expected_open": True,  "notes": "SMB — file server shares.",                  "created_at": datetime(2026, 10, 6, 10, 4)},
    {"id": 1306, "device_id": 13, "port": 3389, "protocol": "tcp", "service": "ms-wbt-server","expected_open": True,  "notes": "RDP — IT admin access.",                     "created_at": datetime(2026, 10, 6, 10, 5)},
    {"id": 1307, "device_id": 13, "port": 8080, "protocol": "tcp", "service": "http-proxy",   "expected_open": False, "notes": "Staging web service (may not always run).",  "created_at": datetime(2026, 10, 6, 10, 6)},
    {"id": 1308, "device_id": 13, "port": 25,   "protocol": "tcp", "service": "smtp",         "expected_open": True,  "notes": "SMTP — outgoing mail for notifications.",    "created_at": datetime(2026, 10, 6, 10, 7)},
    {"id": 1309, "device_id": 13, "port": 8443, "protocol": "tcp", "service": "https-alt",    "expected_open": False, "notes": "HTTPS alternate port for management UI.",    "created_at": datetime(2026, 10, 6, 10, 8)},

    # ---------------------------------------------------------------- #
    # LAB2-SERVER02 (id=14) — 5 entries (backup server)
    # ---------------------------------------------------------------- #
    {"id": 1401, "device_id": 14, "port": 22,   "protocol": "tcp", "service": "ssh",          "expected_open": True,  "notes": "SSH — admin access.",          "created_at": datetime(2026, 10, 6, 11, 0)},
    {"id": 1402, "device_id": 14, "port": 80,   "protocol": "tcp", "service": "http",         "expected_open": False, "notes": "Management web UI.",           "created_at": datetime(2026, 10, 6, 11, 1)},
    {"id": 1403, "device_id": 14, "port": 443,  "protocol": "tcp", "service": "https",        "expected_open": True,  "notes": "Encrypted management web UI.", "created_at": datetime(2026, 10, 6, 11, 2)},
    {"id": 1404, "device_id": 14, "port": 445,  "protocol": "tcp", "service": "microsoft-ds", "expected_open": True,  "notes": "SMB — backup file shares.",    "created_at": datetime(2026, 10, 6, 11, 3)},
    {"id": 1405, "device_id": 14, "port": 3389, "protocol": "tcp", "service": "ms-wbt-server","expected_open": True,  "notes": "RDP — IT admin access.",       "created_at": datetime(2026, 10, 6, 11, 4)},

    # ---------------------------------------------------------------- #
    # LAB3-PC01 (id=15) — 3 entries
    # ---------------------------------------------------------------- #
    {"id": 1501, "device_id": 15, "port": 135, "protocol": "tcp", "service": "msrpc",        "expected_open": True, "notes": "Required for Windows RPC.", "created_at": datetime(2026, 10, 9, 9, 0)},
    {"id": 1502, "device_id": 15, "port": 139, "protocol": "tcp", "service": "netbios-ssn",  "expected_open": True, "notes": "Windows file sharing.",     "created_at": datetime(2026, 10, 9, 9, 1)},
    {"id": 1503, "device_id": 15, "port": 445, "protocol": "tcp", "service": "microsoft-ds", "expected_open": True, "notes": "SMB — shared drives.",      "created_at": datetime(2026, 10, 9, 9, 2)},

    # ---------------------------------------------------------------- #
    # LAB3-PC02 (id=16) — 3 entries
    # ---------------------------------------------------------------- #
    {"id": 1601, "device_id": 16, "port": 135, "protocol": "tcp", "service": "msrpc",        "expected_open": True, "notes": "Required for Windows RPC.", "created_at": datetime(2026, 10, 9, 9, 10)},
    {"id": 1602, "device_id": 16, "port": 139, "protocol": "tcp", "service": "netbios-ssn",  "expected_open": True, "notes": "Windows file sharing.",     "created_at": datetime(2026, 10, 9, 9, 11)},
    {"id": 1603, "device_id": 16, "port": 445, "protocol": "tcp", "service": "microsoft-ds", "expected_open": True, "notes": "SMB — shared drives.",      "created_at": datetime(2026, 10, 9, 9, 12)},

    # ---------------------------------------------------------------- #
    # LAB3-PC03 (id=17) — 3 entries
    # ---------------------------------------------------------------- #
    {"id": 1701, "device_id": 17, "port": 135, "protocol": "tcp", "service": "msrpc",        "expected_open": True, "notes": "Required for Windows RPC.", "created_at": datetime(2026, 10, 9, 9, 20)},
    {"id": 1702, "device_id": 17, "port": 139, "protocol": "tcp", "service": "netbios-ssn",  "expected_open": True, "notes": "Windows file sharing.",     "created_at": datetime(2026, 10, 9, 9, 21)},
    {"id": 1703, "device_id": 17, "port": 445, "protocol": "tcp", "service": "microsoft-ds", "expected_open": True, "notes": "SMB — shared drives.",      "created_at": datetime(2026, 10, 9, 9, 22)},

    # ---------------------------------------------------------------- #
    # LAB3-PC04 (id=18) — 0 entries (device with no allowlist)
    # ---------------------------------------------------------------- #
    # (no entries)

    # ---------------------------------------------------------------- #
    # LAB3-SWITCH01 (id=19) — 4 entries (network device, includes telnet)
    # ---------------------------------------------------------------- #
    {"id": 1901, "device_id": 19, "port": 22,  "protocol": "tcp", "service": "ssh",    "expected_open": True,  "notes": "SSH management access.",                   "created_at": datetime(2026, 10, 11, 10, 0)},
    {"id": 1902, "device_id": 19, "port": 23,  "protocol": "tcp", "service": "telnet", "expected_open": False, "notes": "Legacy telnet — only old firmware.",       "created_at": datetime(2026, 10, 11, 10, 1)},
    {"id": 1903, "device_id": 19, "port": 80,  "protocol": "tcp", "service": "http",   "expected_open": True,  "notes": "Web management interface.",                "created_at": datetime(2026, 10, 11, 10, 2)},
    {"id": 1904, "device_id": 19, "port": 161, "protocol": "udp", "service": "snmp",   "expected_open": True,  "notes": "SNMP monitoring by network management.",   "created_at": datetime(2026, 10, 11, 10, 3)},

    # ---------------------------------------------------------------- #
    # LAB3-SERVER01 (id=20) — 6 entries (storage server)
    # ---------------------------------------------------------------- #
    {"id": 2001, "device_id": 20, "port": 22,   "protocol": "tcp", "service": "ssh",          "expected_open": True,  "notes": "SSH — admin access.",                "created_at": datetime(2026, 10, 11, 11, 0)},
    {"id": 2002, "device_id": 20, "port": 80,   "protocol": "tcp", "service": "http",         "expected_open": False, "notes": "Management UI (not always active).", "created_at": datetime(2026, 10, 11, 11, 1)},
    {"id": 2003, "device_id": 20, "port": 443,  "protocol": "tcp", "service": "https",        "expected_open": True,  "notes": "Encrypted management UI.",           "created_at": datetime(2026, 10, 11, 11, 2)},
    {"id": 2004, "device_id": 20, "port": 445,  "protocol": "tcp", "service": "microsoft-ds", "expected_open": True,  "notes": "SMB — network storage shares.",      "created_at": datetime(2026, 10, 11, 11, 3)},
    {"id": 2005, "device_id": 20, "port": 3389, "protocol": "tcp", "service": "ms-wbt-server","expected_open": True,  "notes": "RDP — IT admin access.",             "created_at": datetime(2026, 10, 11, 11, 4)},
    {"id": 2006, "device_id": 20, "port": 5432, "protocol": "tcp", "service": "postgresql",   "expected_open": True,  "notes": "PostgreSQL — storage metadata DB.",  "created_at": datetime(2026, 10, 11, 11, 5)},
]

# Auto-increment counter for new entries
_next_entry_id = max(e["id"] for e in ENTRIES) + 1


# ================================================================== #
# READ FUNCTIONS
# ================================================================== #

def get_entries_for_device(device_id):
    """
    Return all allowlist entries for a device, sorted by port number.
    Sorted ascending so the table is easy to scan.
    """
    return sorted(
        [e for e in ENTRIES if e["device_id"] == device_id],
        key=lambda e: e["port"]
    )


def get_entry(entry_id):
    """
    Return a single entry dict by its id, or None if not found.
    Returns the actual dict (mutable) so callers can update it in place.
    """
    for entry in ENTRIES:
        if entry["id"] == entry_id:
            return entry
    return None


def count_entries(device_id):
    """
    Count how many allowlist entries a device has.
    Called by admin_devices_mock.py to populate allowlisted_port_count
    dynamically so Device Registry and Dashboard counts stay in sync.
    """
    return sum(1 for e in ENTRIES if e["device_id"] == device_id)


def count_required(device_id):
    """
    Count entries with expected_open=True (flagged as Missing when closed).
    """
    return sum(1 for e in ENTRIES if e["device_id"] == device_id and e["expected_open"])


def count_risky(device_id):
    """
    Count entries whose port is marked risky in port_reference.py.
    Imported lazily to keep this module independent of utils.
    """
    from app.utils.port_reference import is_risky_port
    return sum(1 for e in ENTRIES if e["device_id"] == device_id and is_risky_port(e["port"]))


# ================================================================== #
# WRITE FUNCTIONS
# ================================================================== #

def add_entry(device_id, data):
    """
    Add a new allowlist entry for a device.
    Stamps created_at with the current datetime.

    Args:
        device_id (int): The device this entry belongs to.
        data (dict): Keys: port, protocol, service, expected_open, notes.

    Returns:
        dict: The new entry dict including its assigned id.
    """
    global _next_entry_id

    new_entry = {
        "id":            _next_entry_id,
        "device_id":     device_id,
        "port":          int(data["port"]),
        "protocol":      data["protocol"].lower(),
        "service":       data["service"].lower().strip(),
        "expected_open": bool(data.get("expected_open", False)),
        "notes":         data.get("notes", "").strip(),
        "created_at":    datetime.now(),
    }

    ENTRIES.append(new_entry)
    _next_entry_id += 1
    return new_entry


def update_entry(entry_id, data):
    """
    Update an existing allowlist entry's editable fields.
    created_at is not changed (editing should not re-order the table).

    Args:
        entry_id (int): The entry to update.
        data (dict): Keys: port, protocol, service, expected_open, notes.

    Returns:
        dict or None: The updated entry, or None if not found.
    """
    entry = get_entry(entry_id)
    if not entry:
        return None

    entry["port"]          = int(data["port"])
    entry["protocol"]      = data["protocol"].lower()
    entry["service"]       = data["service"].lower().strip()
    entry["expected_open"] = bool(data.get("expected_open", False))
    entry["notes"]         = data.get("notes", "").strip()
    return entry


def delete_entry(entry_id):
    """
    Remove an entry from the in-memory list.

    Returns:
        dict or None: The deleted entry dict (for flash messages), or None.
    """
    entry = get_entry(entry_id)
    if not entry:
        return None

    ENTRIES[:] = [e for e in ENTRIES if e["id"] != entry_id]
    return entry


def copy_entries(source_id, target_id, mode):
    """
    Copy allowlist entries from one device to another.

    Args:
        source_id (int): Device to copy FROM.
        target_id (int): Device to copy TO.
        mode (str): "merge" — skip entries already on target (same port+protocol).
                    "replace" — delete all target entries first.

    Returns:
        tuple (int, int): (copied_count, skipped_count).
    """
    global _next_entry_id

    source_entries = get_entries_for_device(source_id)

    if mode == "replace":
        # Remove all existing entries on the target device
        ENTRIES[:] = [e for e in ENTRIES if e["device_id"] != target_id]

    # Build a set of (port, protocol) already on the target (after possible removal)
    existing = {
        (e["port"], e["protocol"])
        for e in ENTRIES
        if e["device_id"] == target_id
    }

    copied  = 0
    skipped = 0

    for src in source_entries:
        key = (src["port"], src["protocol"])
        if key in existing:
            skipped += 1
            continue

        new_entry = {
            "id":            _next_entry_id,
            "device_id":     target_id,
            "port":          src["port"],
            "protocol":      src["protocol"],
            "service":       src["service"],
            "expected_open": src["expected_open"],
            "notes":         src["notes"],
            "created_at":    datetime.now(),
        }
        ENTRIES.append(new_entry)
        existing.add(key)
        _next_entry_id += 1
        copied += 1

    return copied, skipped
