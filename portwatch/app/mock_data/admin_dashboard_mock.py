# app/mock_data/admin_dashboard_mock.py
# Dashboard data for PortWatch.
# Now reads scan history from admin_scans_mock.py so the Dashboard,
# Device Registry, and Run Scan page always agree.
#
# TODO: Replace all functions here with real database queries.

from app.mock_data.admin_devices_mock import get_device_summary


def _build_recent_scans():
    """Pull the 8 most recent scans from the scan history mock."""
    from app.mock_data.admin_scans_mock import get_recent_scans
    raw = get_recent_scans(limit=8)
    result = []
    for s in raw:
        result.append({
            "scan_id":     s["id"],
            "device_name": s["device_name"],
            "ip":          s["ip_address"],
            "scan_date":   s["started_at"],
            "open_ports":  s["summary"].get("open_ports", 0),
            "flagged":     s["summary"].get("flagged", 0),
            "highest_risk": s["summary"].get("highest_risk", "None"),
        })
    return result


def _build_summary():
    """
    Build the four Dashboard summary card numbers from live data.
    """
    from app.mock_data.admin_scans_mock import get_findings_summary_all
    device_summary  = get_device_summary()
    findings_totals = get_findings_summary_all()

    return {
        "registered_devices": device_summary["total"],
        "open_ports_found":   findings_totals["open_ports"],
        "flagged_findings":   findings_totals["flagged"],
        "high_risk_findings": findings_totals["high_risk"],
    }


def _build_chart_data():
    """Build chart data from live scan findings."""
    from app.mock_data.admin_scans_mock import get_findings_summary_all
    totals = get_findings_summary_all()
    lc = totals["label_counts"]
    rc = totals["risk_counts"]

    findings_by_label = {
        "labels": ["Approved", "Unexpected", "Risky", "Missing"],
        "counts": [lc.get("Approved", 0), lc.get("Unexpected", 0),
                   lc.get("Risky", 0),    lc.get("Missing", 0)],
        "colors": ["#A6A6A6", "#FFC20E", "#B01B26", "#FFFFFF"],
    }
    findings_by_risk = {
        "labels": ["High", "Medium", "Low"],
        "counts": [rc.get("High", 0), rc.get("Medium", 0), rc.get("Low", 0)],
        "colors": ["#B01B26", "#FFC20E", "#A6A6A6"],
    }
    return findings_by_label, findings_by_risk


def get_admin_dashboard_data():
    """
    Return all data needed to render the Admin Dashboard.
    All numbers now come from live scan history so they update after
    every scan without any manual changes to this file.
    """
    from app.mock_data.admin_scans_mock import get_unacknowledged_high_risk_findings
    high_risk_findings = get_unacknowledged_high_risk_findings()
    chart_label, chart_risk = _build_chart_data()

    return {
        "summary":                _build_summary(),
        "chart_findings_by_label": chart_label,
        "chart_findings_by_risk":  chart_risk,
        "recent_scans":           _build_recent_scans(),
        "high_risk_count":        len(high_risk_findings),
        "alert_scan_id": (
            high_risk_findings[0]["scan_id"] if high_risk_findings else None
        ),
    }
