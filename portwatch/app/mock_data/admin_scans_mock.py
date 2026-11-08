# app/mock_data/admin_scans_mock.py
# In-memory scan history for PortWatch.
# Stored in memory only — resets when the server restarts.
# Will be replaced by database functions with the same names.
#
# Each scan record stores the full findings list so the Scan Results page
# can display per-finding details without extra lookups.
#
# Pre-loaded with ~35 realistic past scans spread over 6 weeks, including:
#   • Devices scanned 3–4 times with real changes between scans
#   • One 6-device batch scan (shared job_id)
#   • Scans with custom port ranges
#   • A mix of risk levels
#   • Several scans with unacknowledged High findings

import threading
import random
from datetime import datetime, timedelta

from app.services.scan_classifier import classify_findings
from app.mock_data.mock_nmap_scanner import scan_device
from app.mock_data.admin_allowlist_mock import get_entries_for_device

# Thread lock — background scan thread writes, web threads read.
_lock = threading.Lock()

SCANS = []
_next_id = 1


# ================================================================== #
# WRITE
# ================================================================== #

def add_scan(record):
    """Store a completed scan record and assign a sequential ID."""
    global _next_id
    with _lock:
        record["id"] = f"SCN-{_next_id:05d}"
        # Ensure every finding has a unique id and an acknowledged flag
        for idx, f in enumerate(record.get("findings", [])):
            if "id" not in f:
                f["id"] = idx + 1
            if "acknowledged" not in f:
                f["acknowledged"] = False
        SCANS.append(record)
        _next_id += 1
    return record


# ================================================================== #
# READ
# ================================================================== #

def get_scan(scan_id):
    """Return a single scan record by its string id, or None."""
    with _lock:
        for s in SCANS:
            if s["id"] == scan_id:
                return s
    return None


def get_recent_scans(limit=8):
    """Return the most recent scans (newest first), up to limit."""
    with _lock:
        sorted_scans = sorted(SCANS, key=lambda s: s["started_at"], reverse=True)
    return sorted_scans[:limit]


def get_latest_scan_for_device(device_id):
    """
    Return the most recent scan for a specific device, or None.
    Used by admin_devices_mock.py to show last_scanned / last_highest_risk.
    """
    with _lock:
        device_scans = [s for s in SCANS if s.get("device_id") == device_id]
    if not device_scans:
        return None
    return max(device_scans, key=lambda s: s["started_at"])


def get_all_scans():
    """Return all scans, newest first."""
    with _lock:
        return sorted(SCANS, key=lambda s: s["started_at"], reverse=True)


def get_previous_scan(scan):
    """
    Return the scan immediately before the given scan for the same device,
    or None if this is the device's first scan.

    'Previous' means the most recent scan whose started_at is strictly
    earlier than the given scan's started_at.
    """
    device_id    = scan.get("device_id")
    current_time = scan.get("started_at")

    with _lock:
        candidates = [
            s for s in SCANS
            if s.get("device_id") == device_id
            and s.get("started_at") < current_time
            and s["id"] != scan["id"]
        ]

    if not candidates:
        return None
    return max(candidates, key=lambda s: s["started_at"])


def get_scans_this_week_count():
    """Return the number of scans started in the last 7 days.
    # Currently unused; kept for the Viewer dashboard / future use.
    """
    cutoff = datetime.now() - timedelta(days=7)
    with _lock:
        return sum(1 for s in SCANS if s.get("started_at", datetime.min) >= cutoff)


def count_unacknowledged_high():
    """Return the number of individual unacknowledged High-risk findings.
    # Currently unused; kept for the Viewer dashboard / future use.
    """
    count = 0
    with _lock:
        scans_copy = list(SCANS)
    for s in scans_copy:
        for f in s.get("findings", []):
            if f.get("risk_level") == "High" and not f.get("acknowledged", False):
                count += 1
    return count


def get_unacknowledged_high_risk_findings():
    """
    Return all individual High-risk findings that have not been acknowledged.
    Used by the Dashboard alert banner.
    """
    results = []
    with _lock:
        scans_copy = list(SCANS)
    for scan in scans_copy:
        for f in scan.get("findings", []):
            if f.get("risk_level") == "High" and not f.get("acknowledged", False):
                results.append({
                    "scan_id":     scan["id"],
                    "device_name": scan["device_name"],
                    "device_id":   scan["device_id"],
                    "port":        f["port"],
                    "label":       f["label"],
                })
    return results


