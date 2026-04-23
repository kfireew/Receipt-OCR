#!/usr/bin/env python3
"""
Test imports without running GUI.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print(f"Project root: {PROJECT_ROOT}")
print(f"sys.path[0:3]: {sys.path[0:3]}")

try:
    print("\nTrying to import main_window...")
    from gui.main_window import MainWindow
    print("SUCCESS: main_window imported")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\nTrying to create tkinter window...")
import tkinter as tk
try:
    root = tk.Tk()
    print("SUCCESS: tk.Tk() created")
    root.destroy()
    print("SUCCESS: window destroyed")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\nTest complete.")