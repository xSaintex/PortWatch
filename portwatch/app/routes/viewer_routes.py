# app/routes/viewer_routes.py
# URL routes for the Viewer role in PortWatch.
# Viewers can see scan results and history but cannot run scans or change anything.

import re as _re
from datetime import date as _date
from flask import Blueprint, render_template, redirect, url_for, flash, Response
from app.utils.auth_decorators import viewer_required

viewer_bp = Blueprint("viewer", __name__, url_prefix="/viewer")


@viewer_bp.route("/dashboard")
@viewer_required
def dashboard():
    """
    Viewer Dashboard — read-only summary of scan findings.
    Reuses the same data functions as the Admin Dashboard so the numbers
    always agree without duplicating logic.
    """
    from app.mock_data.admin_dashboard_mock import (
        _build_summary, _build_recent_scans,
    )
    from app.mock_data.admin_scans_mock import get_unacknowledged_high_risk_findings

    high_risk_findings = get_unacknowledged_high_risk_findings()

    return render_template(
        "viewer/viewer_dashboard.html",
        active_page="dashboard",
        summary=_build_summary(),
        recent_scans=_build_recent_scans(),
        high_risk_count=len(high_risk_findings),
    )


@viewer_bp.route("/history")
@viewer_required
def history():
    """
    Viewer Scan History — read-only, same data as Admin Scan History.
    Reuses the annotation logic so the Changes column and unacknowledged
    dots work identically.
    """
    from app.mock_data.admin_scans_mock import (
        get_all_scans, get_previous_scan,
    )
    from app.mock_data.admin_devices_mock import get_lab_locations
    from app.services.scan_comparator      import compare_scans
    from collections import Counter
    from flask import request as _req

    all_scans = get_all_scans()

    annotated = []
    for s in all_scans:
        prev = get_previous_scan(s)
        changes = compare_scans(
            s.get("findings", []),
            prev.get("findings", []) if prev else None,
        )
        unack_high = sum(
            1 for f in s.get("findings", [])
            if f.get("risk_level") == "High" and not f.get("acknowledged", False)
        )
        annotated.append({**s, "_changes": changes, "_unack_high": unack_high})

    prefill = {
        "search":        _req.args.get("q", ""),
        "deviceName":    "",
        "lab":           _req.args.get("lab",          ""),
        "risk":          _req.args.get("risk",         ""),
        "date_from":     _req.args.get("date_from",    ""),
        "date_to":       _req.args.get("date_to",      ""),
        "unacknowledged": bool(_req.args.get("unacknowledged")),
    }

    job_counts = Counter(
        s["job_id"] for s in all_scans
        if s.get("job_id") and not s["job_id"].startswith("seed-")
    )

    return render_template(
        "viewer/viewer_scan_history.html",
        active_page="history",
        scans=annotated,
        lab_locations=get_lab_locations(),
        total_scans=len(all_scans),
        prefill=prefill,
        job_counts=job_counts,
    )


