# app/mock_data/mock_nmap_scanner.py
# Temporary mock Nmap scanner for development and testing.
# Will be replaced by app/services/nmap_scanner.py using python-nmap.
#
# PURPOSE:
#   Returns realistic-looking scan results WITHOUT actually running Nmap.
#   This lets the full scan pipeline (verify → scan → classify → save) be
#   developed and tested before a real lab network is available.
#
# OUTPUT FORMAT:
#   Returns a list of dicts in the SAME shape that the real nmap_scanner.py
#   will return, so the classifier and job manager need no changes later.
#   Each dict: {port, protocol, state, service, version}
#
# SLEEP BEHAVIOUR:
#   The scanner sleeps to simulate scan time, but ONLY when running inside
#   a real HTTP request. Seeding (at import time) and tests skip the sleep
#   automatically so startup is fast.

import random
import time


# ------------------------------------------------------------------ #
# PER-DEVICE SCAN PROFILE
# Defines what each device "normally" has open for realistic results.
# Keys are IP address suffixes (last octet as int) for readability.
# ------------------------------------------------------------------ #

# Default Windows workstation profile
_WS_PORTS = [
    {"port": 135, "protocol": "tcp", "service": "msrpc",        "version": "Microsoft Windows RPC"},
    {"port": 139, "protocol": "tcp", "service": "netbios-ssn",  "version": "Microsoft Windows netbios-ssn"},
    {"port": 445, "protocol": "tcp", "service": "microsoft-ds", "version": "Windows Server 2019 microsoft-ds"},
]

# Server profile
_SRV_PORTS = [
    {"port": 22,   "protocol": "tcp", "service": "ssh",          "version": "OpenSSH 8.9p1"},
    {"port": 80,   "protocol": "tcp", "service": "http",         "version": "Apache httpd 2.4.57"},
    {"port": 443,  "protocol": "tcp", "service": "https",        "version": "Apache httpd 2.4.57"},
    {"port": 3306, "protocol": "tcp", "service": "mysql",        "version": "MySQL 8.0.35"},
    {"port": 445,  "protocol": "tcp", "service": "microsoft-ds", "version": "Windows Server 2019 microsoft-ds"},
    {"port": 3389, "protocol": "tcp", "service": "ms-wbt-server","version": "Microsoft Terminal Services"},
    {"port": 8080, "protocol": "tcp", "service": "http-proxy",   "version": "Apache Tomcat 10.1"},
]

# Network device profile (switch)
_NET_PORTS = [
    {"port": 22,  "protocol": "tcp", "service": "ssh",    "version": "OpenSSH 7.4"},
    {"port": 80,  "protocol": "tcp", "service": "http",   "version": "lighttpd 1.4.55"},
    {"port": 161, "protocol": "udp", "service": "snmp",   "version": "SNMPv2c"},
]


def _parse_port_spec(port_spec):
    """
    Parse a port specification string into a set of integer port numbers.
    Supports individual ports (e.g. "22") and ranges (e.g. "1-1024"),
    separated by commas.

    Returns a set of ints, or None for "top-ports" (scan all common ports).
    """
    if port_spec.startswith("top"):
        return None   # caller treats None as "top N ports — return everything"

    ports = set()
    for part in port_spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            for p in range(int(lo), int(hi) + 1):
                ports.add(p)
        elif part:
            ports.add(int(part))
    return ports


def scan_device(ip_address, port_spec="top1000", _sleep=True):
    """
    Simulate scanning a single device and return a list of open ports.

    Args:
        ip_address (str): The device's IPv4 address (used as random seed).
        port_spec  (str): "top1000" for the default top-ports scan, or a
                          custom spec like "22,80,443" or "1-1024".
        _sleep     (bool): Set False to skip the simulated delay (used by
                           seeding and tests so startup stays fast).

    Returns:
        list of dict: Open ports. Each dict has:
            port (int), protocol (str), state (str), service (str), version (str)
    """
    # Seed the random number generator with the IP for consistent per-device results
    seed = int(ip_address.replace(".", ""))
    rng  = random.Random(seed)

    # Sleep to simulate real scan duration — only during live HTTP requests
    if _sleep:
        try:
            import flask
            if flask.has_request_context():
                from flask import current_app
                mock_duration = current_app.config.get("MOCK_SCAN_DURATION_SECONDS", 8)
                time.sleep(mock_duration * 0.3)
        except RuntimeError:
            pass  # no app context — skip sleep

    # Choose a base profile based on the IP address
    last_octet = int(ip_address.split(".")[-1])

    if last_octet >= 30:       # servers (30, 31) and network devices (1)
        if last_octet == 1:
            base_ports = list(_NET_PORTS)
        else:
            base_ports = list(_SRV_PORTS)
    else:                      # workstations
        base_ports = list(_WS_PORTS)

    # Instructor PC (last octet 16) also gets RDP
    if last_octet == 16:
        base_ports.append(
            {"port": 3389, "protocol": "tcp",
             "service": "ms-wbt-server", "version": "Microsoft Terminal Services"}
        )
        base_ports.append(
            {"port": 8080, "protocol": "tcp",
             "service": "http-proxy", "version": "Python SimpleHTTPServer 3.11"}
        )

    # Some workstations randomly have an extra unexpected port
    if last_octet not in (1, 30, 31) and rng.random() < 0.45:
        extras = [
            {"port": 3389, "protocol": "tcp", "service": "ms-wbt-server", "version": "Microsoft Terminal Services"},
            {"port": 5900, "protocol": "tcp", "service": "vnc",           "version": "RealVNC 6.7.2"},
            {"port": 8080, "protocol": "tcp", "service": "http-proxy",    "version": "Jetty 9.4"},
            {"port": 21,   "protocol": "tcp", "service": "ftp",           "version": "vsftpd 3.0.3"},
            {"port": 23,   "protocol": "tcp", "service": "telnet",        "version": "Microsoft Windows telnetd"},
        ]
        chosen = rng.choice(extras)
        # Only add if not already in base
        if not any(p["port"] == chosen["port"] for p in base_ports):
            base_ports.append(chosen)

    # Some devices have a required port that is closed (produces Missing)
    # Drop one expected port about 20% of the time
    if rng.random() < 0.20 and len(base_ports) > 1:
        base_ports.pop(rng.randint(0, len(base_ports) - 1))

    # Apply port spec filter (only include ports that are in the requested range)
    allowed_ports = _parse_port_spec(port_spec)
    if allowed_ports is not None:
        base_ports = [p for p in base_ports if p["port"] in allowed_ports]

    # Format results: add state = "open"
    results = []
    for p in base_ports:
        results.append({
            "port":     p["port"],
            "protocol": p["protocol"],
            "state":    "open",
            "service":  p["service"],
            "version":  p["version"],
        })

    return results
