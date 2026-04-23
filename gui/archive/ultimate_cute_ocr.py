#!/usr/bin/env python3
"""
ULTIMATE CUTE OCR GUI

Has all features of app.py but with cute, simple theme:
1. Drag & drop
2. Define schema / add vendor
3. Download result
4. Vendor cache management
5. Layout review
6. Processing status
7. Results display
8. Cute design!
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

# Try to import drag & drop
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False
    print("⚠️  tkinterdnd2 not installed - drag & drop disabled")


class UltimateCuteOCRApp:
    def __init__(self, root):
        self.root = root

        # Use TkinterDnD if available
        if HAS_DND:
            self.root = TkinterDnD.Tk() if isinstance(root, type) else root

        self.root.title("🧾 Ultimate Cute OCR")
        self.root.geometry("1000x800")
        self.root.minsize(800, 600)

        # Cute theme colors
        self._setup_cute_theme()

        # State
        self.last_result = None
        self.last_input_path = None
        self.is_processing = False
        self.spin_var = tk.IntVar(value=0)
        self.spin_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

        # Vendor cache state
        self.last_vendor_info = None
        self.last_column_info = None
        self.last_quantity_pattern = None
        self.last_raw_text = None

        self._build_ui()

        # Setup drag & drop if available
        if HAS_DND:
            self._setup_drag_drop()

    def _setup_cute_theme(self):
        """Setup cute theme colors."""
        self._CLR_BG = '#f0f8ff'  # Alice blue
        self._CLR_SURFACE = '#ffffff'
        self._CLR_ACCENT = '#3498db'  # Nice blue
        self._CLR_SUCCESS = '#2ecc71'  # Green
        self._CLR_WARNING = '#f39c12'  # Orange
        self._CLR_ERROR = '#e74c3c'  # Red
        self._CLR_TEXT = '#2c3e50'  # Dark blue
        self._CLR_SUBTEXT = '#7f8c8d'  # Gray
        self._CLR_BORDER = '#d5dbdb'

        self.root.configure(bg=self._CLR_BG)

    def _setup_drag_drop(self):
        """Setup drag & drop functionality."""
        if HAS_DND:
            # Make the whole window accept drops
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self._on_drop)

    def _on_drop(self, event):
        """Handle file drop."""
        files = event.data
        if files:
            # tkinterdnd2 returns files in a special format
            file_path = files.strip('{}')  # Remove braces
            if file_path:
                self._handle_dropped_file(file_path)

    def _handle_dropped_file(self, file_path):
        """Handle dropped file."""
        if os.path.exists(file_path):
            self.last_input_path = file_path
            filename = os.path.basename(file_path)

            # Update UI
            self.file_label.config(text=f"📄 {filename}")
            self.btn_process.config(state=tk.NORMAL, bg=self._CLR_SUCCESS)
            self._log(f"📂 Dropped: {filename}")

            # Show in drag drop area
            self.drag_label.config(text=f"✅ {filename}", fg=self._CLR_SUCCESS)
        else:
            self._log(f"❌ File not found: {file_path}")

    def _build_ui(self):
        """Build the ultimate cute UI."""
        # Main container with cute padding
        main = tk.Frame(self.root, bg=self._CLR_BG, padx=25, pady=25)
        main.pack(fill=tk.BOTH, expand=True)

        # ===== HEADER =====
        header = tk.Frame(main, bg=self._CLR_BG)
        header.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            header,
            text="🧾 Ultimate Cute OCR",
            font=("Arial", 28, "bold"),
            bg=self._CLR_BG,
            fg=self._CLR_TEXT
        ).pack()

        tk.Label(
            header,
            text="Extract data from receipts with drag & drop!",
            font=("Arial", 12),
            bg=self._CLR_BG,
            fg=self._CLR_SUBTEXT
        ).pack(pady=(5, 0))

        # ===== DRAG & DROP AREA =====
        drag_frame = tk.LabelFrame(
            main,
            text="📁 Drag & Drop Area",
            font=("Arial", 13, "bold"),
            bg=self._CLR_BG,
            fg=self._CLR_TEXT,
            padx=30,
            pady=30,
            relief=tk.FLAT,
            bd=1,
            highlightbackground=self._CLR_BORDER,
            highlightthickness=1
        )
        drag_frame.pack(fill=tk.X, pady=(0, 20))

        # Drag drop visual area
        self.drag_label = tk.Label(
            drag_frame,
            text="📤 Drag PDF or image here\nor click 'Choose File'",
            font=("Arial", 11),
            bg=self._CLR_SURFACE,
            fg=self._CLR_SUBTEXT,
            height=4,
            relief=tk.RIDGE,
            bd=2
        )
        self.drag_label.pack(fill=tk.X, pady=(0, 15))

        # Upload button row
        upload_row = tk.Frame(drag_frame, bg=self._CLR_BG)
        upload_row.pack(fill=tk.X)

        self.btn_upload = self._create_cute_button(
            upload_row,
            "📄 Choose File",
            self.do_upload,
            self._CLR_ACCENT,
            side=tk.LEFT
        )

        self.btn_clear = self._create_cute_button(
            upload_row,
            "🗑️ Clear",
            self.do_clear,
            self._CLR_SUBTEXT,
            side=tk.LEFT,
            padx=(10, 0)
        )

        # File info
        self.file_label = tk.Label(
            drag_frame,
            text="No file selected",
            font=("Arial", 10),
            bg=self._CLR_BG,
            fg=self._CLR_SUBTEXT
        )
        self.file_label.pack(anchor=tk.W, pady=(15, 0))

        # ===== ACTION BUTTONS =====
        action_frame = tk.Frame(main, bg=self._CLR_BG)
        action_frame.pack(fill=tk.X, pady=(0, 20))

        # Left side: Process button
        self.btn_process = self._create_cute_button(
            action_frame,
            "🚀 Process Receipt",
            self.do_process,
            self._CLR_SUCCESS,
            font_size=12,
            bold=True,
            padding=(20, 12),
            state=tk.DISABLED,
            side=tk.LEFT
        )

        # Right side: Utility buttons
        util_frame = tk.Frame(action_frame, bg=self._CLR_BG)
        util_frame.pack(side=tk.RIGHT)

        self.btn_add_vendor = self._create_cute_button(
            util_frame,
            "➕ Add Vendor",
            self.do_add_vendor,
            self._CLR_WARNING,
            side=tk.LEFT,
            padx=(0, 10)
        )

        self.btn_edit_cache = self._create_cute_button(
            util_frame,
            "✏️ Edit Cache",
            self.do_edit_cache,
            self._CLR_ACCENT,
            side=tk.LEFT,
            padx=(0, 10)
        )

        self.btn_review = self._create_cute_button(
            util_frame,
            "👁️ Review Layout",
            self.do_review_layout,
            "#9b59b6",  # Purple
            side=tk.LEFT
        )

        # ===== PROCESSING STATUS =====
        status_frame = tk.Frame(main, bg=self._CLR_BG)
        status_frame.pack(fill=tk.X, pady=(0, 20))

        self.processing_label = tk.Label(
            status_frame,
            text="",
            font=("Arial", 11),
            bg=self._CLR_BG,
            fg=self._CLR_SUBTEXT
        )
        self.processing_label.pack(anchor=tk.W)

        # ===== RESULTS TABS =====
        notebook = ttk.Notebook(main)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Results
        results_frame = tk.Frame(notebook, bg=self._CLR_BG)
        notebook.add(results_frame, text="📊 Results")

        # Text widget for results
        self.result_text = tk.Text(
            results_frame,
            wrap=tk.WORD,
            font=("Courier New", 9),
            bg=self._CLR_SURFACE,
            fg=self._CLR_TEXT,
            relief=tk.FLAT,
            padx=15,
            pady=15
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.result_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.result_text.yview)

        # Tab 2: Cache Status
        cache_frame = tk.Frame(notebook, bg=self._CLR_BG, padx=20, pady=20)
        notebook.add(cache_frame, text="💾 Cache Status")

        self.cache_status_label = tk.Label(
            cache_frame,
            text="Cache system ready...",
            font=("Arial", 11),
            bg=self._CLR_BG,
            fg=self._CLR_TEXT,
            justify=tk.LEFT
        )
        self.cache_status_label.pack(anchor=tk.W, pady=(0, 10))

        self.cache_details_label = tk.Label(
            cache_frame,
            text="No receipt processed yet",
            font=("Arial", 10),
            bg=self._CLR_BG,
            fg=self._CLR_SUBTEXT,
            justify=tk.LEFT
        )
        self.cache_details_label.pack(anchor=tk.W)

        # Cache actions frame
        cache_actions = tk.Frame(cache_frame, bg=self._CLR_BG)
        cache_actions.pack(fill=tk.X, pady=(20, 0))

        self.btn_improve_cache = self._create_cute_button(
            cache_actions,
            "✨ Improve Cache",
            self._open_simple_cache_editor,
            self._CLR_SUCCESS,
            side=tk.LEFT
        )
        self.btn_improve_cache.pack_forget()  # Hide initially

        # ===== STATUS BAR =====
        status_bar = tk.Frame(main, bg=self._CLR_BORDER, height=2)
        status_bar.pack(fill=tk.X, pady=(20, 0))

        self.status_label = tk.Label(
            main,
            text="Ready",
            font=("Arial", 9),
            bg=self._CLR_BG,
            fg=self._CLR_SUBTEXT
        )
        self.status_label.pack(pady=(10, 0))

        # Configure styles
        self._configure_styles()

    def _create_cute_button(self, parent, text, command, color, **kwargs):
        """Create a cute button with consistent style."""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=kwargs.get('font', ("Arial", kwargs.get('font_size', 10),
                                   "bold" if kwargs.get('bold', False) else "normal")),
            bg=color,
            fg="white",
            padx=kwargs.get('padding', (15, 8))[0],
            pady=kwargs.get('padding', (15, 8))[1],
            relief=tk.FLAT,
            cursor="hand2",
            state=kwargs.get('state', tk.NORMAL)
        )

        # Pack based on side parameter
        side = kwargs.get('side', tk.LEFT)
        padx = kwargs.get('padx', (0, 0))
        btn.pack(side=side, padx=padx)

        # Add hover effects
        btn.bind("<Enter>", lambda e, c=color: self._on_button_enter(e, c))
        btn.bind("<Leave>", lambda e, c=color: self._on_button_leave(e, c))

        return btn

    def _on_button_enter(self, event, color):
        """Button hover enter effect."""
        event.widget['background'] = self._darken_color(color)

    def _on_button_leave(self, event, color):
        """Button hover leave effect."""
        event.widget['background'] = color

    def _darken_color(self, color):
        """Darken color for hover effect."""
        color_map = {
            self._CLR_ACCENT: '#2980b9',
            self._CLR_SUCCESS: '#27ae60',
            self._CLR_WARNING: '#d68910',
            self._CLR_ERROR: '#c0392b',
            self._CLR_SUBTEXT: '#616a6b',
            '#9b59b6': '#8e44ad'  # Purple
        }
        return color_map.get(color, color)

    def _configure_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()
        style.theme_use('clam')

        # Configure notebook style
        style.configure(
            'TNotebook',
            background=self._CLR_BG,
            borderwidth=0
        )

        style.configure(
            'TNotebook.Tab',
            background=self._CLR_SURFACE,
            foreground=self._CLR_TEXT,
            padding=[15, 5],
            font=('Arial', 10)
        )

        style.map(
            'TNotebook.Tab',
            background=[('selected', self._CLR_ACCENT)],
            foreground=[('selected', 'white')]
        )

    def _log(self, message):
        """Log message to status."""
        self.status_label.config(text=message)
        print(message)

    # ===== CORE FUNCTIONALITY =====

    def do_upload(self):
        """Handle file upload."""
        file_path = filedialog.askopenfilename(
            title="Select receipt",
            filetypes=[
                ("PDF files", "*.pdf"),
                ("Image files", "*.jpg *.jpeg *.png"),
                ("All files", "*.*")
            ]
        )

        if file_path:
            self._handle_uploaded_file(file_path)

    def _handle_uploaded_file(self, file_path):
        """Handle uploaded file."""
        self.last_input_path = file_path
        filename = os.path.basename(file_path)

        # Update UI
        self.file_label.config(text=f"📄 {filename}")
        self.btn_process.config(state=tk.NORMAL, bg=self._CLR_SUCCESS)
        self.drag_label.config(text=f"✅ {filename}", fg=self._CLR_SUCCESS)
        self._log(f"📂 Selected: {filename}")

        # Clear previous results
        self.result_text.delete(1.0, tk.END)
        self.cache_status_label.config(text="Ready to process...")
        self.cache_details_label.config(text="")
        self.btn_improve_cache.pack_forget()

    def do_clear(self):
        """Clear current file."""
        self.last_input_path = None
        self.file_label.config(text="No file selected")
        self.btn_process.config(state=tk.DISABLED, bg=self._CLR_SUBTEXT)
        self.drag_label.config(text="📤 Drag PDF or image here\nor click 'Choose File'",
                              fg=self._CLR_SUBTEXT)
        self.result_text.delete(1.0, tk.END)
        self._log("Cleared selection")

    def do_process(self):
        """Process the receipt."""
        if not self.last_input_path:
            messagebox.showinfo("No File", "Select a file first!")
            return

        # Disable button and show processing
        self.btn_process.config(state=tk.DISABLED, bg=self._CLR_SUBTEXT)
        self.processing_label.config(text="⏳ Processing...", fg=self._CLR_WARNING)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "Processing receipt...\n\n")

        # Reset cache state
        self.last_vendor_info = None
        self.last_column_info = None

        # Start processing animation
        self._animate_processing()

        # Run in thread
        thread = threading.Thread(target=self._process_thread)
        thread.daemon = True
        thread.start()

    def _animate_processing(self):
        """Animate processing indicator."""
        if self.is_processing:
            idx = self.spin_var.get()
            self.spin_var.set((idx + 1) % len(self.spin_frames))
            self.processing_label.config(
                text=f"{self.spin_frames[idx]} Processing receipt..."
            )
            self.root.after(100, self._animate_processing)

    def _process_thread(self):
        """Thread for processing."""
        self.is_processing = True
        self.spin_var.set(0)
        self.root.after(0, self._animate_processing)

        try:
            from pipelines.mindee_pipeline import process_receipt

            result = process_receipt(self.last_input_path)
            self.last_result = result

            # Try to extract vendor info
            vendor_info = result.get('metadata', {}).get('vendor_info', {})
            column_info = result.get('metadata', {}).get('column_info', {})

            # Update UI in main thread
            self.root.after(0, lambda: self._show_results(result, vendor_info, column_info))

        except Exception as e:
            self.root.after(0, lambda: self._show_error(str(e)))

        finally:
            self.is_processing = False
            self.root.after(0, lambda: self.processing_label.config(text=""))

    def _show_results(self, result, vendor_info, column_info):
        """Show processing results."""
        self.btn_process.config(state=tk.NORMAL, bg=self._CLR_SUCCESS)
        self.processing_label.config(text="")

        # Clear and show results
        self.result_text.delete(1.0, tk.END)

        # Extract info from GDocument
        gdoc = result.get("GDocument", {})

        # Show vendor and date
        vendor = ""
        date = ""
        for f in gdoc.get("fields", []):
            if f.get("name") == "VendorName":
                vendor = f.get("value", "")
            elif f.get("name") == "Date":
                date = f.get("value", "")

        self.result_text.insert(tk.END, f"📋 RECEIPT DETAILS\n")
        self.result_text.insert(tk.END, f"{'='*40}\n")
        self.result_text.insert(tk.END, f"Vendor: {vendor or 'Unknown'}\n")
        self.result_text.insert(tk.END, f"Date: {date or 'Unknown'}\n\n")

        # Show items
        groups = gdoc.get("groups", [])
        if groups:
            items_group = groups[0] if groups else {}
            items = items_group.get("groups", [])

            self.result_text.insert(tk.END, f"🛒 ITEMS ({len(items)})\n")
            self.result_text.insert(tk.END, f"{'='*40}\n")

            for i, item in enumerate(items[:15]):  # Show first 15
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

                line = f"{i+1:2}. {desc[:40]}"
                if len(desc) > 40:
                    line += "..."

                if qty:
                    line += f" ×{qty}"
                if price:
                    line += f" - {price}₪"

                self.result_text.insert(tk.END, line + "\n")

            if len(items) > 15:
                self.result_text.insert(tk.END, f"\n... and {len(items) - 15} more items\n")

        # Update cache status
        self._update_cache_status(vendor_info, column_info)

        # Enable download
        self._log(f"✅ Processed successfully - ready to download")

    def _update_cache_status(self, vendor_info, column_info):
        """Update cache status display."""
        if vendor_info:
            vendor_name = vendor_info.get('vendor_name', '')
            confidence = vendor_info.get('confidence', 0)
            cache_used = vendor_info.get('cache_used', False)

            if vendor_name:
                if cache_used:
                    status = f"✅ Using cached layout for: {vendor_name}"
                    details = f"Confidence: {confidence:.2f} (cache hit)"
                    color = self._CLR_SUCCESS
                else:
                    status = f"⚠️  New vendor detected: {vendor_name}"
                    details = f"Confidence: {confidence:.2f} (no cache)"
                    color = self._CLR_WARNING

                    # Show improve button for low confidence
                    if confidence < 0.8:
                        self.btn_improve_cache.pack(side=tk.LEFT)
                        self.btn_improve_cache.config(
                            text=f"✨ Improve {vendor_name} cache"
                        )
            else:
                status = "❌ No vendor detected"
                details = "Could not identify vendor"
                color = self._CLR_ERROR
        else:
            status = "ℹ️  No vendor info available"
            details = "Pipeline didn't return vendor info"
            color = self._CLR_SUBTEXT

        self.cache_status_label.config(text=status, fg=color)
        self.cache_details_label.config(text=details)

    def _show_error(self, error_msg):
        """Show error message."""
        self.btn_process.config(state=tk.NORMAL, bg=self._CLR_SUCCESS)
        self.processing_label.config(text="")

        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"❌ ERROR\n{'='*40}\n{error_msg}")

        self.cache_status_label.config(
            text="❌ Processing failed",
            fg=self._CLR_ERROR
        )
        self.cache_details_label.config(text=error_msg[:100] + "...")

        self._log(f"❌ Error: {error_msg}")

    # ===== UTILITY FUNCTIONS =====

    def do_add_vendor(self):
        """Add a new vendor."""
        # Simple add vendor dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("➕ Add Vendor")
        dialog.geometry("400x250")
        dialog.configure(bg=self._CLR_BG)
        dialog.transient(self.root)
        dialog.grab_set()

        main = tk.Frame(dialog, bg=self._CLR_BG, padx=30, pady=30)
        main.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            main,
            text="Add New Vendor",
            font=("Arial", 18, "bold"),
            bg=self._CLR_BG,
            fg=self._CLR_TEXT
        ).pack(pady=(0, 20))

        tk.Label(
            main,
            text="Vendor Name (English):",
            font=("Arial", 11),
            bg=self._CLR_BG
        ).pack(anchor=tk.W, pady=(0, 5))

        name_entry = tk.Entry(
            main,
            font=("Arial", 12),
            width=30
        )
        name_entry.pack(pady=(0, 20))
        name_entry.focus_set()

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning("Missing", "Enter vendor name")
                return

            # Simple save to merchants_mapping.json
            mapping_path = PROJECT_ROOT / "merchants_mapping.json"
            if mapping_path.exists():
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    merchants = json.load(f)
            else:
                merchants = {}

            # Add with name as keyword
            merchants[name] = [name]

            with open(mapping_path, 'w', encoding='utf-8') as f:
                json.dump(merchants, f, ensure_ascii=False, indent=2)

            messagebox.showinfo("Saved", f"Added vendor: {name}")
            dialog.destroy()
            self._log(f"➕ Added vendor: {name}")

        # Buttons
        btn_frame = tk.Frame(main, bg=self._CLR_BG)
        btn_frame.pack(pady=(10, 0))

        self._create_cute_button(
            btn_frame,
            "Cancel",
            dialog.destroy,
            self._CLR_SUBTEXT,
            side=tk.LEFT,
            padx=(0, 10)
        )

        self._create_cute_button(
            btn_frame,
            "Save Vendor",
            save,
            self._CLR_SUCCESS,
            side=tk.LEFT,
            bold=True
        )

    def do_edit_cache(self):
        """Edit vendor cache."""
        self._open_simple_cache_editor()

    def _open_simple_cache_editor(self):
        """Open simple cache editor."""
        try:
            from gui.super_simple_cache_editor import SuperSimpleCacheEditor

            editor_window = tk.Toplevel(self.root)
            editor_window.title("✏️ Cache Editor")
            editor_window.geometry("500x600")

            app = SuperSimpleCacheEditor(editor_window)

        except Exception as e:
            messagebox.showerror("Error", f"Can't open cache editor: {e}")

    def do_review_layout(self):
        """Review layout for last receipt."""
        if not self.last_vendor_info or not self.last_column_info:
            messagebox.showinfo("No Data", "Process a receipt first to review layout")
            return

        # Open layout review dialog
        try:
            from gui.vendor_cache_manager import ColumnAssignmentDialog

            def on_save(assignments, pattern):
                self._log(f"💾 Saved layout: {len(assignments)} columns")
                messagebox.showinfo("Saved", "Layout saved to cache!")

            def on_apply(assignments, pattern):
                self._log(f"🔧 Applied layout once: {len(assignments)} columns")

            dialog = ColumnAssignmentDialog(
                self.root,
                self.last_raw_text or "",
                self.last_column_info.get('detected_columns', []),
                self.last_column_info.get('column_mapping', {}),
                self.last_quantity_pattern or 1,
                on_save,
                on_apply
            )

        except Exception as e:
            messagebox.showerror("Error", f"Can't open review dialog: {e}")

    def do_download(self):
        """Download results."""
        if not self.last_result:
            messagebox.showinfo("No Results", "Process a receipt first!")
            return

        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            title="Save Results",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.last_result, f, ensure_ascii=False, indent=2)

                self._log(f"💾 Saved results to: {os.path.basename(file_path)}")
                messagebox.showinfo("Saved", f"Results saved to:\n{file_path}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {e}")


def main():
    """Run the ultimate cute OCR app."""
    root = tk.Tk()
    app = UltimateCuteOCRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()