# ==============================================================================
# File: src/network/scanner.py
# Author: Jay P M Lynch
# Date of Creation: 2026-06-30
# Date of Last Edit: 2026-07-02
# Version: None
# Description: Multi-threaded IP range scanner. Performs non-invasive ICMP sweeps
#              restricted strictly to safe local subnets to discover online hosts.
# ==============================================================================

import subprocess
import platform
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed

def ping_host(ip_address):
    """
    Description: Sends a single ICMP echo request to a target IP address using the OS
                 native ping utility. Adjusts CLI flags dynamically for Windows or Linux.
    Args:
        ip_address (str): Target IP address to ping (e.g., '192.168.0.1').
    Outputs:
        result (tuple): (ip_address, is_active) where is_active is a boolean.
    """
    # FIX: Dynamically construct ping command arguments based on host OS platform
    if platform.system().lower() == "windows":
        # -n 1 (1 packet), -w 1000 (1000ms timeout)
        cmd = ["ping", "-n", "1", "-w", "1000", str(ip_address)]
    else:
        # -c 1 (1 packet), -W 1 (1 second timeout)
        cmd = ["ping", "-c", "1", "-W", "1", str(ip_address)]
    
    try:
        response = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1.5
        )
        return str(ip_address), (response.returncode == 0)
    except (subprocess.TimeoutExpired, Exception):
        return str(ip_address), False


def parse_and_optimize_subnet(subnet_cidr, host_ip=None):
    """
    Description: Safety mechanism to prevent sweeping unnecessarily massive CIDR blocks.
                 If subnet range contains more than 256 hosts, slices it down to the active
                 local /24 range of the host to preserve processing resources and limit traffic.
    Args:
        subnet_cidr (str): Subnet in standard CIDR notation (e.g., '172.19.64.0/20').
        host_ip (str): Optional host IP to ground the /24 slice calculation.
    Outputs:
        ip_list (list): A list of ipaddress.IPv4Address objects to scan.
    """
    try:
        network = ipaddress.IPv4Network(subnet_cidr, strict=False)
        
        # If network size exceeds a class C subnet (/24), restrict scan range
        if network.num_addresses > 256:
            anchor_ip = host_ip if host_ip else subnet_cidr.split("/")[0]
            octets = anchor_ip.split(".")
            optimized_cidr = f"{octets[0]}.{octets[1]}.{octets[2]}.0/24"
            network = ipaddress.IPv4Network(optimized_cidr, strict=False)
            print(f"  [!] Notice: Large subnet detected ({subnet_cidr}). Slicing scope to immediate {optimized_cidr} for efficiency.")

        return list(network.hosts())
    except Exception as err:
        print(f"  [-] Error optimizing subnet calculation: {err}")
        return []


def scan_subnet(subnet_cidr, host_ip=None, max_workers=50):
    """
    Description: Orchestrates a multi-threaded ICMP ping sweep over a filtered local IP range.
    Args:
        subnet_cidr (str): Active local subnet in CIDR format.
        host_ip (str): Optional active host IP to target slice boundaries.
        max_workers (int): Number of parallel threads to dispatch.
    Outputs:
        active_hosts (list): List of discoverable active IP addresses.
    """
    target_hosts = parse_and_optimize_subnet(subnet_cidr, host_ip)
    if not target_hosts:
        return []

    print(f" [*] Beginning parallel sweep of {len(target_hosts)} hosts using {max_workers} threads...")
    active_hosts = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(ping_host, ip): ip for ip in target_hosts}
        
        for future in as_completed(futures):
            try:
                ip, is_active = future.result()
                if is_active:
                    active_hosts.append(ip)
            except Exception:
                pass

    # Safe Fallback: If host_ip is active but somehow missed ping replies, ensure it is represented
    if host_ip and host_ip not in active_hosts:
        active_hosts.append(host_ip)

    active_hosts.sort(key=lambda ip: ipaddress.IPv4Address(ip))
    return active_hosts