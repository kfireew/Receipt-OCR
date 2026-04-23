"""
Vendor cache manager window.
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# Import theme with fallback
import sys
from pathlib import Path

# Add gui directory to path if not already there
gui_dir = Path(__file__).parent
if str(gui_dir) not in sys.path:
    sys.path.insert(0, str(gui_dir))

try:
    from theme import theme
except ImportError as e:
    print(f"FATAL: Could not import theme in cache_manager_window.py: {e}")
    raise


class CacheManagerWindow:
    """Window for managing vendor cache."""

    def __init__(self, parent):
        self.parent = parent

        # Create window
        self.window = tk.Toplevel(parent)
        self.window.title(f"{theme.EMOJI_CACHE} Vendor Cache Manager")
        self.window.geometry("800x600")
        self.window.minsize(600, 400)
        self.window.transient(parent)
        self.window.grab_set()

        # Configure theme
        theme.configure_styles(self.window)

        # Load cache data
        self.cache_data = self._load_cache_data()

        # Build UI
        self._build_ui()

    def _load_cache_data(self):
        """Load vendor cache data from file."""
        cache_path = Path(__file__).parent.parent / "data" / "vendor_cache.json"
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Check if it's v2 format with "vendors" key
                if isinstance(data, dict) and "vendors" in data:
                    return data["vendors"]
                # Otherwise assume it's v1 format with vendors at root
                return data
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load cache: {e}")
            return {}

    def _normalize_vendor_data(self, vendor_data):
        """Normalize vendor data to handle v1 and v2 formats."""
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

    def _save_cache_data(self):
        """Save vendor cache data to file."""
        cache_path = Path(__file__).parent.parent / "data" / "vendor_cache.json"
        try:
            # Try to preserve v2 format if it existed
            with open(cache_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, dict) and "vendors" in existing_data:
                    # It's v2 format, preserve the structure
                    save_data = existing_data.copy()
                    save_data["vendors"] = self.cache_data
                else:
                    # It's v1 format or corrupted
                    save_data = self.cache_data
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            # If reading fails, just save as v2 format
            save_data = {
                "version": "2.0",
                "vendors": self.cache_data
            }
            try:
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(save_data, f, indent=2, ensure_ascii=False)
                return True
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save cache: {e}")
                return False

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
            text=f"{theme.EMOJI_CACHE} Vendor Cache Manager",
            font=theme.FONT_TITLE
        )
        title_label.pack(anchor=tk.W)

        subtitle_label = theme.create_label(
            header,
            text=f"Manage {len(self.cache_data)} vendor templates",
            font=theme.FONT_SUBTITLE,
            fg=theme.CLR_SUBTEXT
        )
        subtitle_label.pack(anchor=tk.W, pady=(5, 0))

        # Toolbar
        toolbar = theme.create_frame(main)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        # Refresh button
        btn_refresh = theme.create_button(
            toolbar, "Refresh", self._refresh,
            style="secondary"
        )
        btn_refresh.pack(side=tk.LEFT, padx=(0, 10))

        # Add vendor button
        btn_add = theme.create_button(
            toolbar, "Add Vendor", self._add_vendor,
            style="primary", emoji=theme.EMOJI_ADD
        )
        btn_add.pack(side=tk.LEFT, padx=(0, 10))

        # Export button
        btn_export = theme.create_button(
            toolbar, "Export All", self._export_all,
            style="secondary"
        )
        btn_export.pack(side=tk.LEFT, padx=(0, 10))

        # Search frame
        search_frame = theme.create_frame(main)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = theme.create_entry(search_frame, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", self._on_search)

        # Vendor list
        list_frame = theme.create_frame(main)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview for vendor list
        columns = ("vendor", "display_name", "trust_score", "parse_count", "last_used")
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        # Configure columns
        self.tree.heading("vendor", text="Vendor Slug")
        self.tree.heading("display_name", text="Display Name")
        self.tree.heading("trust_score", text="Trust Score")
        self.tree.heading("parse_count", text="Parse Count")
        self.tree.heading("last_used", text="Last Used")

        self.tree.column("vendor", width=150)
        self.tree.column("display_name", width=150)
        self.tree.column("trust_score", width=100)
        self.tree.column("parse_count", width=100)
        self.tree.column("last_used", width=150)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Pack tree and scrollbar
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind double-click to edit
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        # Action buttons frame
        action_frame = theme.create_frame(main)
        action_frame.pack(fill=tk.X, pady=(10, 0))

        # Edit button
        self.btn_edit = theme.create_button(
            action_frame, "Edit", self._edit_selected,
            style="primary"
        )
        self.btn_edit.pack(side=tk.LEFT, padx=(0, 10))

        # Delete button
        self.btn_delete = theme.create_button(
            action_frame, "Delete", self._delete_selected,
            style="secondary"
        )
        self.btn_delete.pack(side=tk.LEFT, padx=(0, 10))

        # View details button
        self.btn_view = theme.create_button(
            action_frame, "View Details", self._view_details,
            style="secondary"
        )
        self.btn_view.pack(side=tk.LEFT, padx=(0, 10))

        # Close button
        btn_close = theme.create_button(
            action_frame, "Close", self._close,
            style="secondary"
        )
        btn_close.pack(side=tk.RIGHT)

        # Load data into tree
        self._load_tree_data()

        # Bind mouse wheel to tree for scrolling
        self._bind_mouse_wheel(self.tree)

    def _load_tree_data(self, search_term=""):
        """Load data into treeview."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Add vendors
        for vendor_slug, vendor_data in self.cache_data.items():
            # Normalize vendor data to handle v1 and v2 formats
            normalized = self._normalize_vendor_data(vendor_data)

            # Apply search filter
            display_name = normalized.get('display_name', '')
            if search_term:
                search_lower = search_term.lower()
                if (search_lower not in vendor_slug.lower() and
                    search_lower not in display_name.lower()):
                    continue

            # Extract data from normalized structure
            trust_score = normalized.get('trust_score', 0.0)
            parse_count = normalized.get('parse_count', 0)
            last_used = normalized.get('last_successful_parse', '')

            # Insert into tree
            self.tree.insert(
                "", tk.END,
                values=(vendor_slug, display_name, f"{trust_score:.2f}",
                       parse_count, last_used),
                tags=(vendor_slug,)
            )

        # Update count label
        count = len(self.tree.get_children())
        self.window.title(f"{theme.EMOJI_CACHE} Vendor Cache Manager ({count} vendors)")

    def _on_search(self, event):
        """Handle search."""
        search_term = self.search_entry.get()
        self._load_tree_data(search_term)

    def _on_tree_double_click(self, event):
        """Handle tree double-click."""
        self._edit_selected()

    def _refresh(self):
        """Refresh cache data."""
        self.cache_data = self._load_cache_data()
        self._load_tree_data()
        messagebox.showinfo("Refreshed", "Cache data refreshed from file.")

    def _add_vendor(self):
        """Add new vendor."""
        from .schema_editor_window import SchemaEditorWindow
        editor = SchemaEditorWindow(self.window)
        # Refresh after editor closes
        self.window.wait_window(editor.window)
        self._refresh()

    def _export_all(self):
        """Export all cache data."""
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Vendor Cache"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
                messagebox.showinfo("Exported", f"Cache exported to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {e}")

    def _get_selected_vendor(self):
        """Get selected vendor slug from tree."""
        selection = self.tree.selection()
        if not selection:
            return None

        item = self.tree.item(selection[0])
        return item['values'][0]  # vendor slug is first column

    def _edit_selected(self):
        """Edit selected vendor."""
        vendor_slug = self._get_selected_vendor()
        if vendor_slug:
            self.edit_vendor(vendor_slug)

    def edit_vendor(self, vendor_slug):
        """Edit specific vendor (public method for external calls)."""
        if vendor_slug not in self.cache_data:
            messagebox.showerror("Error", f"Vendor '{vendor_slug}' not found in cache.")
            return

        # Open schema editor for better editing experience
        from .schema_editor_window import SchemaEditorWindow
        editor = SchemaEditorWindow(self.window, vendor_slug, self.cache_data[vendor_slug])
        # Refresh after editor closes
        self.window.wait_window(editor.window)
        self._refresh()

    def _delete_selected(self):
        """Delete selected vendor."""
        vendor_slug = self._get_selected_vendor()
        if not vendor_slug:
            messagebox.showwarning("No Selection", "Please select a vendor to delete.")
            return

        # Confirm deletion
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Delete vendor '{vendor_slug}'?\nThis action cannot be undone."
        )
        if not confirm:
            return

        # Delete from cache
        if vendor_slug in self.cache_data:
            del self.cache_data[vendor_slug]
            if self._save_cache_data():
                messagebox.showinfo("Deleted", f"Vendor '{vendor_slug}' deleted.")
                self._refresh()
            else:
                messagebox.showerror("Error", "Failed to save cache after deletion.")

    def _view_details(self):
        """View vendor details."""
        vendor_slug = self._get_selected_vendor()
        if not vendor_slug:
            messagebox.showwarning("No Selection", "Please select a vendor to view.")
            return

        if vendor_slug in self.cache_data:
            vendor_data = self.cache_data[vendor_slug]

            # Create details window
            details_window = tk.Toplevel(self.window)
            details_window.title(f"Details: {vendor_slug}")
            details_window.geometry("600x500")
            details_window.transient(self.window)

            # Text widget for displaying JSON
            text_widget = tk.Text(
                details_window,
                wrap=tk.WORD,
                bg=theme.CLR_SURFACE,
                fg=theme.CLR_TEXT,
                font=theme.FONT_MONO,
                padx=10,
                pady=10
            )
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Insert formatted JSON
            text_widget.insert(
                tk.END,
                json.dumps(vendor_data, indent=2, ensure_ascii=False)
            )
            text_widget.config(state=tk.DISABLED)

            # Close button
            btn_close = ttk.Button(
                details_window,
                text="Close",
                command=details_window.destroy
            )
            btn_close.pack(pady=(0, 10))

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

    def _close(self):
        """Close the window."""
        self.window.destroy()