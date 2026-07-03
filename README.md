# Local Wi-Fi Speed Testing & Network Analyzer Suite

A clean, cross-platform local network diagnostics and traffic monitoring desktop utility written in Python. Built using CustomTkinter for a modern dark-themed graphical interface, the application separates its operations asynchronously using background worker threads to ensure real-time telemetry rendering never blocks the user experience.

---

## Technical & Legal Compliance
This software operates strictly inside private local subnets (such as home LANs) as an administrative diagnostic utility. To remain compliant with Australian cybersecurity legislation (including the *Commonwealth Criminal Code Act 1995*, Division 477/478):
- **Passive Subnet Scan:** The device scanner performs a parallelized ICMP echo (ping) sweep using native operating system commands over the active private subnet. It does not perform invasive TCP/UDP port scans, vulnerability probing, or unauthorized packet capture of other devices.
- **Dynamic Optimization:** If a large virtual subnet is detected, the application automatically restricts its scan scope to the active `/24` (256-host) block of the host machine, protecting local network performance.

---

## Core Features
- **Active Interface Resolution:** Automatically resolves active physical or virtual adapter configurations (Local IP, Netmask, Subnet range).
- **Asynchronous Bandwidth Tests:** Conducts ping, download, and upload tests using programmatic CDN connections without locking the UI.
- **Parallel Subnet Scanner:** Sweeps up to 254 potential local IP targets using a fast Python `ThreadPoolExecutor` to identify active household devices.
- **Real-Time Usage Graphing:** Displays rolling throughput statistics (KB/s) in a 30-second Matplotlib line chart.

---

## Directory Layout
- `main.py`: Launcher entry point.
- `src/ui/`: Contains layout modules and chart integration logic.
- `src/network/`: Core logic for speed evaluation, traffic counters, and sweeping.
- `src/utils/`: General utilities and OS configuration hooks.
- `concepts_and_drafts/`: Sandboxed script drafts, testing scripts, and historical CLI mockups.

---

## Execution Methods & Environments

Because development spanned both Windows and virtualized Linux environments, the suite supports three specific execution methods.

### 1. Windows Native Command Line (Recommended for Full Features)
Running natively under a Windows environment allows Python to bind directly to your physical network interface card (NIC), such as your Wi-Fi adapter.
- **Subnet Scan Scope:** Identifies your physical router and discoverable household devices (phones, TVs, laptops) on your active LAN.
- **Telemetry Graph:** Instantly displays real-time rolling traffic lines matching background Windows network usage.

**How to Run:**
```cmd
:: Create and activate Windows environment
python -m venv venv_win
venv_win\Scripts\activate

:: Install and run
pip install -r requirements.txt
python main.py

### 2. Windows Double-Click Launcher (run.bat)
When working inside a cross-platform repository, your project directory may physically reside inside your WSL filesystem (accessible in Windows via a network share path \\wsl.localhost\Ubuntu\...).
Standard Windows Command Prompts cannot execute batch scripts directly from UNC network shares.
To solve this, the run.bat launcher implements the pushd and popd patterns. Double-clicking this script:

- Automatically mounts your WSL directory to a temporary Windows network drive letter (e.g., Z:).
- Fires your native Windows Python interpreter (venv_win\Scripts\python.exe) to run the code.
- Accesses your physical network interface card (resolving home devices).
- Safely unmounts the network drive letter when the window is closed.

**How to Run:**
Double-click run.bat directly from Windows File Explorer.

### 3. WSL2 Virtual Environment (Ubuntu Sandbox)

WSL2 operates behind a virtual Hyper-V network switch running NAT.
The Sandbox Limitation: Sweeping the calculated /20 subnet (172.19.64.0/20) will only discover your virtual machine and the Windows host. Your real home Wi-Fi network is hidden from the WSL container's view. It is wise to run this the system like this if you are dubious of it's creator, lol...
The Telemetry Flatline: Because a barebones Ubuntu kernel runs minimal background traffic, the graph will remain at 0.0 KB/s unless you generate traffic inside the VM (e.g., by executing a package update or curl command in a secondary terminal).

**How to Run:**
```bash
:: Install Ubuntu system dependencies
sudo apt update
sudo apt install python3-tk

:: Create and activate environment
python3 -m venv .venv
source .venv/bin/activate

:: Install and run
pip install -r requirements.txt
python3 main.py

### Change Log & Project Timeline
Development followed a strict iterative pattern, verifying backend socket routing capabilities via a Command Line Interface (CLI) harness before implementing any GUI wrappers.

## [1.1.0] - 2026-07-03 (Current Release)
- Added: Integrated a dual-mode run.bat double-click script utilizing pushd/popd drive mappings to execute Windows Python natively from files inside the WSL filesystem.
- Fixed: Reformulated the Matplotlib telemetry chart x-axis to display a positive, rolling timeline window of 1 to 30 seconds (replacing negative offsets).
- Fixed: Addressed a CustomTkinter layout crash by standardizing font weight declarations to standard supported types ("bold").

## [1.0.0] - 2026-07-02
- Added: Initial stable GUI release. Implemented customtkinter layout panels (Telemetry, Bandwidth Test, Subnet Scan).
- Added: Implemented background threading queues to manage asynchronous speed tests and subnet sweeps.
- Fixed: Resolved a Tcl thread hang issue on close by binding a clean WM_DELETE_WINDOW protocol callback to release active schedules (after_cancel) and close matplotlib buffers.
- Project Progress: UI implementation commenced.

## [0.5.0] - 2026-06-30
- Added: Completed the multi-threaded subnet scanner. Dynamic logic checks operating system variables to route Linux-specific (ping -c 1) and Windows-specific (ping -n 1) CLI parameters.
- Fixed: Resolved the "Empty Scanner" bug. Slicing algorithm adjusted to anchor Class-C ranges to the host's actual IP, rather than the zero-IP of the parent subnet.

## [0.1.0] - 2026-06-28
- Added: Initial project setup. Established repository layout, .gitignore filters, and the psutil/socket-based interface resolver.
- Project Progress: Network backend development commenced. Verified basic CLI ping sweeps.

### Current Project Relevant File Tree:

wifi-analyzer/
│
├── .gitignore               # Ignores virtual environments, caches, and system metadata
├── README.md                # The comprehensive release documentation we just wrote
├── requirements.txt         # System dependencies
├── main.py                  # Core application executable
├── run.bat                  # Windows double-click dynamic drive-mounting launcher
│
├── src/                     # Active, production-ready modules
│   ├── __init__.py          # Python package marker
│   │
│   ├── network/             # Core networking backend
│   │   ├── __init__.py
│   │   ├── interface.py     # Cross-platform interface configuration resolver
│   │   ├── metrics.py       # Differential live traffic tracking logic
│   │   ├── scanner.py       # Multi-threaded sweep logic with Windows/Linux dual flags
│   │   └── speed.py         # Speedtest library orchestration wrapper
│   │
│   ├── ui/                  # User interface elements
│   │   ├── __init__.py
│   │   └── dashboard.py     # CustomTkinter dashboard layout and Matplotlib plotting
│   │
│   └── utils/               # General utilities (currently empty)
│       └── __init__.py
│
└── concepts_and_drafts/     # Sandbox environment for historical code or trial snippets
    └── README.md            # Explanation of this folder's purpose