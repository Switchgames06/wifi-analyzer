# ==============================================================================
# File: src/ui/dashboard.py
# Author: Jay P M Lynch
# Date of Creation: 2026-07-03
# Date of Last Edit: 2026-07-03
# Version: None
# Description: Modern graphical user interface constructed via CustomTkinter.
#              Contains embedded Matplotlib telemetry plots, background worker
#              thread orchestration, and safe window clean-up handlers.
# ==============================================================================

import sys
import threading
import queue
import time
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Backend core imports
from src.network.interface import get_active_interface_config, check_internet_connection
from src.network.metrics import TrafficMonitor
from src.network.speed import run_bandwidth_evaluation
from src.network.scanner import scan_subnet

class NetworkAnalyzerApp(ctk.CTk):
    """
    Description: Primary application class holding main thread execution, customtkinter
                 layout managers, navigation panels, and multi-threaded coordination.
    """
    def __init__(self):
        """
        Description: Initialises system telemetry buffers, UI themes, and frame stacks.
        Args:
            None
        Outputs:
            None
        """
        super().__init__()

        # Window Metadata
        self.title("Local Wi-Fi & Network Diagnostic Analyzer")
        self.geometry("1100x650")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # FIX: Formulate a positive 30-second rolling window [1, 2, ..., 30]
        self.time_series = list(range(1, 31))
        self.download_series = [0.0] * 30
        self.upload_series = [0.0] * 30

        # Track active .after() loop handles to prevent orphaned event executions on exit
        self.metrics_after_id = None
        self.workers_after_id = None

        # Background Worker Synchronization Queues
        self.speedtest_queue = queue.Queue()
        self.scanner_queue = queue.Queue()

        # Resolve active network configs
        self.network_config = get_active_interface_config()
        self.traffic_monitor = None
        if self.network_config:
            self.traffic_monitor = TrafficMonitor(self.network_config["interface_name"])

        # Setup GUI Component layout
        self._build_sidebar()
        self._build_dashboard_panel()
        self._build_speedtest_panel()
        self._build_scanner_panel()

        # Raise default panel
        self.select_panel("dashboard")

        # Start live monitoring loop
        if self.traffic_monitor:
            self.update_live_metrics()
            
        # Register frame queue observers
        self.observe_background_workers()

        # Override default window manager deletion protocol to execute clean termination
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _build_sidebar(self):
        """
        Description: Construct lateral sidebar layout displaying logo labels and panel toggles.
        Args:
            None
        Outputs:
            None
        """
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Title Label
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="NET-ANALYZER", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.logo_label.pack(pady=25, padx=20)

        # Navigation Buttons
        self.btn_dash = ctk.CTkButton(
            self.sidebar_frame, 
            text="Telemetry Dashboard", 
            command=lambda: self.select_panel("dashboard")
        )
        self.btn_dash.pack(pady=10, padx=20)

        self.btn_speed = ctk.CTkButton(
            self.sidebar_frame, 
            text="Bandwidth Test", 
            command=lambda: self.select_panel("speed")
        )
        self.btn_speed.pack(pady=10, padx=20)

        self.btn_scan = ctk.CTkButton(
            self.sidebar_frame, 
            text="Subnet Device Scan", 
            command=lambda: self.select_panel("scan")
        )
        self.btn_scan.pack(pady=10, padx=20)

    def _build_dashboard_panel(self):
        """
        Description: Generates network telemetry summary frames and embeds live plotting canvas.
        Args:
            None
        Outputs:
            None
        """
        self.dash_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        
        # Upper Config Panel
        self.info_panel = ctk.CTkFrame(self.dash_frame, corner_radius=8)
        self.info_panel.pack(fill="x", pady=10, padx=15)
        
        # Populate interface metadata labels
        if self.network_config:
            meta_text = (
                f"Adapter Name: {self.network_config['interface_name']}   |   "
                f"Local IP: {self.network_config['ip']}   |   "
                f"Subnet CIDR: {self.network_config['subnet_cidr']}"
            )
        else:
            meta_text = "No active local network interface resolved."

        # FIX: Replaced invalid 'semibold' with standard 'bold'
        self.info_label = ctk.CTkLabel(
            self.info_panel, 
            text=meta_text, 
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.info_label.pack(pady=12, padx=15)

        # Chart Frame
        self.chart_panel = ctk.CTkFrame(self.dash_frame, corner_radius=8)
        self.chart_panel.pack(fill="both", expand=True, pady=10, padx=15)

        # Embed Matplotlib Line Chart
        plt.style.use("dark_background")
        self.fig, self.ax = plt.subplots(figsize=(6, 3.5), dpi=100)
        self.fig.patch.set_facecolor("#212121")  # Match customtkinter theme base hex
        self.ax.set_facecolor("#2b2b2b")
        
        # Axis parameters
        self.ax.set_title("Host Interface Throughput (Real-Time)", fontsize=10, pad=8)
        self.ax.set_ylabel("Throughput (KB/s)", fontsize=8)
        self.ax.set_xlabel("Observation Window (Seconds)", fontsize=8, labelpad=6)
        self.ax.grid(True, color="#444444", linestyle="--", linewidth=0.5)

        # FIX: Fix horizontal axis to our positive sequential gauge [1, 30]
        self.ax.set_xlim(1, 30)

        self.down_line, = self.ax.plot(self.time_series, self.download_series, color="#1f77b4", label="Download")
        self.up_line, = self.ax.plot(self.time_series, self.upload_series, color="#d62728", label="Upload")
        self.ax.legend(loc="upper left", fontsize=8)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_panel)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def _build_speedtest_panel(self):
        """
        Description: Constructs layout containing interactive triggers and bandwidth diagnostics.
        Args:
            None
        Outputs:
            None
        """
        self.speed_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        
        # Interactive parameters
        self.speed_hdr = ctk.CTkLabel(
            self.speed_frame, 
            text="Bandwidth Quality Evaluator", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.speed_hdr.pack(pady=20)

        # Speed Value Display Frame
        self.val_panel = ctk.CTkFrame(self.speed_frame, corner_radius=8, width=500, height=180)
        self.val_panel.pack_propagate(False)
        self.val_panel.pack(pady=15)

        self.lbl_ping = ctk.CTkLabel(self.val_panel, text="Ping Latency: -- ms", font=ctk.CTkFont(size=14))
        self.lbl_ping.pack(pady=15)
        self.lbl_down = ctk.CTkLabel(self.val_panel, text="Download Speed: -- Mbps", font=ctk.CTkFont(size=14))
        self.lbl_down.pack(pady=10)
        self.lbl_up = ctk.CTkLabel(self.val_panel, text="Upload Speed: -- Mbps", font=ctk.CTkFont(size=14))
        self.lbl_up.pack(pady=10)


        # ADD: Create an indeterminate progress bar (keep it hidden initially)
        self.speed_progress = ctk.CTkProgressBar(self.speed_frame, width=300)
        self.speed_progress.configure(mode="indeterminate")

        # Trigger
        self.btn_run_speed = ctk.CTkButton(
            self.speed_frame, 
            text="Execute Bandwidth Test", 
            command=self.dispatch_speed_worker
        )
        self.btn_run_speed.pack(pady=25)

    def _build_scanner_panel(self):
        """
        Description: Builds local subnet devices panel layout.
        Args:
            None
        Outputs:
            None
        """
        self.scan_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")

        self.scan_hdr = ctk.CTkLabel(
            self.scan_frame, 
            text="Local Subnet Host Discovery", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.scan_hdr.pack(pady=20)

        self.btn_run_scan = ctk.CTkButton(
            self.scan_frame, 
            text="Scan Subnet", 
            command=self.dispatch_scanner_worker
        )
        self.btn_run_scan.pack(pady=10)

        # Scrolled text panel for discoveries
        self.txt_devices = ctk.CTkTextbox(self.scan_frame, width=550, height=300, font=ctk.CTkFont(size=13))
        self.txt_devices.pack(pady=20)
        self.txt_devices.insert("0.0", "Execute 'Scan Subnet' to discover active devices on local domain...")

    def select_panel(self, panel_name):
        """
        Description: Navigation router managing stack visibilities for content frames.
        Args:
            panel_name (str): Key of frame target ('dashboard', 'speed', 'scan').
        Outputs:
            None
        """
        # Collapse all screens first
        self.dash_frame.grid_forget()
        self.speed_frame.grid_forget()
        self.scan_frame.grid_forget()

        # Route target
        if panel_name == "dashboard":
            self.dash_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        elif panel_name == "speed":
            self.speed_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        elif panel_name == "scan":
            self.scan_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

    def update_live_metrics(self):
        """
        Description: Periodically pulls active interface metrics, updates raw historical lists,
                     re-draws embedded charts, and schedules future evaluations.
        Args:
            None
        Outputs:
            None
        """
        if self.traffic_monitor:
            rates = self.traffic_monitor.get_throughput()
            
            # Slice timeline series shifts
            self.download_series.pop(0)
            self.download_series.append(rates["download_kb_s"])

            self.upload_series.pop(0)
            self.upload_series.append(rates["upload_kb_s"])

            # Redraw chart parameters dynamically
            self.down_line.set_ydata(self.download_series)
            self.up_line.set_ydata(self.upload_series)
            
            # Re-scale plot limits based on peak values recorded
            peak = max(max(self.download_series), max(self.upload_series))
            self.ax.set_ylim(0, max(50, peak + 20))
            self.canvas.draw()

        # Save loop scheduling handles for cleanup on exit
        self.metrics_after_id = self.after(1000, self.update_live_metrics)

    # MODIFY: Shows and runs the progress bar when the test starts
    def dispatch_speed_worker(self):
        """
        Description: Spawns non-blocking thread to fetch remote CDN speed test metrics.
        Args:
            None
        Outputs:
            None
        """
        self.btn_run_speed.configure(state="disabled", text="Testing Bandwidth...")
        self.lbl_ping.configure(text="Ping Latency: Evaluating...")
        self.lbl_down.configure(text="Download Speed: Evaluating...")
        self.lbl_up.configure(text="Upload Speed: Evaluating...")

        # ADD: Display and start progress animation
        self.speed_progress.pack(pady=10)
        self.speed_progress.start()

        # Worker target definition
        def worker():
            res = run_bandwidth_evaluation()
            self.speedtest_queue.put(res)

        threading.Thread(target=worker, daemon=True).start()

    def dispatch_scanner_worker(self):
        """
        Description: Spawns non-blocking thread to run target sweep algorithms.
        Args:
            None
        Outputs:
            None
        """
        if not self.network_config:
            self.txt_devices.delete("0.0", "end")
            self.txt_devices.insert("0.0", "Error: No active network adapter resolved.")
            return

        self.btn_run_scan.configure(state="disabled", text="Scanning...")
        self.txt_devices.delete("0.0", "end")
        self.txt_devices.insert("0.0", "Starting parallel sweep of active subnet...\n")

        # Worker target definition
        def worker():
            res = scan_subnet(self.network_config["subnet_cidr"], host_ip=self.network_config["ip"])
            self.scanner_queue.put(res)

        threading.Thread(target=worker, daemon=True).start()

    # MODIFY: Updated to handle speed progress bar toggling and detailed scanner parsing
    def observe_background_workers(self):
        """
        Description: Non-blocking scheduler matching active queue payloads. Runs safely inside
                     the Tkinter UI loop to update UI states immediately when workers complete tasks.
        Args:
            None
        Outputs:
            None
        """
        try:
            results = self.speedtest_queue.get_nowait()
            self.btn_run_speed.configure(state="normal", text="Execute Bandwidth Test")
            
            # ADD: Stop and hide progress animation
            self.speed_progress.stop()
            self.speed_progress.pack_forget()

            if results:
                self.lbl_ping.configure(text=f"Ping Latency: {results['ping_ms']} ms")
                self.lbl_down.configure(text=f"Download Speed: {results['download_mbps']} Mbps")
                self.lbl_up.configure(text=f"Upload Speed: {results['upload_mbps']} Mbps")
            else:
                self.lbl_ping.configure(text="Ping Latency: Probe Timeout")
                self.lbl_down.configure(text="Download Speed: Probe Failed")
                self.lbl_up.configure(text="Upload Speed: Probe Failed")
        except queue.Empty:
            pass

        try:
            # MODIFY: Refactored parser to parse IP, MAC, Vendor, and Category details
            devices = self.scanner_queue.get_nowait()
            self.btn_run_scan.configure(state="normal", text="Scan Subnet")
            self.txt_devices.delete("0.0", "end")
            
            self.txt_devices.insert("0.0", f"Discovered Devices ({len(devices)} online):\n\n")
            for device in devices:
                marker = ""
                if self.network_config and device["ip"] == self.network_config["ip"]:
                    marker = " (Host Machine)"
                
                # Write a cleanly formatted visual profile of each active device
                self.txt_devices.insert(
                    "end", 
                    f"  IP: {device['ip']:<15}{marker}\n"
                    f"  MAC Address:  {device['mac']}\n"
                    f"  Manufacturer: {device['vendor']}\n"
                    f"  Device Type:  {device['device_type']}\n"
                    f"  --------------------------------------------------\n"
                )
        except queue.Empty:
            pass

        # Save worker observer loop handles for cleanup on exit
        self.workers_after_id = self.after(200, self.observe_background_workers)

    def on_closing(self):
        """
        Description: Safely tears down running Tcl callbacks, closes active Matplotlib 
                     figure buffers, and releases system terminal processes smoothly on exit.
        Args:
            None
        Outputs:
            None
        """
        print("[*] Terminating Network Diagnostic Suite cleanly...")

        # 1. Cancel scheduled loops to prevent orphaned callbacks trying to execute on dead references
        if self.metrics_after_id:
            self.after_cancel(self.metrics_after_id)
        if self.workers_after_id:
            self.after_cancel(self.workers_after_id)

        # 2. Release Matplotlib plot structures from active memory cache
        plt.close(self.fig)

        # 3. Destroy GUI widgets and kill system process cleanly
        self.destroy()
        sys.exit(0)