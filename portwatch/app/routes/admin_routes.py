# app/routes/admin_routes.py
# All URL routes for the Administrator role in PortWatch.
# Every URL here starts with /admin (set by url_prefix below).
#
# HOW BLUEPRINTS WORK:
#   A Blueprint is like a mini-app. We define routes here, then register
#   this Blueprint in app/__init__.py so Flask knows about them.

import ipaddress
import re as _re
from flask import Blueprint, render_template, redirect, url_for, request, flash
from app.mock_data.admin_dashboard_mock import get_admin_dashboard_data
from app.mock_data.admin_devices_mock import (
    get_all_devices,
    get_device_by_id,
    # get_device_summary is still used by admin_dashboard_mock.py (Dashboard).
    # It is no longer called here directly because the Device Registry stat
    # cards were removed from the template.
    get_lab_locations,
    add_device,
    update_device,
    delete_device,
    toggle_device_status,
)
from app.mock_data.admin_allowlist_mock import (
    get_entries_for_device,
    get_entry,
    count_entries,
    count_required,
    count_risky,
    add_entry,
    update_entry,
    delete_entry,
    copy_entries,
)
from app.utils.port_reference import PORT_REFERENCE, get_port_info, is_risky_port

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
def require_admin():
    """
    Protect every /admin route with a single before_request hook.
    This is equivalent to applying @admin_required to every route function,
    but in one place — easier to maintain and impossible to forget on a new route.
    """
    from flask_login import current_user as _cu
    from app.mock_data.admin_audit_log_mock import add_audit_entry

    if not _cu.is_authenticated:
        # Redirect silently — the login page is self-explanatory
        return redirect(url_for("auth.login", next=request.path))

    if _cu.role != "administrator":
        add_audit_entry(
            "access_denied",
            user=_cu.username,
            target=request.path,
            detail=f"Viewer @{_cu.username} tried to access admin page: {request.path}",
            category="Security",
            result="blocked",
        )
        from flask import flash as _flash
        _flash("You don't have permission to access that page.", "error")
        return redirect(url_for("viewer.dashboard"))

# ------------------------------------------------------------------ #
# ROOT REDIRECT — separate Blueprint so it can handle "/"
# (admin_bp has url_prefix="/admin" so it cannot own "/" directly)
# ------------------------------------------------------------------ #
from flask import Blueprint as _Blueprint
root_bp = _Blueprint("root", __name__)

@root_bp.route("/")
def index():
    """
    Site root — send users to their role dashboard, or to login if not signed in.
    """
    from flask_login import current_user
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.role == "administrator":
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("viewer.dashboard"))


# ================================================================== #
# VALIDATION HELPER
# ================================================================== #

def validate_device_form(name, ip_str, lab_location, device_type, notes,
                         editing_id=None):
    """
    Validate Add/Edit Device form data server-side.

    Returns a dict mapping field names to error strings.
    An empty dict means all checks passed.

    Args:
        name         (str): Device hostname.
        ip_str       (str): Raw IPv4 string from the form.
        lab_location (str): Lab name.
        device_type  (str): Must be one of the four allowed values.
        notes        (str): Optional free text.
        editing_id   (int|None): When editing, skip uniqueness checks for
                     this device's own name/IP.
    """
    errors = {}   # field_name -> message

    # ---- Device Name ----
    if not name:
        errors["name"] = "Device name is required."
    elif len(name) > 50:
        errors["name"] = "Device name must be 50 characters or fewer."
    else:
        for d in get_all_devices():
            if d["name"].lower() == name.lower() and d["id"] != editing_id:
                errors["name"] = "A device with this name already exists."
                break

    # ---- IP Address ----
    if not ip_str:
        errors["ip_address"] = "IP address is required."
    else:
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            if not isinstance(ip_obj, ipaddress.IPv4Address):
                errors["ip_address"] = "Only IPv4 addresses are supported."
            elif not ip_obj.is_private:
                # Reject public IPs — lab devices must be on a private network
                errors["ip_address"] = (
                    "Only private lab network addresses can be registered "
                    "(e.g. 192.168.x.x, 10.x.x.x, 172.16–31.x.x)."
                )
            else:
                for d in get_all_devices():
                    if d["ip_address"] == ip_str and d["id"] != editing_id:
                        errors["ip_address"] = (
                            f"This IP address is already registered to '{d['name']}'."
                        )
                        break
        except ValueError:
            errors["ip_address"] = f"'{ip_str}' is not a valid IPv4 address."

    # ---- Lab / Location ----
    if not lab_location:
        errors["lab_location"] = "Lab / Location is required."

    # ---- Device Type ----
    allowed_types = ["Workstation", "Server", "Network Device", "Other"]
    if not device_type:
        errors["device_type"] = "Device type is required."
    elif device_type not in allowed_types:
        errors["device_type"] = (
            f"Device type must be one of: {', '.join(allowed_types)}."
        )

    # ---- Notes (optional) ----
    if notes and len(notes) > 200:
        errors["notes"] = "Notes must be 200 characters or fewer."

    return errors


# ================================================================== #
# DASHBOARD
# ================================================================== #

# TODO: protect with Flask-Login admin role check
@admin_bp.route("/dashboard")
def dashboard():
    """Admin dashboard — summary of devices and latest scan findings."""
    data = get_admin_dashboard_data()
    return render_template(
        "admin/admin_dashboard.html",
        active_page="dashboard",
        **data,
    )


# ================================================================== #
# DEVICE REGISTRY
# ================================================================== #

