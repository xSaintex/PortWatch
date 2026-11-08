import nmap

scanner = nmap.PortScanner()
scanner.scan("127.0.0.1", "1-1024")

for host in scanner.all_hosts():
    print(f"Host: {host} ({scanner[host].state()})")
    for proto in scanner[host].all_protocols():
        for port in sorted(scanner[host][proto].keys()):
            info = scanner[host][proto][port]
            print(f"  {port}/{proto}  {info['state']}  {info['name']}")