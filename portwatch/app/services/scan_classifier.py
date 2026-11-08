# app/services/scan_classifier.py
# REAL classification logic — compares open ports found by the scanner
# against a device's allowlist and the risky-port reference table, then
# assigns a label and risk level to each finding.
#
# This file does NOT depend on any mock data. It only needs:
#   - The list of open ports returned by the scanner (real or mock)
#   - The device's allowlist entries
#   - app/utils/port_reference.py (the permanent risky-port reference)
#
# When real Nmap scanning is connected, this file stays UNCHANGED.
# Only the function that calls the scanner needs to change.

from app.utils.port_reference import is_risky_port, get_port_info


# ================================================================== #
# LABEL AND RISK LEVEL CONSTANTS
# ================================================================== #

LABEL_APPROVED    = "Approved"
LABEL_UNEXPECTED  = "Unexpected"
LABEL_RISKY       = "Risky"
LABEL_MISSING     = "Missing"

RISK_HIGH   = "High"
RISK_MEDIUM = "Medium"
RISK_LOW    = "Low"
RISK_NONE   = "None"

# Priority order for determining the "highest risk" in a scan summary.
# Higher index = higher priority.
RISK_PRIORITY = {None: 0, RISK_NONE: 1, RISK_LOW: 2, RISK_MEDIUM: 3, RISK_HIGH: 4}


