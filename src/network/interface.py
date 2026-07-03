# ==============================================================================
# File: src/network/interface.py
# Author: Jay P M Lynch
# Date of Creation: 2026-06-28
# Date of Last Edit: 2026-06-30
# Version: None
# Description: Resolves local network configurations including active interfaces,
#              IP addresses, subnets, default gateways, and egress connectivity status.
# ==============================================================================

import os
import socket
import struct
import ipaddress
import sys
import psutil

def get_outbound_ip_fallback():
    """
    Description: Determines the host's active local IP address using a UDP socket.
                 This triggers the OS routing table to expose the primary route.
    Args:
        None
    Outputs:
        local_ip (str): Detected primary outbound IP address, or '127.0.0.1'.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Target a public IP to evaluate route path. Does not send actual data.
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = "127.0.0.1"
    finally:
        s.close()
    return local_ip


def get_active_interface_config():
    """
    Description: Resolves active network adapter metrics (IP, netmask, subnet) 
                 by matching active outbound IP routing against psutil interfaces.
                 Works seamlessly on Windows, macOS, and Linux.
    Args:
        None
    Outputs:
        config (dict): Active interface statistics, or None if offline.
    """
    active_ip = get_outbound_ip_fallback()
    if active_ip == "127.0.0.1":
        return None

    # ADD: Cross-platform loop matching active IP to its operating system adapter name
    interfaces = psutil.net_if_addrs()
    for name, addrs in interfaces.items():
        for addr in addrs:
            if addr.family == socket.AF_INET and addr.address == active_ip:
                netmask = addr.netmask
                
                # Compute CIDR block
                try:
                    network = ipaddress.IPv4Network(f"{active_ip}/{netmask}", strict=False)
                    subnet_cidr = str(network)
                except Exception:
                    subnet_cidr = f"{active_ip}/24"

                return {
                    "interface_name": name,
                    "ip": active_ip,
                    "netmask": netmask,
                    "subnet_cidr": subnet_cidr
                }
    return None


def check_internet_connection(host="8.8.8.8", port=53, timeout=2.0):
    """
    Description: Verifies network egress capability by establishing a lightweight TCP handshake.
    Args:
        host (str): IP address of target host.
        port (int): Port of target host.
        timeout (float): Connection timeout threshold.
    Outputs:
        is_online (bool): True if connection succeeds, False otherwise.
    """
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except socket.error:
        return False