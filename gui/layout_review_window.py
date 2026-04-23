"""
Layout review window for reviewing column detection results.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from .theme import theme


class LayoutReviewWindow:
    """Window for reviewing and correcting layout detection."""

    def __init__(self, parent, column_info, quantity_pattern, raw_text=None):
        self.parent = parent
        self.column_info = column_info
        self.quantity_pattern = quantity_pattern
        self.raw_text = raw_text or ""

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title(f"{theme.EMOJI_REVIEW} Layout Review")
        self.window.geometry("900x700")
        self.window.minsize(700, 500)
        self.window.transient(parent)
        self.window.grab_set()

        # Configure theme
        theme.configure_styles(self.window)

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the UI."""
        # Main container
        main = theme.create_frame(self.window, padx=20, pady=20)
        main.pack(fill=tk.BOTH, expand=True)

        # Header
        header = theme.create_frame(main)
        header.pack(fill=tk.X, pady=(0, 20))

        title_label = theme.create_label(
            header,
            text=f"{theme.EMOJI_REVIEW} Layout Review",
            font=theme.FONT_TITLE
        )
        title_label.pack(anchor=tk.W)

        subtitle_label = theme.create_label(
            header,
            text="Review and correct detected columns and patterns",
            font=theme.FONT_SUBTITLE,
            fg=theme.CLR_SUBTEXT
        )
        subtitle_label.pack(anchor=tk.W, pady=(5, 0))

        # Detection Summary
        summary_frame = theme.create_frame(main, bg=theme.CLR_SURFACE)
        summary_frame.pack(fill=tk.X, pady=(0, 20))

        summary_label = theme.create_label(
            summary_frame,
            text="Detection Summary",
            font=("Arial", 11, "bold"),
            bg=theme.CLR_SURFACE
        )
        summary_label.pack(anchor=tk.W, padx=10, pady=(10, 5))

        # Summary content
        summary_content = theme.create_frame(summary_frame, bg=theme.CLR_SURFACE)
        summary_content.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Extract summary info
        num_columns = len(self.column_info.get('detected_columns', []))
        headers = self.column_info.get('headers', [])
        confidence = self.column_info.get('confidence', 0.0)

        summary_text = f"""
        • Detected {num_columns} columns
        • Headers: {', '.join(headers) if headers else 'None detected'}
        • Quantity Pattern: {self.quantity_pattern}
        • Detection Confidence: {confidence:.2f}
        """
        summary_text_widget = tk.Text(
            summary_content,
            height=5,
            wrap=tk.WORD,
            bg=theme.CLR_SURFACE,
            fg=theme.CLR_TEXT,
            font=theme.FONT_MONO,
            relief=tk.FLAT
        )
        summary_text_widget.pack(fill=tk.X)
        summary_text_widget.insert(tk.END, summary_text.strip())
        summary_text_widget.config(state=tk.DISABLED)

        # Column Assignment Section
        columns_frame = theme.create_frame(main)
        columns_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        columns_label = theme.create_label(
            columns_frame,
            text="Column Assignments",
            font=("Arial", 12, "bold")
        )
        columns_label.pack(anchor=tk.W, pady=(0, 10))

        # Create notebook for tabs
        notebook = ttk.Notebook(columns_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Detected Columns
        detected_tab = ttk.Frame(notebook)
        notebook.add(detected_tab, text="Detected Columns")

        self._build_detected_columns_tab(detected_tab)

        # Tab 2: Raw Text
        if self.raw_text:
            raw_tab = ttk.Frame(notebook)
            notebook.add(raw_tab, text="Raw Text")
            self._build_raw_text_tab(raw_tab)

        # Tab 3: Manual Assignment
        manual_tab = ttk.Frame(notebook)
        notebook.add(manual_tab, text="Manual Assignment")
        self._build_manual_assignment_tab(manual_tab)

        # Action buttons
        buttons_frame = theme.create_frame(main)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))

        # Accept button
        btn_accept = theme.create_button(
            buttons_frame, "Accept Detection", self._accept_detection,
            style="Primary.TButton", emoji="✅"
        )
        btn_accept.pack(side=tk.LEFT, padx=(0, 10))

        # Correct button
        btn_correct = theme.create_button(
            buttons_frame, "Correct Manually", self._correct_manually,
            style="Secondary.TButton"
        )
        btn_correct.pack(side=tk.LEFT, padx=(0, 10))

        # Save to cache button
        btn_save_cache = theme.create_button(
            buttons_frame, "Save to Vendor Cache", self._save_to_cache,
            style="Success.TButton", emoji="💾"
        )
        btn_save_cache.pack(side=tk.LEFT, padx=(0, 10))

        # Cancel button
        btn_cancel = theme.create_button(
            buttons_frame, "Cancel", self._cancel,
            style="Secondary.TButton"
        )
        btn_cancel.pack(side=tk.RIGHT)

    def _build_detected_columns_tab(self, parent):
        """Build detected columns tab."""
        # Treeview for detected columns
        columns = ("index", "header", "assigned_type", "confidence", "sample_value")
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=10)

        # Configure columns
        tree.heading("index", text="#")
        tree.heading("header", text="Header (Hebrew)")
        tree.heading("assigned_type", text="Assigned Type")
        tree.heading("confidence", text="Confidence")
        tree.heading("sample_value", text="Sample Value")

        tree.column("index", width=50)
        tree.column("header", width=150)
        tree.column("assigned_type", width=150)
        tree.column("confidence", width=100)
        tree.column("sample_value", width=200)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        # Pack tree and scrollbar
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate with detected columns
        detected_columns = self.column_info.get('detected_columns', [])
        for i, col in enumerate(detected_columns, 1):
            header = col.get('header', '')
            assigned_type = col.get('assigned_type', 'unknown')
            confidence = col.get('confidence', 0.0)
            sample_value = col.get('sample_value', '')

            tree.insert("", tk.END, values=(
                i,
                header,
                assigned_type,
                f"{confidence:.2f}",
                sample_value[:50] + "..." if len(sample_value) > 50 else sample_value
            ))

        # Add context menu for reassigning columns
        context_menu = tk.Menu(parent, tearoff=0)
        column_types = ["description", "quantity", "unit_price", "line_total",
                       "catalog_no", "barcode", "discount", "tax", "other"]

        for col_type in column_types:
            context_menu.add_command(
                label=f"Assign as {col_type}",
                command=lambda t=col_type: self._reassign_column(tree, t)
            )

        tree.bind("<Button-3>", lambda e: self._show_context_menu(e, context_menu, tree))

    def _build_raw_text_tab(self, parent):
        """Build raw text tab."""
        # Text widget for raw text
        text_widget = tk.Text(
            parent,
            wrap=tk.WORD,
            bg=theme.CLR_SURFACE,
            fg=theme.CLR_TEXT,
            font=theme.FONT_MONO,
            padx=10,
            pady=10
        )
        text_widget.pack(fill=tk.BOTH, expand=True)

        # Insert raw text
        text_widget.insert(tk.END, self.raw_text)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add search functionality
        search_frame = tk.Frame(parent, bg=theme.CLR_BG)
        search_frame.pack(fill=tk.X, padx=10, pady=(5, 0))

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        search_entry = tk.Entry(search_frame, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 5))

        def search_text():
            search_term = search_entry.get()
            if search_term:
                # Remove previous highlights
                text_widget.tag_remove("highlight", "1.0", tk.END)

                # Search for term
                start_pos = "1.0"
                while True:
                    start_pos = text_widget.search(search_term, start_pos, stopindex=tk.END)
                    if not start_pos:
                        break
                    end_pos = f"{start_pos}+{len(search_term)}c"
                    text_widget.tag_add("highlight", start_pos, end_pos)
                    start_pos = end_pos

                # Configure highlight tag
                text_widget.tag_config("highlight", background="yellow", foreground="black")
                text_widget.see("1.0")

        btn_search = ttk.Button(search_frame, text="Search", command=search_text)
        btn_search.pack(side=tk.LEFT)

    def _build_manual_assignment_tab(self, parent):
        """Build manual assignment tab."""
        # Instructions
        instructions = theme.create_label(
            parent,
            text="Manually assign column types by clicking on detected columns\nand selecting the appropriate type from the context menu.",
            font=theme.FONT_SMALL,
            fg=theme.CLR_SUBTEXT
        )
        instructions.pack(anchor=tk.W, padx=10, pady=(10, 10))

        # Manual assignment controls
        controls_frame = theme.create_frame(parent)
        controls_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        # Vendor name input
        vendor_frame = theme.create_frame(controls_frame)
        vendor_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(vendor_frame, text="Vendor Name:").pack(side=tk.LEFT, padx=(0, 10))
        self.vendor_entry = theme.create_entry(vendor_frame, width=30)
        self.vendor_entry.pack(side=tk.LEFT)

        # Pattern selection
        pattern_frame = theme.create_frame(controls_frame)
        pattern_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(pattern_frame, text="Quantity Pattern:").pack(side=tk.LEFT, padx=(0, 10))
        self.manual_pattern_var = tk.IntVar(value=self.quantity_pattern)

        pattern_options = [
            ("Pattern 1: Total = Quantity × Price", 1),
            ("Pattern 2: Price = Total / Quantity", 2),
            ("Pattern 3: Quantity = Total / Price", 3)
        ]

        for text, value in pattern_options:
            rb = ttk.Radiobutton(pattern_frame, text=text, variable=self.manual_pattern_var, value=value)
            rb.pack(anchor=tk.W, pady=2)

        # Preview area for manual mapping
        preview_frame = theme.create_frame(parent, bg=theme.CLR_SURFACE)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        preview_label = theme.create_label(
            preview_frame,
            text="Manual Column Mapping Preview",
            font=("Arial", 11, "bold"),
            bg=theme.CLR_SURFACE
        )
        preview_label.pack(anchor=tk.W, padx=10, pady=(10, 5))

        # Preview text widget
        preview_text = tk.Text(
            preview_frame,
            height=10,
            wrap=tk.WORD,
            bg=theme.CLR_SURFACE,
            fg=theme.CLR_TEXT,
            font=theme.FONT_MONO,
            relief=tk.FLAT
        )
        preview_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        preview_text.insert(tk.END, "Column mappings will appear here...")
        preview_text.config(state=tk.DISABLED)

    def _show_context_menu(self, event, menu, tree):
        """Show context menu for column reassignment."""
        # Get clicked item
        item = tree.identify_row(event.y)
        if item:
            tree.selection_set(item)
            menu.post(event.x_root, event.y_root)

    def _reassign_column(self, tree, column_type):
        """Reassign selected column to new type."""
        selection = tree.selection()
        if selection:
            # Update tree item
            item = selection[0]
            values = list(tree.item(item, "values"))
            values[2] = column_type  # Update assigned_type
            tree.item(item, values=tuple(values))

    def _accept_detection(self):
        """Accept the current detection."""
        messagebox.showinfo("Accepted", "Layout detection accepted. Continuing with processing...")
        self.window.destroy()

    def _correct_manually(self):
        """Correct detection manually."""
        messagebox.showinfo("Manual Correction", "Manual correction would open detailed editor...")
        # In a real implementation, this would open a more detailed editor

    def _save_to_cache(self):
        """Save current layout to vendor cache."""
        vendor_name = self.vendor_entry.get().strip() if hasattr(self, 'vendor_entry') else ""

        if not vendor_name:
            messagebox.showwarning("Vendor Required", "Please enter a vendor name to save to cache.")
            return

        confirm = messagebox.askyesno(
            "Save to Cache",
            f"Save current layout to vendor cache for '{vendor_name}'?\n"
            f"This will create/update a template for this vendor."
        )

        if confirm:
            # In a real implementation, this would save the current column mappings
            # and pattern to the vendor cache
            messagebox.showinfo("Saved", f"Layout saved to vendor cache for '{vendor_name}'.")
            self.window.destroy()

    def _cancel(self):
        """Cancel layout review."""
        self.window.destroy()