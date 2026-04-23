#!/usr/bin/env python3
"""
SUPER SIMPLE CACHE EDITOR

Minimal, cute GUI for editing vendor cache.
Just what you need, nothing extra.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime


class SuperSimpleCacheEditor:
    """Super simple GUI - minimal and cute!"""

    def __init__(self, root):
        self.root = root
        self.root.title("Cache Editor")
        self.root.geometry("500x600")

        # Make it cute
        self.root.configure(bg='#f0f8ff')  # Alice blue

        # Cache file
        self.cache_file = "data/vendor_cache.json"

        # Load cache
        self.cache = self._load_cache()

        # Current vendor
        self.current_vendor = None

        self._setup_ui()

    def _load_cache(self):
        """Load vendor cache."""
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"version": "2.0", "vendors": {}}

    def _save_cache(self):
        """Save vendor cache."""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def _setup_ui(self):
        """Setup super simple UI."""
        # Main container with cute background
        main = tk.Frame(self.root, bg='#f0f8ff', padx=20, pady=20)
        main.pack(fill=tk.BOTH, expand=True)

        # Title with emoji
        title_frame = tk.Frame(main, bg='#f0f8ff')
        title_frame.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            title_frame,
            text="✏️ Vendor Cache Editor",
            font=("Arial", 18, "bold"),
            bg='#f0f8ff',
            fg='#2c3e50'
        ).pack()

        # Vendor selection (simple dropdown)
        vendor_frame = tk.Frame(main, bg='#f0f8ff')
        vendor_frame.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            vendor_frame,
            text="Select Vendor:",
            font=("Arial", 11, "bold"),
            bg='#f0f8ff'
        ).pack(anchor=tk.W, pady=(0, 5))

        # Get vendor list
        vendors = list(self.cache.get("vendors", {}).keys())
        if not vendors:
            vendors = ["No vendors found"]

        self.vendor_var = tk.StringVar(value=vendors[0])
        vendor_dropdown = ttk.Combobox(
            vendor_frame,
            textvariable=self.vendor_var,
            values=vendors,
            state="readonly",
            width=30,
            font=("Arial", 10)
        )
        vendor_dropdown.pack()

        # Load button
        ttk.Button(
            vendor_frame,
            text="Load Vendor",
            command=self._load_vendor,
            style="Cute.TButton"
        ).pack(pady=(10, 0))

        # Separator
        ttk.Separator(main, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)

        # Vendor info (minimal)
        self.info_frame = tk.Frame(main, bg='#f0f8ff')
        self.info_frame.pack(fill=tk.X, pady=(0, 20))

        # Columns section
        columns_frame = tk.LabelFrame(
            main,
            text="📋 Columns (Left to Right)",
            font=("Arial", 12, "bold"),
            bg='#f0f8ff',
            fg='#2c3e50',
            padx=15,
            pady=15
        )
        columns_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Scrollable columns area
        canvas = tk.Canvas(columns_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(columns_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.columns_container = tk.Frame(canvas, bg='white')

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.create_window((0, 0), window=self.columns_container, anchor="nw")

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind configure to update scrollregion
        self.columns_container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Save button (cute style)
        button_frame = tk.Frame(main, bg='#f0f8ff')
        button_frame.pack(fill=tk.X)

        ttk.Button(
            button_frame,
            text="💾 Save Changes",
            command=self._save_changes,
            style="Save.TButton",
            width=20
        ).pack()

        # Status label
        self.status_label = tk.Label(
            main,
            text="Ready",
            font=("Arial", 9),
            bg='#f0f8ff',
            fg='#7f8c8d'
        )
        self.status_label.pack(pady=(10, 0))

        # Configure cute styles
        self._configure_styles()

        # Load first vendor
        if vendors[0] != "No vendors found":
            self._load_vendor()

    def _configure_styles(self):
        """Configure cute button styles."""
        style = ttk.Style()

        # Cute button style
        style.configure(
            "Cute.TButton",
            font=("Arial", 10),
            padding=6,
            background="#3498db",
            foreground="white"
        )

        # Save button style (green)
        style.configure(
            "Save.TButton",
            font=("Arial", 11, "bold"),
            padding=8,
            background="#2ecc71",
            foreground="white"
        )

        # Map states
        style.map(
            "Cute.TButton",
            background=[("active", "#2980b9")],
            foreground=[("active", "white")]
        )

        style.map(
            "Save.TButton",
            background=[("active", "#27ae60")],
            foreground=[("active", "white")]
        )

    def _load_vendor(self):
        """Load selected vendor."""
        vendor_key = self.vendor_var.get()

        if vendor_key == "No vendors found":
            messagebox.showinfo("No Vendors", "No vendors in cache yet!")
            return

        self.current_vendor = vendor_key
        vendor_data = self.cache["vendors"][vendor_key]

        # Clear info frame
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        # Show minimal info
        display_name = vendor_data.get("basics", {}).get("display_name", vendor_key)
        last_modified = vendor_data.get("basics", {}).get("last_modified", "Never")

        tk.Label(
            self.info_frame,
            text=f"Vendor: {display_name}",
            font=("Arial", 11, "bold"),
            bg='#f0f8ff'
        ).pack(anchor=tk.W)

        tk.Label(
            self.info_frame,
            text=f"Last modified: {last_modified}",
            font=("Arial", 9),
            bg='#f0f8ff',
            fg='#7f8c8d'
        ).pack(anchor=tk.W, pady=(2, 0))

        # Clear and load columns
        for widget in self.columns_container.winfo_children():
            widget.destroy()

        # Get columns from cache
        columns = []

        # Try columns_gui first
        columns_gui = vendor_data.get("columns_gui", [])
        if columns_gui:
            for col in columns_gui:
                columns.append({
                    'hebrew': col.get('hebrew_header', ''),
                    'english': col.get('english_name', ''),
                    'type': col.get('type', 'text')
                })

        # Try legacy detected_columns
        if not columns:
            legacy = vendor_data.get("legacy_fields", {})
            detected = legacy.get("detected_columns", [])
            for col in detected:
                columns.append({
                    'hebrew': col.get('hebrew_text', ''),
                    'english': col.get('assigned_field', ''),
                    'type': 'auto'
                })

        # Create column editors
        for i, col in enumerate(columns):
            self._add_column_editor(i, col)

        self.status_label.config(text=f"Loaded: {display_name}")

    def _add_column_editor(self, index, column):
        """Add a column editor row."""
        row = tk.Frame(self.columns_container, bg='white', pady=5)
        row.pack(fill=tk.X, padx=5)

        # Column number
        tk.Label(
            row,
            text=f"{index+1}.",
            font=("Arial", 10, "bold"),
            bg='white',
            width=3
        ).pack(side=tk.LEFT)

        # Hebrew name (uneditable, just display)
        tk.Label(
            row,
            text=column['hebrew'] or f"Column {index+1}",
            font=("Arial", 10),
            bg='white',
            width=15,
            anchor=tk.W
        ).pack(side=tk.LEFT, padx=(5, 10))

        # English field (simple dropdown)
        field_var = tk.StringVar(value=column['english'])

        # Common field options
        field_options = [
            "description", "product_code", "quantity",
            "unit_price", "line_net_total", "weight",
            "discount", "ignore"
        ]

        field_dropdown = ttk.Combobox(
            row,
            textvariable=field_var,
            values=field_options,
            state="readonly",
            width=15,
            font=("Arial", 9)
        )
        field_dropdown.pack(side=tk.LEFT, padx=(0, 10))

        # Data type (simple dropdown)
        type_var = tk.StringVar(value=column['type'])

        type_options = ["text", "number", "price", "barcode", "auto"]

        type_dropdown = ttk.Combobox(
            row,
            textvariable=type_var,
            values=type_options,
            state="readonly",
            width=10,
            font=("Arial", 9)
        )
        type_dropdown.pack(side=tk.LEFT)

        # Store references
        row.field_var = field_var
        row.type_var = type_var

    def _save_changes(self):
        """Save changes to cache."""
        if not self.current_vendor:
            messagebox.showinfo("No Vendor", "Load a vendor first!")
            return

        # Get all column values
        columns_gui = []
        for i, child in enumerate(self.columns_container.winfo_children()):
            if hasattr(child, 'field_var'):
                hebrew_text = ""
                # Try to get Hebrew text from label (second child)
                if len(child.winfo_children()) > 1:
                    label = child.winfo_children()[1]
                    hebrew_text = label.cget("text")

                columns_gui.append({
                    'index': i + 1,
                    'hebrew_header': hebrew_text,
                    'english_name': child.field_var.get(),
                    'type': child.type_var.get()
                })

        # Update cache
        vendor_data = self.cache["vendors"][self.current_vendor]
        vendor_data["columns_gui"] = columns_gui
        vendor_data["basics"]["last_modified"] = datetime.now().strftime("%Y-%m-%d")

        # Save
        self._save_cache()

        self.status_label.config(text=f"✅ Saved {len(columns_gui)} columns")
        messagebox.showinfo("Saved", f"Saved changes to {self.current_vendor}")


def main():
    """Run the super simple editor."""
    root = tk.Tk()
    app = SuperSimpleCacheEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()