# TODO: protect with Flask-Login admin role check
@admin_bp.route("/devices")
def devices():
    """Device Registry — full list of registered lab devices."""
    # When the page is opened after a successful add, the route includes
    # ?new_device=<id> so the template can mark that row for highlighting.
    new_device_id = request.args.get("new_device", type=int)

    return render_template(
        "admin/admin_device_registry.html",
        active_page="devices",
        devices=get_all_devices(),
        # summary= removed; stat cards were removed from the template.
        # get_device_summary() is still used by admin_dashboard_mock.py.
        lab_locations=get_lab_locations(),
        # No active modal or form errors on a fresh GET request
        open_device_modal=False,
        form_errors={},
        form_data={},
        # None unless the user just added a device; used for highlight + scroll
        new_device_id=new_device_id,
    )


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/devices/add", methods=["POST"])
def devices_add():
    """
    Handle the Add Device form POST.

    SUCCESS path:
      - Add the device to memory with add_device().
      - Flash a success message with a link to set up the allowlist.
      - Redirect back to GET /admin/devices.
      WHY redirect instead of re-rendering directly:
        Post/Redirect/Get (PRG) pattern. If we rendered the page directly
        on success and the user pressed F5 (refresh), the browser would
        re-submit the POST, creating a duplicate device. Redirecting to the
        GET route makes the refresh-after-submit safe.

    ERROR path:
      - Do NOT redirect. Re-render the page with the modal already open,
        the typed values pre-filled, and error messages under each field.
        This way the user does not lose what they typed.
    """
    # Read and strip all form fields
    name         = request.form.get("name",         "").strip()
    ip_address   = request.form.get("ip_address",   "").strip()
    lab_location = request.form.get("lab_location", "").strip()
    device_type  = request.form.get("device_type",  "").strip()
    # Checkbox: present in form = "active", absent = "inactive"
    status       = "active" if request.form.get("status") else "inactive"
    notes        = request.form.get("notes",        "").strip()

    form_data = {
        "name":         name,
        "ip_address":   ip_address,
        "lab_location": lab_location,
        "device_type":  device_type,
        "status":       status,
        "notes":        notes,
    }

    errors = validate_device_form(name, ip_address, lab_location,
                                  device_type, notes)

    if errors:
        # Re-render the page with the modal open and errors shown inline.
        # open_device_modal=True tells the template to auto-open the modal.
        return render_template(
            "admin/admin_device_registry.html",
            active_page="devices",
            devices=get_all_devices(),
            lab_locations=get_lab_locations(),
            open_device_modal=True,
            form_errors=errors,
            form_data=form_data,
            new_device_id=None,
        )

    # Validation passed — add the device
    new_device = add_device(form_data)

    # TODO: save to database — replace add_device() with a DB insert here

    # Build the success flash: name + a link to set up the allowlist
    allowlist_url = url_for("admin.allowlist") + f"?device_id={new_device['id']}"
    flash(
        f"'{new_device['name']}' was added to the registry. "
        f'<a href="{allowlist_url}" class="pw-flash-link">Set up allowlist →</a>',
        "success",
    )

    # PRG: redirect to the GET route so F5 doesn't resubmit the form.
    # Include the new device's id as ?new_device=<id> so the page can
    # scroll to it, highlight it, and show it on page 1.
    return redirect(url_for("admin.devices", new_device=new_device["id"]))


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/devices/<int:device_id>/edit", methods=["POST"])
def devices_edit(device_id):
    """Handle the Edit Device form POST."""
    device = get_device_by_id(device_id)
    if not device:
        flash("Device not found.", "error")
        return redirect(url_for("admin.devices"))

    name         = request.form.get("name",         "").strip()
    ip_address   = request.form.get("ip_address",   "").strip()
    lab_location = request.form.get("lab_location", "").strip()
    device_type  = request.form.get("device_type",  "").strip()
    status       = "active" if request.form.get("status") else "inactive"
    notes        = request.form.get("notes",        "").strip()

    errors = validate_device_form(name, ip_address, lab_location,
                                  device_type, notes, editing_id=device_id)

    if errors:
        for msg in errors.values():
            flash(msg, "error")
        return redirect(url_for("admin.devices"))

    update_device(device_id, {
        "name":         name,
        "ip_address":   ip_address,
        "lab_location": lab_location,
        "device_type":  device_type,
        "status":       status,
        "notes":        notes,
    })

    # TODO: save to database — replace update_device() with a DB update here
    flash(f"'{name}' was updated.", "success")
    return redirect(url_for("admin.devices"))


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/devices/<int:device_id>/toggle-status", methods=["POST"])
def devices_toggle_status(device_id):
    """Activate or deactivate a device without deleting it."""
    result = toggle_device_status(device_id)
    if not result:
        flash("Device not found.", "error")
        return redirect(url_for("admin.devices"))

    device_name, new_status = result
    action_word = "activated" if new_status == "active" else "deactivated"

    # TODO: save to database — replace toggle_device_status() with a DB update
    flash(f"'{device_name}' was {action_word}.", "success")
    return redirect(url_for("admin.devices"))


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/devices/<int:device_id>/delete", methods=["POST"])
def devices_delete(device_id):
    """Delete a device and (in a real app) cascade to its allowlist and history."""
    device_name = delete_device(device_id)
    if not device_name:
        flash("Device not found.", "error")
        return redirect(url_for("admin.devices"))

    # TODO: save to database — replace delete_device() with a DB delete + cascade
    flash(f"'{device_name}' was deleted from the registry.", "success")
    return redirect(url_for("admin.devices"))


# ================================================================== #
# PLACEHOLDER ROUTES
# ================================================================== #

# ================================================================== #
# ALLOWLIST MANAGEMENT
# ================================================================== #

def _validate_entry_form(port_str, protocol, service, notes,
                         device_id, editing_entry_id=None):
    """
    Validate Add/Edit allowlist entry form fields server-side.
    Returns a dict of field_name -> error message (empty = all passed).
    """
    errors = {}

    # ---- Port ----
    if not port_str:
        errors["port"] = "Port number is required."
    else:
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                errors["port"] = "Port must be a number between 1 and 65535."
            else:
                # Uniqueness: same port+protocol must not already exist for this device
                for e in get_entries_for_device(device_id):
                    if (e["port"] == port
                            and e["protocol"] == protocol
                            and e["id"] != editing_entry_id):
                        errors["port"] = (
                            f"Port {port}/{protocol.upper()} is already on "
                            f"this device's allowlist."
                        )
                        break
        except (ValueError, TypeError):
            errors["port"] = "Port must be a whole number."

    # ---- Protocol ----
    if protocol not in ("tcp", "udp"):
        errors["protocol"] = "Protocol must be TCP or UDP."

    # ---- Service name ----
    if not service:
        errors["service"] = "Service name is required."
    elif len(service) > 30:
        errors["service"] = "Service name must be 30 characters or fewer."
    elif not _re.match(r'^[a-z0-9\-]+$', service):
        errors["service"] = (
            "Service name may only contain lowercase letters, numbers, "
            "and hyphens (e.g. 'ssh', 'http', 'ms-wbt-server')."
        )

    # ---- Notes (optional) ----
    if notes and len(notes) > 200:
        errors["notes"] = "Notes must be 200 characters or fewer."

    return errors


def _render_allowlist(device, entries, new_entry_id=None,
                      open_entry_modal=False, open_delete_modal=False,
                      open_copy_modal=False,
                      form_errors=None, form_data=None):
    """
    Helper that builds the full context dict and renders the allowlist page
    for a selected device. Used by both GET and POST-with-errors.
    """
    all_devices = get_all_devices()

    # Group devices by lab for the selector <optgroup>
    labs = {}
    for d in all_devices:
        labs.setdefault(d["lab_location"], []).append(d)

    # Build entries for each other device for the Copy modal preview
    entries_by_device = {
        d["id"]: get_entries_for_device(d["id"])
        for d in all_devices
        if d["id"] != device["id"]
    }

    return render_template(
        "admin/admin_allowlist_management.html",
        active_page="allowlist",
        # Device context
        device=device,
        entries=entries,
        entry_count=len(entries),
        required_count=count_required(device["id"]),
        risky_count=count_risky(device["id"]),
        # Device selector (grouped by lab)
        all_devices=all_devices,
        labs_grouped=labs,
        # For Copy modal
        entries_by_device=entries_by_device,
        # New-row highlight (same pattern as Device Registry)
        new_entry_id=new_entry_id,
        # Modal state
        open_entry_modal=open_entry_modal,
        open_delete_modal=open_delete_modal,
        open_copy_modal=open_copy_modal,
        form_errors=form_errors or {},
        form_data=form_data or {},
        # Port reference data — passed to JS as JSON for auto-fill and risky warning
        port_reference=PORT_REFERENCE,
    )


