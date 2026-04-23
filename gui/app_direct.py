#!/usr/bin/env python3
"""
OBSOLETE - NOT USED BY MAIN GUI
================================
Direct launch of Receipt OCR GUI - no CLI menu.
"""

import os
import sys
from pathlib import Path
import tkinter as tk

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

print("Starting Receipt OCR GUI...")

def create_main_window():
    """Create and configure the main application window."""
    try:
        from gui.main_window import MainWindow
    except ImportError as e:
        print(f"Error importing GUI modules: {e}")
        print("Make sure all modular GUI files exist in the gui/ directory.")
        return None

    # Create root window - NO TkinterDnD, just regular tk.Tk()
    root = tk.Tk()
    print("Created tk.Tk() window")

    # Create main application
    try:
        app = MainWindow(root)
        print("MainWindow created successfully")
        return app
    except Exception as e:
        print(f"Error creating MainWindow: {e}")
        import traceback
        traceback.print_exc()
        if root:
            root.destroy()
        return None

def main():
    """Main entry point - launches GUI directly."""
    app = create_main_window()

    if app:
        print("Starting mainloop...")
        try:
            app.root.mainloop()
            print("Mainloop exited normally.")
        except Exception as e:
            print(f"Error in mainloop: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Failed to create app. Press Enter to exit.")
        input()

if __name__ == "__main__":
    main()