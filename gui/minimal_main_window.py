"""
Minimal MainWindow for testing.
"""

import tkinter as tk
from tkinter import ttk


class MinimalMainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("🧾 Minimal Test")
        self.root.geometry("600x400")

        # Simple colors
        self.CLR_BG = '#f0f8ff'
        self.CLR_TEXT = '#2c3e50'

        self.root.configure(bg=self.CLR_BG)

        # Build minimal UI
        self._build_minimal_ui()

    def _build_minimal_ui(self):
        """Build minimal UI."""
        print("DEBUG: Building minimal UI...")

        # Simple header
        header = tk.Frame(self.root, bg=self.CLR_BG, padx=20, pady=20)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="🧾 Minimal Test",
            font=("Arial", 20, "bold"),
            bg=self.CLR_BG,
            fg=self.CLR_TEXT
        ).pack(anchor=tk.W)

        # Simple button
        button_frame = tk.Frame(self.root, bg=self.CLR_BG, padx=20, pady=10)
        button_frame.pack(fill=tk.X)

        btn = tk.Button(
            button_frame,
            text="Test Button",
            command=self._on_test,
            bg="#3498db",
            fg="white",
            font=("Arial", 10)
        )
        btn.pack()

        # Status
        self.status = tk.Label(
            self.root,
            text="Ready",
            font=("Arial", 9),
            bg=self.CLR_BG,
            fg="#7f8c8d"
        )
        self.status.pack(fill=tk.X, padx=20, pady=20)

        print("DEBUG: Minimal UI built successfully.")

    def _on_test(self):
        """Test button callback."""
        self.status.config(text="Button clicked!")
        print("DEBUG: Button clicked")


def test():
    """Test the minimal window."""
    root = tk.Tk()
    app = MinimalMainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    test()