def _render_overview():
    """Render the overview state (no device selected)."""
    all_devices = get_all_devices()
    labs = {}
    for d in all_devices:
        labs.setdefault(d["lab_location"], []).append(d)

    # Build overview rows sorted: 0-entry devices first, then by name
    overview_rows = sorted(
        all_devices,
        key=lambda d: (d["allowlisted_port_count"] > 0, d["name"])
    )

    # Pre-compute required counts for each device to avoid calling
    # functions from the template directly
    required_counts = {d["id"]: count_required(d["id"]) for d in all_devices}

    return render_template(
        "admin/admin_allowlist_management.html",
        active_page="allowlist",
        device=None,
        entries=[],
        entry_count=0,
        required_count=0,
        risky_count=0,
        all_devices=all_devices,
        labs_grouped=labs,
        overview_rows=overview_rows,
        required_counts=required_counts,
        entries_by_device={},
        new_entry_id=None,
        open_entry_modal=False,
        open_delete_modal=False,
        open_copy_modal=False,
        form_errors={},
        form_data={},
        port_reference=PORT_REFERENCE,
    )


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/allowlist")
def allowlist():
    """
    Allowlist Management page.
    Without ?device_id: show the overview table of all devices.
    With ?device_id=<id>: show that device's allowlist.
    After a successful add, ?new_entry=<id> highlights the new row.
    """
    device_id    = request.args.get("device_id",  type=int)
    new_entry_id = request.args.get("new_entry",  type=int)

    if not device_id:
        return _render_overview()

    device = get_device_by_id(device_id)
    if not device:
        flash("Device not found.", "error")
        return _render_overview()

    entries = get_entries_for_device(device_id)
    return _render_allowlist(device, entries, new_entry_id=new_entry_id)


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/allowlist/<int:device_id>/entries/add", methods=["POST"])
def allowlist_entry_add(device_id):
    """Add a new port to a device's allowlist."""
    device = get_device_by_id(device_id)
    if not device:
        flash("Device not found.", "error")
        return redirect(url_for("admin.allowlist"))

    port_str      = request.form.get("port",          "").strip()
    protocol      = request.form.get("protocol",      "tcp").strip().lower()
    service       = request.form.get("service",       "").strip().lower()
    expected_open = bool(request.form.get("expected_open"))
    notes         = request.form.get("notes",         "").strip()

    form_data = {
        "port":          port_str,
        "protocol":      protocol,
        "service":       service,
        "expected_open": expected_open,
        "notes":         notes,
    }

    errors = _validate_entry_form(port_str, protocol, service, notes, device_id)

    if errors:
        entries = get_entries_for_device(device_id)
        return _render_allowlist(
            device, entries,
            open_entry_modal=True,
            form_errors=errors,
            form_data=form_data,
        )

    # TODO: save to database
    new_entry = add_entry(device_id, form_data)
    flash(
        f"Port {new_entry['port']}/{new_entry['protocol'].upper()} "
        f"({new_entry['service']}) was added to {device['name']}'s allowlist.",
        "success",
    )
    return redirect(url_for("admin.allowlist",
                            device_id=device_id,
                            new_entry=new_entry["id"]))


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/allowlist/<int:device_id>/entries/<int:entry_id>/edit",
                methods=["POST"])
def allowlist_entry_edit(device_id, entry_id):
    """Edit an existing allowlist entry."""
    device = get_device_by_id(device_id)
    entry  = get_entry(entry_id)
    if not device or not entry:
        flash("Entry not found.", "error")
        return redirect(url_for("admin.allowlist", device_id=device_id))

    port_str      = request.form.get("port",          "").strip()
    protocol      = request.form.get("protocol",      "tcp").strip().lower()
    service       = request.form.get("service",       "").strip().lower()
    expected_open = bool(request.form.get("expected_open"))
    notes         = request.form.get("notes",         "").strip()

    form_data = {
        "port":          port_str,
        "protocol":      protocol,
        "service":       service,
        "expected_open": expected_open,
        "notes":         notes,
    }

    errors = _validate_entry_form(port_str, protocol, service, notes,
                                  device_id, editing_entry_id=entry_id)

    if errors:
        entries = get_entries_for_device(device_id)
        return _render_allowlist(
            device, entries,
            open_entry_modal=True,
            form_errors=errors,
            form_data={"editing_entry_id": entry_id, **form_data},
        )

    # TODO: save to database
    update_entry(entry_id, form_data)
    flash(
        f"Port {int(port_str)}/{protocol.upper()} ({service}) was updated.",
        "success",
    )
    return redirect(url_for("admin.allowlist", device_id=device_id))


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/allowlist/<int:device_id>/entries/<int:entry_id>/delete",
                methods=["POST"])
def allowlist_entry_delete(device_id, entry_id):
    """Remove an entry from a device's allowlist."""
    device = get_device_by_id(device_id)
    deleted = delete_entry(entry_id)

    if not device or not deleted:
        flash("Entry not found.", "error")
        return redirect(url_for("admin.allowlist", device_id=device_id))

    # TODO: save to database
    flash(
        f"Port {deleted['port']}/{deleted['protocol'].upper()} "
        f"({deleted['service']}) was removed from {device['name']}'s allowlist.",
        "success",
    )
    return redirect(url_for("admin.allowlist", device_id=device_id))


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/allowlist/<int:device_id>/copy", methods=["POST"])
def allowlist_copy(device_id):
    """Copy allowlist entries from another device."""
    device = get_device_by_id(device_id)
    if not device:
        flash("Device not found.", "error")
        return redirect(url_for("admin.allowlist"))

    source_id = request.form.get("source_device_id", type=int)
    mode      = request.form.get("copy_mode", "merge").strip()

    if not source_id:
        flash("Please select a source device.", "error")
        return redirect(url_for("admin.allowlist", device_id=device_id))

    source = get_device_by_id(source_id)
    if not source:
        flash("Source device not found.", "error")
        return redirect(url_for("admin.allowlist", device_id=device_id))

    # TODO: save to database
    copied, skipped = copy_entries(source_id, device_id, mode)

    msg = (
        f"Copied {copied} "
        f"{'entry' if copied == 1 else 'entries'} from {source['name']}."
    )
    if skipped:
        msg += f" {skipped} {'was' if skipped == 1 else 'were'} skipped (already exist)."
    flash(msg, "success")
    return redirect(url_for("admin.allowlist", device_id=device_id))


# ================================================================== #
# RUN SCAN
# ================================================================== #

