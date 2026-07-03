# ==============================================================================
# File: src/network/speed.py
# Author: Jay P M Lynch
# Date of Creation: 2026-06-28
# Date of Last Edit: 2026-06-30
# Version: None
# Description: Wrapper interface for the speedtest-cli library. Handles remote
#              test server discovery, latency polling, and speed evaluations.
# ==============================================================================

import speedtest

def run_bandwidth_evaluation():
    """
    Description: Contacts public Speedtest servers, determines the lowest latency peer,
                 and executes download and upload bandwidth testing.
    Args:
        None
    Outputs:
        results (dict): Diagnostic metrics containing 'ping_ms', 'download_mbps', 
                        and 'upload_mbps', or None if network errors occur.
    """
    try:
        # Initialize the Speedtest controller object
        st = speedtest.Speedtest(secure=True)
        
        # Discover optimal target server based on latency/physical proximity
        st.get_best_server()
        
        # Run tests (returns results in bits per second, which we convert to Megabits/s)
        download_bps = st.download()
        upload_bps = st.upload()
        ping_ms = st.results.ping

        return {
            "ping_ms": round(ping_ms, 2),
            "download_mbps": round(download_bps / 1_000_000.0, 2),
            "upload_mbps": round(upload_bps / 1_000_000.0, 2)
        }
    except Exception as err:
        # Contain socket errors or API deprecation issues silently to report failures cleanly
        print(f"[-] Speedtest run aborted due to error: {err}")
        return None