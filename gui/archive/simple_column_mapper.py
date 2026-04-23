#!/usr/bin/env python3
"""
SIMPLE COLUMN MAPPER GUI

User-friendly interface for mapping receipt columns.
- Shows raw text on left
- Shows detected columns as buttons on right
- Click button to assign meaning
- Simple and intuitive
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import os
from typing import Dict, List, Any, Optional, Callable


class SimpleColumnMapper:
    """Simple GUI for mapping columns with buttons instead of dropdowns."""

    # Common column meanings (in Hebrew for user)
    COLUMN_MEANINGS = [
        "תיאור מוצר",
        "ברקוד / קוד",
        "כמות",
        "מחיר יחידה",
        "סה״כ שורה",
        "הנחה",
        "משקל",
        "התעלם"
    ]

    # Mapping from Hebrew button text to internal field name
    HEBREW_TO_FIELD = {
        "תיאור מוצר": "description",
        "ברקוד / קוד": "product_code",
        "כמות": "quantity",
        "מחיר יחידה": "unit_price",
        "סה״כ שורה": "line_net_total",
        "הנחה": "discount",
        "משקל": "weight",
        "התעלם": "ignore"
    }

    def __init__(self, parent, raw_text: str, detected_columns: List[Dict],
                 on_save: Callable, vendor_name: str = ""):
        """
        Args:
            parent: Parent window
            raw_text: Raw receipt text
            detected_columns: List of column info dicts
            on_save: Callback when user saves
            vendor_name: Vendor name for display
        """
        self.parent = parent
        self.raw_text = raw_text
        self.detected_columns = detected_columns
        self.on_save = on_save
        self.vendor_name = vendor_name

        self.column_assignments = {}  # {column_index: field_name}

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"מיפוי עמודות - {vendor_name}" if vendor_name else "מיפוי עמודות")
        self.dialog.geometry("1000x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._setup_ui()

    def _setup_ui(self):
        """Setup the simple GUI."""
        # Main container
        main = ttk.Frame(self.dialog, padding="10")
        main.pack(fill=tk.BOTH, expand=True)

        # Title
        title = f"מיפוי עמודות לקבלה"
        if self.vendor_name:
            title += f" - {self.vendor_name}"

        ttk.Label(
            main,
            text=title,
            font=("Arial", 16, "bold")
        ).pack(pady=(0, 10))

        # Instructions
        ttk.Label(
            main,
            text="לחץ על עמודה משמאל, ואז לחץ על המשמעות שלה מימין",
            font=("Arial", 10)
        ).pack(pady=(0, 20))

        # Two panes
        paned = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left: Raw text preview
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=2)

        ttk.Label(
            left_frame,
            text="תוכן הקבלה",
            font=("Arial", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 5))

        text_frame = ttk.Frame(left_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.text_widget = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=("Courier New", 9),
            height=20
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)

        # Add raw text
        self.text_widget.insert(tk.END, self.raw_text[:2000])  # First 2000 chars
        self.text_widget.config(state=tk.DISABLED)

        # Right: Column mapping
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)

        ttk.Label(
            right_frame,
            text="עמודות שזוהו",
            font=("Arial", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))

        # Column buttons frame
        col_frame = ttk.Frame(right_frame)
        col_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        self.column_buttons = []
        self.selected_column = None

        for i, col in enumerate(self.detected_columns):
            btn_frame = ttk.Frame(col_frame)
            btn_frame.pack(fill=tk.X, pady=5)

            hebrew_text = col.get('hebrew_text', f'עמודה {i+1}')
            btn = ttk.Button(
                btn_frame,
                text=hebrew_text,
                width=20,
                command=lambda idx=i: self._select_column(idx)
            )
            btn.pack(side=tk.LEFT, padx=(0, 10))

            # Label for assigned meaning
            meaning_label = ttk.Label(btn_frame, text="(לא נבחר)", foreground="gray")
            meaning_label.pack(side=tk.LEFT)

            self.column_buttons.append((btn, meaning_label))

        # Separator
        ttk.Separator(right_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)

        # Meaning buttons
        ttk.Label(
            right_frame,
            text="בחר משמעות:",
            font=("Arial", 11, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))

        meaning_frame = ttk.Frame(right_frame)
        meaning_frame.pack(fill=tk.BOTH, expand=True)

        self.meaning_buttons = []
        for meaning in self.COLUMN_MEANINGS:
            btn = ttk.Button(
                meaning_frame,
                text=meaning,
                command=lambda m=meaning: self._assign_meaning(m),
                width=15
            )
            btn.pack(pady=3)
            self.meaning_buttons.append(btn)

        # Current selection label
        self.selection_label = ttk.Label(
            right_frame,
            text="נבחרה עמודה: אף אחת",
            font=("Arial", 10),
            foreground="blue"
        )
        self.selection_label.pack(pady=20)

        # Save button
        save_btn = ttk.Button(
            right_frame,
            text="שמור תבנית",
            command=self._save,
            style="Accent.TButton"
        )
        save_btn.pack(pady=10)

        # Style for accent button
        style = ttk.Style()
        style.configure("Accent.TButton", foreground="white", background="#0078D7")

    def _select_column(self, column_index: int):
        """Select a column for mapping."""
        self.selected_column = column_index

        # Update button appearances
        for i, (btn, label) in enumerate(self.column_buttons):
            if i == column_index:
                btn.config(style="Selected.TButton")
            else:
                btn.config(style="TButton")

        # Update selection label
        col_text = self.detected_columns[column_index].get('hebrew_text', f'עמודה {column_index+1}')
        self.selection_label.config(text=f"נבחרה עמודה: {col_text}")

        # Style for selected button
        style = ttk.Style()
        style.configure("Selected.TButton", background="#E1F5FE", foreground="black")

    def _assign_meaning(self, meaning: str):
        """Assign meaning to selected column."""
        if self.selected_column is None:
            messagebox.showinfo("בחר עמודה", "בחר עמודה קודם על ידי לחיצה עליה")
            return

        field_name = self.HEBREW_TO_FIELD.get(meaning, "ignore")
        self.column_assignments[self.selected_column] = field_name

        # Update button label
        _, label = self.column_buttons[self.selected_column]
        label.config(text=f"({meaning})", foreground="green")

        # Clear selection
        self.selected_column = None
        self.selection_label.config(text="נבחרה עמודה: אף אחת")

        # Reset button styles
        for btn, _ in self.column_buttons:
            btn.config(style="TButton")

    def _save(self):
        """Save the column mappings."""
        if not self.column_assignments:
            messagebox.showwarning("אין מיפוי", "לא מיפית אף עמודה. לחץ על עמודה ואז על משמעות שלה.")
            return

        # Convert to format expected by cache
        assignments = {}
        for i, col in enumerate(self.detected_columns):
            if i in self.column_assignments:
                hebrew_text = col.get('hebrew_text', f'Column {i+1}')
                field_name = self.column_assignments[i]
                if field_name != "ignore":
                    assignments[hebrew_text] = field_name

        # Call callback
        self.on_save(assignments, quantity_pattern=1)  # Default pattern

        self.dialog.destroy()
        messagebox.showinfo("נשמר", f"נשמר מיפוי ל-{len(assignments)} עמודות")


def test_simple_gui():
    """Test the simple GUI."""
    root = tk.Tk()
    root.withdraw()

    # Sample raw text
    raw_text = """חנות כלבו
תאור כמות מחיר נטו
מוצר א 2 10.00 20.00
מוצר ב 1 15.50 15.50"""

    # Sample detected columns
    detected_columns = [
        {'hebrew_text': 'תאור'},
        {'hebrew_text': 'כמות'},
        {'hebrew_text': 'מחיר'},
        {'hebrew_text': 'נטו'}
    ]

    def on_save(assignments, pattern):
        print(f"Saved: {assignments}, pattern: {pattern}")

    gui = SimpleColumnMapper(
        root,
        raw_text,
        detected_columns,
        on_save,
        "חנות כלבו"
    )

    root.wait_window(gui.dialog)
    root.destroy()


if __name__ == "__main__":
    test_simple_gui()