@viewer_bp.route("/history/export.csv")
@viewer_required
def history_export_csv():
    """
    Export scan history as a CSV file matching the current filters.
    Reuses scan_history_filters.py (same logic as Admin CSV export).
    """
    import csv, io
    from datetime import date as _date
    from flask import request as _req
    from flask_login import current_user
    from app.mock_data.admin_scans_mock     import get_all_scans, get_previous_scan
    from app.mock_data.admin_audit_log_mock import add_audit_entry
    from app.services.scan_comparator      import compare_scans
    from app.services.scan_history_filters import apply_filters

    def _parse_date(s):
        try:
            return _date.fromisoformat(s) if s else None
        except ValueError:
            return None

    filters = {
        "search":        _req.args.get("q",            ""),
        "lab":           _req.args.get("lab",          ""),
        "risk":          _req.args.get("risk",         ""),
        "date_from":     _parse_date(_req.args.get("date_from", "")),
        "date_to":       _parse_date(_req.args.get("date_to",   "")),
        "unacknowledged": bool(_req.args.get("unacknowledged")),
    }

    scans = apply_filters(get_all_scans(), filters)

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
            return "; ".join(f"{x['port']}/{x['protocol']}" for x in items)

        def _svc_list(items):
            return "; ".join(
                f"{x['port']}/{x['protocol']} ({x['old_service']} → {x['new_service']})"
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

    active_filters = {k: v for k, v in filters.items() if v}
    add_audit_entry(
        "report_exported",
        user=current_user.username,
        target="viewer-history",
        detail=(
            f"Viewer CSV export: {len(scans)} rows. "
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


@viewer_bp.route("/scans/<string:scan_id>")
@viewer_required
def scan_results(scan_id):
    """Viewer Scan Results — read-only details for one scan."""
    return render_template(
        "viewer/viewer_scan_results.html",
        active_page="history",
        scan_id=scan_id,
    )


@viewer_bp.route("/scans/<string:scan_id>/report.pdf")
@viewer_required
def scan_report_pdf(scan_id):
    """
    Download a PDF scan report.
    Reuses generate_scan_report_pdf() from the admin service — viewers get
    the same report content, just accessed via the viewer URL prefix.
    """
    from flask_login import current_user
    from app.mock_data.admin_scans_mock import get_scan
    from app.mock_data.admin_audit_log_mock import add_audit_entry
    from app.services.pdf_report_generator import generate_scan_report_pdf

    scan = get_scan(scan_id)
    if not scan:
        flash("Scan not found.", "error")
        return redirect(url_for("viewer.dashboard"))

    pdf_bytes = generate_scan_report_pdf(scan)

    if not pdf_bytes:
        flash("The PDF report could not be generated.", "error")
        return redirect(url_for("viewer.dashboard"))

    add_audit_entry(
        "report_exported",
        user=current_user.username,
        target=scan_id,
        detail=(
            f"PDF report exported for scan {scan_id} "
            f"by {current_user.full_name} (@{current_user.username})."
        ),
    )

    safe_device = _re.sub(r"[^\w\-]", "_", scan.get("device_name", "unknown"))
    scan_date   = (scan.get("started_at").strftime("%Y-%m-%d")
                   if scan.get("started_at") else "unknown-date")
    filename    = f"portwatch_{scan_id}_{safe_device}_{scan_date}.pdf"

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@viewer_bp.route("/account")
@viewer_required
def account():
    """Viewer My Account page — read-only details + change-password form."""
    return render_template(
        "viewer/viewer_my_account.html",
        active_page="account",
        form_errors={},
    )


@viewer_bp.route("/account/password", methods=["POST"])
@viewer_required
def account_change_password():
    """
    Change the currently logged-in viewer's own password.
    Post/Redirect/Get: on success flash + redirect; on error re-render
    with errors under the correct field (never re-fill password fields).

    Why we require the current password:
      An unattended browser session must not allow a silent password change.
      Verifying the current password ensures the person at the keyboard is
      the account owner.
    """
    from flask import request as _req
    from flask_login import current_user
    from app.mock_data.admin_users_mock     import (
        check_user_password, reset_password, get_user,
    )
    from app.mock_data.admin_audit_log_mock import add_audit_entry
    from app.utils.user_validators          import validate_password

    current_pw  = _req.form.get("current_password",  "")
    new_pw      = _req.form.get("new_password",       "")
    confirm_pw  = _req.form.get("confirm_new_password","")

    form_errors = {}

    # 1. Verify the current password (never log it)
    user_dict = get_user(current_user.id)
    if not check_user_password(user_dict, current_pw):
        form_errors["current_password"] = "Current password is incorrect."
        add_audit_entry(
            "password_change_failed",
            user=current_user.username,
            target=current_user.username,
            detail=f"Password change failed: wrong current password for @{current_user.username}.",
            category="Security",
            result="blocked",
        )
        return render_template(
            "viewer/viewer_my_account.html",
            active_page="account",
            form_errors=form_errors,
        )

    # 2. Validate the new password using the shared validator
    pw_error = validate_password(new_pw, confirm_pw)
    if pw_error:
        # Assign the error to the right field
        if "match" in pw_error.lower():
            form_errors["confirm_new_password"] = pw_error
        else:
            form_errors["new_password"] = pw_error
        return render_template(
            "viewer/viewer_my_account.html",
            active_page="account",
            form_errors=form_errors,
        )

    # 3. New password must differ from the current one
    if check_user_password(user_dict, new_pw):
        form_errors["new_password"] = "New password must be different from your current password."
        return render_template(
            "viewer/viewer_my_account.html",
            active_page="account",
            form_errors=form_errors,
        )

    # 4. Save the new password hash (never store the plain text)
    reset_password(current_user.id, new_pw, must_change=False)
    # TODO: save to database

    add_audit_entry(
        "password_changed",
        user=current_user.username,
        target=current_user.username,
        detail=f"@{current_user.username} changed their own password.",
        category="Users",
        result="success",
    )

    flash("Your password has been updated.", "success")
    return redirect(url_for("viewer.account"))