def _validate_port_spec(port_spec_str):
    """
    Validate a custom port specification string.
    Accepts comma-separated ports and ranges, e.g. "22,80,443" or "1-1024".
    Returns a list of error strings (empty list = valid).
    """
    import re as _re
    errors = []
    if not port_spec_str:
        errors.append("Port range cannot be empty.")
        return errors
    if len(port_spec_str) > 100:
        errors.append("Port range is too long (max 100 characters).")
        return errors
    if not _re.match(r'^[\d,\-\s]+$', port_spec_str):
        errors.append(
            "Port range may only contain digits, commas, and hyphens "
            "(e.g. 22,80,443 or 1-1024)."
        )
        return errors
    for part in port_spec_str.split(","):
        part = part.strip()
        if not part:
            errors.append("Port range contains an empty section (stray comma?).")
            continue
        if "-" in part:
            sub = part.split("-")
            if len(sub) != 2:
                errors.append(f"'{part}' is not a valid range."); continue
            try:
                lo, hi = int(sub[0]), int(sub[1])
            except ValueError:
                errors.append(f"'{part}' contains a non-numeric value."); continue
            if not (1 <= lo <= 65535) or not (1 <= hi <= 65535):
                errors.append(f"Ports in '{part}' must be between 1 and 65535.")
            elif lo >= hi:
                errors.append(
                    f"Range '{part}' is invalid — start must be less than end."
                )
        else:
            try:
                p = int(part)
            except ValueError:
                errors.append(f"'{part}' is not a valid port number."); continue
            if not (1 <= p <= 65535):
                errors.append(f"Port {part} is out of range (must be 1–65535).")
    return errors


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/scan", methods=["GET"])
def scan():
    """Run Scan page. ?device_id=<id> preselects a device."""
    from app.mock_data.admin_scans_mock import get_recent_scans
    from app.services.scan_job_manager  import get_running_job

    all_devs    = get_all_devices()
    active_devs = [d for d in all_devs if d["status"] == "active"]

    preselected = None
    pid = request.args.get("device_id", type=int)
    if pid:
        dev = get_device_by_id(pid)
        if not dev:
            flash("Device not found.", "error")
        elif dev["status"] != "active":
            flash(
                f"'{dev['name']}' is inactive. Activate it before scanning.",
                "error",
            )
        else:
            preselected = dev

    return render_template(
        "admin/admin_run_scan.html",
        active_page="scan",
        all_devices=all_devs,
        active_count=len(active_devs),
        no_allowlist_count=sum(
            1 for d in active_devs if d["allowlisted_port_count"] == 0
        ),
        preselected_device=preselected,
        recent_scans=get_recent_scans(limit=5),
        running_job=get_running_job(),
        form_errors={},
        form_data={},
    )


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/scan/start", methods=["POST"])
def scan_start():
    """Validate + start a scan job (POST/Redirect/Get)."""
    from app.mock_data.admin_scans_mock      import get_recent_scans
    from app.services.scan_job_manager       import (
        create_and_start_job, get_running_job, verify_device_authorization,
    )
    from app.mock_data.admin_audit_log_mock  import add_audit_entry

    target_mode  = request.form.get("target_mode",  "single")
    device_id    = request.form.get("device_id",    type=int)
    port_mode    = request.form.get("port_mode",    "top1000")
    custom_ports = request.form.get("custom_ports", "").strip()
    confirmed    = bool(request.form.get("confirmed"))

    form_data = {
        "target_mode":  target_mode,
        "device_id":    device_id,
        "port_mode":    port_mode,
        "custom_ports": custom_ports,
        "confirmed":    confirmed,
    }

    all_devs    = get_all_devices()
    active_devs = [d for d in all_devs if d["status"] == "active"]
    errors      = {}

    if not confirmed:
        errors["confirmed"] = (
            "You must confirm that these devices are authorized before scanning."
        )

    target_devices = []
    if target_mode == "single":
        if not device_id:
            errors["device_id"] = "Please select a device."
        else:
            dev = get_device_by_id(device_id)
            if not dev:
                errors["device_id"] = "Selected device not found."
            elif dev["status"] != "active":
                errors["device_id"] = f"'{dev['name']}' is inactive. Activate it first."
            else:
                target_devices = [dev]
    else:
        target_devices = active_devs
        if not target_devices:
            errors["target_mode"] = "There are no active devices to scan."

    if port_mode == "custom":
        port_errors = _validate_port_spec(custom_ports)
        if port_errors:
            errors["custom_ports"] = port_errors[0]

    if not errors and get_running_job():
        errors["general"] = "A scan is already running. Please wait for it to finish."

    if errors:
        pre = get_device_by_id(device_id) if device_id else None
        return render_template(
            "admin/admin_run_scan.html",
            active_page="scan",
            all_devices=all_devs,
            active_count=len(active_devs),
            no_allowlist_count=sum(
                1 for d in active_devs if d["allowlisted_port_count"] == 0
            ),
            preselected_device=pre,
            recent_scans=get_recent_scans(limit=5),
            running_job=get_running_job(),
            form_errors=errors,
            form_data=form_data,
        )

    # Pre-scan authorization check (also repeated per-device in job manager)
    for dev in target_devices:
        ok, reason = verify_device_authorization(dev)
        if not ok:
            add_audit_entry(
                "scan_blocked",
                target=dev["ip_address"],
                detail=f"Scan blocked: {reason}",
            )
            flash(
                f"Scan blocked: {dev['ip_address']} is not an authorized active "
                f"lab device. This attempt has been logged.",
                "error",
            )
            return redirect(url_for("admin.scan"))

    port_spec = custom_ports if port_mode == "custom" else "top1000"
    job_id    = create_and_start_job(target_devices, port_spec)
    return redirect(url_for("admin.scan_progress", job_id=job_id))


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/scan/progress/<job_id>")
def scan_progress(job_id):
    """Scan progress page — JS polls the status endpoint every second."""
    from app.services.scan_job_manager import get_job, STAGES
    job = get_job(job_id)
    if not job:
        flash("Scan job not found.", "error")
        return redirect(url_for("admin.scan"))
    return render_template(
        "admin/admin_scan_progress.html",
        active_page="scan",
        job=job,
        stages=STAGES,
    )


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/scan/status/<job_id>")
def scan_status(job_id):
    """JSON endpoint polled by admin_scan_progress.js."""
    from flask import jsonify
    from app.services.scan_job_manager import get_job, build_status_response
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(build_status_response(job))


# TODO: protect with Flask-Login admin role check — debug only
@admin_bp.route("/scan/test-blocked", methods=["POST"])
def scan_test_blocked():
    """Developer test: simulate a blocked scan. Only active in DEBUG mode."""
    from flask import current_app
    from app.mock_data.admin_audit_log_mock import add_audit_entry
    if not current_app.debug:
        flash("This route is only available in debug mode.", "error")
        return redirect(url_for("admin.scan"))
    fake_ip = "8.8.8.8"
    add_audit_entry(
        "scan_blocked",
        target=fake_ip,
        detail=(
            f"Test blocked scan: {fake_ip} is a public IP address. "
            "Only private lab network devices can be scanned."
        ),
    )
    flash(
        f"Scan blocked: {fake_ip} is not an authorized active lab device. "
        "This attempt has been logged.",
        "error",
    )
    return redirect(url_for("admin.scan"))


# ================================================================== #
# SCAN HISTORY
# ================================================================== #

# NOTE — Why scans cannot be deleted from this page:
#   Scan records are security evidence. Deleting a scan could hide a
#   previously detected threat or gap in scanning coverage. If a device
#   was vulnerable and a scan found it, that scan must remain in the
#   record even if the device is later patched or removed. Deletion
#   would make audits and incident investigations unreliable.
#   Future versions may support "archiving" with a confirmation flow and
#   an audit log entry, but never silent deletion.

