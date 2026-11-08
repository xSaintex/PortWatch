# app/services/scan_job_manager.py
# Manages the full lifecycle of a PortWatch scan job.
#
# WHY A BACKGROUND THREAD?
#   A web request must respond quickly (within a second or two) or the
#   browser shows an error. A real Nmap scan takes minutes. We solve this
#   by running the scan in a background daemon thread: the web route
#   creates the job, starts the thread, and immediately redirects the
#   user to the progress page. The thread keeps running and updates a
#   shared in-memory job dict that the progress page polls via AJAX.
#
# THREAD SAFETY:
#   Multiple threads can read/write JOBS at the same time, which can
#   corrupt data. We use a threading.Lock() to ensure only one thread
#   modifies the dict at a time.

import threading
import time
import uuid
import ipaddress
from datetime import datetime
from flask import current_app

# ------------------------------------------------------------------ #
# JOB STORAGE
# ------------------------------------------------------------------ #

# All active and recently completed jobs, keyed by job_id (UUID string).
JOBS = {}
_jobs_lock = threading.Lock()   # protects JOBS from concurrent writes

# Define the stages a scan passes through so the progress page can
# show a proper stepper UI.
STAGES = [
    "Verifying authorization",
    "Running Nmap scan",
    "Parsing results",
    "Comparing with allowlist",
    "Classifying findings and risk levels",
    "Saving to scan history",
]


# ================================================================== #
# PUBLIC API
# ================================================================== #

def create_and_start_job(devices, port_spec):
    """
    Create a new scan job and immediately start it in a background thread.

    Args:
        devices   (list of dict): Device records from admin_devices_mock.
        port_spec (str):          Port range string, e.g. "top1000" or "22,80,443".

    Returns:
        str: The job_id (UUID) that the route redirects to.
    """
    job_id = str(uuid.uuid4())

    job = {
        "job_id":         job_id,
        "status":         "running",        # "running" | "completed" | "failed"
        "stage":          STAGES[0],        # current stage name
        "stage_index":    0,                # 0-based index into STAGES
        "total_stages":   len(STAGES),
        "devices":        devices,          # full list of target devices
        "devices_done":   [],               # completed devices (with results)
        "devices_total":  len(devices),
        "current_device": None,             # name of device being scanned now
        "percent":        0,
        "port_spec":      port_spec,
        "started_at":     datetime.now(),
        "finished_at":    None,
        "error":          None,
        "results_summary": None,            # filled in when complete
    }

    with _jobs_lock:
        JOBS[job_id] = job

    # Start the background thread.
    # daemon=True means the thread is killed automatically when the
    # main Flask process exits — we don't want it to keep the server alive.
    thread = threading.Thread(
        target=_run_job,
        args=(job_id,),
        daemon=True,
    )
    thread.start()

    return job_id


def get_job(job_id):
    """Return the job dict for a given job_id, or None."""
    with _jobs_lock:
        return JOBS.get(job_id)


def get_running_job():
    """
    Return the job dict of the currently running job, or None if no job
    is in progress. Used to prevent starting two scans at the same time.
    """
    with _jobs_lock:
        for job in JOBS.values():
            if job["status"] == "running":
                return job
    return None


def build_status_response(job):
    """
    Build the JSON-serialisable status dict returned by /admin/scan/status/<id>.
    Only includes fields that can be safely sent to the browser.
    """
    done_list = []
    for d in job.get("devices_done", []):
        done_list.append({
            "device_name":    d["device_name"],
            "ip_address":     d["ip_address"],
            "open_ports":     d.get("summary", {}).get("open_ports", 0),
            "flagged":        d.get("summary", {}).get("flagged", 0),
            "highest_risk":   d.get("summary", {}).get("highest_risk", "None"),
            "scan_id":        d.get("scan_id"),
        })

    return {
        "status":         job["status"],
        "stage":          job["stage"],
        "stage_index":    job["stage_index"],
        "total_stages":   job["total_stages"],
        "current_device": job["current_device"],
        "devices_done":   done_list,
        "devices_total":  job["devices_total"],
        "percent":        job["percent"],
        "error":          job["error"],
        "results_summary": job["results_summary"],
    }


# ================================================================== #
# AUTHORIZATION CHECK
# ================================================================== #

def verify_device_authorization(device):
    """
    Check that a device is allowed to be scanned.
    Rules:
      1. It must exist in the device registry (caller already found it).
      2. Its status must be "active".
      3. Its IP must be a private address (no accidental public-internet scans).

    Returns:
        (bool, str): (is_authorized, reason_if_blocked)
    """
    if device["status"] != "active":
        return False, f"{device['ip_address']} is not active."

    try:
        ip = ipaddress.ip_address(device["ip_address"])
        if not ip.is_private:
            return False, (
                f"{device['ip_address']} is a public IP address. "
                "Only private lab network devices can be scanned."
            )
    except ValueError:
        return False, f"{device['ip_address']} is not a valid IP address."

    return True, ""


# ================================================================== #
# BACKGROUND JOB RUNNER
# ================================================================== #

def _set(job, **kwargs):
    """Thread-safe helper to update job fields."""
    with _jobs_lock:
        job.update(kwargs)


def _run_job(job_id):
    """
    The main function that runs inside the background thread.
    Processes every target device one by one through the full scan pipeline.
    """
    # We need to work inside the Flask application context so we can
    # access config values and import Flask-aware modules.
    from app import create_app
    app = create_app()

    with app.app_context():
        job = JOBS[job_id]

        try:
            _execute_job(job)
        except Exception as exc:
            # Catch any unexpected error so the thread does not die silently
            _set(job,
                 status="failed",
                 error=str(exc),
                 percent=100,
                 stage="Saving to scan history",
                 stage_index=len(STAGES) - 1)
            _add_audit("scan_failed",
                       detail=f"Job {job_id} failed: {exc}")


