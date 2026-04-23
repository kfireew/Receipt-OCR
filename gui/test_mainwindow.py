#!/usr/bin/env python3
"""
Test MainWindow creation.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tkinter as tk

print("Testing MainWindow creation...")

try:
    print("Creating tk.Tk()...")
    root = tk.Tk()

    print("Importing MainWindow...")
    from gui.main_window import MainWindow

    print("Creating MainWindow instance...")
    app = MainWindow(root)

    print("SUCCESS: MainWindow created!")

    # Don't run mainloop, just destroy
    root.destroy()
    print("Window destroyed.")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\nTest complete.")