# TODO: protect with Flask-Login admin role check
@admin_bp.route("/history")
def history():
    """
    Scan History page — browse all past scan records with filters.
    Optional query params prefill the filter bar:
      device_id, lab, risk, date_from, date_to, unacknowledged=1
    """
    from app.mock_data.admin_scans_mock import (
        get_all_scans,
        # get_scans_this_week_count and count_unacknowledged_high are no longer
        # passed to the template (stat cards removed). Kept in admin_scans_mock.py
        # for the Viewer dashboard / future use.
    )
    from app.services.scan_comparator      import compare_scans
    from app.services.scan_history_filters import apply_filters

    all_scans  = get_all_scans()

    # Annotate each scan with its change-detection result and lab_location
    # so the template can render the Changes column without extra logic.
    # We do this once here to avoid redundant calls inside the template.
    annotated = []
    for s in all_scans:
        from app.mock_data.admin_scans_mock import get_previous_scan
        prev = get_previous_scan(s)
        changes = compare_scans(
            s.get("findings", []),
            prev.get("findings", []) if prev else None,
        )
        # Count unacknowledged High findings on this specific scan
        unack_high = sum(
            1 for f in s.get("findings", [])
            if f.get("risk_level") == "High" and not f.get("acknowledged", False)
        )
        annotated.append({**s, "_changes": changes, "_unack_high": unack_high})

    # Prefill filter values from query parameters.
    # ?device_id= is converted to a device name for the search box
    # (the Device dropdown was removed; search covers both name and IP).
    device_id_param = request.args.get("device_id", type=int)
    prefill_search  = request.args.get("q", "")
    if device_id_param and not prefill_search:
        dev = get_device_by_id(device_id_param)
        if dev:
            prefill_search = dev["name"]

    prefill = {
        "search":        prefill_search,
        "deviceName":    prefill_search,   # JS uses this to fill the search box
        "lab":           request.args.get("lab",          ""),
        "risk":          request.args.get("risk",         ""),
        "date_from":     request.args.get("date_from",    ""),
        "date_to":       request.args.get("date_to",      ""),
        "unacknowledged": bool(request.args.get("unacknowledged")),
    }

    # Count job-mates (how many devices share the same job_id) for the
    # batch-scan icon. Build a dict: job_id → count of scans with that id.
    from collections import Counter
    job_counts = Counter(
        s["job_id"] for s in all_scans
        if s.get("job_id") and not s["job_id"].startswith("seed-")
    )

    return render_template(
        "admin/admin_scan_history.html",
        active_page="history",
        scans=annotated,
        all_devices=get_all_devices(),
        lab_locations=get_lab_locations(),
        total_scans=len(all_scans),
        prefill=prefill,
        job_counts=job_counts,
    )


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/history/export.csv")
def history_export_csv():
    """
    Export scan history as a CSV file matching the current filters.
    The filters are read from the same query params as the /history route
    so the download always reflects what the user sees on screen.
    Adds an audit log entry recording the export.
    """
    import csv
    import io
    from datetime import date as _date
    from flask import Response
    from app.mock_data.admin_scans_mock     import get_all_scans, get_previous_scan
    from app.mock_data.admin_audit_log_mock import add_audit_entry
    from app.services.scan_comparator      import compare_scans
    from app.services.scan_history_filters import apply_filters

    # Parse filter params (same logic as the GET route)
    def _parse_date(s):
        try:
            return _date.fromisoformat(s) if s else None
        except ValueError:
            return None

    filters = {
        "search":        request.args.get("q",            ""),
        "lab":           request.args.get("lab",          ""),
        "risk":          request.args.get("risk",         ""),
        "date_from":     _parse_date(request.args.get("date_from",    "")),
        "date_to":       _parse_date(request.args.get("date_to",      "")),
        "unacknowledged": bool(request.args.get("unacknowledged")),
    }

    scans = apply_filters(get_all_scans(), filters)

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Scan ID", "Device Name", "IP Address", "Lab / Location",
        "Scanned At", "Duration (s)", "Port Range",
        "Open Ports", "Approved", "Unexpected", "Risky", "Missing",
        "Highest Risk",
        "Newly Opened Ports", "Closed Ports", "Changed Services",
        "Unacknowledged High Findings",
    ])

    for s in scans:
        summary = s.get("summary", {})
        lc      = summary.get("label_counts", {})

        prev    = get_previous_scan(s)
        changes = compare_scans(
            s.get("findings", []),
            prev.get("findings", []) if prev else None,
        )

        def _port_list(items):
            return "; ".join(
                f"{x['port']}/{x['protocol']}" for x in items
            )

        def _svc_list(items):
            return "; ".join(
                f"{x['port']}/{x['protocol']} "
                f"({x['old_service']} → {x['new_service']})"
                for x in items
            )

        unack_high = sum(
            1 for f in s.get("findings", [])
            if f.get("risk_level") == "High" and not f.get("acknowledged", False)
        )

        writer.writerow([
            s.get("id", ""),
            s.get("device_name", ""),
            s.get("ip_address", ""),
            s.get("lab_location", ""),
            s.get("started_at", "").strftime("%Y-%m-%d %H:%M")
                if hasattr(s.get("started_at"), "strftime") else "",
            s.get("duration_seconds", ""),
            s.get("port_spec", ""),
            summary.get("open_ports", 0),
            lc.get("Approved",   0),
            lc.get("Unexpected", 0),
            lc.get("Risky",      0),
            lc.get("Missing",    0),
            summary.get("highest_risk", "None"),
            _port_list(changes.get("newly_opened",    [])),
            _port_list(changes.get("closed",          [])),
            _svc_list( changes.get("service_changed", [])),
            unack_high,
        ])

    # Audit log
    active_filters = {k: v for k, v in filters.items() if v}
    add_audit_entry(
        "report_exported",
        detail=(
            f"CSV export: {len(scans)} rows. "
            f"Filters: {active_filters if active_filters else 'none'}."
        ),
    )

    today    = _date.today().isoformat()
    filename = f"portwatch_scan_history_{today}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ================================================================== #
# USER MANAGEMENT  (replaces the "coming soon" placeholder)
# ================================================================== #

