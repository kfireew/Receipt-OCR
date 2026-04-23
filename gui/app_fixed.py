#!/usr/bin/env python3
"""
OBSOLETE - NOT USED BY MAIN GUI
================================
Fixed version of Receipt OCR GUI.
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

print("Starting fixed GUI...")


class FixedReceiptOCRApp:
    """Fixed version of the main application."""

    def __init__(self, root):
        self.root = root

        # Use TkinterDnD if available
        try:
            from tkinterdnd2 import TkinterDnD
            if not isinstance(root, TkinterDnD.Tk):
                # Wrap the root window
                self.root = TkinterDnD.Tk._report_exception = lambda *args: None
        except ImportError:
            pass

        self.root.title("🧾 Receipt OCR (Fixed)")
        self.root.geometry("900x700")

        # Simple theme
        self.CLR_BG = '#f0f8ff'
        self.CLR_SURFACE = '#ffffff'
        self.CLR_ACCENT = '#3498db'
        self.CLR_TEXT = '#2c3e50'

        self.root.configure(bg=self.CLR_BG)

        # Build UI
        self._build_simple_ui()

    def _build_simple_ui(self):
        """Build simple UI."""
        # Header
        header = tk.Frame(self.root, bg=self.CLR_BG, padx=20, pady=20)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="🧾 Receipt OCR (Fixed Version)",
            font=("Arial", 20, "bold"),
            bg=self.CLR_BG,
            fg=self.CLR_TEXT
        ).pack(anchor=tk.W)

        tk.Label(
            header,
            text="Modular GUI with vendor cache support",
            font=("Arial", 10),
            bg=self.CLR_BG,
            fg="#7f8c8d"
        ).pack(anchor=tk.W, pady=(5, 0))

        # Buttons frame
        buttons = tk.Frame(self.root, bg=self.CLR_BG, padx=20, pady=10)
        buttons.pack(fill=tk.X)

        # Test buttons
        tk.Button(
            buttons,
            text="Test Theme Import",
            command=self._test_theme,
            bg=self.CLR_ACCENT,
            fg="white",
            font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            buttons,
            text="Test Components",
            command=self._test_components,
            bg="#2ecc71",
            fg="white",
            font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Status
        self.status = tk.Label(
            self.root,
            text="Ready",
            font=("Arial", 9),
            bg=self.CLR_BG,
            fg="#7f8c8d"
        )
        self.status.pack(fill=tk.X, padx=20, pady=10)

        # Text area
        text_frame = tk.Frame(self.root, bg=self.CLR_BG)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self.text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            bg=self.CLR_SURFACE,
            fg=self.CLR_TEXT,
            font=("Consolas", 10),
            height=15
        )
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(text_frame, command=self.text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.config(yscrollcommand=scrollbar.set)

    def _log(self, msg):
        """Log message."""
        self.text.insert(tk.END, msg + "\n")
        self.text.see(tk.END)

    def _test_theme(self):
        """Test theme import."""
        try:
            from gui.theme import theme
            self._log(f"Theme imported: {theme.CLR_BG}")
            self.status.config(text="Theme import successful!")
        except Exception as e:
            self._log(f"Theme import failed: {e}")

    def _test_components(self):
        """Test components import."""
        try:
            from gui.components import ConfidenceMeter
            self._log("Components import successful!")
            self.status.config(text="Components import successful!")
        except Exception as e:
            self._log(f"Components import failed: {e}")


def main():
    """Main entry point."""
    print("Creating window...")

    root = tk.Tk()
    app = FixedReceiptOCRApp(root)

    print("Starting mainloop...")
    root.mainloop()
    print("Done.")


if __name__ == "__main__":
    main()