def get_findings_summary_all():
    """
    Aggregate label and risk counts across ALL scans for Dashboard charts.
    """
    label_counts = {"Approved": 0, "Unexpected": 0, "Risky": 0, "Missing": 0}
    risk_counts  = {"High": 0, "Medium": 0, "Low": 0}
    open_ports_total = 0
    flagged_total    = 0

    with _lock:
        scans_copy = list(SCANS)

    for scan in scans_copy:
        summary = scan.get("summary", {})
        open_ports_total += summary.get("open_ports", 0)
        flagged_total    += summary.get("flagged", 0)
        for label, cnt in summary.get("label_counts", {}).items():
            if label in label_counts:
                label_counts[label] += cnt
        for risk, cnt in summary.get("risk_counts", {}).items():
            if risk in risk_counts:
                risk_counts[risk] += cnt

    return {
        "open_ports":   open_ports_total,
        "flagged":      flagged_total,
        "label_counts": label_counts,
        "risk_counts":  risk_counts,
        "high_risk":    risk_counts["High"],
    }


def get_next_scan(scan):
    """
    Return the scan immediately after the given scan for the same device,
    or None if this is the most recent scan of that device.
    """
    device_id    = scan.get("device_id")
    current_time = scan.get("started_at")

    with _lock:
        candidates = [
            s for s in SCANS
            if s.get("device_id") == device_id
            and s.get("started_at") > current_time
            and s["id"] != scan["id"]
        ]

    if not candidates:
        return None
    return min(candidates, key=lambda s: s["started_at"])


def acknowledge_finding(scan_id, finding_id):
    """
    Mark a single finding as acknowledged (in-memory).
    Returns True if the finding was found and updated, False otherwise.
    """
    scan = get_scan(scan_id)
    if not scan:
        return False
    with _lock:
        for f in scan.get("findings", []):
            if f.get("id") == finding_id:
                f["acknowledged"] = True
                return True
    return False


def acknowledge_all(scan_id):
    """
    Mark all Risky / Unexpected / Missing findings in a scan as acknowledged.
    Returns the count of findings that were newly acknowledged.
    """
    scan = get_scan(scan_id)
    if not scan:
        return 0
    count = 0
    with _lock:
        for f in scan.get("findings", []):
            if (f.get("label") in ("Risky", "Unexpected", "Missing")
                    and not f.get("acknowledged", False)):
                f["acknowledged"] = True
                count += 1
    return count


# ================================================================== #
# PRE-LOAD ~35 REALISTIC PAST SCANS
# ================================================================== #

def _make_record(dev_id, dev_name, ip, lab, started, duration_s=8,
                 port_spec="top1000", job_id=None):
    """Helper: run mock scan + classify and build a scan record dict."""
    finished  = started + timedelta(seconds=duration_s)
    allowlist = get_entries_for_device(dev_id)
    open_ports = scan_device(ip, port_spec, _sleep=False)  # no sleep during seeding
    result     = classify_findings(open_ports, allowlist)
    # Give every finding a unique integer id so Acknowledge routes can address them
    for idx, f in enumerate(result["findings"]):
        f["id"]             = idx + 1
        f["acknowledged"]   = False
    return {
        "id":               None,
        "job_id":           job_id or f"seed-{dev_id}-{int(started.timestamp())}",
        "device_id":        dev_id,
        "device_name":      dev_name,
        "ip_address":       ip,
        "lab_location":     lab,
        "port_spec":        port_spec,
        "started_at":       started,
        "finished_at":      finished,
        "duration_seconds": duration_s,
        "host_status":      "up",
        "findings":         result["findings"],
        "summary":          result["summary"],
    }