def _render_users(open_modal=None, form_errors=None, form_data=None,
                  new_user_id=None):
    """Helper: render the User Management page with optional modal state."""
    from app.mock_data.admin_users_mock import get_all_users, get_current_user
    return render_template(
        "admin/admin_user_management.html",
        active_page="users",
        users=get_all_users(),
        current_user=get_current_user(),
        open_modal=open_modal,          # "add", "edit", "reset", or None
        form_errors=form_errors or {},
        form_data=form_data or {},
        new_user_id=new_user_id,
    )


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/users")
def users():
    """User Management page — list and manage all user accounts."""
    new_user_id = request.args.get("new_user", type=int)
    return _render_users(new_user_id=new_user_id)


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/users/add", methods=["POST"])
def users_add():
    """
    Create a new user account. PRG pattern.

    WHY RE-AUTHENTICATION FOR ADMINISTRATOR ACCOUNTS:
      An unattended logged-in browser session could be exploited to create
      a new administrator account silently. By requiring the current user
      to re-enter their own password when granting Administrator access,
      we ensure that the person at the keyboard is who they say they are.
      This applies to: creating a new Admin, promoting a Viewer to Admin,
      and activating an inactive Admin account.
    """
    from app.mock_data.admin_users_mock  import (
        get_all_users, get_current_user, add_user, check_user_password,
    )
    from app.mock_data.admin_audit_log_mock import add_audit_entry
    from app.utils.user_validators import (
        validate_full_name, validate_username,
        validate_password, validate_role,
    )

    full_name          = request.form.get("full_name",           "").strip()
    username           = request.form.get("username",            "").strip().lower()
    password           = request.form.get("password",            "")
    confirm            = request.form.get("confirm_password",    "")
    role               = request.form.get("role",                "").strip().lower()
    status             = "active" if request.form.get("status") else "inactive"
    admin_grant_pw     = request.form.get("admin_grant_password","")

    # Never echo passwords back into the form
    form_data = {
        "full_name": full_name,
        "username":  username,
        "role":      role,
        "status":    status,
        # passwords intentionally omitted
    }

    errors = {}
    err = validate_full_name(full_name);       errors["full_name"] = err if err else None
    err = validate_username(username, get_all_users());
    errors["username"] = err if err else None
    err = validate_password(password, confirm); errors["password"] = err if err else None
    err = validate_role(role);                  errors["role"]     = err if err else None
    errors = {k: v for k, v in errors.items() if v}

    current_user = get_current_user()
    actor = current_user["username"] if current_user else "Admin"

    # ── Re-authentication check for Administrator accounts ────────────
    # Only required when the new account is an Administrator.
    if not errors and role == "administrator":
        if not admin_grant_pw:
            errors["admin_grant_password"] = (
                "Your password is required to grant Administrator access."
            )
        elif not check_user_password(current_user, admin_grant_pw):
            errors["admin_grant_password"] = (
                "Incorrect password. Administrator access was not granted."
            )
            add_audit_entry(
                "user_action_blocked",
                user=actor,
                target=username,
                detail=f"Administrator re-authentication failed for @{username}.",
                category="Security",
                result="blocked",
            )

    if errors:
        return _render_users(open_modal="add", form_errors=errors, form_data=form_data)

    new_user = add_user({
        "full_name": full_name,
        "username":  username,
        "password":  password,
        "role":      role,
        "status":    status,
    })
    # TODO: save to database

    reauth_note = " (re-authenticated)" if role == "administrator" else ""
    add_audit_entry(
        "user_created",
        user=actor,
        target=username,
        detail=f"New {role} account created for '{full_name}' (@{username}).{reauth_note}",
    )
    flash(f"User @{username} was created.", "success")
    return redirect(url_for("admin.users", new_user=new_user["id"]))


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/users/<int:user_id>/edit", methods=["POST"])
def users_edit(user_id):
    """Update a user's profile (name, role, status). PRG pattern."""
    from app.mock_data.admin_users_mock import (
        get_user, get_current_user, update_user, count_active_admins,
        check_user_password,
    )
    from app.mock_data.admin_audit_log_mock import add_audit_entry
    from app.utils.user_validators import validate_full_name, validate_role

    target = get_user(user_id)
    if not target:
        flash("User not found.", "error")
        return redirect(url_for("admin.users"))

    current_user = get_current_user()
    actor = current_user["username"] if current_user else "Admin"

    full_name      = request.form.get("full_name",           "").strip()
    role           = request.form.get("role",                "").strip().lower()
    status         = "active" if request.form.get("status") else "inactive"
    admin_grant_pw = request.form.get("admin_grant_password","")

    form_data = {
        "edit_user_id": user_id,
        "full_name":    full_name,
        "role":         role,
        "status":       status,
    }

    errors = {}
    err = validate_full_name(full_name); errors["full_name"] = err if err else None
    err = validate_role(role);           errors["role"]      = err if err else None
    errors = {k: v for k, v in errors.items() if v}

    if errors:
        return _render_users(open_modal="edit", form_errors=errors, form_data=form_data)

    # Safety: cannot change own role or status
    if current_user and user_id == current_user["id"]:
        if role != target["role"] or status != target["status"]:
            flash("You cannot change your own role or status.", "error")
            return redirect(url_for("admin.users"))

    # Safety: must keep at least one active administrator
    old_role   = target["role"]
    old_status = target["status"]
    would_lose_admin = (
        old_role == "administrator" and old_status == "active"
        and (role != "administrator" or status != "active")
    )
    if would_lose_admin and count_active_admins() <= 1:
        flash("At least one active Administrator is required.", "error")
        add_audit_entry("user_action_blocked", user=actor, target=target["username"],
                        detail="Blocked: would remove last active administrator.")
        return redirect(url_for("admin.users"))

    # ── Re-authentication check for Viewer → Administrator promotion ──
    # Only required when the role is changing TO administrator.
    promoting_to_admin = (old_role != "administrator" and role == "administrator")
    if promoting_to_admin:
        if not admin_grant_pw:
            errors["admin_grant_password"] = (
                "Your password is required to grant Administrator access."
            )
        elif not check_user_password(current_user, admin_grant_pw):
            errors["admin_grant_password"] = (
                "Incorrect password. Administrator access was not granted."
            )
            add_audit_entry(
                "user_action_blocked",
                user=actor,
                target=target["username"],
                detail=f"Administrator re-authentication failed for @{target['username']}.",
                category="Security",
                result="blocked",
            )
        if errors:
            return _render_users(open_modal="edit", form_errors=errors, form_data=form_data)

    update_user(user_id, {"full_name": full_name, "role": role, "status": status})
    # TODO: save to database

    reauth_note = " (re-authenticated)" if promoting_to_admin else ""
    if old_role != role:
        add_audit_entry("user_role_changed", user=actor, target=target["username"],
                        detail=f"Role changed from {old_role} to {role}.{reauth_note}")
    if old_status != status:
        action = "user_activated" if status == "active" else "user_deactivated"
        add_audit_entry(action, user=actor, target=target["username"])
    if old_role == role and old_status == status:
        add_audit_entry("user_updated", user=actor, target=target["username"],
                        detail="Profile updated (full name changed).")

    flash(f"@{target['username']} was updated.", "success")
    return redirect(url_for("admin.users"))


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
def users_reset_password(user_id):
    """Reset a user's password. PRG pattern. Never echo the password."""
    from app.mock_data.admin_users_mock import get_user, get_current_user, reset_password
    from app.mock_data.admin_audit_log_mock import add_audit_entry
    from app.utils.user_validators import validate_password

    target = get_user(user_id)
    if not target:
        flash("User not found.", "error")
        return redirect(url_for("admin.users"))

    current_user = get_current_user()
    actor = current_user["username"] if current_user else "Admin"

    new_pw  = request.form.get("new_password",     "")
    confirm = request.form.get("confirm_new_password", "")
    must_change = bool(request.form.get("must_change_password"))

    err = validate_password(new_pw, confirm)
    if err:
        form_data = {"reset_user_id": user_id}
        return _render_users(open_modal="reset",
                             form_errors={"new_password": err},
                             form_data=form_data)

    reset_password(user_id, new_pw, must_change)
    # TODO: save to database — NEVER store new_pw; only the hash is saved

    add_audit_entry(
        "user_password_reset",
        user=actor,
        target=target["username"],
        detail=f"Password reset for @{target['username']}."
               + (" Must change at next login." if must_change else ""),
    )
    flash(f"Password for @{target['username']} was reset.", "success")
    return redirect(url_for("admin.users"))


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/users/<int:user_id>/toggle-status", methods=["POST"])
def users_toggle_status(user_id):
    """Activate or deactivate a user account. PRG pattern."""
    from app.mock_data.admin_users_mock import (
        get_user, get_current_user, toggle_user_status, count_active_admins,
        check_user_password,
    )
    from app.mock_data.admin_audit_log_mock import add_audit_entry

    target = get_user(user_id)
    if not target:
        flash("User not found.", "error")
        return redirect(url_for("admin.users"))

    current_user = get_current_user()
    actor = current_user["username"] if current_user else "Admin"

    # Safety: cannot deactivate own account
    if current_user and user_id == current_user["id"]:
        flash("You cannot deactivate your own account.", "error")
        add_audit_entry("user_action_blocked", user=actor, target=target["username"],
                        detail="Blocked: cannot deactivate own account.")
        return redirect(url_for("admin.users"))

    # Safety: cannot deactivate the last active administrator
    if (target["role"] == "administrator" and target["status"] == "active"
            and count_active_admins() <= 1):
        flash("At least one active Administrator is required.", "error")
        add_audit_entry("user_action_blocked", user=actor, target=target["username"],
                        detail="Blocked: would remove last active administrator.")
        return redirect(url_for("admin.users"))

    # ── Re-authentication check for activating an Administrator ───────
    # Activating an inactive admin is equivalent to granting admin access.
    activating_admin = (
        target["role"] == "administrator" and target["status"] == "inactive"
    )
    if activating_admin:
        admin_grant_pw = request.form.get("admin_grant_password", "")
        if not admin_grant_pw:
            flash(
                "Your password is required to activate an Administrator account.",
                "error",
            )
            add_audit_entry(
                "user_action_blocked",
                user=actor,
                target=target["username"],
                detail=f"Administrator re-authentication failed (empty) for @{target['username']}.",
                category="Security",
                result="blocked",
            )
            return redirect(url_for("admin.users"))
        if not check_user_password(current_user, admin_grant_pw):
            flash(
                "Incorrect password. Administrator access was not granted.",
                "error",
            )
            add_audit_entry(
                "user_action_blocked",
                user=actor,
                target=target["username"],
                detail=f"Administrator re-authentication failed for @{target['username']}.",
                category="Security",
                result="blocked",
            )
            return redirect(url_for("admin.users"))

    result = toggle_user_status(user_id)
    # TODO: save to database
    username, new_status = result
    action_word  = "activated" if new_status == "active" else "deactivated"
    audit_action = "user_activated" if new_status == "active" else "user_deactivated"
    reauth_note  = " (re-authenticated)" if activating_admin else ""
    add_audit_entry(audit_action, user=actor, target=username,
                    detail=f"@{username} was {action_word}.{reauth_note}")
    flash(f"@{username} was {action_word}.", "success")
    return redirect(url_for("admin.users"))


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
def users_delete(user_id):
    """Delete a user account permanently. PRG pattern."""
    from app.mock_data.admin_users_mock import (
        get_user, get_current_user, delete_user, count_active_admins,
    )
    from app.mock_data.admin_audit_log_mock import add_audit_entry

    target = get_user(user_id)
    if not target:
        flash("User not found.", "error")
        return redirect(url_for("admin.users"))

    current_user = get_current_user()
    actor = current_user["username"] if current_user else "Admin"

    # Safety: cannot delete own account
    if current_user and user_id == current_user["id"]:
        flash("You cannot delete your own account.", "error")
        add_audit_entry("user_action_blocked", user=actor, target=target["username"],
                        detail="Blocked: cannot delete own account.")
        return redirect(url_for("admin.users"))

    # Safety: cannot delete the last active administrator
    if target["role"] == "administrator" and target["status"] == "active" \
            and count_active_admins() <= 1:
        flash("At least one active Administrator is required.", "error")
        add_audit_entry("user_action_blocked", user=actor, target=target["username"],
                        detail="Blocked: would remove last active administrator.")
        return redirect(url_for("admin.users"))

    username  = target["username"]
    full_name = target["full_name"]
    delete_user(user_id)
    # TODO: save to database

    add_audit_entry(
        "user_deleted",
        user=actor,
        target=username,
        detail=f"User '{full_name}' (@{username}) was deleted. Audit log entries are kept.",
    )
    flash(f"@{username} was deleted.", "success")
    return redirect(url_for("admin.users"))


