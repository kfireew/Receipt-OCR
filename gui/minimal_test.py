#!/usr/bin/env python3
"""
Minimal test to isolate the crash issue.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tkinter as tk

print("Creating minimal window...")

try:
    root = tk.Tk()
    root.title("Minimal Test")
    root.geometry("400x200")

    label = tk.Label(root, text="If this window appears and doesn't crash,\nthe issue is in the GUI construction.")
    label.pack(pady=20)

    button = tk.Button(root, text="Test Theme Import", command=lambda: test_theme_import())
    button.pack(pady=10)

    def test_theme_import():
        try:
            from gui.theme import theme
            print(f"Theme imported: {theme.CLR_BG}")
            label.config(text="Theme import successful!")
        except Exception as e:
            print(f"Theme import failed: {e}")
            import traceback
            traceback.print_exc()
            label.config(text=f"Theme import failed: {e}")

    close_btn = tk.Button(root, text="Close", command=root.destroy)
    close_btn.pack(pady=10)

    print("Starting mainloop...")
    root.mainloop()
    print("Mainloop exited normally.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()