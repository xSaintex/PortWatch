# app/services/scan_comparator.py
# REAL change-detection logic — compares a scan's open ports against the
# previous scan of the same device and reports what opened, closed, or changed.
#
# This file has NO dependency on mock data. It only works with the lists
# of findings that both the current and previous scan already contain.
# When the database is added, this function continues to work unchanged.

# ── What counts as "open" for comparison purposes ─────────────────────────
# We compare only ports that were physically found open by the scanner.
# "Missing" findings (allowlisted but not found open) are excluded because
# they represent closed ports, not open ones; including them would cause
# false "closed" reports that duplicate the Missing label.
_OPEN_LABELS = {"Approved", "Unexpected", "Risky"}


def compare_scans(current_findings, previous_findings):
    """
    Detect port-level changes between two scans of the same device.

    HOW EACH CHANGE CATEGORY IS DEFINED:
    ──────────────────────────────────────
    newly_opened:
        A port+protocol pair is open NOW but was NOT open in the previous scan.
        This could mean a new service was started, a firewall rule changed, or
        malware opened a backdoor. Worth flagging for review.

    closed:
        A port+protocol pair was open in the PREVIOUS scan but is NOT open now.
        Could be normal (a service stopped) or unexpected (a required service
        went down). The allowlist "Missing" label already tracks allowlisted
        closed ports; this is for general awareness.

    service_changed:
        The same port+protocol is open in BOTH scans, but the detected service
        name or version string has changed. This can indicate an upgrade,
        a service swap, or (in a security context) a service being replaced
        by a malicious lookalike.

    is_first_scan:
        True when previous_findings is None or empty. There is nothing to
        compare against, so "no changes" would be misleading.

    has_changes:
        Convenience flag — True if at least one of the three lists is non-empty.

    Args:
        current_findings  (list): Findings from the scan being displayed.
                                  Each is a dict with keys: port, protocol,
                                  service, version, label, risk_level.
        previous_findings (list | None): Findings from the immediately
                                  preceding scan of the same device.
                                  None or [] means this is the first scan.

    Returns:
        dict with keys:
            is_first_scan    (bool)
            has_changes      (bool)
            newly_opened     (list of dicts: port, protocol, service, version)
            closed           (list of dicts: port, protocol, service, version)
            service_changed  (list of dicts: port, protocol,
                              old_service, new_service,
                              old_version, new_version)
    """
    # ── Handle first-scan edge case ──────────────────────────────────────
    if not previous_findings:
        return {
            "is_first_scan":   True,
            "has_changes":     False,
            "newly_opened":    [],
            "closed":          [],
            "service_changed": [],
        }

    # ── Build lookup maps keyed by (port, protocol) ─────────────────────
    # We only include findings that represent actually-open ports.
    def _open_map(findings):
        m = {}
        for f in (findings or []):
            if f.get("label") in _OPEN_LABELS:
                key = (int(f["port"]), f["protocol"].lower())
                m[key] = f
        return m

    current_map  = _open_map(current_findings)
    previous_map = _open_map(previous_findings)

    current_keys  = set(current_map.keys())
    previous_keys = set(previous_map.keys())

    # ── NEWLY OPENED: in current but not in previous ─────────────────────
    newly_opened = []
    for key in current_keys - previous_keys:
        f = current_map[key]
        newly_opened.append({
            "port":     f["port"],
            "protocol": f["protocol"],
            "service":  f.get("service", ""),
            "version":  f.get("version", ""),
        })
    newly_opened.sort(key=lambda x: x["port"])

    # ── CLOSED: in previous but not in current ───────────────────────────
    closed = []
    for key in previous_keys - current_keys:
        f = previous_map[key]
        closed.append({
            "port":     f["port"],
            "protocol": f["protocol"],
            "service":  f.get("service", ""),
            "version":  f.get("version", ""),
        })
    closed.sort(key=lambda x: x["port"])

    # ── SERVICE/VERSION CHANGED: same port in both, but different details ─
    service_changed = []
    for key in current_keys & previous_keys:
        cur  = current_map[key]
        prev = previous_map[key]

        cur_svc  = (cur.get("service")  or "").strip().lower()
        prev_svc = (prev.get("service") or "").strip().lower()
        cur_ver  = (cur.get("version")  or "").strip()
        prev_ver = (prev.get("version") or "").strip()

        svc_diff = cur_svc  != prev_svc  and cur_svc  and prev_svc
        ver_diff = cur_ver  != prev_ver  and cur_ver  and prev_ver

        if svc_diff or ver_diff:
            service_changed.append({
                "port":        cur["port"],
                "protocol":    cur["protocol"],
                "old_service": prev.get("service", ""),
                "new_service": cur.get("service",  ""),
                "old_version": prev_ver,
                "new_version": cur_ver,
            })
    service_changed.sort(key=lambda x: x["port"])

    has_changes = bool(newly_opened or closed or service_changed)

    return {
        "is_first_scan":   False,
        "has_changes":     has_changes,
        "newly_opened":    newly_opened,
        "closed":          closed,
        "service_changed": service_changed,
    }