def classify_findings(open_ports, allowlist_entries):
    """
    Compare the scanner's open-port results against a device's allowlist
    and produce a classified list of findings.

    HOW EACH FINDING IS LABELLED (rules in priority order):
    ─────────────────────────────────────────────────────
    1. RISKY — The port is open AND it is marked as high-risk in port_reference.py.
       Risk level: High.
       This label is applied EVEN if the port is on the allowlist, because a risky
       service being open is always worth flagging in the scan results.
       The reason field notes whether the port was approved or not.

    2. APPROVED — The port is open AND it matches an allowlist entry
       (same port number AND same protocol).
       Risk level: None (no problem found).
       EXCEPTION: If the detected service name differs from the allowlist service,
       the finding is still Approved but the reason notes the mismatch.
       This supports detecting silent service changes later.

    3. UNEXPECTED — The port is open but NOT on the allowlist (and not risky).
       Risk level: Medium (something is running that the admin did not approve).

    4. MISSING — The port is on the allowlist with expected_open=True,
       but the scanner did NOT find it open.
       Risk level: Low (the expected service may have stopped or be blocked).

    Args:
        open_ports (list of dict): Ports the scanner found open.
            Each dict has: port (int), protocol (str), state (str),
            service (str), version (str).
        allowlist_entries (list of dict): The device's allowlist from the mock
            (or later the database). Each has: port, protocol, service,
            expected_open (bool).

    Returns:
        dict with keys:
            findings      — list of finding dicts (see below)
            summary       — dict with counts and highest_risk
    """
    findings = []

    # Build a lookup: (port, protocol) -> allowlist entry for quick searching.
    allowlist_map = {
        (int(e["port"]), e["protocol"].lower()): e
        for e in allowlist_entries
    }

    # Track which allowlist (port, protocol) pairs were seen as open,
    # so we can detect Missing ones at the end.
    seen_open = set()

    # ------------------------------------------------------------------ #
    # STEP 1: Process every port the scanner found open.
    # ------------------------------------------------------------------ #
    for port_info in open_ports:
        port     = int(port_info["port"])
        protocol = port_info["protocol"].lower()
        service  = port_info.get("service", "unknown")
        version  = port_info.get("version", "")
        key      = (port, protocol)

        risky       = is_risky_port(port)
        on_allowlist = key in allowlist_map

        if on_allowlist:
            seen_open.add(key)

        if risky:
            # ---- RULE 1: RISKY ---------------------------------------- #
            # Always flag risky services, even if they are allowlisted.
            risky_info = get_port_info(port)
            if on_allowlist:
                reason = (
                    f"High-risk service approved on allowlist. "
                    f"{risky_info['risk_reason']}"
                )
            else:
                reason = (
                    f"High-risk service not on allowlist. "
                    f"{risky_info['risk_reason']}"
                )
            findings.append({
                "port":       port,
                "protocol":   protocol,
                "service":    service,
                "version":    version,
                "label":      LABEL_RISKY,
                "risk_level": RISK_HIGH,
                "reason":     reason,
            })

        elif on_allowlist:
            # ---- RULE 2: APPROVED ------------------------------------- #
            allowlist_service = allowlist_map[key]["service"].lower()
            detected_service  = service.lower()

            if allowlist_service != detected_service and detected_service not in ("", "unknown"):
                # Service mismatch — still Approved but flagged for review
                reason = (
                    f"Service differs: expected '{allowlist_service}', "
                    f"found '{detected_service}'. May indicate a configuration change."
                )
            else:
                reason = "Port matches the approved allowlist entry."

            findings.append({
                "port":       port,
                "protocol":   protocol,
                "service":    service,
                "version":    version,
                "label":      LABEL_APPROVED,
                "risk_level": RISK_NONE,
                "reason":     reason,
            })

        else:
            # ---- RULE 3: UNEXPECTED ----------------------------------- #
            findings.append({
                "port":       port,
                "protocol":   protocol,
                "service":    service,
                "version":    version,
                "label":      LABEL_UNEXPECTED,
                "risk_level": RISK_MEDIUM,
                "reason":     "Port is open but not on the allowlist.",
            })

    # ------------------------------------------------------------------ #
    # STEP 2: Find MISSING ports (allowlisted as required but not found).
    # ------------------------------------------------------------------ #
    for key, entry in allowlist_map.items():
        if entry.get("expected_open") and key not in seen_open:
            # ---- RULE 4: MISSING -------------------------------------- #
            findings.append({
                "port":       key[0],
                "protocol":   key[1],
                "service":    entry["service"],
                "version":    "",
                "label":      LABEL_MISSING,
                "risk_level": RISK_LOW,
                "reason":     (
                    f"Port expected to be open (marked Required on allowlist) "
                    f"but was not found by the scanner."
                ),
            })

    # ------------------------------------------------------------------ #
    # STEP 3: Build the summary.
    # ------------------------------------------------------------------ #
    label_counts = {
        LABEL_APPROVED:   0,
        LABEL_UNEXPECTED: 0,
        LABEL_RISKY:      0,
        LABEL_MISSING:    0,
    }
    risk_counts = {RISK_HIGH: 0, RISK_MEDIUM: 0, RISK_LOW: 0, RISK_NONE: 0}
    highest_risk = RISK_NONE

    for f in findings:
        label_counts[f["label"]] = label_counts.get(f["label"], 0) + 1
        rl = f["risk_level"]
        if rl and rl != RISK_NONE:
            risk_counts[rl] = risk_counts.get(rl, 0) + 1
        if RISK_PRIORITY.get(rl, 0) > RISK_PRIORITY.get(highest_risk, 0):
            highest_risk = rl

    flagged = (
        label_counts[LABEL_UNEXPECTED]
        + label_counts[LABEL_RISKY]
        + label_counts[LABEL_MISSING]
    )

    summary = {
        "open_ports":     len(open_ports),
        "flagged":        flagged,
        "label_counts":   label_counts,
        "risk_counts":    risk_counts,
        "highest_risk":   highest_risk,
    }

    # Sort findings: Risky first, then Unexpected, then Missing, then Approved
    label_order = {LABEL_RISKY: 0, LABEL_UNEXPECTED: 1, LABEL_MISSING: 2, LABEL_APPROVED: 3}
    findings.sort(key=lambda f: (label_order.get(f["label"], 9), f["port"]))

    return {"findings": findings, "summary": summary}
