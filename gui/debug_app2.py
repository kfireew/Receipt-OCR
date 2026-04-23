#!/usr/bin/env python3
"""
Debug version of app.py to see what happens after pressing 1.
"""

import os
import sys
from pathlib import Path
import tkinter as tk

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

print("DEBUG: Starting debug_app2.py")
print(f"DEBUG: sys.path: {sys.path[:3]}")

def create_main_window():
    """Create and configure the main application window."""
    print("DEBUG: Entering create_main_window()")

    try:
        from gui.main_window import MainWindow
        print("DEBUG: MainWindow imported successfully")
    except ImportError as e:
        print(f"Error importing GUI modules: {e}")
        print("Make sure all modular GUI files exist in the gui/ directory.")
        return None

    # Create root window
    root = None

    # Try to use TkinterDnD for drag and drop
    try:
        from tkinterdnd2 import TkinterDnD
        print("DEBUG: tkinterdnd2 available, creating TkinterDnD.Tk()")
        root = TkinterDnD.Tk()
    except ImportError:
        print("Note: tkinterdnd2 not installed - drag & drop disabled")
        root = tk.Tk()

    print(f"DEBUG: Root window created: {type(root)}")

    # Create main application
    print("DEBUG: Creating MainWindow instance...")
    app = MainWindow(root)
    print("DEBUG: MainWindow instance created")
    return app

def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("🧾 Receipt OCR GUI with Vendor Cache")
    print("="*60)

    print("\nAvailable modes:")
    print("1. Main OCR GUI (recommended)")
    print("2. Simple Cache Editor")
    print("3. Exit")

    choice = "1"  # Hardcode choice 1 for testing
    print(f"\nDEBUG: Choice selected: {choice}")

    if choice == "1":
        # Run main GUI
        print("DEBUG: Creating main window...")
        app = create_main_window()
        if app:
            print("\nDEBUG: Starting main GUI mainloop...")
            app.root.mainloop()
            print("DEBUG: mainloop() returned")
        else:
            print("Failed to create main window.")

    elif choice == "2":
        # Run simple cache editor
        print("\nStarting simple cache editor...")
        # run_simple_cache_editor()

    elif choice == "3":
        print("Exiting.")
        return

    else:
        print("Invalid choice. Exiting.")

if __name__ == "__main__":
    main()