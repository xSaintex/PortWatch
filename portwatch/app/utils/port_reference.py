# app/utils/port_reference.py
# Reference data for common network ports used by PortWatch.
#
# PURPOSE:
#   This is NOT mock data. It is real, permanent reference information that:
#     1. Populates the "Service" auto-fill in the Add/Edit Port modal.
#     2. Drives the "Risky" badge and tooltip in the Allowlist table.
#     3. Will be used by the Nmap scanner (later) to label findings.
#
# SERVICE NAMES:
#   Service names intentionally match Nmap's output naming so that scan
#   results can be compared directly against allowlist entries without
#   any translation step. For example, Nmap returns "ms-wbt-server" for
#   port 3389, so that is the name used here — not "RDP".
#
# TODO: Expand this list as more services are encountered in lab scans.

# Each key is an integer port number.
# Each value is a dict:
#   service     — Nmap service name (lowercase, hyphens, no spaces)
#   description — Human-readable description shown in the UI
#   is_risky    — True if this port/service is considered high-risk
#   risk_reason — Explanation shown in the risky warning box (only when is_risky)

PORT_REFERENCE = {
    21: {
        "service":     "ftp",
        "description": "File Transfer Protocol — transfers files in plaintext",
        "is_risky":    True,
        "risk_reason": "FTP transmits credentials and data unencrypted. Use SFTP or FTPS instead.",
    },
    22: {
        "service":     "ssh",
        "description": "Secure Shell — encrypted remote administration",
        "is_risky":    False,
        "risk_reason": "",
    },
    23: {
        "service":     "telnet",
        "description": "Telnet — remote terminal access in plaintext",
        "is_risky":    True,
        "risk_reason": "Telnet sends all data including passwords unencrypted. Use SSH instead.",
    },
    25: {
        "service":     "smtp",
        "description": "Simple Mail Transfer Protocol — sends email",
        "is_risky":    False,
        "risk_reason": "",
    },
    53: {
        "service":     "domain",
        "description": "DNS — resolves domain names to IP addresses",
        "is_risky":    False,
        "risk_reason": "",
    },
    80: {
        "service":     "http",
        "description": "HTTP — unencrypted web traffic",
        "is_risky":    False,
        "risk_reason": "",
    },
    110: {
        "service":     "pop3",
        "description": "Post Office Protocol — retrieves email from a server",
        "is_risky":    False,
        "risk_reason": "",
    },
    135: {
        "service":     "msrpc",
        "description": "Microsoft RPC endpoint mapper",
        "is_risky":    True,
        "risk_reason": "MSRPC has a history of critical remote-execution vulnerabilities and is commonly exploited.",
    },
    139: {
        "service":     "netbios-ssn",
        "description": "NetBIOS Session Service — Windows file/printer sharing",
        "is_risky":    True,
        "risk_reason": "NetBIOS exposes host information and has been exploited in attacks like EternalBlue.",
    },
    143: {
        "service":     "imap",
        "description": "Internet Message Access Protocol — reads email from a server",
        "is_risky":    False,
        "risk_reason": "",
    },
    161: {
        "service":     "snmp",
        "description": "Simple Network Management Protocol — network device monitoring",
        "is_risky":    False,
        "risk_reason": "",
    },
    443: {
        "service":     "https",
        "description": "HTTP over TLS/SSL — encrypted web traffic",
        "is_risky":    False,
        "risk_reason": "",
    },
    445: {
        "service":     "microsoft-ds",
        "description": "Microsoft Directory Services / SMB file sharing",
        "is_risky":    True,
        "risk_reason": "SMB (port 445) has been exploited by WannaCry, EternalBlue, and other major attacks. Keep patched and firewalled.",
    },
    1433: {
        "service":     "ms-sql-s",
        "description": "Microsoft SQL Server database",
        "is_risky":    True,
        "risk_reason": "Exposing a database server directly is a major risk. Ensure strong credentials and restrict access.",
    },
    3306: {
        "service":     "mysql",
        "description": "MySQL / MariaDB database server",
        "is_risky":    True,
        "risk_reason": "Exposing a database server directly is a major risk. Ensure strong credentials and restrict access.",
    },
    3389: {
        "service":     "ms-wbt-server",
        "description": "Remote Desktop Protocol (RDP) — Windows remote desktop",
        "is_risky":    True,
        "risk_reason": "RDP is a frequent target for brute-force and ransomware attacks. Restrict to trusted IPs only.",
    },
    5432: {
        "service":     "postgresql",
        "description": "PostgreSQL database server",
        "is_risky":    True,
        "risk_reason": "Exposing a database server directly is a major risk. Ensure strong credentials and restrict access.",
    },
    5900: {
        "service":     "vnc",
        "description": "Virtual Network Computing — graphical remote desktop",
        "is_risky":    True,
        "risk_reason": "VNC has historically weak authentication and is frequently scanned by attackers. Use a VPN instead.",
    },
    8080: {
        "service":     "http-proxy",
        "description": "HTTP alternate port — often used for web proxies or dev servers",
        "is_risky":    False,
        "risk_reason": "",
    },
    8443: {
        "service":     "https-alt",
        "description": "HTTPS alternate port — encrypted web traffic on non-standard port",
        "is_risky":    False,
        "risk_reason": "",
    },
    9090: {
        "service":     "zeus-admin",
        "description": "Web management interface (common for monitoring tools)",
        "is_risky":    False,
        "risk_reason": "",
    },
}


# ================================================================== #
# HELPER FUNCTIONS
# ================================================================== #

def get_port_info(port):
    """
    Look up a port number in the reference dictionary.

    Args:
        port (int): The port number to look up.

    Returns:
        dict or None: The reference dict for that port, or None if unknown.
    """
    return PORT_REFERENCE.get(int(port))


def is_risky_port(port):
    """
    Return True if the port is flagged as high-risk in the reference data.
    Returns False for unknown ports (unknown is not the same as risky).

    Args:
        port (int): The port number to check.
    """
    info = get_port_info(port)
    return bool(info and info.get("is_risky"))
