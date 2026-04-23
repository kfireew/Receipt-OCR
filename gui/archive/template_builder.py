#!/usr/bin/env python3
"""
TEMPLATE BUILDER GUI

Point-and-click interface for creating perfect vendor templates.
A human can visually define the receipt/invoice structure for 100% accuracy.

Features:
1. View raw text with line numbers
2. Mark header/footer boundaries
3. Define item boundaries (click start/end lines)
4. Map columns visually
5. Test template immediately
6. Save as verified template
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

class TemplateBuilder:
    """GUI for creating perfect vendor templates."""

    def __init__(self, root):
        self.root = root
        self.root.title("Vendor Template Builder - 100% Accuracy")
        self.root.geometry("1200x800")

        # Data
        self.raw_text = ""
        self.lines = []
        self.vendor_key = ""
        self.vendor_name = ""

        # Template being built
        self.template = {
            'vendor_key': '',
            'display_name': '',
            'created_date': '',
            'modified_date': '',
            'created_by': 'gui',
            'confidence': 1.0,
            'validation_rate': 1.0,
            'user_verified': True,
            'parsing_rules': {
                'document_type': 'receipt',  # or 'invoice'
                'skip_header_lines': 0,
                'skip_footer_lines': 0,
                'multi_line_items': False,
                'lines_per_item': 1,
                'column_detection_method': 'fixed_positions',
                'item_separator': 'single_line'
            },
            'column_definitions': [],
            'column_positions': {},
            'extraction_patterns': {}
        }

        # UI state
        self.selected_lines = set()
        self.header_end = 0
        self.footer_start = 0
        self.item_boundaries = []  # List of (start_line, end_line)

        self._setup_ui()

    def _setup_ui(self):
        """Setup the GUI interface."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # Row 0: File selection
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(file_frame, text="Raw Text File:").pack(side=tk.LEFT, padx=(0, 10))
        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, width=50).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(file_frame, text="Browse", command=self._load_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(file_frame, text="Load", command=self._load_text).pack(side=tk.LEFT)

        # Row 1: Vendor info
        vendor_frame = ttk.LabelFrame(main_frame, text="Vendor Information", padding="10")
        vendor_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(vendor_frame, text="Vendor Key (English):").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.vendor_key_var = tk.StringVar()
        ttk.Entry(vendor_frame, textvariable=self.vendor_key_var, width=20).grid(row=0, column=1, sticky=tk.W, padx=(0, 20))

        ttk.Label(vendor_frame, text="Display Name (Hebrew):").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.vendor_name_var = tk.StringVar()
        ttk.Entry(vendor_frame, textvariable=self.vendor_name_var, width=30).grid(row=0, column=3, sticky=tk.W)

        ttk.Label(vendor_frame, text="Document Type:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        self.doc_type_var = tk.StringVar(value="receipt")
        ttk.Combobox(vendor_frame, textvariable=self.doc_type_var, values=["receipt", "invoice"], width=15, state="readonly").grid(row=1, column=1, sticky=tk.W, padx=(0, 20), pady=(10, 0))

        # Row 2: Text viewer and controls
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        paned.columnconfigure(1, weight=1)

        # Left: Text viewer with line numbers
        viewer_frame = ttk.Frame(paned)
        paned.add(viewer_frame, weight=2)

        # Line numbers
        line_frame = ttk.Frame(viewer_frame)
        line_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.line_canvas = tk.Canvas(line_frame, width=50, bg='lightgray')
        self.line_canvas.pack(side=tk.LEFT, fill=tk.Y)

        # Text widget for raw text
        text_frame = ttk.Frame(viewer_frame)
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.text_widget = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.NONE,
            font=('Courier', 10),
            height=30,
            width=80
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)

        # Right: Controls
        control_frame = ttk.LabelFrame(paned, text="Template Definition", padding="10")
        paned.add(control_frame, weight=1)

        # Header/Footer controls
        ttk.Label(control_frame, text="Header Lines (to skip):").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.header_var = tk.IntVar(value=0)
        ttk.Spinbox(control_frame, from_=0, to=100, textvariable=self.header_var, width=10,
                    command=self._highlight_header).grid(row=0, column=1, sticky=tk.W, pady=(0, 5))

        ttk.Label(control_frame, text="Footer Lines (to skip):").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.footer_var = tk.IntVar(value=0)
        ttk.Spinbox(control_frame, from_=0, to=100, textvariable=self.footer_var, width=10,
                    command=self._highlight_footer).grid(row=1, column=1, sticky=tk.W, pady=(0, 5))

        ttk.Button(control_frame, text="Mark Item Start", command=self._mark_item_start).grid(row=2, column=0, columnspan=2, pady=(10, 5), sticky=tk.W+tk.E)
        ttk.Button(control_frame, text="Mark Item End", command=self._mark_item_end).grid(row=3, column=0, columnspan=2, pady=(0, 5), sticky=tk.W+tk.E)

        # Item boundaries list
        ttk.Label(control_frame, text="Item Boundaries:").grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        self.boundaries_listbox = tk.Listbox(control_frame, height=5)
        self.boundaries_listbox.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))

        ttk.Button(control_frame, text="Clear Selection", command=self._clear_selection).grid(row=6, column=0, columnspan=2, pady=(5, 5), sticky=tk.W+tk.E)

        # Column definition
        ttk.Label(control_frame, text="Define Columns:", font=('', 10, 'bold')).grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=(20, 5))

        # Column table
        columns_frame = ttk.Frame(control_frame)
        columns_frame.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Create treeview for columns
        self.column_tree = ttk.Treeview(columns_frame, columns=('Index', 'Hebrew', 'English', 'Type'), show='headings', height=5)
        self.column_tree.heading('Index', text='#')
        self.column_tree.heading('Hebrew', text='Hebrew Name')
        self.column_tree.heading('English', text='English Field')
        self.column_tree.heading('Type', text='Data Type')

        self.column_tree.column('Index', width=40)
        self.column_tree.column('Hebrew', width=100)
        self.column_tree.column('English', width=100)
        self.column_tree.column('Type', width=80)

        scrollbar = ttk.Scrollbar(columns_frame, orient=tk.VERTICAL, command=self.column_tree.yview)
        self.column_tree.configure(yscrollcommand=scrollbar.set)

        self.column_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Column controls
        col_control_frame = ttk.Frame(control_frame)
        col_control_frame.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Button(col_control_frame, text="Add Column", command=self._add_column_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(col_control_frame, text="Edit Column", command=self._edit_column).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(col_control_frame, text="Delete Column", command=self._delete_column).pack(side=tk.LEFT)

        # Row 3: Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Button(action_frame, text="Test Template", command=self._test_template).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="Save Template", command=self._save_template).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="Load Template", command=self._load_template).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(action_frame, text="Clear All", command=self._clear_all).pack(side=tk.LEFT)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN).grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E))

        # Bind events
        self.text_widget.bind('<Button-1>', self._on_text_click)
        self.doc_type_var.trace('w', self._on_doc_type_change)

    def _load_file(self):
        """Browse for raw text file."""
        filename = filedialog.askopenfilename(
            title="Select raw text file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.file_path_var.set(filename)

    def _load_text(self):
        """Load raw text from file."""
        filename = self.file_path_var.get()
        if not filename or not os.path.exists(filename):
            messagebox.showerror("Error", "Please select a valid file")
            return

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.raw_text = f.read()
            self.lines = self.raw_text.splitlines()

            # Display in text widget
            self.text_widget.delete(1.0, tk.END)
            for i, line in enumerate(self.lines):
                self.text_widget.insert(tk.END, f"{line}\n")

            self._update_line_numbers()
            self.status_var.set(f"Loaded {len(self.lines)} lines from {os.path.basename(filename)}")

            # Auto-detect vendor from first few lines
            self._auto_detect_vendor()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {str(e)}")

    def _update_line_numbers(self):
        """Update line numbers in the sidebar."""
        self.line_canvas.delete("all")
        if not self.lines:
            return

        # Calculate visible lines
        first_line = int(self.text_widget.index('@0,0').split('.')[0])
        last_line = int(self.text_widget.index('@0,10000').split('.')[0])
        last_line = min(last_line, len(self.lines))

        for i in range(first_line, last_line + 1):
            y_pos = (i - first_line) * 16  # Approximate line height
            self.line_canvas.create_text(5, y_pos + 8, anchor=tk.W, text=str(i), font=('Courier', 10))

            # Highlight selected lines
            if i in self.selected_lines:
                self.line_canvas.create_rectangle(0, y_pos, 50, y_pos + 16, fill='lightblue', outline='')

            # Highlight header
            if i < self.header_var.get():
                self.line_canvas.create_rectangle(30, y_pos, 50, y_pos + 16, fill='lightgray', outline='')

            # Highlight footer
            if i >= len(self.lines) - self.footer_var.get():
                self.line_canvas.create_rectangle(30, y_pos, 50, y_pos + 16, fill='lightgray', outline='')

    def _auto_detect_vendor(self):
        """Auto-detect vendor from first few lines."""
        if not self.lines:
            return

        # Look for common vendor patterns in first 10 lines
        search_text = '\n'.join(self.lines[:10])

        # Check for known vendors
        known_vendors = {
            'גלוברנדס': 'globrands',
            'שופרסל': 'shufersal',
            'תנובה': 'tnuva',
            'רמי לוי': 'rami_levi'
        }

        for hebrew, key in known_vendors.items():
            if hebrew in search_text:
                self.vendor_key_var.set(key)
                self.vendor_name_var.set(hebrew)
                self.status_var.set(f"Auto-detected vendor: {hebrew} ({key})")
                break

    def _on_text_click(self, event):
        """Handle click in text widget."""
        # Get clicked line
        index = self.text_widget.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0]) - 1  # Convert to 0-based

        if 0 <= line_num < len(self.lines):
            # Toggle selection
            if line_num in self.selected_lines:
                self.selected_lines.remove(line_num)
            else:
                self.selected_lines.add(line_num)

            self._update_line_numbers()
            self.status_var.set(f"Selected line {line_num + 1}: {self.lines[line_num][:50]}...")

    def _highlight_header(self):
        """Highlight header lines."""
        self.header_end = self.header_var.get()
        self._update_line_numbers()

        # Update template
        self.template['parsing_rules']['skip_header_lines'] = self.header_end
        self.template['parsing_rules']['lines_per_item'] = 1 if not self.template['parsing_rules']['multi_line_items'] else 2

    def _highlight_footer(self):
        """Highlight footer lines."""
        self.footer_start = len(self.lines) - self.footer_var.get()
        self._update_line_numbers()

        # Update template
        self.template['parsing_rules']['skip_footer_lines'] = self.footer_var.get()

    def _on_doc_type_change(self, *args):
        """Handle document type change."""
        doc_type = self.doc_type_var.get()
        self.template['parsing_rules']['document_type'] = doc_type
        self.template['is_invoice'] = (doc_type == 'invoice')

        if doc_type == 'invoice':
            # Default values for invoices
            self.template['parsing_rules']['multi_line_items'] = True
            self.template['parsing_rules']['lines_per_item'] = 2
            self.header_var.set(10)  # Common for invoices
        else:
            # Default for receipts
            self.template['parsing_rules']['multi_line_items'] = False
            self.template['parsing_rules']['lines_per_item'] = 1
            self.header_var.set(2)

        self._highlight_header()

    def _mark_item_start(self):
        """Mark start of an item."""
        if len(self.selected_lines) != 1:
            messagebox.showwarning("Warning", "Please select exactly one line as item start")
            return

        start_line = min(self.selected_lines)

        # Find matching end line
        end_line = start_line

        if self.template['parsing_rules']['multi_line_items']:
            # For multi-line items, try to find the end
            lines_per_item = self.template['parsing_rules']['lines_per_item']
            end_line = min(start_line + lines_per_item - 1, len(self.lines) - 1)

        self.item_boundaries.append((start_line, end_line))
        self._update_boundaries_list()

        self.status_var.set(f"Added item: lines {start_line+1}-{end_line+1}")
        self.selected_lines.clear()
        self._update_line_numbers()

    def _mark_item_end(self):
        """Mark end of an item (for variable length items)."""
        if len(self.selected_lines) != 1:
            messagebox.showwarning("Warning", "Please select exactly one line as item end")
            return

        end_line = min(self.selected_lines)

        # Find matching start line (look for nearest start)
        if self.item_boundaries:
            last_start, last_end = self.item_boundaries[-1]
            if last_end == -1:  # Unfinished item
                self.item_boundaries[-1] = (last_start, end_line)
                self._update_boundaries_list()
                self.status_var.set(f"Completed item: lines {last_start+1}-{end_line+1}")
            else:
                messagebox.showinfo("Info", "No unfinished item to complete")
        else:
            messagebox.showwarning("Warning", "No item started. Use 'Mark Item Start' first")

        self.selected_lines.clear()
        self._update_line_numbers()

    def _update_boundaries_list(self):
        """Update the item boundaries listbox."""
        self.boundaries_listbox.delete(0, tk.END)
        for i, (start, end) in enumerate(self.item_boundaries):
            if end == -1:
                self.boundaries_listbox.insert(tk.END, f"Item {i+1}: Line {start+1} (unfinished)")
            else:
                self.boundaries_listbox.insert(tk.END, f"Item {i+1}: Lines {start+1}-{end+1}")

    def _clear_selection(self):
        """Clear selected lines."""
        self.selected_lines.clear()
        self._update_line_numbers()
        self.status_var.set("Selection cleared")

    def _add_column_dialog(self):
        """Open dialog to add a column."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Column")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # Form fields
        ttk.Label(dialog, text="Hebrew Name (as appears):").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        hebrew_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=hebrew_var, width=30).grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)

        ttk.Label(dialog, text="English Field Name:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        english_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=english_var, width=30).grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)

        ttk.Label(dialog, text="Data Type:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        type_var = tk.StringVar(value="text")
        type_combo = ttk.Combobox(dialog, textvariable=type_var, values=["text", "barcode", "quantity", "price", "total"], state="readonly", width=20)
        type_combo.grid(row=2, column=1, padx=10, pady=10, sticky=tk.W)

        ttk.Label(dialog, text="Extraction Pattern (optional):").grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)
        pattern_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=pattern_var, width=30).grid(row=3, column=1, padx=10, pady=10, sticky=tk.W)

        ttk.Label(dialog, text="Required:").grid(row=4, column=0, padx=10, pady=10, sticky=tk.W)
        required_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dialog, variable=required_var).grid(row=4, column=1, padx=10, pady=10, sticky=tk.W)

        def save_column():
            if not hebrew_var.get() or not english_var.get():
                messagebox.showerror("Error", "Hebrew and English names are required")
                return

            column = {
                'index': len(self.template['column_definitions']) + 1,
                'hebrew_name': hebrew_var.get(),
                'english_name': english_var.get(),
                'data_type': type_var.get(),
                'required': required_var.get(),
                'extraction_pattern': pattern_var.get() if pattern_var.get() else None
            }

            self.template['column_definitions'].append(column)
            self._update_column_tree()
            dialog.destroy()
            self.status_var.set(f"Added column: {hebrew_var.get()} -> {english_var.get()}")

        def cancel():
            dialog.destroy()

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=5, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="Save", command=save_column).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.LEFT)

    def _update_column_tree(self):
        """Update the column treeview."""
        # Clear existing items
        for item in self.column_tree.get_children():
            self.column_tree.delete(item)

        # Add columns
        for col in self.template['column_definitions']:
            self.column_tree.insert('', tk.END, values=(
                col['index'],
                col['hebrew_name'],
                col['english_name'],
                col['data_type']
            ))

    def _edit_column(self):
        """Edit selected column."""
        selection = self.column_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a column to edit")
            return

        # Get column index from tree
        item = self.column_tree.item(selection[0])
        values = item['values']
        col_index = values[0] - 1  # Convert to 0-based

        if 0 <= col_index < len(self.template['column_definitions']):
            col = self.template['column_definitions'][col_index]

            # Similar to add dialog but pre-filled
            dialog = tk.Toplevel(self.root)
            dialog.title("Edit Column")
            dialog.geometry("400x300")
            dialog.transient(self.root)
            dialog.grab_set()

            # Form fields (pre-filled)
            ttk.Label(dialog, text="Hebrew Name:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
            hebrew_var = tk.StringVar(value=col['hebrew_name'])
            ttk.Entry(dialog, textvariable=hebrew_var, width=30).grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)

            ttk.Label(dialog, text="English Field Name:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
            english_var = tk.StringVar(value=col['english_name'])
            ttk.Entry(dialog, textvariable=english_var, width=30).grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)

            ttk.Label(dialog, text="Data Type:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
            type_var = tk.StringVar(value=col['data_type'])
            type_combo = ttk.Combobox(dialog, textvariable=type_var, values=["text", "barcode", "quantity", "price", "total"], state="readonly", width=20)
            type_combo.grid(row=2, column=1, padx=10, pady=10, sticky=tk.W)

            ttk.Label(dialog, text="Extraction Pattern:").grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)
            pattern_var = tk.StringVar(value=col.get('extraction_pattern', ''))
            ttk.Entry(dialog, textvariable=pattern_var, width=30).grid(row=3, column=1, padx=10, pady=10, sticky=tk.W)

            ttk.Label(dialog, text="Required:").grid(row=4, column=0, padx=10, pady=10, sticky=tk.W)
            required_var = tk.BooleanVar(value=col.get('required', True))
            ttk.Checkbutton(dialog, variable=required_var).grid(row=4, column=1, padx=10, pady=10, sticky=tk.W)

            def save_changes():
                self.template['column_definitions'][col_index] = {
                    'index': col_index + 1,
                    'hebrew_name': hebrew_var.get(),
                    'english_name': english_var.get(),
                    'data_type': type_var.get(),
                    'required': required_var.get(),
                    'extraction_pattern': pattern_var.get() if pattern_var.get() else None
                }
                self._update_column_tree()
                dialog.destroy()
                self.status_var.set(f"Updated column: {hebrew_var.get()}")

            def delete_column():
                if messagebox.askyesno("Confirm", "Delete this column?"):
                    del self.template['column_definitions'][col_index]
                    # Re-index
                    for i, c in enumerate(self.template['column_definitions']):
                        c['index'] = i + 1
                    self._update_column_tree()
                    dialog.destroy()
                    self.status_var.set("Column deleted")

            # Buttons
            button_frame = ttk.Frame(dialog)
            button_frame.grid(row=5, column=0, columnspan=2, pady=20)

            ttk.Button(button_frame, text="Save", command=save_changes).pack(side=tk.LEFT, padx=10)
            ttk.Button(button_frame, text="Delete", command=delete_column).pack(side=tk.LEFT, padx=10)
            ttk.Button(button_frame, text="Cancel", command=lambda: dialog.destroy()).pack(side=tk.LEFT)

    def _delete_column(self):
        """Delete selected column."""
        selection = self.column_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a column to delete")
            return

        if messagebox.askyesno("Confirm", "Delete selected column?"):
            item = self.column_tree.item(selection[0])
            values = item['values']
            col_index = values[0] - 1

            if 0 <= col_index < len(self.template['column_definitions']):
                del self.template['column_definitions'][col_index]
                # Re-index
                for i, col in enumerate(self.template['column_definitions']):
                    col['index'] = i + 1
                self._update_column_tree()
                self.status_var.set(f"Deleted column")

    def _test_template(self):
        """Test the current template."""
        if not self.raw_text:
            messagebox.showwarning("Warning", "Please load raw text first")
            return

        if not self.vendor_key_var.get() or not self.vendor_name_var.get():
            messagebox.showwarning("Warning", "Please enter vendor information")
            return

        if not self.template['column_definitions']:
            messagebox.showwarning("Warning", "Please define at least one column")
            return

        # Update template with current values
        self.template['vendor_key'] = self.vendor_key_var.get()
        self.template['display_name'] = self.vendor_name_var.get()
        self.template['modified_date'] = datetime.now().isoformat()

        # Use the fixed vendor cache to test
        try:
            from phases.phase6_vendor_cache_fixed import Phase6VendorCacheFixed
            cache = Phase6VendorCacheFixed()

            # Save template to cache
            cache.cache['vendors'][self.template['vendor_key']] = self.template
            cache._save_cache()

            # Test parsing
            column_info, success = cache.apply_template(self.template['vendor_key'], self.raw_text)

            if success:
                items = column_info.get('extracted_items', [])
                messagebox.showinfo("Test Result",
                    f"Template test successful!\n"
                    f"Extracted {len(items)} items.\n"
                    f"\nFirst item preview:\n"
                    f"{json.dumps(items[0] if items else {}, ensure_ascii=False, indent=2)}")
                self.status_var.set(f"Test successful: {len(items)} items extracted")
            else:
                messagebox.showwarning("Test Result", "Template test failed. Check your definitions.")
                self.status_var.set("Test failed")

        except Exception as e:
            messagebox.showerror("Error", f"Test failed: {str(e)}")
            self.status_var.set(f"Test error: {str(e)}")

    def _save_template(self):
        """Save template to file."""
        if not self.vendor_key_var.get():
            messagebox.showwarning("Warning", "Please enter vendor key")
            return

        # Update template
        self.template['vendor_key'] = self.vendor_key_var.get()
        self.template['display_name'] = self.vendor_name_var.get()
        self.template['modified_date'] = datetime.now().isoformat()
        self.template['created_date'] = self.template.get('created_date', datetime.now().isoformat())

        # Ask for filename
        default_name = f"{self.template['vendor_key']}_template.json"
        filename = filedialog.asksaveasfilename(
            title="Save Template",
            initialfile=default_name,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.template, f, ensure_ascii=False, indent=2)

                # Also save to vendor cache
                from phases.phase6_vendor_cache_fixed import Phase6VendorCacheFixed
                cache = Phase6VendorCacheFixed()
                cache.cache['vendors'][self.template['vendor_key']] = self.template
                cache._save_cache()

                messagebox.showinfo("Success", f"Template saved to:\n{filename}\n\nAlso added to vendor cache.")
                self.status_var.set(f"Template saved: {self.template['display_name']}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {str(e)}")

    def _load_template(self):
        """Load template from file."""
        filename = filedialog.askopenfilename(
            title="Load Template",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.template = json.load(f)

                # Update UI
                self.vendor_key_var.set(self.template.get('vendor_key', ''))
                self.vendor_name_var.set(self.template.get('display_name', ''))

                parsing_rules = self.template.get('parsing_rules', {})
                self.doc_type_var.set(parsing_rules.get('document_type', 'receipt'))
                self.header_var.set(parsing_rules.get('skip_header_lines', 0))
                self.footer_var.set(parsing_rules.get('skip_footer_lines', 0))

                self._update_column_tree()
                self._highlight_header()
                self._highlight_footer()

                messagebox.showinfo("Success", f"Template loaded: {self.template.get('display_name')}")
                self.status_var.set(f"Template loaded: {self.template.get('display_name')}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to load: {str(e)}")

    def _clear_all(self):
        """Clear all template data."""
        if messagebox.askyesno("Confirm", "Clear all template data?"):
            self.template = {
                'vendor_key': '',
                'display_name': '',
                'created_date': '',
                'modified_date': '',
                'created_by': 'gui',
                'confidence': 1.0,
                'validation_rate': 1.0,
                'user_verified': True,
                'parsing_rules': {
                    'document_type': 'receipt',
                    'skip_header_lines': 0,
                    'skip_footer_lines': 0,
                    'multi_line_items': False,
                    'lines_per_item': 1,
                    'column_detection_method': 'fixed_positions',
                    'item_separator': 'single_line'
                },
                'column_definitions': [],
                'column_positions': {},
                'extraction_patterns': {}
            }

            self.vendor_key_var.set('')
            self.vendor_name_var.set('')
            self.doc_type_var.set('receipt')
            self.header_var.set(0)
            self.footer_var.set(0)
            self.selected_lines.clear()
            self.item_boundaries = []
            self._update_boundaries_list()
            self._update_column_tree()
            self._update_line_numbers()
            self.status_var.set("All cleared")

def main():
    """Main entry point."""
    root = tk.Tk()
    app = TemplateBuilder(root)
    root.mainloop()

if __name__ == "__main__":
    main()