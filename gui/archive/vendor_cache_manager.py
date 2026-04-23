"""
Vendor cache management GUI component.
Provides manual review, correction, and saving of vendor layouts.
"""

import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path


class VendorCacheManager:
    """Manages vendor cache through GUI interface."""

    # Column meanings for dropdown
    COLUMN_MEANINGS = [
        "Product Description",
        "Product Code / CatalogNo",
        "Quantity",
        "Units Per Box",
        "Box Count",
        "Unit Price",
        "Line Gross Total",
        "Line Net Total",
        "Discount Amount",
        "Discount Percent",
        "Ignore this column"
    ]

    # Mapping from dropdown text to internal field names
    MEANING_TO_FIELD = {
        "Product Description": "description",
        "Product Code / CatalogNo": "product_code",
        "Quantity": "quantity",
        "Units Per Box": "units_per_box",
        "Box Count": "box_count",
        "Unit Price": "unit_price",
        "Line Gross Total": "line_gross_total",
        "Line Net Total": "line_net_total",
        "Discount Amount": "discount_amount",
        "Discount Percent": "discount_percent",
        "Ignore this column": "ignore"
    }

    FIELD_TO_MEANING = {v: k for k, v in MEANING_TO_FIELD.items()}

    def __init__(self, cache_path: Optional[str] = None):
        """
        Args:
            cache_path: Path to vendor_cache.json file
        """
        if cache_path:
            self.cache_path = Path(cache_path)
        else:
            project_root = Path(__file__).parent.parent
            self.cache_path = project_root / "data" / "vendor_cache.json"

        # Ensure data directory exists
        self.cache_path.parent.mkdir(exist_ok=True)

    def load_cache(self) -> Dict[str, Any]:
        """Load vendor cache from file."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f)

                    # Handle v2.0 format with "vendors" key
                    if "vendors" in cache and isinstance(cache["vendors"], dict):
                        # This is v2.0 format, return the vendors dict directly
                        vendors = cache["vendors"]
                        # Ensure all entries have required fields
                        for vendor_key, entry in vendors.items():
                            # Check legacy_fields for backward compatibility
                            legacy = entry.get("legacy_fields", {})
                            if "confirmed_by_user" not in legacy:
                                legacy["confirmed_by_user"] = False
                            if "confidence" not in legacy:
                                legacy["confidence"] = 0.0
                            if "last_seen" not in legacy:
                                legacy["last_seen"] = datetime.now().strftime("%Y-%m-%d")
                        return vendors
                    else:
                        # Old format - ensure all entries have required fields
                        for vendor_key, entry in cache.items():
                            if "confirmed_by_user" not in entry:
                                entry["confirmed_by_user"] = False
                            if "confidence" not in entry:
                                entry["confidence"] = 0.0
                            if "last_seen" not in entry:
                                entry["last_seen"] = datetime.now().strftime("%Y-%m-%d")
                        return cache
            except (json.JSONDecodeError, IOError) as e:
                messagebox.showerror("Cache Error", f"Failed to load vendor cache: {e}")
                return {}
        else:
            return {}

    def save_cache(self, cache: Dict[str, Any]):
        """Save vendor cache to file in v2.0 format."""
        try:
            # Check if this is already in v2.0 format with "vendors" key
            if "vendors" in cache:
                # Already v2.0 format
                cache_to_save = cache
            else:
                # Convert to v2.0 format
                cache_to_save = {
                    "version": "2.0",
                    "vendors": cache
                }

            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_to_save, f, ensure_ascii=False, indent=2)
            return True
        except (IOError, TypeError) as e:
            messagebox.showerror("Cache Error", f"Failed to save vendor cache: {e}")
            return False

    def get_vendor_entry(self, vendor_key: str) -> Optional[Dict[str, Any]]:
        """Get a vendor entry from cache."""
        cache = self.load_cache()
        return cache.get(vendor_key)

    def save_vendor_entry(self, vendor_key: str, entry: Dict[str, Any]):
        """Save or update a vendor entry in cache."""
        cache = self.load_cache()
        cache[vendor_key] = entry
        return self.save_cache(cache)

    def delete_vendor_entry(self, vendor_key: str):
        """Delete a vendor entry from cache."""
        cache = self.load_cache()
        if vendor_key in cache:
            del cache[vendor_key]
            return self.save_cache(cache)
        return True

    def get_all_vendors(self) -> List[Dict[str, Any]]:
        """Get all vendors with their cache entries."""
        cache = self.load_cache()
        result = []
        for vendor_key, entry in cache.items():
            # Handle v2.0 format where display_name might be in basics or legacy_fields
            display_name = None
            confidence = 0.0
            last_seen = "Never"
            parse_count = 0
            confirmed = False

            # Try to get from legacy_fields (v2.0 format)
            legacy = entry.get("legacy_fields", {})
            if legacy:
                display_name = legacy.get("display_name")
                confidence = legacy.get("confidence", 0.0)
                last_seen = legacy.get("last_seen", "Never")
                parse_count = legacy.get("parse_count", 0)
                confirmed = legacy.get("confirmed_by_user", False)

            # Fall back to basics (v2.0 format)
            if not display_name:
                basics = entry.get("basics", {})
                display_name = basics.get("display_name")

            # Fall back to top level (old format)
            if not display_name:
                display_name = entry.get("display_name", vendor_key)
                confidence = entry.get("confidence", 0.0)
                last_seen = entry.get("last_seen", "Never")
                parse_count = entry.get("parse_count", 0)
                confirmed = entry.get("confirmed_by_user", False)

            # Create result entry with all needed fields
            result.append({
                "key": vendor_key,
                "display_name": display_name or vendor_key,
                "last_seen": last_seen,
                "parse_count": parse_count,
                "confidence": confidence,
                "confirmed_by_user": confirmed,
                **entry  # Keep original entry for backward compatibility
            })
        return result


class VendorCacheManagementDialog:
    """Dialog for managing vendor cache entries."""

    def __init__(self, parent, cache_manager: VendorCacheManager):
        """
        Args:
            parent: Parent window
            cache_manager: VendorCacheManager instance
        """
        self.parent = parent
        self.cache_manager = cache_manager

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Vendor Layout Management")
        self.dialog.geometry("1000x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._build_ui()
        self._load_vendors()

    def _build_ui(self):
        """Build the vendor management UI."""
        # Main container
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(
            header_frame,
            text="Vendor Layouts",
            font=("Segoe UI", 16, "bold")
        ).pack(side=tk.LEFT)

        # Buttons
        button_frame = ttk.Frame(header_frame)
        button_frame.pack(side=tk.RIGHT)

        ttk.Button(
            button_frame,
            text="Refresh",
            command=self._load_vendors
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_frame,
            text="Close",
            command=self.dialog.destroy
        ).pack(side=tk.LEFT)

        # Vendor table
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview for vendors
        columns = ("Vendor", "Last Seen", "Parses", "Confidence", "Confirmed", "Actions")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=15
        )

        # Configure columns
        col_widths = [200, 100, 80, 100, 100, 150]
        for col, width in zip(columns, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=tk.CENTER)

        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind double-click to edit
        self.tree.bind("<Double-1>", self._on_edit_vendor)

    def _load_vendors(self):
        """Load vendors into the table."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Load vendors
        vendors = self.cache_manager.get_all_vendors()

        for vendor in vendors:
            vendor_key = vendor["key"]
            display_name = vendor.get("display_name", vendor_key)
            last_seen = vendor.get("last_seen", "Never")
            parse_count = vendor.get("parse_count", 0)
            confidence = vendor.get("confidence", 0.0)
            confirmed = "Yes" if vendor.get("confirmed_by_user", False) else "No"

            # Format confidence as percentage
            confidence_str = f"{confidence * 100:.1f}%"

            # Add to tree
            self.tree.insert(
                "",
                tk.END,
                iid=vendor_key,
                values=(display_name, last_seen, parse_count, confidence_str, confirmed, "Edit | Delete | Reset")
            )

    def _on_edit_vendor(self, event):
        """Handle edit vendor action."""
        selection = self.tree.selection()
        if not selection:
            return

        vendor_key = selection[0]
        entry = self.cache_manager.get_vendor_entry(vendor_key)

        if entry:
            self._open_edit_dialog(vendor_key, entry)

    def _open_edit_dialog(self, vendor_key: str, entry: Dict[str, Any]):
        """Open dialog to edit vendor settings."""
        # This would open the same column assignment panel as in main app
        # For now, just show a message
        messagebox.showinfo(
            "Edit Vendor",
            f"Would open edit dialog for: {entry.get('display_name', vendor_key)}\n"
            f"Column assignments: {len(entry.get('column_assignments', {}))} columns"
        )


