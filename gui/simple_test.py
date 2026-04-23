#!/usr/bin/env python3
"""
Simple test to check if basic GUI works.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("Testing minimal GUI...")

try:
    import tkinter as tk
    print("✓ tkinter imports successfully")

    # Test creating a simple window
    root = tk.Tk()
    root.title("Test Window")
    root.geometry("400x300")

    label = tk.Label(root, text="GUI test - if you see this, tkinter works!")
    label.pack(pady=50)

    button = tk.Button(root, text="Close", command=root.destroy)
    button.pack()

    print("✓ Basic tkinter window created")
    print("Opening window... Close it to continue test.")

    root.mainloop()

except Exception as e:
    print(f"✗ Error with tkinter: {e}")
    import traceback
    traceback.print_exc()

print("\nTesting theme module...")
try:
    from gui.theme import theme
    print(f"✓ Theme module loaded: {theme.CLR_BG}")
except Exception as e:
    print(f"✗ Error with theme: {e}")
    import traceback
    traceback.print_exc()

print("\nTest complete.")