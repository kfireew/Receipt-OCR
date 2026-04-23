"""
Simple vendor editor window for cache manager.
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from .theme import theme


class VendorEditorWindow:
    """Simple window for editing vendor cache entries."""

    def __init__(self, parent, vendor_slug, vendor_data):
        self.parent = parent
        self.vendor_slug = vendor_slug

        # Handle different vendor data formats (v1 vs v2)
        self.vendor_data = self._normalize_vendor_data(vendor_data.copy())

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title(f"Edit Vendor: {vendor_slug}")
        self.window.geometry("600x500")
        self.window.minsize(500, 400)
        self.window.transient(parent)
        self.window.grab_set()

        # Configure theme
        theme.configure_styles(self.window)

        # Build UI
        self._build_ui()

    def _normalize_vendor_data(self, vendor_data):
        """Normalize vendor data to consistent format (handle v1 and v2 formats)."""
        # Check if it's v2 format with nested structure
        if "legacy_fields" in vendor_data:
            # It's v2 format, extract legacy fields
            legacy = vendor_data.get("legacy_fields", {})
            normalized = legacy.copy()

            # Add basics from v2 if available
            if "basics" in vendor_data:
                basics = vendor_data["basics"]
                normalized["display_name"] = basics.get("display_name", legacy.get("display_name", ""))

            # Add confidence from v2 if available
            if "confidence" in vendor_data:
                confidence = vendor_data["confidence"]
                normalized["trust_score"] = confidence.get("trust_score", legacy.get("confidence", 0.5))
                normalized["user_verified"] = confidence.get("user_verified", legacy.get("confirmed_by_user", False))

            # Add parse_count from usage_stats if available
            if "usage_stats" in vendor_data:
                usage = vendor_data["usage_stats"]
                normalized["parse_count"] = usage.get("total_parses", legacy.get("parse_count", 0))
                normalized["validation_rate"] = usage.get("validation_rate", 0.0)
                normalized["last_successful_parse"] = usage.get("last_used", legacy.get("last_seen", ""))

            # Add column_mapping from legacy_fields or column_assignments
            if "column_assignments" in legacy:
                normalized["column_mapping"] = legacy["column_assignments"]

            return normalized
        else:
            # It's v1 format or already normalized
            return vendor_data

    def _build_ui(self):
        """Build the UI."""
        # Main container with scrollbar
        main_frame = tk.Frame(self.window, bg=theme.CLR_BG)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas and scrollbar
        canvas = tk.Canvas(main_frame, bg=theme.CLR_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=theme.CLR_BG)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mouse wheel to scroll the canvas
        self._bind_mouse_wheel(canvas)
        self._bind_mouse_wheel(scrollable_frame)

        # Content
        content = theme.create_frame(scrollable_frame, padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        # Header
        header = theme.create_frame(content)
        header.pack(fill=tk.X, pady=(0, 20))

        title_label = theme.create_label(
            header,
            text=f"Edit Vendor: {self.vendor_slug}",
            font=theme.FONT_TITLE
        )
        title_label.pack(anchor=tk.W)

        # Basic Info
        info_frame = theme.create_frame(content)
        info_frame.pack(fill=tk.X, pady=(0, 20))

        info_label = theme.create_label(
            info_frame,
            text="Basic Information",
            font=("Arial", 12, "bold")
        )
        info_label.pack(anchor=tk.W, pady=(0, 10))

        # Display Name
        name_frame = theme.create_frame(info_frame)
        name_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(name_frame, text="Display Name:").pack(side=tk.LEFT, padx=(0, 10))
        self.display_name_var = tk.StringVar(value=self.vendor_data.get('display_name', ''))
        display_name_entry = tk.Entry(name_frame, textvariable=self.display_name_var, width=30)
        display_name_entry.pack(side=tk.LEFT)

        # Trust Score
        score_frame = theme.create_frame(info_frame)
        score_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(score_frame, text="Trust Score:").pack(side=tk.LEFT, padx=(0, 10))
        self.trust_score_var = tk.DoubleVar(value=self.vendor_data.get('trust_score', 0.5))
        score_scale = ttk.Scale(
            score_frame,
            from_=0.0,
            to=1.0,
            variable=self.trust_score_var,
            orient=tk.HORIZONTAL,
            length=200
        )
        score_scale.pack(side=tk.LEFT, padx=(0, 10))

        score_label = ttk.Label(score_frame, text=f"{self.trust_score_var.get():.2f}")
        score_label.pack(side=tk.LEFT)

        # Update score label when scale changes
        def update_score_label(*args):
            score_label.config(text=f"{self.trust_score_var.get():.2f}")

        self.trust_score_var.trace("w", update_score_label)

        # Parse Count
        count_frame = theme.create_frame(info_frame)
        count_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(count_frame, text="Parse Count:").pack(side=tk.LEFT, padx=(0, 10))
        self.parse_count_var = tk.IntVar(value=self.vendor_data.get('parse_count', 0))
        count_spinbox = ttk.Spinbox(
            count_frame,
            from_=0,
            to=1000,
            textvariable=self.parse_count_var,
            width=10
        )
        count_spinbox.pack(side=tk.LEFT)

        # User Verified
        verified_frame = theme.create_frame(info_frame)
        verified_frame.pack(fill=tk.X, pady=(0, 10))

        self.user_verified_var = tk.BooleanVar(value=self.vendor_data.get('user_verified', False))
        verified_check = ttk.Checkbutton(
            verified_frame,
            text="User Verified",
            variable=self.user_verified_var
        )
        verified_check.pack(anchor=tk.W)

        # Column Mappings Display
        columns_frame = theme.create_frame(content)
        columns_frame.pack(fill=tk.X, pady=(0, 20))

        columns_label = theme.create_label(
            columns_frame,
            text="Column Mappings (Read-only)",
            font=("Arial", 12, "bold")
        )
        columns_label.pack(anchor=tk.W, pady=(0, 10))

        # Text widget for column mappings
        column_mappings = self.vendor_data.get('column_mapping', {})
        columns_text = tk.Text(
            columns_frame,
            height=8,
            wrap=tk.WORD,
            bg=theme.CLR_SURFACE,
            fg=theme.CLR_TEXT,
            font=theme.FONT_MONO,
            relief=tk.FLAT
        )
        columns_text.pack(fill=tk.X)

        # Format and insert column mappings
        if column_mappings:
            formatted = []
            for hebrew, col_type in column_mappings.items():
                formatted.append(f"{hebrew} → {col_type}")
            columns_text.insert(tk.END, "\n".join(formatted))
        else:
            columns_text.insert(tk.END, "No column mappings")

        columns_text.config(state=tk.DISABLED)

        # Stats Display
        stats_frame = theme.create_frame(content)
        stats_frame.pack(fill=tk.X, pady=(0, 20))

        stats_label = theme.create_label(
            stats_frame,
            text="Statistics",
            font=("Arial", 12, "bold")
        )
        stats_label.pack(anchor=tk.W, pady=(0, 10))

        # Stats text widget
        stats_text = tk.Text(
            stats_frame,
            height=6,
            wrap=tk.WORD,
            bg=theme.CLR_SURFACE,
            fg=theme.CLR_TEXT,
            font=theme.FONT_MONO,
            relief=tk.FLAT
        )
        stats_text.pack(fill=tk.X)

        # Format and insert stats
        stats_info = [
            f"Quantity Pattern: {self.vendor_data.get('quantity_pattern', 1)}",
            f"Row Format: {self.vendor_data.get('row_format', 'single_line')}",
            f"Validation Rate: {self.vendor_data.get('validation_rate', 0.0):.2f}",
            f"Last Successful Parse: {self.vendor_data.get('last_successful_parse', 'Never')}",
            f"Verification Date: {self.vendor_data.get('verification_date', 'Never')}"
        ]
        stats_text.insert(tk.END, "\n".join(stats_info))
        stats_text.config(state=tk.DISABLED)

        # Action buttons
        buttons_frame = theme.create_frame(content)
        buttons_frame.pack(fill=tk.X, pady=(20, 0))

        # Save button
        btn_save = theme.create_button(
            buttons_frame, "Save Changes", self._save,
            style="primary", emoji="💾"
        )
        btn_save.pack(side=tk.LEFT, padx=(0, 10))

        # Cancel button
        btn_cancel = theme.create_button(
            buttons_frame, "Cancel", self._cancel,
            style="secondary"
        )
        btn_cancel.pack(side=tk.LEFT)

        # Delete button
        btn_delete = theme.create_button(
            buttons_frame, "Delete Vendor", self._delete,
            style="secondary"
        )
        btn_delete.pack(side=tk.RIGHT)

    def _save(self):
        """Save changes to vendor."""
        # Update normalized vendor data
        self.vendor_data['display_name'] = self.display_name_var.get()
        self.vendor_data['trust_score'] = self.trust_score_var.get()
        self.vendor_data['parse_count'] = self.parse_count_var.get()
        self.vendor_data['user_verified'] = self.user_verified_var.get()

        # Load cache
        cache_path = Path(__file__).parent.parent / "data" / "vendor_cache.json"
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load cache: {e}")
            return

        # Check if it's v2 format
        is_v2_format = isinstance(cache_data, dict) and "vendors" in cache_data

        if is_v2_format:
            # Update v2 format - need to update nested structure
            if self.vendor_slug not in cache_data["vendors"]:
                messagebox.showerror("Error", f"Vendor '{self.vendor_slug}' not found in v2 cache.")
                return

            # Update legacy fields in v2 structure
            vendor_entry = cache_data["vendors"][self.vendor_slug]

            # Update basics if exists
            if "basics" in vendor_entry:
                vendor_entry["basics"]["display_name"] = self.display_name_var.get()

            # Update confidence if exists
            if "confidence" in vendor_entry:
                vendor_entry["confidence"]["trust_score"] = self.trust_score_var.get()
                vendor_entry["confidence"]["user_verified"] = self.user_verified_var.get()

            # Update usage_stats if exists
            if "usage_stats" in vendor_entry:
                vendor_entry["usage_stats"]["total_parses"] = self.parse_count_var.get()

            # Always update legacy_fields
            if "legacy_fields" not in vendor_entry:
                vendor_entry["legacy_fields"] = {}

            vendor_entry["legacy_fields"]["display_name"] = self.display_name_var.get()
            vendor_entry["legacy_fields"]["parse_count"] = self.parse_count_var.get()
            vendor_entry["legacy_fields"]["confirmed_by_user"] = self.user_verified_var.get()
            vendor_entry["legacy_fields"]["confidence"] = self.trust_score_var.get()
        else:
            # v1 format - direct update
            cache_data[self.vendor_slug] = self.vendor_data

        # Save cache
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save cache: {e}")
            return

        messagebox.showinfo("Saved", f"Vendor '{self.vendor_slug}' updated successfully.")
        self.window.destroy()

    def _cancel(self):
        """Cancel editing."""
        self.window.destroy()

    def _delete(self):
        """Delete vendor."""
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete vendor '{self.vendor_slug}'?\n"
            "This action cannot be undone."
        )

        if confirm:
            # Load cache
            cache_path = Path(__file__).parent.parent / "data" / "vendor_cache.json"
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load cache: {e}")
                return

            # Delete from cache
            if self.vendor_slug in cache_data:
                del cache_data[self.vendor_slug]

                # Save cache
                try:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(cache_data, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save cache: {e}")
                    return

                messagebox.showinfo("Deleted", f"Vendor '{self.vendor_slug}' deleted successfully.")
                self.window.destroy()
            else:
                messagebox.showerror("Error", f"Vendor '{self.vendor_slug}' not found in cache.")

    def _bind_mouse_wheel(self, widget):
        """Bind mouse wheel to a widget for scrolling."""
        def _on_mouse_wheel(event):
            # Windows and Mac: event.delta
            # Linux: event.num (4=up, 5=down)
            if event.num == 4:  # Linux scroll up
                widget.yview_scroll(-1, "units")
            elif event.num == 5:  # Linux scroll down
                widget.yview_scroll(1, "units")
            elif hasattr(event, 'delta'):
                # Windows/Mac: negative delta = scroll down, positive = scroll up
                # Standardize: scroll down = move down in content
                if event.delta > 0:
                    widget.yview_scroll(-1, "units")
                else:
                    widget.yview_scroll(1, "units")
            return "break"

        # Bind to the widget
        widget.bind("<MouseWheel>", _on_mouse_wheel)
        widget.bind("<Button-4>", _on_mouse_wheel)  # Linux scroll up
        widget.bind("<Button-5>", _on_mouse_wheel)  # Linux scroll down