class ColumnAssignmentDialog:
    """Dialog for manually assigning column meanings."""

    def __init__(self, parent, raw_text: str, detected_columns: List[Dict],
                 current_assignments: Dict[str, str], quantity_pattern: int,
                 on_save: Callable, on_apply: Callable):
        """
        Args:
            parent: Parent window
            raw_text: Raw text from receipt
            detected_columns: List of column info dicts
            current_assignments: Current column assignments {hebrew_header: field_name}
            quantity_pattern: Detected quantity pattern (1, 2, or 3)
            on_save: Callback when user saves to cache
            on_apply: Callback when user applies once
        """
        self.parent = parent
        self.detected_columns = detected_columns
        self.current_assignments = current_assignments
        self.quantity_pattern = quantity_pattern
        self.on_save = on_save
        self.on_apply = on_apply

        self.column_widgets = []  # Store (Combobox, StringVar) for each column
        self.quantity_var = tk.IntVar(value=quantity_pattern)

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Review Column Layout")
        self.dialog.geometry("900x800")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._build_ui()

    def _build_ui(self):
        """Build the column assignment UI."""
        # Main container with two panes
        main_pane = tk.PanedWindow(self.dialog, orient=tk.HORIZONTAL, sashwidth=5)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left pane: Receipt preview
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, width=400)

        ttk.Label(
            left_frame,
            text="Parsed Receipt Preview",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))

        # Preview text
        preview_text = tk.Text(
            left_frame,
            wrap=tk.WORD,
            height=20,
            font=("Consolas", 9)
        )
        preview_text.pack(fill=tk.BOTH, expand=True)

        # Add first 20 lines of raw text as preview
        preview_text.insert(tk.END, "First 20 lines of raw text:\n\n")
        lines = self.parent.raw_text.split('\n')[:20] if hasattr(self.parent, 'raw_text') else []
        for i, line in enumerate(lines, 1):
            preview_text.insert(tk.END, f"{i:2}: {line}\n")
        preview_text.config(state=tk.DISABLED)

        # Right pane: Column assignment
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, width=500)

        ttk.Label(
            right_frame,
            text="Column Assignment",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))

        # Instructions
        ttk.Label(
            right_frame,
            text="Assign meanings to each detected column:",
            font=("Segoe UI", 9)
        ).pack(anchor=tk.W, pady=(0, 15))

        # Column assignment frame with scrollbar
        canvas_frame = ttk.Frame(right_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add column assignment rows
        for i, col in enumerate(self.detected_columns):
            self._add_column_row(scrollable_frame, i, col)

        # Quantity pattern selection
        self._add_quantity_pattern_section(scrollable_frame)

        # Save buttons
        self._add_action_buttons(right_frame)

    def _add_column_row(self, parent, index: int, column: Dict):
        """Add a row for column assignment."""
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=5)

        # Column header text
        header_text = column.get('hebrew_text', f'Column {index + 1}')
        ttk.Label(
            row_frame,
            text=f"{index + 1}. {header_text[:30]}",
            width=30,
            anchor=tk.W
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Dropdown for assignment
        var = tk.StringVar()
        combobox = ttk.Combobox(
            row_frame,
            textvariable=var,
            values=VendorCacheManager.COLUMN_MEANINGS,
            state="readonly",
            width=25
        )
        combobox.pack(side=tk.LEFT)

        # Set default value if we have a current assignment
        field_name = column.get('assigned_field')
        if field_name:
            meaning = VendorCacheManager.FIELD_TO_MEANING.get(field_name)
            if meaning:
                var.set(meaning)
            else:
                var.set("Ignore this column")
        else:
            var.set("Ignore this column")

        self.column_widgets.append((combobox, var))

    def _add_quantity_pattern_section(self, parent):
        """Add quantity pattern selection section."""
        section_frame = ttk.LabelFrame(parent, text="Quantity Pattern", padding=10)
        section_frame.pack(fill=tk.X, pady=20)

        # Radio buttons for patterns
        patterns = [
            ("Single quantity column", 1),
            ("Two columns — multiply them", 2),
            ("Three columns — third is the result, use it directly", 3)
        ]

        for text, value in patterns:
            rb = ttk.Radiobutton(
                section_frame,
                text=text,
                variable=self.quantity_var,
                value=value
            )
            rb.pack(anchor=tk.W, pady=2)

    def _add_action_buttons(self, parent):
        """Add action buttons at the bottom."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=20)

        ttk.Button(
            button_frame,
            text="Apply once",
            command=self._on_apply_once
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            button_frame,
            text="Save and remember this vendor",
            style="Primary.TButton",
            command=self._on_save_vendor
        ).pack(side=tk.LEFT)

    def _on_apply_once(self):
        """Handle 'Apply once' button click."""
        assignments = self._get_assignments()
        quantity_pattern = self.quantity_var.get()

        if self.on_apply:
            self.on_apply(assignments, quantity_pattern)

        self.dialog.destroy()

    def _on_save_vendor(self):
        """Handle 'Save and remember this vendor' button click."""
        assignments = self._get_assignments()
        quantity_pattern = self.quantity_var.get()

        if self.on_save:
            self.on_save(assignments, quantity_pattern)

        self.dialog.destroy()

    def _get_assignments(self) -> Dict[str, str]:
        """Get column assignments from UI."""
        assignments = {}
        for i, (combobox, var) in enumerate(self.column_widgets):
            if i < len(self.detected_columns):
                header_text = self.detected_columns[i].get('hebrew_text', f'Column {i + 1}')
                meaning = var.get()
                field_name = VendorCacheManager.MEANING_TO_FIELD.get(meaning, "ignore")
                if field_name != "ignore":
                    assignments[header_text] = field_name
        return assignments


if __name__ == "__main__":
    # Test the dialog
    root = tk.Tk()
    root.withdraw()

    # Create mock data
    detected_columns = [
        {"hebrew_text": "תאור", "assigned_field": "description"},
        {"hebrew_text": "ברקוד", "assigned_field": "product_code"},
        {"hebrew_text": "תומכ", "assigned_field": "quantity"},
        {"hebrew_text": "ריחמ", "assigned_field": "unit_price"},
        {"hebrew_text": "נטו", "assigned_field": "line_net_total"},
    ]

    current_assignments = {
        "תאור": "description",
        "ברקוד": "product_code",
        "תומכ": "quantity",
        "ריחמ": "unit_price",
        "נטו": "line_net_total"
    }

    def on_save(assignments, pattern):
        print(f"Save to cache: {assignments}, pattern: {pattern}")

    def on_apply(assignments, pattern):
        print(f"Apply once: {assignments}, pattern: {pattern}")

    dialog = ColumnAssignmentDialog(
        root,
        "Test raw text",
        detected_columns,
        current_assignments,
        3,
        on_save,
        on_apply
    )

    root.wait_window(dialog.dialog)
    root.destroy()