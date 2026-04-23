"""
Improved schema editor window with table-based column editing and better UI.
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime

from .theme import theme


class SchemaEditorWindow:
    """Improved window for adding/editing vendor schemas with table-based editing."""

    def __init__(self, parent, vendor_slug=None, vendor_data=None):
        self.parent = parent
        self.vendor_slug = vendor_slug
        self.is_edit_mode = vendor_slug is not None

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title(f"{theme.EMOJI_ADD} {'Edit' if self.is_edit_mode else 'Add'} Vendor Schema")
        self.window.geometry("800x600")
        self.window.minsize(700, 500)
        self.window.transient(parent)
        self.window.grab_set()

        # Configure theme
        theme.configure_styles(self.window)

        # Normalize vendor data
        self.vendor_data = self._normalize_vendor_data(vendor_data) if vendor_data else {}

        # Column types for dropdown
        self.column_types = [
            "description", "code", "barcode", "price", "quantity",
            "line_total", "unit", "discount", "tax", "vat",
            "date", "invoice_no", "customer_no", "vendor_name"
        ]

        # Build UI
        self._build_ui()

        # Load data if in edit mode
        if self.is_edit_mode:
            self._load_existing_data()

    def _normalize_vendor_data(self, vendor_data):
        """Normalize vendor data to consistent format."""
        if "legacy_fields" in vendor_data:
            legacy = vendor_data.get("legacy_fields", {})
            normalized = legacy.copy()

            if "basics" in vendor_data:
                normalized["display_name"] = vendor_data["basics"].get("display_name", "")

            if "column_assignments" in legacy:
                normalized["column_mapping"] = legacy["column_assignments"]

            return normalized
        return vendor_data

    def _build_ui(self):
        """Build improved UI with tabs and table-based editing."""
        # Main notebook for tabs
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Basic Info Tab
        self.basic_frame = theme.create_frame(self.notebook)
        self.notebook.add(self.basic_frame, text="📝 Basic Info")
        self._build_basic_tab()

        # Column Mapping Tab
        self.columns_frame = theme.create_frame(self.notebook)
        self.notebook.add(self.columns_frame, text="📊 Column Mapping")
        self._build_columns_tab()

        # Validation Rules Tab
        self.validation_frame = theme.create_frame(self.notebook)
        self.notebook.add(self.validation_frame, text="✅ Validation Rules")
        self._build_validation_tab()

        # Action buttons at bottom
        self._build_action_buttons()

    def _build_basic_tab(self):
        """Build basic information tab."""
        content = theme.create_frame(self.basic_frame, padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        # Title
        title = theme.create_label(
            content,
            text=f"{theme.EMOJI_ADD} {'Edit' if self.is_edit_mode else 'Add'} Vendor Schema",
            font=theme.FONT_TITLE
        )
        title.pack(anchor=tk.W, pady=(0, 20))

        # Vendor name (English name - auto-generates slug internally)
        name_frame = theme.create_frame(content)
        name_frame.pack(fill=tk.X, pady=(0, 15))

        name_label_frame = theme.create_frame(name_frame)
        name_label_frame.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(name_label_frame, text="Vendor Name (English):").pack(anchor=tk.W)
        name_desc = theme.create_label(
            name_label_frame,
            text="English vendor name, e.g., 'Globrands'",
            font=theme.FONT_SMALL,
            fg=theme.CLR_SUBTEXT
        )
        name_desc.pack(anchor=tk.W)

        self.entry_name = theme.create_entry(name_frame, width=30)
        self.entry_name.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Trust score
        score_frame = theme.create_frame(content)
        score_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(score_frame, text="Trust Score:").pack(side=tk.LEFT, padx=(0, 10))
        self.trust_score = tk.DoubleVar(value=1.0)
        score_scale = ttk.Scale(
            score_frame,
            from_=0.0,
            to=1.0,
            variable=self.trust_score,
            orient=tk.HORIZONTAL,
            length=200
        )
        score_scale.pack(side=tk.LEFT, padx=(0, 10))
        self.score_label = ttk.Label(score_frame, text="1.0")
        self.score_label.pack(side=tk.LEFT)

        # Update score label when scale changes
        def update_score_label(*args):
            self.score_label.config(text=f"{self.trust_score.get():.2f}")

        self.trust_score.trace("w", update_score_label)

        # User verified checkbox
        self.user_verified = tk.BooleanVar(value=True)
        verified_check = ttk.Checkbutton(
            content,
            text="User Verified Schema",
            variable=self.user_verified
        )
        verified_check.pack(anchor=tk.W, pady=(10, 0))

    def _build_columns_tab(self):
        """Build column mapping tab with table."""
        content = theme.create_frame(self.columns_frame, padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        # Title and instructions
        title = theme.create_label(
            content,
            text="Column Mapping",
            font=theme.FONT_TITLE
        )
        title.pack(anchor=tk.W, pady=(0, 10))

        instructions = theme.create_label(
            content,
            text="Add Hebrew column headers and map them to column types",
            font=theme.FONT_SUBTITLE,
            fg=theme.CLR_SUBTEXT
        )
        instructions.pack(anchor=tk.W, pady=(0, 20))

        # Table for column mappings
        table_frame = theme.create_frame(content)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Create treeview with scrollbar
        columns = ("hebrew", "type", "actions")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=8
        )

        # Define headings
        self.tree.heading("hebrew", text="Hebrew Header")
        self.tree.heading("type", text="Column Type")
        self.tree.heading("actions", text="Actions")

        self.tree.column("hebrew", width=200)
        self.tree.column("type", width=150)
        self.tree.column("actions", width=100)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add/Edit controls
        control_frame = theme.create_frame(content)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(control_frame, text="Hebrew Header:").pack(side=tk.LEFT, padx=(0, 10))
        self.hebrew_entry = theme.create_entry(control_frame, width=20)
        self.hebrew_entry.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(control_frame, text="Type:").pack(side=tk.LEFT, padx=(0, 10))
        self.type_combo = ttk.Combobox(
            control_frame,
            values=self.column_types,
            state="readonly",
            width=15
        )
        self.type_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.type_combo.current(0)  # Select first item

        # Add button
        add_btn = theme.create_button(
            control_frame,
            text="Add Column",
            command=self._add_column_mapping,
            style="secondary",
            emoji="➕"
        )
        add_btn.pack(side=tk.LEFT)

        # Remove selected button
        remove_btn = theme.create_button(
            content,
            text="Remove Selected",
            command=self._remove_selected_column,
            style="secondary",
            emoji="🗑️"
        )
        remove_btn.pack(anchor=tk.W, pady=(5, 0))

    def _build_validation_tab(self):
        """Build validation rules tab."""
        content = theme.create_frame(self.validation_frame, padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        title = theme.create_label(
            content,
            text="Validation Rules",
            font=theme.FONT_TITLE
        )
        title.pack(anchor=tk.W, pady=(0, 20))

        # Quantity calculation method
        calc_frame = theme.create_frame(content)
        calc_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(calc_frame, text="Quantity Calculation:").pack(side=tk.LEFT, padx=(0, 10))
        self.calc_method = tk.StringVar(value="auto")
        calc_combo = ttk.Combobox(
            calc_frame,
            textvariable=self.calc_method,
            values=["auto", "qty × price = total", "total ÷ price = qty", "total ÷ qty = price"],
            state="readonly",
            width=25
        )
        calc_combo.pack(side=tk.LEFT)

        # Add description for quantity calculation
        calc_desc = theme.create_label(
            calc_frame,
            text="How to calculate missing values",
            font=theme.FONT_SMALL,
            fg=theme.CLR_SUBTEXT
        )
        calc_desc.pack(side=tk.LEFT, padx=(10, 0))

        # Tolerance - with better explanation
        tol_frame = theme.create_frame(content)
        tol_frame.pack(fill=tk.X, pady=(0, 15))

        tol_label_frame = theme.create_frame(tol_frame)
        tol_label_frame.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(tol_label_frame, text="Tolerance (%):").pack(anchor=tk.W)
        tol_desc = theme.create_label(
            tol_label_frame,
            text="Allowed difference in calculations",
            font=theme.FONT_SMALL,
            fg=theme.CLR_SUBTEXT
        )
        tol_desc.pack(anchor=tk.W)

        self.tolerance = tk.DoubleVar(value=1.0)
        tol_spin = ttk.Spinbox(
            tol_frame,
            from_=0.0,
            to=20.0,
            increment=0.5,
            textvariable=self.tolerance,
            width=10
        )
        tol_spin.pack(side=tk.LEFT, padx=(0, 10))

        # Example: 1.0% means 1% difference allowed
        tol_example = theme.create_label(
            tol_frame,
            text="e.g., 1.0% = allows small rounding errors",
            font=theme.FONT_SMALL,
            fg=theme.CLR_SUBTEXT
        )
        tol_example.pack(side=tk.LEFT)

        # Skip lines - used in parsing stage to filter non-product lines
        skip_frame = theme.create_frame(content)
        skip_frame.pack(fill=tk.X, pady=(0, 15))

        skip_label_frame = theme.create_frame(skip_frame)
        skip_label_frame.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(skip_label_frame, text="Skip non-product lines:").pack(anchor=tk.W)
        skip_desc = theme.create_label(
            skip_label_frame,
            text="Lines containing these Hebrew phrases are ignored during parsing",
            font=theme.FONT_SMALL,
            fg=theme.CLR_SUBTEXT
        )
        skip_desc.pack(anchor=tk.W)
        skip_explain = theme.create_label(
            skip_label_frame,
            text="Used to filter headers/footers like 'חשבונית מס', 'סה״כ כולל'",
            font=theme.FONT_SMALL,
            fg=theme.CLR_SUBTEXT
        )
        skip_explain.pack(anchor=tk.W)

        self.skip_entry = theme.create_entry(skip_frame, width=30)
        self.skip_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.skip_entry.insert(0, "חשבונית מס,מספר לקוח,תאריך תעודה,סה״כ כולל")

        # Add example button to show common skip phrases
        def show_skip_examples():
            examples = [
                "COMMON NON-PRODUCT LINES TO SKIP:",
                "These appear on receipts but aren't product items:",
                "",
                "HEADERS:",
                "• חשבונית מס - Invoice tax (appears at top)",
                "• מספר לקוח - Customer number",
                "• תאריך תעודה - Document date",
                "• ספק - Supplier/Vendor name",
                "",
                "FOOTERS/TOTALS:",
                "• סה״כ כולל - Total amount (appears at bottom)",
                "• סה״כ לתשלום - Amount to pay",
                "• מע״מ - VAT tax amount",
                "• הנחה - Discount amount",
                "",
                "USAGE: During parsing, lines containing these phrases",
                "are filtered out before extracting product items."
            ]
            messagebox.showinfo("Skip Line Examples", "\n".join(examples))

        example_btn = theme.create_button(
            skip_frame,
            text="📋",
            command=show_skip_examples,
            style="secondary"
        )
        example_btn.pack(side=tk.LEFT, padx=(10, 0))

    def _build_action_buttons(self):
        """Build action buttons at bottom."""
        button_frame = theme.create_frame(self.window, pady=10)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=20)

        save_text = "Save Schema" if self.is_edit_mode else "Add Schema"
        save_emoji = "💾" if self.is_edit_mode else "➕"
        btn_save = theme.create_button(
            button_frame, text=save_text,
            command=self._save, style="primary", emoji=save_emoji
        )
        btn_save.pack(side=tk.LEFT, padx=(0, 10))

        btn_cancel = theme.create_button(
            button_frame, text="Cancel",
            command=self._cancel, style="secondary"
        )
        btn_cancel.pack(side=tk.LEFT)

        # Preview button
        btn_preview = theme.create_button(
            button_frame, text="Preview JSON",
            command=self._preview_json, style="secondary", emoji="👁️"
        )
        btn_preview.pack(side=tk.RIGHT)

    def _add_column_mapping(self):
        """Add a column mapping to the table."""
        hebrew = self.hebrew_entry.get().strip()
        col_type = self.type_combo.get().strip()

        if not hebrew:
            messagebox.showwarning("Missing", "Enter Hebrew header text.")
            return

        if not col_type:
            messagebox.showwarning("Missing", "Select column type.")
            return

        # Add to treeview with action buttons
        item_id = self.tree.insert("", tk.END, values=(hebrew, col_type, "✏️ 🗑️"))

        # Clear entry
        self.hebrew_entry.delete(0, tk.END)

    def _remove_selected_column(self):
        """Remove selected column from table."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Select a column to remove.")
            return

        for item in selection:
            self.tree.delete(item)

    def _load_existing_data(self):
        """Load existing data into form."""
        if not self.vendor_data:
            return

        # Get English vendor name - priority:
        # 1. From merchants_mapping.json (proper casing)
        # 2. From vendor_data['basics']['display_name'] (v2 format)
        # 3. From vendor_data['display_name'] (v1 format)
        english_name = ""

        try:
            import json
            from pathlib import Path

            # First try merchants_mapping.json for proper casing
            mapping_path = Path(__file__).parent.parent / "merchants_mapping.json"
            if mapping_path.exists() and self.vendor_slug:
                with open(mapping_path, "r", encoding="utf-8") as f:
                    mapping = json.load(f)

                # Check if vendor exists in mapping (case-insensitive)
                vendor_slug_lower = self.vendor_slug.lower()
                for slug, names in mapping.items():
                    if slug.lower() == vendor_slug_lower:
                        if isinstance(names, list):
                            # Find English name (non-Hebrew)
                            for name in names:
                                if name and not any('\u0590' <= c <= '\u05FF' for c in str(name)):
                                    english_name = name
                                    break
                        break

            # If not found in mapping, try cache structure
            if not english_name:
                # Check v2 format: vendor_data['basics']['display_name']
                if 'basics' in self.vendor_data:
                    basics = self.vendor_data['basics']
                    if isinstance(basics, dict) and 'display_name' in basics:
                        english_name = basics['display_name']
                # Check v1 format: vendor_data['display_name']
                elif 'display_name' in self.vendor_data:
                    english_name = self.vendor_data['display_name']

        except Exception as e:
            print(f"Error loading vendor name: {e}")
            # Last resort fallback
            english_name = self.vendor_data.get('display_name', '')

        # Set vendor name (should be English)
        if english_name:
            self.entry_name.insert(0, english_name)

        # Set trust score
        self.trust_score.set(self.vendor_data.get('trust_score', 1.0))

        # Set user verified
        self.user_verified.set(self.vendor_data.get('user_verified', True))

        # Load column mappings
        column_mapping = self.vendor_data.get('column_mapping', {})
        for hebrew, col_type in column_mapping.items():
            self.tree.insert("", tk.END, values=(hebrew, col_type, "✏️ 🗑️"))

        # Load validation rules
        validation = self.vendor_data.get('validation_rules', {})
        if validation:
            self.tolerance.set(validation.get('tolerance_percent', 1.0))
            self.calc_method.set(validation.get('quantity_calculation', 'auto'))

        parsing = self.vendor_data.get('parsing_rules', {})
        if parsing:
            if 'skip_lines' in parsing:
                skip_text = ",".join(parsing['skip_lines'])
                self.skip_entry.delete(0, tk.END)
                self.skip_entry.insert(0, skip_text)

    def _save(self):
        """Save vendor schema."""
        display_name = self.entry_name.get().strip()

        if not display_name:
            messagebox.showerror("Error", "Vendor name is required.")
            return

        # Auto-generate slug from display name
        vendor_slug = display_name.lower().replace(" ", "_").replace("/", "_").replace("\\", "_")

        # Get column mappings from treeview
        column_mapping = {}
        for child in self.tree.get_children():
            values = self.tree.item(child)['values']
            hebrew = values[0]
            col_type = values[1]
            column_mapping[hebrew] = col_type

        if not column_mapping:
            messagebox.showerror("Error", "At least one column mapping is required.")
            return

        # Get validation rules
        skip_lines = [s.strip() for s in self.skip_entry.get().split(",") if s.strip()]

        # Build comprehensive vendor data
        vendor_data = {
            'display_name': display_name,
            'column_mapping': column_mapping,
            'trust_score': float(self.trust_score.get()),
            'user_verified': bool(self.user_verified.get()),
            'parse_count': self.vendor_data.get('parse_count', 0),
            'validation_rules': {
                'quantity_calculation': self.calc_method.get(),
                'tolerance_percent': float(self.tolerance.get()),
                'auto_validate': True
            },
            'parsing_rules': {
                'document_type': 'receipt',  # Always receipt for Receipt OCR
                'skip_lines': skip_lines,
                'item_separator': 'multi_line',
                'numeric_format': 'decimal_dot'
            },
            'last_modified': datetime.now().strftime("%Y-%m-%d")
        }

        # Save to cache
        cache_path = Path(__file__).parent.parent / "data" / "vendor_cache.json"
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except:
            cache = {}

        # Handle v2 format if present
        if isinstance(cache, dict) and "vendors" in cache:
            if "vendors" not in cache:
                cache["vendors"] = {}
            cache["vendors"][vendor_slug] = {
                "basics": {
                    "display_name": display_name,
                    "user_created": True,
                    "creation_date": datetime.now().strftime("%Y-%m-%d"),
                    "last_modified": datetime.now().strftime("%Y-%m-%d"),
                    "document_type": "receipt"  # Always receipt for Receipt OCR
                },
                "confidence": {
                    "trust_score": float(self.trust_score.get()),
                    "user_verified": bool(self.user_verified.get()),
                    "verification_date": datetime.now().strftime("%Y-%m-%d")
                },
                "legacy_fields": vendor_data
            }
        else:
            cache[vendor_slug] = vendor_data

        # Save
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Success", f"Schema for '{vendor_slug}' saved successfully!")
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Save failed: {e}")

    def _preview_json(self):
        """Preview the JSON that will be saved."""
        display_name = self.entry_name.get().strip() or "Example Vendor"
        # Auto-generate slug like in _save method
        vendor_slug = display_name.lower().replace(" ", "_").replace("/", "_").replace("\\", "_")

        # Get column mappings
        column_mapping = {}
        for child in self.tree.get_children():
            values = self.tree.item(child)['values']
            column_mapping[values[0]] = values[1]

        # Build preview data
        preview_data = {
            vendor_slug: {
                'display_name': display_name,
                'column_mapping': column_mapping,
                'trust_score': float(self.trust_score.get()),
                'user_verified': bool(self.user_verified.get()),
                'validation_rules': {
                    'tolerance_percent': float(self.tolerance.get()),
                    'auto_validate': True
                }
            }
        }

        # Show in messagebox
        preview_text = json.dumps(preview_data, indent=2, ensure_ascii=False)
        if len(preview_text) > 1000:
            preview_text = preview_text[:1000] + "\n... (truncated)"

        messagebox.showinfo("Preview", preview_text)

    def _cancel(self):
        """Cancel editing."""
        self.window.destroy()