def _seed_scans():
    """
    Pre-load ~35 scans spread over the last 6 weeks.
    Designed to produce interesting change-detection data:
      - Devices 13 (LAB2-SERVER01) and 1 (LAB1-PC01) scanned 4 times each
      - One 6-device batch job (BATCH-001)
      - Custom port-range scans
      - A mix of High / Medium / Low risk results
    """
    now = datetime.now()

    def ago(days=0, hours=0):
        return now - timedelta(days=days, hours=hours)

    # ── Individual device scans (past 6 weeks) ──────────────────────────

    # LAB2-SERVER01 (id=13) — scanned 4 times, expect changes
    for i, (d, h, dur) in enumerate([
        (0,  9,  12),   # today
        (6,  8,  11),   # 6 days ago
        (20, 10, 10),   # 3 weeks ago
        (42, 14,  9),   # 6 weeks ago
    ]):
        add_scan(_make_record(13, "LAB2-SERVER01", "192.168.10.30",
                               "Computer Lab 2", ago(d, h), dur))

    # LAB1-PC01 (id=1) — scanned 4 times
    for d, h, dur in [(0, 12, 8), (9, 11, 8), (21, 9, 8), (40, 13, 7)]:
        add_scan(_make_record(1, "LAB1-PC01", "192.168.10.11",
                               "Computer Lab 1", ago(d, h), dur))

    # LAB1-PC03 (id=3) — 3 scans
    for d, h in [(0, 14), (7, 10), (28, 8)]:
        add_scan(_make_record(3, "LAB1-PC03", "192.168.10.13",
                               "Computer Lab 1", ago(d, h)))

    # LAB2-SERVER02 (id=14) — 3 scans
    for d, h in [(1, 16), (15, 12), (35, 9)]:
        add_scan(_make_record(14, "LAB2-SERVER02", "192.168.10.31",
                               "Computer Lab 2", ago(d, h), 11))

    # Other devices scanned once or twice
    single_scans = [
        (8,  "LAB2-PC02",     "192.168.10.22", "Computer Lab 2", 1,  7,  8),
        (2,  "LAB1-PC02",     "192.168.10.12", "Computer Lab 1", 2, 11,  8),
        (15, "LAB3-PC01",     "192.168.20.11", "Computer Lab 3", 3, 12,  8),
        (6,  "LAB1-PC06",     "192.168.10.16", "Computer Lab 1", 4, 14,  8),
        (7,  "LAB2-PC01",     "192.168.10.21", "Computer Lab 2", 5, 10,  8),
        (16, "LAB3-PC02",     "192.168.20.12", "Computer Lab 3", 5,  9,  8),
        (20, "LAB3-SERVER01", "192.168.20.30", "Server Room",    7, 13, 10),
        (19, "LAB3-SWITCH01", "192.168.20.1",  "Server Room",    8, 10,  9),
        (5,  "LAB1-PC05",     "192.168.10.15", "Computer Lab 1", 10, 9,  8),
        (10, "LAB2-PC04",     "192.168.10.24", "Computer Lab 2", 11, 8,  8),
        (17, "LAB3-PC03",     "192.168.20.13", "Computer Lab 3", 13, 7,  8),
        (7,  "LAB2-PC01",     "192.168.10.21", "Computer Lab 2", 18, 9,  8),
        (15, "LAB3-PC01",     "192.168.20.11", "Computer Lab 3", 22, 11, 8),
        (20, "LAB3-SERVER01", "192.168.20.30", "Server Room",    25, 14, 10),
        (8,  "LAB2-PC02",     "192.168.10.22", "Computer Lab 2", 30, 10, 8),
    ]
    for dev_id, dev_name, ip, lab, d, h, dur in single_scans:
        add_scan(_make_record(dev_id, dev_name, ip, lab, ago(d, h), dur))

    # ── 6-device BATCH scan (shared job_id) ────────────────────────────
    batch_id = "BATCH-20261028"
    batch_devices = [
        (1,  "LAB1-PC01",  "192.168.10.11", "Computer Lab 1"),
        (2,  "LAB1-PC02",  "192.168.10.12", "Computer Lab 1"),
        (3,  "LAB1-PC03",  "192.168.10.13", "Computer Lab 1"),
        (5,  "LAB1-PC05",  "192.168.10.15", "Computer Lab 1"),
        (6,  "LAB1-PC06",  "192.168.10.16", "Computer Lab 1"),
        (7,  "LAB2-PC01",  "192.168.10.21", "Computer Lab 2"),
    ]
    for i, (dev_id, dev_name, ip, lab) in enumerate(batch_devices):
        add_scan(_make_record(dev_id, dev_name, ip, lab,
                               ago(12, 10) + timedelta(seconds=i * 9),
                               9, "top1000", batch_id))

    # ── Custom port range scans ─────────────────────────────────────────
    add_scan(_make_record(13, "LAB2-SERVER01", "192.168.10.30",
                           "Computer Lab 2", ago(3, 11), 5, "22,80,443,3306,3389"))
    add_scan(_make_record(14, "LAB2-SERVER02", "192.168.10.31",
                           "Computer Lab 2", ago(8, 9), 5, "22,80,443,3389"))


# Run seed on first import
_seed_scans()
