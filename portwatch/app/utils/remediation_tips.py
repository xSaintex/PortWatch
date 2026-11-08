# app/utils/remediation_tips.py
# REAL reference data: remediation recommendations shown in Scan Results
# and printed in PDF reports for non-Approved findings.
#
# This is permanent reference data, not mock data — it will be used by
# both the web UI and the PDF generator when the app is fully deployed.

# Per-port tips keyed by integer port number.
_PORT_TIPS = {
    21:   "Disable FTP. Use SFTP or FTPS for file transfers; FTP sends credentials in plaintext.",
    22:   "Ensure SSH uses key-based authentication and has password authentication disabled.",
    23:   "Disable Telnet immediately and replace with SSH for all remote access.",
    25:   "Restrict SMTP to authorised mail servers only; enable authentication.",
    80:   "Redirect HTTP to HTTPS so traffic is encrypted in transit.",
    110:  "Migrate from POP3 to IMAP over TLS; disable plain POP3 if no longer needed.",
    135:  "Block MSRPC from external access. Apply all Windows security patches promptly.",
    139:  "Disable NetBIOS over TCP/IP if not required. Restrict SMB to the local network.",
    143:  "Use IMAP over TLS (port 993) and disable unencrypted IMAP.",
    161:  "Use SNMPv3 with authentication and encryption. Change the default community string.",
    443:  "Keep the TLS certificate up to date and enforce TLS 1.2 or higher.",
    445:  "Disable SMB 1.0. Restrict SMB access to authorised lab subnets. Keep Windows patched.",
    1433: "Never expose SQL Server directly to the network. Use a firewall rule to restrict access to application servers only.",
    3306: "Bind MySQL to 127.0.0.1 or restrict to authorised IPs. Never expose it to the public network.",
    3389: "Disable RDP if not required. If needed, restrict to IT staff IPs only and enable Network Level Authentication.",
    5432: "Bind PostgreSQL to 127.0.0.1 or restrict to authorised application hosts.",
    5900: "Disable VNC if possible. If required, restrict access to VPN or IT staff IPs and use strong authentication.",
    8080: "Confirm whether this service is needed. If yes, add it to the allowlist; if not, disable it.",
    8443: "Ensure this HTTPS endpoint uses a valid certificate and is intentionally exposed.",
}

# Default tips per finding label (used when no port-specific tip is available).
_LABEL_TIPS = {
    "Unexpected": (
        "Confirm whether this service is intentional. "
        "If yes, add it to the device's allowlist. "
        "If not, identify and disable the process that opened this port."
    ),
    "Risky": (
        "This port hosts a high-risk service. Review whether it is necessary "
        "and apply the port-specific hardening advice below."
    ),
    "Missing": (
        "The expected service was not found open. "
        "Check whether the service is stopped, crashed, or blocked by a firewall rule."
    ),
    "Approved": (
        "Service differs from what is on the allowlist. "
        "Verify whether this software update was authorised and update the allowlist entry if so."
    ),
}


def get_recommendation(finding):
    """
    Return a remediation recommendation string for a single finding dict.

    Priority:
      1. Port-specific tip (most useful).
      2. Label-based tip.
      3. Generic fallback.

    Args:
        finding (dict): A finding with at least 'port', 'label', 'reason' keys.

    Returns:
        str: A one-sentence recommendation.
    """
    port  = finding.get("port")
    label = finding.get("label", "")

    # Port-specific tip takes priority
    if port and int(port) in _PORT_TIPS:
        return _PORT_TIPS[int(port)]

    # For Approved findings, only show a tip when there is a service mismatch
    if label == "Approved":
        reason = finding.get("reason", "")
        if "Service differs" in reason or "differs" in reason:
            return _LABEL_TIPS["Approved"]
        return ""   # clean Approved findings need no action

    return _LABEL_TIPS.get(label, "Review this finding with the IT Department.")
