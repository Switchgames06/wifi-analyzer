# ==============================================================================
# File: main.py
# Author: Jay P M Lynch
# Date of Creation: 2026-06-28
# Date of Last Edit: 2026-07-03
# Version: 1.1.0
# Description: Core launcher and diagnostic verification harness for the
#              Local Wi-Fi Speed Testing & Network Analyzer Suite.
# ==============================================================================

from src.ui.dashboard import NetworkAnalyzerApp

def main():
    """
    Description: Instantiates and fires the main Tkinter graphical loop.
    Args:
        None
    Outputs:
        None
    """
    app = NetworkAnalyzerApp()
    app.mainloop()

if __name__ == "__main__":
    main()