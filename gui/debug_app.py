#!/usr/bin/env python3
"""
Debug version of app.py to catch crashes.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("DEBUG: Starting debug app...")
print(f"DEBUG: Project root: {PROJECT_ROOT}")
print(f"DEBUG: Python path: {sys.path[:3]}...")

try:
    import tkinter as tk
    print("DEBUG: tkinter imported successfully")
except Exception as e:
    print(f"DEBUG: tkinter import failed: {e}")
    traceback.print_exc()
    sys.exit(1)


def create_main_window():
    """Create and configure the main application window."""
    print("DEBUG: create_main_window() called")

    try:
        print("DEBUG: Trying to import MainWindow...")
        from gui.main_window import MainWindow
        print("DEBUG: MainWindow imported successfully")
    except ImportError as e:
        print(f"DEBUG: Error importing MainWindow: {e}")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"DEBUG: Unexpected error importing MainWindow: {e}")
        traceback.print_exc()
        return None

    # Create root window
    root = None

    # Create root window - drag & drop disabled
    root = tk.Tk()
    print("DEBUG: Created tk.Tk() window (drag & drop disabled)")

    try:
        print("DEBUG: Creating MainWindow instance...")
        app = MainWindow(root)
        print("DEBUG: MainWindow created successfully")
        return app
    except Exception as e:
        print(f"DEBUG: Error creating MainWindow instance: {e}")
        traceback.print_exc()
        return None


def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("Receipt OCR GUI - DEBUG MODE")
    print("="*60)

    print("\nDEBUG: Creating main window...")
    app = create_main_window()

    if app:
        print("DEBUG: Starting mainloop...")
        try:
            app.root.mainloop()
            print("DEBUG: Mainloop exited normally.")
        except Exception as e:
            print(f"DEBUG: Error in mainloop: {e}")
            traceback.print_exc()
    else:
        print("DEBUG: Failed to create app.")

    print("\nDEBUG: Exiting.")


if __name__ == "__main__":
    main()