# ================================================================== #
# AUDIT LOG  (replaces the "coming soon" placeholder)
#
# WHY THIS PAGE IS READ-ONLY:
#   Audit log entries are security evidence. Allowing admins to modify
#   or delete entries would let someone cover their tracks after a
#   suspicious action was logged. The page intentionally has no edit
#   or delete controls. The same principle applies to the CSV export —
#   the exported file is a point-in-time snapshot that cannot be altered
#   by anyone through the UI.
# ================================================================== #

# TODO: protect with Flask-Login admin role check
@admin_bp.route("/audit-log")
def audit_log():
    """
    Audit Log page — read-only record of all admin actions.
    Accepts query params to prefill filters:
      q, category, result, user, date_from, date_to
    """
    from app.mock_data.admin_audit_log_mock import (
        get_all_entries, get_all_categories, get_all_usernames,
    )

    all_entries = get_all_entries()   # newest first

    prefill = {
        "q":        request.args.get("q",        ""),
        "category": request.args.get("category", ""),
        "result":   request.args.get("result",   ""),
        "user":     request.args.get("user",      ""),
        "date_from":request.args.get("date_from", ""),
        "date_to":  request.args.get("date_to",   ""),
        "blocked":  bool(request.args.get("blocked")),
    }

    return render_template(
        "admin/admin_audit_log.html",
        active_page="audit_log",
        entries=all_entries,
        categories=get_all_categories(),
        usernames=get_all_usernames(),
        prefill=prefill,
        total_entries=len(all_entries),
    )


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/audit-log/export.csv")
def audit_log_export_csv():
    """
    Export audit log entries matching the current filters as a CSV download.
    Logs the export itself so every report download is auditable.
    """
    import csv
    import io
    from datetime import date as _date
    from flask import Response
    from app.mock_data.admin_audit_log_mock import (
        get_all_entries, add_audit_entry,
    )
    from app.mock_data.admin_users_mock import get_current_user

    def _parse_date(s):
        try:
            return _date.fromisoformat(s) if s else None
        except ValueError:
            return None

    q         = request.args.get("q",        "").strip().lower()
    category  = request.args.get("category", "").strip()
    result    = request.args.get("result",   "").strip()
    user      = request.args.get("user",     "").strip().lower()
    date_from = _parse_date(request.args.get("date_from", ""))
    date_to   = _parse_date(request.args.get("date_to",   ""))
    blocked   = bool(request.args.get("blocked"))

    rows = get_all_entries()

    # Apply filters (same logic as the client-side JS)
    filtered = []
    for e in rows:
        if q and q not in (e.get("username") or "").lower() \
               and q not in (e.get("target")  or "").lower() \
               and q not in (e.get("detail")  or "").lower():
            continue
        if category and e.get("category") != category:
            continue
        if result and e.get("result") != result:
            continue
        if user and (e.get("username") or "").lower() != user:
            continue
        entry_date = e.get("timestamp")
        if hasattr(entry_date, "date"):
            entry_date = entry_date.date()
        if date_from and entry_date and entry_date < date_from:
            continue
        if date_to   and entry_date and entry_date > date_to:
            continue
        if blocked and e.get("result") != "blocked":
            continue
        filtered.append(e)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Timestamp", "Username", "IP Address",
        "Action", "Category", "Target", "Details", "Result",
    ])
    for e in filtered:
        writer.writerow([
            e.get("id", ""),
            e.get("timestamp", "").strftime("%Y-%m-%d %H:%M:%S")
                if hasattr(e.get("timestamp"), "strftime") else "",
            e.get("username",   ""),
            e.get("ip_address", ""),
            e.get("action",     ""),
            e.get("category",   ""),
            e.get("target",     ""),
            e.get("detail",     ""),
            e.get("result",     ""),
        ])

    cu = get_current_user()
    actor = cu["username"] if cu else "Admin"
    active_filters = {k: v for k, v in {
        "q": q, "category": category, "result": result,
        "user": user, "date_from": date_from, "date_to": date_to,
    }.items() if v}
    add_audit_entry(
        "report_exported",
        user=actor,
        target="audit-log",
        detail=f"Audit log CSV export: {len(filtered)} rows. "
               f"Filters: {active_filters if active_filters else 'none'}.",
    )

    today    = _date.today().isoformat()
    filename = f"portwatch_audit_log_{today}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ================================================================== #
