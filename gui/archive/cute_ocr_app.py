#!/usr/bin/env python3
"""
CUTE OCR APP

Updated OCR GUI with:
1. Cute, simple theme like super_simple_cache_editor
2. Links to new cache editor when confidence is low
3. Shows cache status clearly
"""

import json
import os
import sys
import shutil
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, font as tkfont
from tkinter import ttk

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()


try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

# Translation for Hebrew keywords
try:
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except ImportError:
    HAS_TRANSLATOR = False


class CuteReceiptOCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🧾 Receipt OCR")
        self.root.geometry("900x750")
        self.root.minsize(700, 500)

        # Cute theme colors
        self._CLR_BG = '#f0f8ff'  # Alice blue
        self._CLR_SURFACE = '#ffffff'
        self._CLR_ACCENT = '#3498db'  # Nice blue
        self._CLR_SUCCESS = '#2ecc71'  # Green
        self._CLR_WARNING = '#f39c12'  # Orange
        self._CLR_ERROR = '#e74c3c'  # Red
        self._CLR_TEXT = '#2c3e50'  # Dark blue
        self._CLR_SUBTEXT = '#7f8c8d'  # Gray

        self.root.configure(bg=self._CLR_BG)

        # Vendor cache state
        self.last_vendor_info = None
        self.last_column_info = None
        self.last_quantity_pattern = None
        self.last_raw_text = None

        self.last_result = None
        self.last_input_path = None
        self.is_processing = False

        self._build_ui()

    def _build_ui(self):
        """Build cute UI."""
        # Main container
        main = tk.Frame(self.root, bg=self._CLR_BG, padx=20, pady=20)
        main.pack(fill=tk.BOTH, expand=True)

        # Header with emoji
        header = tk.Frame(main, bg=self._CLR_BG)
        header.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            header,
            text="🧾 Receipt OCR",
            font=("Arial", 24, "bold"),
            bg=self._CLR_BG,
            fg=self._CLR_TEXT
        ).pack()

        tk.Label(
            header,
            text="Upload receipt to extract data",
            font=("Arial", 12),
            bg=self._CLR_BG,
            fg=self._CLR_SUBTEXT
        ).pack(pady=(5, 0))

        # Upload area
        upload_frame = tk.LabelFrame(
            main,
            text="📁 Upload Receipt",
            font=("Arial", 13, "bold"),
            bg=self._CLR_BG,
            fg=self._CLR_TEXT,
            padx=20,
            pady=20
        )
        upload_frame.pack(fill=tk.X, pady=(0, 20))

        # Upload button (cute style)
        self.btn_upload = tk.Button(
            upload_frame,
            text="📄 Choose File",
            command=self.do_upload,
            font=("Arial", 11),
            bg=self._CLR_ACCENT,
            fg="white",
            padx=20,
            pady=10,
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.btn_upload.pack()

        # File label
        self.file_label = tk.Label(
            upload_frame,
            text="No file selected",
            font=("Arial", 10),
            bg=self._CLR_BG,
            fg=self._CLR_SUBTEXT
        )
        self.file_label.pack(pady=(10, 0))

        # Cache status area
        cache_frame = tk.LabelFrame(
            main,
            text="💾 Cache Status",
            font=("Arial", 13, "bold"),
            bg=self._CLR_BG,
            fg=self._CLR_TEXT,
            padx=20,
            pady=20
        )
        cache_frame.pack(fill=tk.X, pady=(0, 20))

        self.cache_status_label = tk.Label(
            cache_frame,
            text="Ready to process...",
            font=("Arial", 10),
            bg=self._CLR_BG,
            fg=self._CLR_SUBTEXT
        )
        self.cache_status_label.pack(anchor=tk.W)

        self.cache_details_label = tk.Label(
            cache_frame,
            text="",
            font=("Arial", 9),
            bg=self._CLR_BG,
            fg=self._CLR_SUBTEXT
        )
        self.cache_details_label.pack(anchor=tk.W, pady=(2, 0))

        # Edit cache button (initially hidden)
        self.edit_cache_btn = tk.Button(
            cache_frame,
            text="✏️ Edit Vendor Cache",
            command=self._open_simple_cache_editor,
            font=("Arial", 10),
            bg=self._CLR_WARNING,
            fg="white",
            padx=15,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.edit_cache_btn.pack(pady=(10, 0))
        self.edit_cache_btn.pack_forget()  # Hide initially

        # Processing area
        process_frame = tk.Frame(main, bg=self._CLR_BG)
        process_frame.pack(fill=tk.X, pady=(0, 20))

        # Process button
        self.btn_process = tk.Button(
            process_frame,
            text="🚀 Process Receipt",
            command=self.do_process,
            font=("Arial", 12, "bold"),
            bg=self._CLR_SUCCESS,
            fg="white",
            padx=25,
            pady=12,
            relief=tk.FLAT,
            cursor="hand2",
            state=tk.DISABLED
        )
        self.btn_process.pack()

        # Processing indicator (hidden initially)
        self.processing_label = tk.Label(
            process_frame,
            text="",
            font=("Arial", 10),
            bg=self._CLR_BG,
            fg=self._CLR_SUBTEXT
        )
        self.processing_label.pack(pady=(10, 0))

        # Results area
        results_frame = tk.LabelFrame(
            main,
            text="📊 Results",
            font=("Arial", 13, "bold"),
            bg=self._CLR_BG,
            fg=self._CLR_TEXT,
            padx=20,
            pady=20
        )
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Text widget for results
        self.result_text = tk.Text(
            results_frame,
            wrap=tk.WORD,
            font=("Courier New", 9),
            height=15,
            bg=self._CLR_SURFACE,
            fg=self._CLR_TEXT,
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.result_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.result_text.yview)

        # Status bar at bottom
        self.status_label = tk.Label(
            main,
            text="Ready",
            font=("Arial", 9),
            bg=self._CLR_BG,
            fg=self._CLR_SUBTEXT
        )
        self.status_label.pack(pady=(10, 0))

        # Configure button hover effects
        self._configure_button_styles()

    def _configure_button_styles(self):
        """Configure button hover effects."""
        def on_enter(e, color):
            e.widget['background'] = self._darken_color(color)

        def on_leave(e, color):
            e.widget['background'] = color

        # Upload button
        self.btn_upload.bind("<Enter>", lambda e: on_enter(e, self._CLR_ACCENT))
        self.btn_upload.bind("<Leave>", lambda e: on_leave(e, self._CLR_ACCENT))

        # Process button
        self.btn_process.bind("<Enter>", lambda e: on_enter(e, self._CLR_SUCCESS))
        self.btn_process.bind("<Leave>", lambda e: on_leave(e, self._CLR_SUCCESS))

        # Edit cache button
        self.edit_cache_btn.bind("<Enter>", lambda e: on_enter(e, self._CLR_WARNING))
        self.edit_cache_btn.bind("<Leave>", lambda e: on_leave(e, self._CLR_WARNING))

    def _darken_color(self, color):
        """Darken a hex color for hover effect."""
        # Simple darkening - you could implement proper color manipulation
        if color == self._CLR_ACCENT:
            return '#2980b9'
        elif color == self._CLR_SUCCESS:
            return '#27ae60'
        elif color == self._CLR_WARNING:
            return '#d68910'
        return color

    def _log(self, message):
        """Log message to status and result text."""
        self.status_label.config(text=message)
        print(message)

    def do_upload(self):
        """Handle file upload."""
        file_path = filedialog.askopenfilename(
            title="Select receipt",
            filetypes=[("PDF files", "*.pdf"), ("Image files", "*.jpg *.jpeg *.png"), ("All files", "*.*")]
        )

        if file_path:
            self.last_input_path = file_path
            filename = os.path.basename(file_path)
            self.file_label.config(text=f"📄 {filename}")
            self.btn_process.config(state=tk.NORMAL)
            self._log(f"Selected: {filename}")

            # Clear previous results
            self.result_text.delete(1.0, tk.END)
            self.cache_status_label.config(text="Ready to process...")
            self.cache_details_label.config(text="")
            self.edit_cache_btn.pack_forget()

    def do_process(self):
        """Process the receipt."""
        if not self.last_input_path or not os.path.exists(self.last_input_path):
            messagebox.showerror("Error", "No file selected or file doesn't exist")
            return

        # Disable button and show processing
        self.btn_process.config(state=tk.DISABLED)
        self.processing_label.config(text="⏳ Processing...")
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "Processing receipt...\n\n")

        # Reset cache state
        self.last_vendor_info = None
        self.last_column_info = None

        # Run in thread to keep UI responsive
        thread = threading.Thread(target=self._process_thread)
        thread.daemon = True
        thread.start()

    def _process_thread(self):
        """Thread for processing receipt."""
        try:
            # Use the updated pipeline with cache
            from pipelines.mindee_pipeline import process_receipt

            result = process_receipt(self.last_input_path)
            self.last_result = result

            # Try to extract vendor info from pipeline output
            # (The pipeline should ideally return this in metadata)
            vendor_info = result.get('metadata', {}).get('vendor_info', {})
            column_info = result.get('metadata', {}).get('column_info', {})

            # Update UI in main thread
            self.root.after(0, lambda: self._show_results(result, vendor_info, column_info))

        except Exception as e:
            self.root.after(0, lambda: self._show_error(str(e)))

    def _show_results(self, result, vendor_info, column_info):
        """Show processing results."""
        self.btn_process.config(state=tk.NORMAL)
        self.processing_label.config(text="")

        # Clear and show results
        self.result_text.delete(1.0, tk.END)

        # Extract basic info from GDocument
        gdoc = result.get("GDocument", {})

        # Show vendor and date
        vendor = ""
        date = ""
        for f in gdoc.get("fields", []):
            if f.get("name") == "VendorName":
                vendor = f.get("value", "")
            elif f.get("name") == "Date":
                date = f.get("value", "")

        self.result_text.insert(tk.END, f"📋 Receipt Details:\n")
        self.result_text.insert(tk.END, f"  Vendor: {vendor or 'Unknown'}\n")
        self.result_text.insert(tk.END, f"  Date: {date or 'Unknown'}\n\n")

        # Show items
        groups = gdoc.get("groups", [])
        if groups:
            items_group = groups[0] if groups else {}
            items = items_group.get("groups", [])

            self.result_text.insert(tk.END, f"🛒 Items ({len(items)}):\n")
            for i, item in enumerate(items[:10]):  # Show first 10
                fields = item.get("fields", [])
                desc = ""
                price = ""
                qty = ""
                for f in fields:
                    if f.get("name") == "Description":
                        desc = f.get("value", "")
                    elif f.get("name") == "Price":
                        price = f.get("value", "")
                    elif f.get("name") == "Quantity":
                        qty = f.get("value", "")

                self.result_text.insert(tk.END, f"  {i+1}. {desc[:30]}...")
                if qty:
                    self.result_text.insert(tk.END, f" x{qty}")
                if price:
                    self.result_text.insert(tk.END, f" - {price}₪")
                self.result_text.insert(tk.END, "\n")

            if len(items) > 10:
                self.result_text.insert(tk.END, f"  ... and {len(items) - 10} more items\n")

        # Update cache status
        self._update_cache_status(vendor_info, column_info)

        self._log(f"✅ Processed successfully")

    def _update_cache_status(self, vendor_info, column_info):
        """Update cache status display."""
        if vendor_info:
            vendor_name = vendor_info.get('vendor_name', '')
            confidence = vendor_info.get('confidence', 0)
            cache_used = vendor_info.get('cache_used', False)

            if vendor_name:
                if cache_used:
                    self.cache_status_label.config(
                        text=f"✅ Using cached layout for: {vendor_name}",
                        fg=self._CLR_SUCCESS
                    )
                    self.cache_details_label.config(
                        text=f"Confidence: {confidence:.2f} (cache hit)"
                    )
                else:
                    self.cache_status_label.config(
                        text=f"⚠️  New vendor detected: {vendor_name}",
                        fg=self._CLR_WARNING
                    )
                    self.cache_details_label.config(
                        text=f"Confidence: {confidence:.2f} (no cache)"
                    )

                    # Show edit button for low confidence or new vendor
                    if confidence < 0.8:
                        self.edit_cache_btn.pack(pady=(10, 0))
                        self.edit_cache_btn.config(
                            text=f"✏️ Improve cache for {vendor_name}"
                        )
            else:
                self.cache_status_label.config(
                    text="❌ No vendor detected",
                    fg=self._CLR_ERROR
                )
        else:
            self.cache_status_label.config(
                text="ℹ️  No vendor info available",
                fg=self._CLR_SUBTEXT
            )

    def _show_error(self, error_msg):
        """Show error message."""
        self.btn_process.config(state=tk.NORMAL)
        self.processing_label.config(text="")

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"❌ Error:\n{error_msg}")

        self.cache_status_label.config(
            text="❌ Processing failed",
            fg=self._CLR_ERROR
        )
        self.cache_details_label.config(text="")

        self._log(f"❌ Error: {error_msg}")

    def _open_simple_cache_editor(self):
        """Open the simple cache editor."""
        try:
            from gui.super_simple_cache_editor import SuperSimpleCacheEditor

            # Open in new window
            editor_window = tk.Toplevel(self.root)
            editor_window.title("✏️ Cache Editor")
            editor_window.geometry("500x600")

            app = SuperSimpleCacheEditor(editor_window)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open cache editor: {e}")

    def do_manage_vendor_cache(self):
        """Open vendor cache management - using new simple editor."""
        self._open_simple_cache_editor()

    def do_add_vendor(self):
        """Open dialog to add a new vendor."""
        # Simple version of add vendor
        dialog = tk.Toplevel(self.root)
        dialog.title("➕ Add Vendor")
        dialog.geometry("400x300")
        dialog.configure(bg=self._CLR_BG)

        main = tk.Frame(dialog, bg=self._CLR_BG, padx=20, pady=20)
        main.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            main,
            text="Add New Vendor",
            font=("Arial", 16, "bold"),
            bg=self._CLR_BG,
            fg=self._CLR_TEXT
        ).pack(pady=(0, 20))

        tk.Label(
            main,
            text="Vendor Name:",
            font=("Arial", 11),
            bg=self._CLR_BG
        ).pack(anchor=tk.W, pady=(0, 5))

        name_entry = tk.Entry(
            main,
            font=("Arial", 11),
            width=30
        )
        name_entry.pack(pady=(0, 20))

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Missing Name", "Enter vendor name")
                return

            # Load merchants mapping
            mapping_path = PROJECT_ROOT / "merchants_mapping.json"
            if mapping_path.exists():
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    merchants = json.load(f)
            else:
                merchants = {}

            # Add vendor with its name as keyword
            merchants[name] = [name]

            # Save
            with open(mapping_path, 'w', encoding='utf-8') as f:
                json.dump(merchants, f, ensure_ascii=False, indent=2)

            messagebox.showinfo("Saved", f"Added vendor: {name}")
            dialog.destroy()
            self._log(f"➕ Added vendor: {name}")

        # Buttons
        btn_frame = tk.Frame(main, bg=self._CLR_BG)
        btn_frame.pack(pady=(20, 0))

        tk.Button(
            btn_frame,
            text="Cancel",
            command=dialog.destroy,
            font=("Arial", 10),
            bg=self._CLR_SUBTEXT,
            fg="white",
            padx=15,
            pady=5,
            relief=tk.FLAT
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            btn_frame,
            text="Save",
            command=save,
            font=("Arial", 10, "bold"),
            bg=self._CLR_SUCCESS,
            fg="white",
            padx=20,
            pady=5,
            relief=tk.FLAT
        ).pack(side=tk.LEFT)


def main():
    """Run the cute OCR app."""
    root = tk.Tk()
    app = CuteReceiptOCRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()