# app/services/scan_history_filters.py
# Server-side filter logic for the Scan History page.
#
# This is a pure Python function that takes a list of scan records and a
# set of filter criteria and returns the matching subset. It is used by
# both the page route (to know total counts for the summary strip) and the
# CSV export route (so the downloaded file always matches what the user sees).
#
# Keeping the filter logic here — rather than duplicating it in two routes —
# means any change to filtering behaviour is made in one place only.

from datetime import datetime, date


def apply_filters(scans, filters):
    """
    Filter a list of scan records according to the given criteria.

    Args:
        scans   (list): All scan records (dicts), newest first.
        filters (dict): May contain any subset of:
            search          (str)  — matches device name or IP (case-insensitive)
            device_id       (int)  — exact device ID
            lab             (str)  — device lab/location (case-insensitive exact)
            risk            (str)  — "High", "Medium", "Low", or "None"
            date_from       (date) — inclusive start date (compares started_at.date())
            date_to         (date) — inclusive end date
            unacknowledged  (bool) — only scans with ≥1 unacknowledged High finding

    Returns:
        list: The filtered subset, preserving the input order (newest first).
    """
    search        = (filters.get("search")        or "").strip().lower()
    # device_id filter kept for compatibility; currently unused (device dropdown removed).
    device_id     = filters.get("device_id")
    lab           = (filters.get("lab")           or "").strip().lower()
    risk          = (filters.get("risk")          or "").strip()
    date_from     = filters.get("date_from")       # date or None
    date_to       = filters.get("date_to")         # date or None
    unacknowledged = bool(filters.get("unacknowledged"))

    result = []
    for s in scans:
        # ── Search: device name or IP ────────────────────────────────
        if search:
            if (search not in s.get("device_name", "").lower() and
                    search not in s.get("ip_address", "").lower()):
                continue

        # ── Device ID ────────────────────────────────────────────────
        if device_id is not None and s.get("device_id") != device_id:
            continue

        # ── Lab / Location ────────────────────────────────────────────
        if lab:
            scan_lab = (s.get("lab_location") or "").strip().lower()
            if scan_lab != lab:
                continue

        # ── Highest risk ──────────────────────────────────────────────
        if risk:
            scan_risk = s.get("summary", {}).get("highest_risk", "None")
            if scan_risk != risk:
                continue

        # ── Date range ────────────────────────────────────────────────
        scan_date = s.get("started_at")
        if isinstance(scan_date, datetime):
            scan_date = scan_date.date()

        if date_from and scan_date and scan_date < date_from:
            continue
        if date_to   and scan_date and scan_date > date_to:
            continue

        # ── Unacknowledged High findings ──────────────────────────────
        if unacknowledged:
            has_unack_high = any(
                f.get("risk_level") == "High" and not f.get("acknowledged", False)
                for f in s.get("findings", [])
            )
            if not has_unack_high:
                continue

        result.append(s)

    return result