# SCAN RESULTS  (replaces the "coming soon" placeholder)
# ================================================================== #

# TODO: protect with Flask-Login admin role check
@admin_bp.route("/scans/<string:scan_id>")
def scan_results(scan_id):
    """
    Scan Results page — detailed findings for a single scan.
    Uses <string:scan_id> (not <int:…>) because IDs are like "SCN-00001".
    """
    from app.mock_data.admin_scans_mock  import (
        get_scan, get_previous_scan, get_next_scan,
    )
    from app.services.scan_comparator    import compare_scans
    from app.utils.remediation_tips      import get_recommendation

    scan = get_scan(scan_id)
    if not scan:
        flash(f"Scan {scan_id} was not found.", "error")
        return redirect(url_for("admin.history"))

    # Enrich each finding with a recommendation
    findings = []
    for f in scan.get("findings", []):
        findings.append({**f, "recommendation": get_recommendation(f)})

    prev_scan = get_previous_scan(scan)
    next_scan = get_next_scan(scan)
    changes   = compare_scans(
        scan.get("findings", []),
        prev_scan.get("findings", []) if prev_scan else None,
    )

    # Count unacknowledged High findings for the alert banner
    unack_high = sum(
        1 for f in scan.get("findings", [])
        if f.get("risk_level") == "High" and not f.get("acknowledged", False)
    )

    # Look up the device (may have been deleted)
    device = get_device_by_id(scan.get("device_id"))

    return render_template(
        "admin/admin_scan_results.html",
        active_page="history",
        scan=scan,
        findings=findings,
        changes=changes,
        prev_scan=prev_scan,
        next_scan=next_scan,
        device=device,
        unack_high=unack_high,
        pdf_url=url_for("admin.scan_report_pdf", scan_id=scan_id),
    )


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/scans/<string:scan_id>/findings/<int:finding_id>/acknowledge",
                methods=["POST"])
def scan_finding_acknowledge(scan_id, finding_id):
    """Acknowledge a single finding (Post/Redirect/Get)."""
    from app.mock_data.admin_scans_mock  import get_scan, acknowledge_finding
    from app.mock_data.admin_audit_log_mock import add_audit_entry

    scan = get_scan(scan_id)
    if not scan:
        flash(f"Scan {scan_id} was not found.", "error")
        return redirect(url_for("admin.history"))

    ok = acknowledge_finding(scan_id, finding_id)
    if ok:
        # TODO: save to database
        add_audit_entry(
            "finding_acknowledged",
            detail=f"Finding {finding_id} in scan {scan_id} acknowledged by Admin.",
        )
        flash("Finding acknowledged.", "success")
    else:
        flash("Finding not found.", "error")

    return redirect(url_for("admin.scan_results", scan_id=scan_id))


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/scans/<string:scan_id>/acknowledge-all", methods=["POST"])
def scan_acknowledge_all(scan_id):
    """Acknowledge all Risky/Unexpected/Missing findings in a scan (Post/Redirect/Get)."""
    from app.mock_data.admin_scans_mock  import get_scan, acknowledge_all
    from app.mock_data.admin_audit_log_mock import add_audit_entry

    scan = get_scan(scan_id)
    if not scan:
        flash(f"Scan {scan_id} was not found.", "error")
        return redirect(url_for("admin.history"))

    count = acknowledge_all(scan_id)
    # TODO: save to database
    add_audit_entry(
        "finding_acknowledged",
        detail=f"All {count} finding(s) in scan {scan_id} acknowledged by Admin.",
    )
    flash(f"{count} finding{'s' if count != 1 else ''} acknowledged.", "success")
    return redirect(url_for("admin.scan_results", scan_id=scan_id))


# TODO: protect with Flask-Login admin role check
@admin_bp.route("/scans/<string:scan_id>/report.pdf")
def scan_report_pdf(scan_id):
    """Generate and return a PDF report for the scan as a download."""
    from flask import Response
    from app.mock_data.admin_scans_mock     import get_scan
    from app.mock_data.admin_audit_log_mock import add_audit_entry
    from app.services.pdf_report_generator  import generate_scan_report_pdf

    scan = get_scan(scan_id)
    if not scan:
        flash(f"Scan {scan_id} was not found.", "error")
        return redirect(url_for("admin.history"))

    pdf_bytes = generate_scan_report_pdf(scan)

    if not pdf_bytes:
        flash("The PDF report could not be generated.", "error")
        return redirect(url_for("admin.history"))

    # TODO: protect with Flask-Login — record who downloaded the report
    add_audit_entry(
        "report_exported",
        detail=f"PDF report exported for scan {scan_id} by Admin.",
    )

    # Build a safe filename: portwatch_SCN-00001_LAB2-SERVER01_2026-11-06.pdf
    import re as _re
    safe_device = _re.sub(r"[^\w\-]", "_", scan.get("device_name", "unknown"))
    scan_date   = (scan.get("started_at").strftime("%Y-%m-%d")
                   if scan.get("started_at") else "unknown-date")
    filename    = f"portwatch_{scan_id}_{safe_device}_{scan_date}.pdf"

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
