# ==============================================================================
# File: src/network/oui_resolver.py
# Author: Jay P M Lynch
# Date of Creation: 2026-07-04
# Date of Last Edit: 2026-07-04
# Version: None
# Description: Advanced offline OUI (Organizationally Unique Identifier) 
#              dictionary and device classifier. Categorises MAC addresses 
#              and dynamically detects locally-administered randomized MACs.
# ==============================================================================

# Expanded database containing specific home device signatures
OUI_DB = {
    # Apple (iPhones, iPads, Macs, AppleTVs)
    "F82793": "Apple Inc.",
    "3CD0F8": "Apple Inc.",
    "E05163": "Apple Inc.",
    "001CB3": "Apple Inc.",
    "A05272": "Apple Inc.", 
    "28C709": "Apple Inc.",
    
    # Sagemcom
    "345D9E": "Sagemcom Broadband SAS",
    "7C1689": "Sagemcom Broadband SAS",
    
    # Wistron Neweb (ROG Motherboards, Wi-Fi Chips, TVs)
    "BC307E": "Wistron Neweb Corp (ROG/Wireless Chipset)",
    
    # Samsung (Smart TVs, Mobile Devices)
    "3C5A37": "Samsung Electronics",
    "0012FB": "Samsung Electronics",
    "D0E782": "Samsung Electronics",
    
    # LG (Smart TVs, Home Appliances)
    "001C62": "LG Electronics",
    "B4E1EB": "LG Electronics",
    
    # Sony (PlayStations, Smart TVs)
    "0013E3": "Sony Interactive",
    "A8E3EE": "Sony Corporation",
    
    # Gaming Consoles
    "001F32": "Nintendo Co., Ltd.",
    "E0E751": "Nintendo Co., Ltd.",
    "0009DD": "Sega/SegaNet",
    
    # Network Infrastructure / Routers
    "0014D1": "TP-Link Technologies",
    "503EAA": "TP-Link Technologies",
    "00180A": "Cisco Systems",
    "000F66": "Cisco-Linksys",
    "240A64": "Netgear",
    
    # Laptops / Personal Computers
    "0050B6": "Hewlett-Packard",
    "000F1F": "Dell Inc.",
    "001676": "Intel Corporation",
    "001A92": "Asustek Computer",
    "3C5282": "Lenovo",
    
    # Smart Home / IoT Systems
    "18FE34": "Espressif Inc. (IoT)",
    "240AC4": "Espressif Inc. (IoT)",
    "30AEA4": "Espressif Inc. (IoT)",
    "B827EB": "Raspberry Pi Foundation",
    "DCA632": "Raspberry Pi Foundation",
    "001A11": "Google LLC (Chromecast/Nest)",
    "F80FF9": "Google LLC (Chromecast/Nest)"
}

def resolve_oui_vendor(mac_address):
    """
    Description: Normalizes a physical MAC address and extracts its OUI block
                 to cross-reference against our offline vendor database.
                 Dynamically identifies randomized/locally administered private MACs.
    Args:
        mac_address (str): Target physical hardware address (e.g., '3C-D0-F8-12-34-56').
    Outputs:
        vendor_name (str): The identified manufacturer, or 'Unknown Vendor'.
    """
    if not mac_address or mac_address == "Unknown MAC":
        return "Unknown Vendor"

    # Normalize MAC string into raw hex characters (e.g. "3CD0F8123456")
    clean_mac = mac_address.replace(":", "").replace("-", "").upper()
    
    # ADD: Detect if the second hex digit is 2, 6, A, or E (The U/L Locally Administered bit)
    # This signifies a randomized virtual MAC used by modern mobile OSes for privacy.
    if len(clean_mac) >= 2 and clean_mac[1] in ["2", "6", "A", "E"]:
        return "Private MAC (Locally Administered)"

    oui_prefix = clean_mac[:6]
    return OUI_DB.get(oui_prefix, "Unknown Vendor")


def classify_device_type(vendor_name):
    """
    Description: Analyzes a manufacturer's profile name using string heuristic 
                 keywords to classify devices into user-friendly hardware groups.
    Args:
        vendor_name (str): Target manufacturer's name.
    Outputs:
        category (str): Identified hardware category (e.g., 'Smart TV / Media').
    """
    vendor_lower = vendor_name.lower()

    # ADD: Handle randomized private MACs
    if "private mac" in vendor_lower:
        return "Mobile Phone / Tablet (Privacy Randomized)"
    elif "sagemcom" in vendor_lower:
        return "Home Gateway / Wi-Fi Router"
    elif "apple" in vendor_lower:
        return "Apple Device (Phone/Tablet/Mac)"
    elif any(brand in vendor_lower for brand in ["samsung", "lg", "sony corporation"]):
        return "Smart TV / Media Display"
    elif any(gaming in vendor_lower for gaming in ["nintendo", "sony interactive", "sega"]):
        return "Gaming Console"
    elif any(network in vendor_lower for network in ["tp-link", "cisco", "netgear", "linksys"]):
        return "Network Infrastructure"
    elif any(pc in vendor_lower for pc in ["dell", "hewlett", "intel", "asustek", "lenovo", "wistron"]):
        return "PC / Laptop / Desktop"
    elif any(iot in vendor_lower for iot in ["espressif", "raspberry", "google"]):
        return "Smart Home / IoT Device"
    
    return "Unknown Device Type"