def _execute_job(job):
    """
    The actual scan pipeline. Called from inside the background thread
    with a valid Flask application context.
    """
    from app.mock_data.admin_audit_log_mock import add_audit_entry as _add_audit_entry
    from app.mock_data.admin_allowlist_mock  import get_entries_for_device
    from app.mock_data.admin_scans_mock      import add_scan
    from app.mock_data.mock_nmap_scanner     import scan_device
    from app.services.scan_classifier        import classify_findings

    devices    = job["devices"]
    port_spec  = job["port_spec"]
    total      = len(devices)
    mock_delay = current_app.config.get("MOCK_SCAN_DURATION_SECONDS", 8)

    _add_audit_entry(
        "scan_started",
        detail=f"Scan started for {total} device(s), port spec: {port_spec}.",
    )

    # ---------------------------------------------------------------- #
    # STAGE 0: Verify authorization for ALL devices first
    # ---------------------------------------------------------------- #
    _set(job, stage=STAGES[0], stage_index=0, percent=2)
    time.sleep(0.5)   # brief pause so the UI shows the first stage

    for device in devices:
        ok, reason = verify_device_authorization(device)
        if not ok:
            _add_audit_entry(
                "scan_blocked",
                target=device["ip_address"],
                detail=f"Scan blocked: {reason}",
            )
            _set(job,
                 status="failed",
                 error=(
                     f"Scan blocked: {device['ip_address']} is not an authorized "
                     f"active lab device. Reason: {reason}. This attempt has been logged."
                 ),
                 percent=100)
            return

    # ---------------------------------------------------------------- #
    # STAGES 1–5: Process each device
    # ---------------------------------------------------------------- #
    per_device_percent = 95.0 / total   # share of the progress bar per device

    for i, device in enumerate(devices):
        device_id   = device["id"]
        device_name = device["name"]
        device_ip   = device["ip_address"]

        base_pct = 5 + i * per_device_percent

        # Stage 1: Scanning
        _set(job,
             stage=STAGES[1],
             stage_index=1,
             current_device=f"{device_name} ({device_ip})",
             percent=int(base_pct))

        # The mock scanner already sleeps internally (30% of mock_delay).
        # We also sleep here to spread time across stages.
        open_ports = scan_device(device_ip, port_spec)  # _sleep=True (default) for live scans
        time.sleep(mock_delay * 0.15)

        # Stage 2: Parsing
        _set(job, stage=STAGES[2], stage_index=2, percent=int(base_pct + per_device_percent * 0.25))
        time.sleep(mock_delay * 0.1)

        # Stage 3: Compare with allowlist
        _set(job, stage=STAGES[3], stage_index=3, percent=int(base_pct + per_device_percent * 0.5))
        allowlist = get_entries_for_device(device_id)
        time.sleep(mock_delay * 0.1)

        # Stage 4: Classify
        _set(job, stage=STAGES[4], stage_index=4, percent=int(base_pct + per_device_percent * 0.7))
        result = classify_findings(open_ports, allowlist)
        time.sleep(mock_delay * 0.1)

        # Stage 5: Save
        _set(job, stage=STAGES[5], stage_index=5, percent=int(base_pct + per_device_percent * 0.9))

        scan_record = add_scan({
            "job_id":           job["job_id"],
            "device_id":        device_id,
            "device_name":      device_name,
            "ip_address":       device_ip,
            "port_spec":        port_spec,
            "started_at":       job["started_at"],
            "finished_at":      datetime.now(),
            "duration_seconds": mock_delay,
            "host_status":      "up",
            "findings":         result["findings"],
            "summary":          result["summary"],
        })

        # Record the completed device with its summary and scan_id
        done_entry = {
            "device_id":    device_id,
            "device_name":  device_name,
            "ip_address":   device_ip,
            "summary":      result["summary"],
            "scan_id":      scan_record["id"],
        }
        with _jobs_lock:
            job["devices_done"].append(done_entry)

    # ---------------------------------------------------------------- #
    # All devices done — build results summary and mark complete
    # ---------------------------------------------------------------- #
    total_open    = sum(d["summary"].get("open_ports", 0) for d in job["devices_done"])
    total_flagged = sum(d["summary"].get("flagged",    0) for d in job["devices_done"])
    total_high    = sum(
        1 for d in job["devices_done"]
        if d["summary"].get("highest_risk") == "High"
    )

    risk_priority = {"High": 3, "Medium": 2, "Low": 1, "None": 0, None: 0}
    overall_highest = max(
        (d["summary"].get("highest_risk", "None") for d in job["devices_done"]),
        key=lambda r: risk_priority.get(r, 0),
        default="None",
    )

    results_summary = {
        "devices_scanned": total,
        "total_open":      total_open,
        "total_flagged":   total_flagged,
        "high_risk_devices": total_high,
        "highest_risk":    overall_highest,
        "devices_done":    job["devices_done"],
    }

    _add_audit_entry(
        "scan_completed",
        detail=(
            f"Scan completed: {total} device(s), "
            f"{total_open} open ports, {total_flagged} flagged, "
            f"highest risk: {overall_highest}."
        ),
    )

    _set(job,
         status="completed",
         stage=STAGES[5],
         stage_index=len(STAGES) - 1,
         percent=100,
         current_device=None,
         finished_at=datetime.now(),
         results_summary=results_summary)


def _add_audit(action, target=None, detail=None):
    """Convenience wrapper for audit logging inside the job runner."""
    try:
        from app.mock_data.admin_audit_log_mock import add_audit_entry
        add_audit_entry(action, target=target, detail=detail)
    except Exception:
        pass   # audit errors must never crash the scan
