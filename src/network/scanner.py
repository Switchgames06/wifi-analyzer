# ==============================================================================
# File: src/network/scanner.py
# Author: Jay P M Lynch
# Date of Creation: 2026-06-30
# Date of Last Edit: 2026-07-04
# Version: None
# Description: Multi-threaded IP range scanner. Performs non-invasive ICMP sweeps
#              restricted strictly to safe local subnets to discover online hosts.
#              Queries local OS ARP tables and matches host interfaces.
# ==============================================================================

import os
import subprocess
import platform
import ipaddress
import re
import socket
import psutil
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import our offline classification modules
from src.network.oui_resolver import resolve_oui_vendor, classify_device_type

def ping_host(ip_address):
    """
    Description: Sends a single ICMP echo request to a target IP address using the OS
                 native ping utility. Adjusts CLI flags dynamically for Windows or Linux.
    Args:
        ip_address (str): Target IP address to ping.
    Outputs:
        result (tuple): (ip_address, is_active) where is_active is a boolean.
    """
    if platform.system().lower() == "windows":
        cmd = ["ping", "-n", "1", "-w", "1000", str(ip_address)]
    else:
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
        subnet_cidr (str): Subnet in standard CIDR notation.
        host_ip (str): Optional host IP to ground the /24 slice calculation.
    Outputs:
        ip_list (list): A list of ipaddress.IPv4Address objects to scan.
    """
    try:
        network = ipaddress.IPv4Network(subnet_cidr, strict=False)
        
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


def get_mac_from_arp(ip_address):
    """
    Description: Queries the local operating system's ARP table to retrieve 
                 the physical MAC address associated with a discovered IP.
    Args:
        ip_address (str): Target IP address to look up.
    Outputs:
        mac_str (str): Normalized MAC address (XX:XX:XX:XX:XX:XX) or 'Unknown MAC' on failure.
    """
    is_windows = (platform.system().lower() == "windows")
    
    try:
        if is_windows:
            cmd = ["arp", "-a", str(ip_address)]
            output = subprocess.check_output(
                cmd, 
                stderr=subprocess.DEVNULL, 
                text=True, 
                creationflags=0x08000000
            )
            match = re.search(r"(([0-9a-fA-F]{2}-){5}[0-9a-fA-F]{2})", output)
            if match:
                return match.group(1).replace("-", ":").upper()
        else:
            if os.path.exists("/proc/net/arp"):
                with open("/proc/net/arp", "r") as f:
                    next(f)
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 4 and parts[0] == str(ip_address):
                            mac = parts[3].upper()
                            if mac != "00:00:00:00:00:00":
                                return mac
    except Exception:
        pass

    return "Unknown MAC"


# ADD: Resolves host's own MAC address directly from psutil
def get_self_mac(host_ip):
    """
    Description: Scans the host's physical adapters using psutil to find the 
                 hardware MAC address associated with our active local IP.
    Args:
        host_ip (str): Active local IP address.
    Outputs:
        mac_str (str): Active physical MAC address, or 'Unknown MAC'.
    """
    try:
        adapters = psutil.net_if_addrs()
        for name, addrs in adapters.items():
            has_ip = False
            mac_addr = None
            for addr in addrs:
                if addr.family == socket.AF_INET and addr.address == host_ip:
                    has_ip = True
                if addr.family == psutil.AF_LINK:
                    mac_addr = addr.address
            
            if has_ip and mac_addr:
                return mac_addr.replace("-", ":").upper()
    except Exception:
        pass
    return "Unknown MAC"


def scan_subnet(subnet_cidr, host_ip=None, max_workers=50):
    """
    Description: Orchestrates a multi-threaded ICMP ping sweep, parses OS ARP tables,
                 resolves hardware manufacturers, and categorises discovered hosts.
    Args:
        subnet_cidr (str): Active local subnet in CIDR format.
        host_ip (str): Optional active host IP.
        max_workers (int): Number of parallel threads to dispatch.
    Outputs:
        discovered_devices (list): List of dict structures containing IP, MAC, Vendor, and Type.
    """
    target_hosts = parse_and_optimize_subnet(subnet_cidr, host_ip)
    if not target_hosts:
        return []

    print(f" [*] Beginning parallel sweep of {len(target_hosts)} hosts using {max_workers} threads...")
    active_ips = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(ping_host, ip): ip for ip in target_hosts}
        
        for future in as_completed(futures):
            try:
                ip, is_active = future.result()
                if is_active:
                    active_ips.append(ip)
            except Exception:
                pass

    # Safe Fallback: Ensure the host machine is represented
    if host_ip and host_ip not in active_ips:
        active_ips.append(host_ip)

    discovered_devices = []
    for ip in active_ips:
        # FIX: Query local psutil interface MAC if targeting our own host machine IP
        if ip == host_ip:
            mac = get_self_mac(host_ip)
        else:
            mac = get_mac_from_arp(ip)
            
        vendor = resolve_oui_vendor(mac)
        device_type = classify_device_type(vendor)

        discovered_devices.append({
            "ip": ip,
            "mac": mac,
            "vendor": vendor,
            "device_type": device_type
        })

    discovered_devices.sort(key=lambda dev: ipaddress.IPv4Address(dev["ip"]))
    return discovered_devices