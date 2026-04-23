#!/usr/bin/env python3
"""
Simple working version of the Receipt OCR GUI.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import shutil
import threading

print("Starting simple app...")

# Simple theme colors
CLR_BG = '#f0f8ff'
CLR_SURFACE = '#ffffff'
CLR_ACCENT = '#3498db'
CLR_SUCCESS = '#2ecc71'
CLR_WARNING = '#f39c12'
CLR_ERROR = '#e74c3c'
CLR_TEXT = '#2c3e50'
CLR_SUBTEXT = '#7f8c8d'


class SimpleReceiptOCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🧾 Simple Receipt OCR")
        self.root.geometry("800x600")
        self.root.configure(bg=CLR_BG)

        self.last_result = None
        self.is_processing = False

        self._build_ui()

    def _build_ui(self):
        """Build simple UI."""
        # Header
        header = tk.Frame(self.root, bg=CLR_BG, padx=20, pady=20)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="🧾 Simple Receipt OCR",
            font=("Arial", 20, "bold"),
            bg=CLR_BG,
            fg=CLR_TEXT
        ).pack(anchor=tk.W)

        tk.Label(
            header,
            text="Test version - Basic functionality",
            font=("Arial", 10),
            bg=CLR_BG,
            fg=CLR_SUBTEXT
        ).pack(anchor=tk.W, pady=(5, 0))

        # Buttons
        button_frame = tk.Frame(self.root, bg=CLR_BG, padx=20, pady=10)
        button_frame.pack(fill=tk.X)

        self.browse_btn = tk.Button(
            button_frame,
            text="📤 Browse for Receipt",
            command=self.do_browse,
            bg=CLR_ACCENT,
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=8
        )
        self.browse_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.cache_btn = tk.Button(
            button_frame,
            text="📁 Cache Manager",
            command=self.do_cache,
            bg=CLR_SURFACE,
            fg=CLR_TEXT,
            font=("Arial", 10),
            padx=15,
            pady=8
        )
        self.cache_btn.pack(side=tk.LEFT)

        # Status
        self.status_label = tk.Label(
            self.root,
            text="Ready",
            font=("Arial", 9),
            bg=CLR_BG,
            fg=CLR_SUBTEXT
        )
        self.status_label.pack(fill=tk.X, padx=20, pady=(0, 10))

        # Text area for output
        text_frame = tk.Frame(self.root, bg=CLR_BG)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self.text_out = tk.Text(
            text_frame,
            wrap=tk.WORD,
            bg=CLR_SURFACE,
            fg=CLR_TEXT,
            font=("Consolas", 10),
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.text_out.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_out.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_out.config(yscrollcommand=scrollbar.set)

        # Footer
        footer = tk.Frame(self.root, bg=CLR_BG, pady=10)
        footer.pack(side=tk.BOTTOM, fill=tk.X)

        tk.Label(
            footer,
            text="Simple Test Version",
            font=("Arial", 8),
            bg=CLR_BG,
            fg=CLR_SUBTEXT
        ).pack()

    def _log(self, message):
        """Add message to text area."""
        self.text_out.insert(tk.END, message + "\n")
        self.text_out.see(tk.END)

    def do_browse(self):
        """Browse for file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("Image/PDF files", "*.pdf *.png *.jpg *.jpeg"), ("All files", "*.*")],
        )
        if file_path:
            self._log(f"Selected: {file_path}")
            self._log("(Processing would happen here)")
            self.status_label.config(text=f"Loaded: {os.path.basename(file_path)}")

    def do_cache(self):
        """Open cache manager."""
        self._log("Cache manager would open here")
        messagebox.showinfo("Cache", "Cache manager functionality")

    def run_test(self):
        """Run a test."""
        self._log("Testing GUI components...")
        self._log(f"Background: {CLR_BG}")
        self._log(f"Accent: {CLR_ACCENT}")
        self._log("Test complete!")


def main():
    """Main entry point."""
    print("Creating window...")

    root = tk.Tk()
    app = SimpleReceiptOCRApp(root)

    # Add a test button
    test_btn = tk.Button(
        root, text="Run Test",
        command=app.run_test,
        bg=CLR_SUCCESS, fg="white"
    )
    test_btn.pack(pady=10)

    print("Starting mainloop...")
    root.mainloop()
    print("Done.")


if __name__ == "__main__":
    main()