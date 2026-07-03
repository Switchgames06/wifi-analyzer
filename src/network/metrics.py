# ==============================================================================
# File: src/network/metrics.py
# Author: Jay P M Lynch
# Date of Creation: 2026-06-28
# Date of Last Edit: 2026-06-30
# Version: None
# Description: Monitors real-time network traffic throughput on the host interface
#              by parsing psutil I/O counters and calculating raw delta rates.
# ==============================================================================

import time
import psutil

class TrafficMonitor:
    """
    Description: Tracks instantaneous upload and download throughput rates by calculating
                 the differential change in network I/O bytes over small intervals.
    """
    
    def __init__(self, interface_name):
        """
        Description: Initializes traffic state baselines for delta monitoring.
        Args:
            interface_name (str): Active interface name to observe (e.g., 'eth0').
        Outputs:
            None
        """
        self.interface_name = interface_name
        self.last_timestamp = time.time()
        self.last_bytes_sent, self.last_bytes_recv = self._get_io_bytes()

    def _get_io_bytes(self):
        """
        Description: Fetches raw cumulative bytes sent and received for the monitored interface.
        Args:
            None
        Outputs:
            bytes_sent_recv (tuple): Cumulative (bytes_sent, bytes_received) integers.
        """
        stats = psutil.net_io_counters(pernic=True)
        if self.interface_name in stats:
            io = stats[self.interface_name]
            return io.bytes_sent, io.bytes_recv
        return 0, 0

    def get_throughput(self):
        """
        Description: Calculates the network throughput since the last function execution.
        Args:
            None
        Outputs:
            throughput (dict): Active rates, returning 'upload_kb_s' and 'download_kb_s'.
        """
        current_time = time.time()
        time_delta = current_time - self.last_timestamp
        
        # Avoid dividing by zero if metrics are pulled too rapidly
        if time_delta <= 0:
            time_delta = 0.001

        current_sent, current_recv = self._get_io_bytes()

        # Calculate difference (in bytes)
        delta_sent = current_sent - self.last_bytes_sent
        delta_recv = current_recv - self.last_bytes_recv

        # Handle system I/O counter resets (e.g., if interface cycles offline/online)
        if delta_sent < 0:
            delta_sent = 0
        if delta_recv < 0:
            delta_recv = 0

        # Convert bytes/sec to Kilobytes/sec (1 KB = 1024 bytes)
        upload_rate = (delta_sent / time_delta) / 1024.0
        download_rate = (delta_recv / time_delta) / 1024.0

        # Slide baselines forward
        self.last_timestamp = current_time
        self.last_bytes_sent = current_sent
        self.last_bytes_recv = current_recv

        return {
            "upload_kb_s": round(upload_rate, 2),
            "download_kb_s": round(download_rate, 2)
        }