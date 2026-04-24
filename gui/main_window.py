"""
Main window for Receipt OCR GUI.
"""

import json
import os
import sys
import shutil
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Use absolute imports to avoid package confusion
import sys
from pathlib import Path

# Add gui directory to path if not already there
gui_dir = Path(__file__).parent
if str(gui_dir) not in sys.path:
    sys.path.insert(0, str(gui_dir))

try:
    from theme import theme
    from components import DropZone, ProcessingSpinner, ResultDisplay, ConfidenceMeter, CacheStatusDisplay
except ImportError as e:
    print(f"FATAL: Could not import GUI modules: {e}")
    print(f"GUI dir: {gui_dir}")
    print(f"sys.path: {sys.path[:3]}")
    raise


class MainWindow:
    """Main application window."""

    def __init__(self, root):
        self.root = root
        self.root.title(f"{theme.EMOJI_RECEIPT} Receipt OCR")
        self.root.geometry("1000x800")
        self.root.minsize(800, 600)

        # Configure theme
        theme.configure_styles(self.root)

        # State
        self.last_result = None
        self.last_input_path = None
        self.is_processing = False

        # Vendor cache state
        self.last_vendor_info = None
        self.last_column_info = None
        self.last_quantity_pattern = None
        self.last_raw_text = None
        self.last_confidence_score = 0.0

        # Pipeline callback registry for user decisions
        self.pipeline_callbacks = {
            'ask_replace_schema': self._wrap_gui_callback(self._show_replace_schema_dialog),
            'on_mapping_missing': self._wrap_gui_callback(self._add_merchant_mapping),
            'create_cache_entry': self._wrap_gui_callback(self._show_create_cache_dialog),  # NEW: for low-confidence new vendors
            'edit_schema_low_confidence': self._wrap_gui_callback(self._show_edit_schema_low_confidence_dialog)  # NEW: for low-confidence existing cache
        }

        # Check if tkinterdnd2 is available for drag and drop
        try:
            from tkinterdnd2 import TkinterDnD, DND_FILES
            self.has_dnd = True
            print("Drag & drop enabled (tkinterdnd2 available)")
        except ImportError:
            self.has_dnd = False
            print("Note: Drag & drop disabled - tkinterdnd2 not installed")

        # Build UI
        self._build_ui()

    def _add_merchant_mapping(self, hebrew_text):
        """
        Add merchant mapping for Hebrew text.

        Args:
            hebrew_text: Hebrew merchant name

        Returns:
            English key for the merchant (placeholder for now)
        """
        # For now, return a placeholder
        # In future, should show do_add_vendor dialog and return English name
        print(f"GUI: Would add merchant mapping for: {hebrew_text}")
        return f"mapped_{hebrew_text[:10]}"

    def _wrap_gui_callback(self, callback_func):
        """
        Wrap a GUI callback to run synchronously in main thread via root.after().
        Uses queue.Queue to wait for GUI response.

        Args:
            callback_func: The GUI method to wrap

        Returns:
            Wrapped function that can be called from background thread and returns result
        """
        import queue

        def wrapped(*args, **kwargs):
            result_queue = queue.Queue()

            # Create a wrapper that will run in main thread and put result in queue
            def gui_task():
                try:
                    result = callback_func(*args, **kwargs)
                    result_queue.put(result)
                except Exception as e:
                    result_queue.put(e)

            # Schedule GUI task in main thread
            self.root.after(0, gui_task)

            # Wait for result (blocking in background thread is OK)
            try:
                result = result_queue.get(timeout=30)  # 30 second timeout
                if isinstance(result, Exception):
                    raise result
                return result
            except queue.Empty:
                raise TimeoutError("GUI callback timed out after 30 seconds")

        return wrapped

    def _build_ui(self):
        """Build the main UI."""
        # Header
        self._build_header()

        # Action bar
        self._build_action_bar()

        # Drop zone
        self._build_drop_zone()

        # Confidence meter and cache status
        self._build_status_displays()

        # Result display (with drag & drop support on text widget)
        self._build_result_display()

        # Footer
        self._build_footer()

    def _build_header(self):
        """Build the header section."""
        header = theme.create_frame(self.root, padx=24, pady=20)
        header.pack(fill=tk.X)

        # Title with emoji
        title_label = theme.create_label(
            header,
            text=f"{theme.EMOJI_RECEIPT} Receipt OCR",
            font=theme.FONT_TITLE
        )
        title_label.pack(anchor=tk.W)

        # Subtitle
        subtitle_label = theme.create_label(
            header,
            text="Upload receipt to extract data with vendor cache optimization",
            font=theme.FONT_SUBTITLE,
            fg=theme.CLR_SUBTEXT
        )
        subtitle_label.pack(anchor=tk.W, pady=(5, 0))

    def _build_action_bar(self):
        """Build the action bar with buttons."""
        bar = theme.create_frame(self.root, padx=24, pady=12)
        bar.pack(fill=tk.X)

        # Left side: Cache toggle and main actions
        left_frame = theme.create_frame(bar)
        left_frame.pack(side=tk.LEFT)

        # Cache toggle (main pipeline automatically uses cache if available)
        self.cache_var = tk.BooleanVar(value=True)
        cache_frame = theme.create_frame(left_frame)
        cache_frame.pack(side=tk.LEFT, padx=(0, 20))

        self.cache_check = tk.Checkbutton(
            cache_frame,
            text="Use Vendor Cache",
            variable=self.cache_var,
            bg=theme.CLR_BG,
            fg=theme.CLR_TEXT,
            font=("Arial", 10),
            activebackground=theme.CLR_BG,
            activeforeground=theme.CLR_TEXT,
            selectcolor=theme.CLR_SURFACE
        )
        self.cache_check.pack(side=tk.LEFT)

        # Main action buttons
        actions_frame = theme.create_frame(left_frame)
        actions_frame.pack(side=tk.LEFT)

        self.btn_browse = theme.create_button(
            actions_frame, "Browse", self.do_browse,
            style="primary", emoji=theme.EMOJI_UPLOAD
        )
        self.btn_browse.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_save = theme.create_button(
            actions_frame, "Save as Folder", self.do_save_folder,
            style="secondary", emoji=theme.EMOJI_SAVE
        )
        self.btn_save.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_save.config(state=tk.DISABLED)

        # Right side: Vendor management and status
        right_frame = theme.create_frame(bar)
        right_frame.pack(side=tk.RIGHT)

        # Vendor management buttons
        vendor_frame = theme.create_frame(right_frame)
        vendor_frame.pack(side=tk.LEFT, padx=(0, 20))

        self.btn_add_vendor = theme.create_button(
            vendor_frame, "Add Vendor", self.do_add_vendor,
            style="secondary", emoji=theme.EMOJI_ADD
        )
        self.btn_add_vendor.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_add_schema = theme.create_button(
            vendor_frame, "Add Schema", self.do_add_schema,
            style="secondary", emoji=theme.EMOJI_SCHEMA
        )
        self.btn_add_schema.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_cache = theme.create_button(
            vendor_frame, "Vendor Cache", self.do_manage_vendor_cache,
            style="secondary", emoji=theme.EMOJI_CACHE
        )
        self.btn_cache.pack(side=tk.LEFT)

        # Status area
        status_frame = theme.create_frame(right_frame)
        status_frame.pack(side=tk.LEFT)

        self.lbl_status = ttk.Label(status_frame, text="Ready", style="Status.TLabel")
        self.lbl_status.pack()

        # Spinner
        self.spinner = ProcessingSpinner(self.root, self.lbl_status)

    def _build_drop_zone(self):
        """Build the drag and drop zone."""
        self.drop_zone = DropZone(self.root, self._process_file, self.has_dnd)

    def _build_status_displays(self):
        """Build confidence meter and cache status displays."""
        # Confidence meter
        self.confidence_meter = ConfidenceMeter(self.root, "Confidence Score:")

        # Cache status display
        self.cache_status = CacheStatusDisplay(self.root)
        self.cache_status.set_improve_callback(self.do_improve_cache)

    def _build_result_display(self):
        """Build the result display area with drag & drop support on text widget."""
        # Pass the process file callback to ResultDisplay for DnD on text widget
        self.result_display = ResultDisplay(self.root, self._process_file)

    def _build_footer(self):
        """Build the footer."""
        footer = theme.create_frame(self.root, pady=10)
        footer.pack(side=tk.BOTTOM, fill=tk.X)

        footer_label = theme.create_label(
            footer,
            text="Receipt OCR with Vendor Cache Learning System",
            font=theme.FONT_SMALL,
            fg=theme.CLR_SUBTEXT
        )
        footer_label.pack()

        copyright_label = theme.create_label(
            footer,
            text="© 2024 Kfir Ezer",
            font=theme.FONT_SMALL,
            fg=theme.CLR_SUBTEXT
        )
        copyright_label.pack(pady=(2, 0))

    # ===== Event Handlers =====

    def _process_file(self, file_path):
        """Process a file (called from drop zone or browse)."""
        self.result_display.clear()
        self._set_busy(True)
        self.spinner.start()

        self.result_display.log(f"Processing: {file_path}")
        cache_status = "enabled" if self.cache_var.get() else "disabled"
        self.result_display.log(f"Vendor cache: {cache_status}")

        # Run processing in background thread
        threading.Thread(target=self._process_file_thread, args=(file_path,), daemon=True).start()

    def _process_file_thread(self, file_path):
        """Process file in background thread."""
        try:
            # Reset vendor cache state
            self.last_vendor_info = None
            self.last_column_info = None
            self.last_quantity_pattern = None
            self.last_raw_text = None
            self.last_confidence_score = 0.0

            # Use main pipeline directly (modified to return metadata)
            use_cache = self.cache_var.get()
            try:
                from pipelines.mindee_pipeline import process_receipt
                result = process_receipt(
                    file_path,
                    api_key=None,
                    model_id=None,
                    save_to_output=True,
                    gui_callbacks=self.pipeline_callbacks
                )

                # If pipeline returns just GDocument (backward compatibility), wrap it
                if 'GDocument' not in result:
                    self.result_display.log("Pipeline returned old format, wrapping with metadata")
                    result = {
                        'GDocument': result,
                        'vendor_info': {},
                        'column_info': {},
                        'quantity_pattern': 1,
                        'confidence_score': 0.5,
                        'cache_hit': False,
                        'raw_text': ""
                    }

            except ImportError as e:
                raise ImportError(f"Pipeline not available: {e}")

            self.last_result = result
            self.last_input_path = file_path

            # Extract items count
            gdoc = result.get("GDocument", {})
            groups = gdoc.get("groups", [])
            items_count = 0
            if groups and len(groups) > 0:
                table_group = groups[0]
                table_items = table_group.get("groups", [])
                items_count = len(table_items)

            # Extract vendor cache info from result
            vendor_info = result.get('vendor_info', {})
            column_info = result.get('column_info', {})
            quantity_pattern = result.get('quantity_pattern', 1)
            confidence_score = result.get('confidence_score', 0.0)
            cache_hit = result.get('cache_hit', False)

            # Update UI in main thread
            self.root.after(0, lambda: self._update_after_processing(
                items_count, result, vendor_info, column_info,
                quantity_pattern, confidence_score, cache_hit
            ))

        except Exception as e:
            import traceback
            error_msg = f"Error: {e}\n{traceback.format_exc()}"
            self.root.after(0, lambda: self.result_display.log(error_msg))
            self.root.after(0, lambda: self._set_busy(False))
            self.root.after(0, lambda: self.spinner.stop("Error ❌"))

    def _update_after_processing(self, items_count, result, vendor_info,
                                column_info, quantity_pattern,
                                confidence_score, cache_hit):
        """Update UI after processing completes."""
        self.result_display.log(f"Extracted {items_count} items")

        # Try to log result as JSON, but don't fail if serialization fails
        try:
            # Show clean ABBYY GDocument instead of entire result dict with metadata
            gdoc_wrapper = result.get("GDocument", {})
            if "GDocument" in gdoc_wrapper:
                # Double nested: {"GDocument": {"GDocument": {...}}}
                clean_gdoc = gdoc_wrapper.get("GDocument", {})
            else:
                # Single nested: {"GDocument": {...}}
                clean_gdoc = gdoc_wrapper

            result_json = json.dumps(clean_gdoc, indent=2, ensure_ascii=False)
            self.result_display.log(result_json)

            # Also log metadata summary for debugging
            self.result_display.log(f"\n=== Processing Metadata ===")
            self.result_display.log(f"Confidence Score: {confidence_score:.2f}")
            self.result_display.log(f"Cache Hit: {cache_hit}")
            if vendor_info and vendor_info.get('name'):
                self.result_display.log(f"Vendor: {vendor_info.get('name')}")
            if vendor_info and vendor_info.get('trust_score'):
                self.result_display.log(f"Trust Score: {vendor_info.get('trust_score'):.2f}")

        except (TypeError, ValueError) as e:
            self.result_display.log(f"Note: Could not serialize result to JSON: {e}")
            # Log at least the keys we have
            self.result_display.log(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")

        # Update vendor cache state
        self.last_vendor_info = vendor_info
        self.last_column_info = column_info
        self.last_quantity_pattern = quantity_pattern
        self.last_confidence_score = confidence_score

        # Debug: log confidence score
        print(f"GUI updating confidence meter with score: {confidence_score} (type: {type(confidence_score)})")

        # Update confidence meter
        self.confidence_meter.update(confidence_score)

        # Update cache status
        vendor_name = vendor_info.get('vendor_slug') if vendor_info else None
        trust_score = vendor_info.get('trust_score', 0.0) if vendor_info else 0.0
        self.cache_status.update(vendor_name, trust_score, cache_hit)

        # Layout review is automatic in pipeline - no manual button needed

        # Enable save button
        self.btn_save.config(state=tk.NORMAL)

        # Stop spinner
        self._set_busy(False)
        self.spinner.stop("Done ✅")

    def _set_busy(self, busy: bool):
        """Set busy state."""
        self.is_processing = busy
        state = tk.DISABLED if busy else tk.NORMAL

        self.btn_browse.config(state=state)
        self.btn_save.config(state=state if self.last_result else tk.DISABLED)
        self.btn_add_vendor.config(state=state)
        self.btn_add_schema.config(state=state)
        self.btn_cache.config(state=state)

    # ===== Public Methods (called from buttons) =====

    def do_browse(self):
        """Browse for file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("Image/PDF files", "*.pdf *.png *.jpg *.jpeg"), ("All files", "*.*")],
        )
        if file_path:
            self._process_file(file_path)

    def do_save_folder(self):
        """Save result as folder."""
        if not self.last_result:
            messagebox.showwarning("No result", "Process a receipt first.")
            return

        # Get vendor and date from result
        # Handle double GDocument nesting: {'GDocument': {'GDocument': {...}}}
        gdoc_wrapper = self.last_result.get("GDocument", {})
        if "GDocument" in gdoc_wrapper:
            # Double nested: {"GDocument": {"GDocument": {...}}}
            gdoc = gdoc_wrapper.get("GDocument", {})
        else:
            # Single nested: {"GDocument": {...}}
            gdoc = gdoc_wrapper

        vendor = ""
        date = ""

        for f in gdoc.get("fields", []):
            if f.get("name") == "VendorName":
                vendor = f.get("value", "")
            elif f.get("name") == "Date":
                date = f.get("value", "")

        if not vendor:
            vendor = "Unknown"
        if not date:
            date = "Unknown"

        # Format date
        if date and date != "Unknown" and '-' in date and len(date.split('-')[0]) == 4:
            parts = date.split('-')
            date = f"{parts[2]}.{parts[1]}.{parts[0][-2:]}"

        # Generate filename
        receipt_name = None
        if vendor and date and date != "Unknown":
            receipt_name = f"{vendor}_{date}"
        else:
            receipt_name = f"{vendor}_{date}" if vendor else "Unknown"

        # Get save location
        folder_path = filedialog.askdirectory(title="Choose where to save the folder")
        if not folder_path:
            return

        output = Path(folder_path) / receipt_name
        output.mkdir(parents=True, exist_ok=True)

        # Copy original file
        ext = Path(self.last_input_path).suffix
        dst_file = output / f"{receipt_name}{ext}"
        shutil.copy2(self.last_input_path, dst_file)

        # Save JSON (save clean GDocument, not entire result dict)
        json_path = output / f"{receipt_name}.JSON"
        # Get clean GDocument for saving
        gdoc_wrapper = self.last_result.get("GDocument", {})
        if "GDocument" in gdoc_wrapper:
            # Double nested: {"GDocument": {"GDocument": {...}}}
            clean_gdoc = gdoc_wrapper.get("GDocument", {})
        else:
            # Single nested: {"GDocument": {...}}
            clean_gdoc = gdoc_wrapper

        json_path.write_text(
            json.dumps(clean_gdoc, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Copy to clipboard (copy clean GDocument)
        self.root.clipboard_clear()
        self.root.clipboard_append(json.dumps(clean_gdoc, ensure_ascii=False))

        messagebox.showinfo("Saved", f"Folder created:\n{output}\n\nJSON copied to clipboard!")
        self.result_display.log(f"\nSaved to folder: {output}")

    def do_add_vendor(self):
        """Add new vendor to merchants_mapping.json with Google Translate suggestions."""
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("➕ Add New Vendor")
        dialog.geometry("500x350")
        dialog.transient(self.root)
        dialog.grab_set()

        theme.configure_styles(dialog)

        # Content frame
        content = theme.create_frame(dialog, padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        # Title
        title = theme.create_label(
            content,
            text="➕ Add New Vendor",
            font=theme.FONT_TITLE
        )
        title.pack(anchor=tk.W, pady=(0, 15))

        # Description
        desc = theme.create_label(
            content,
            text="Enter vendor name in English, get Hebrew translation suggestions",
            font=theme.FONT_SUBTITLE,
            fg=theme.CLR_SUBTEXT
        )
        desc.pack(anchor=tk.W, pady=(0, 20))

        # Vendor name (English) with auto-translate
        name_frame = theme.create_frame(content)
        name_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(name_frame, text="English Name:").pack(side=tk.LEFT, padx=(0, 10))
        self.new_vendor_var = tk.StringVar()
        name_entry = theme.create_entry(name_frame, width=30)
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Translate button
        translate_btn = theme.create_button(
            name_frame, "Translate", command=lambda: self._translate_vendor_name(name_entry, suggestions_list),
            style="secondary", emoji="🌐"
        )
        translate_btn.pack(side=tk.LEFT, padx=(10, 0))

        # Hebrew suggestions frame
        suggestions_frame = theme.create_frame(content)
        suggestions_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(suggestions_frame, text="Hebrew Suggestions:").pack(side=tk.LEFT, padx=(0, 10))

        # Listbox for suggestions
        suggestions_list = tk.Listbox(
            suggestions_frame,
            height=4,
            bg=theme.CLR_SURFACE,
            fg=theme.CLR_TEXT,
            font=theme.FONT_BODY,
            relief=tk.SOLID,
            borderwidth=1
        )
        suggestions_list.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # Select button for suggestions
        select_btn = theme.create_button(
            suggestions_frame, "Select",
            command=lambda: self._select_suggestion(suggestions_list, hebrew_entry),
            style="secondary", emoji="✓"
        )
        select_btn.pack(side=tk.LEFT)

        # Hebrew name entry
        hebrew_frame = theme.create_frame(content)
        hebrew_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(hebrew_frame, text="Hebrew Name:").pack(side=tk.LEFT, padx=(0, 10))
        self.new_vendor_hebrew_var = tk.StringVar()
        hebrew_entry = theme.create_entry(hebrew_frame, width=30)
        hebrew_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Buttons
        button_frame = theme.create_frame(content)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        btn_add = theme.create_button(
            button_frame, "Add Vendor", command=lambda: self._save_new_vendor(name_entry, hebrew_entry, dialog),
            style="primary", emoji="➕"
        )
        btn_add.pack(side=tk.LEFT, padx=(0, 10))

        btn_cancel = theme.create_button(
            button_frame, "Cancel", command=dialog.destroy,
            style="secondary"
        )
        btn_cancel.pack(side=tk.LEFT)

    def _translate_vendor_name(self, name_entry, suggestions_list):
        """Translate English vendor name to Hebrew using Google Translate."""
        english_name = name_entry.get().strip()
        if not english_name:
            messagebox.showwarning("No Name", "Please enter an English vendor name first.")
            return

        # Clear suggestions list
        suggestions_list.delete(0, tk.END)

        try:
            # Try to use deep_translator
            from deep_translator import GoogleTranslator

            # Translate to Hebrew - try 'iw' (ISO 639-1 for Hebrew) or 'he'
            try:
                translated = GoogleTranslator(source='auto', target='iw').translate(english_name)
            except:
                # Fallback to 'he' if 'iw' doesn't work
                translated = GoogleTranslator(source='auto', target='he').translate(english_name)

            if translated:
                # Add the main translation
                suggestions_list.insert(tk.END, translated)

                # Generate variations using confusion map
                variations = self._generate_hebrew_variations(translated)
                for variation in variations:
                    suggestions_list.insert(tk.END, variation)

                # Also add common variations with keywords (optional)
                common_keywords = ["חנות", "מרכול", "סופר", "רשת", "קמעונאי"]
                for keyword in common_keywords:
                    suggestions_list.insert(tk.END, f"{translated} {keyword}")
                    suggestions_list.insert(tk.END, f"{keyword} {translated}")

                # Add variations with keywords too
                for variation in variations[:2]:  # Just first 2 variations with keywords
                    suggestions_list.insert(tk.END, f"{variation} חנות")
                    suggestions_list.insert(tk.END, f"חנות {variation}")

        except ImportError:
            # Fallback: use simple transliteration or common patterns
            suggestions_list.insert(tk.END, f"[No translator] {english_name}")
            # Add common Hebrew store names
            suggestions_list.insert(tk.END, f"{english_name} חנות")
            suggestions_list.insert(tk.END, f"חנות {english_name}")
        except Exception as e:
            suggestions_list.insert(tk.END, f"Translation error: {str(e)[:50]}")

    def _generate_hebrew_variations(self, text):
        """Generate Hebrew text variations using OCR confusion patterns from JSON file."""
        if not text or len(text) < 2:
            return []

        try:
            # Load confusion map from JSON file
            import json
            from pathlib import Path
            conf_map_path = Path(__file__).parent.parent / "hebrew_ocr_confusion_map.json"

            if not conf_map_path.exists():
                # Fallback to hardcoded map if file doesn't exist
                return self._generate_hebrew_variations_fallback(text)

            with open(conf_map_path, "r", encoding="utf-8") as f:
                conf_data = json.load(f)

            confusion_map = conf_data.get("confusion_map", {})
            common_suffixes = conf_data.get("common_suffixes", ["ים", "ות", "ס"])
            common_prefixes = conf_data.get("common_prefixes", ["ה", "ב", "כ", "ל", "מ"])

        except Exception as e:
            print(f"Error loading confusion map: {e}")
            return self._generate_hebrew_variations_fallback(text)

        variations = []
        text_chars = list(text)

        # PHASE 1: Single-letter substitutions (most common)
        for i, char in enumerate(text_chars):
            if char in confusion_map:
                substitute = confusion_map[char]
                # Create variation with substituted character
                variation_chars = text_chars.copy()
                variation_chars[i] = substitute
                variation = ''.join(variation_chars)
                if variation != text:  # Don't add duplicate of original
                    variations.append(variation)

        # PHASE 2: Double-letter substitutions (less common but important)
        # This catches cases like גלוברנדס → גלוכנדס (ב→כ, ר→נ, ד→ס)
        # We'll do combinations of 2 substitutions
        substitution_points = []
        for i, char in enumerate(text_chars):
            if char in confusion_map:
                substitution_points.append(i)

        # Generate combinations of 2 substitutions
        if len(substitution_points) >= 2:
            from itertools import combinations
            for i, j in combinations(substitution_points, 2):
                if i != j:
                    # Apply both substitutions
                    variation_chars = text_chars.copy()
                    variation_chars[i] = confusion_map.get(text_chars[i], text_chars[i])
                    variation_chars[j] = confusion_map.get(text_chars[j], text_chars[j])
                    variation = ''.join(variation_chars)
                    if variation != text and variation not in variations:
                        variations.append(variation)

        # PHASE 3: Triple-letter substitutions (rare but possible)
        if len(substitution_points) >= 3:
            from itertools import combinations
            for i, j, k in combinations(substitution_points, 3):
                if i != j != k:
                    variation_chars = text_chars.copy()
                    variation_chars[i] = confusion_map.get(text_chars[i], text_chars[i])
                    variation_chars[j] = confusion_map.get(text_chars[j], text_chars[j])
                    variation_chars[k] = confusion_map.get(text_chars[k], text_chars[k])
                    variation = ''.join(variation_chars)
                    if variation != text and variation not in variations:
                        variations.append(variation)

        # PHASE 4: Add common suffixes
        for suffix in common_suffixes:
            if suffix and not text.endswith(suffix):
                variation = text + suffix
                if variation not in variations:
                    variations.append(variation)

        # PHASE 5: Add common prefixes
        for prefix in common_prefixes:
            if prefix and not text.startswith(prefix):
                variation = prefix + text
                if variation not in variations:
                    variations.append(variation)

        # Remove duplicates and limit to reasonable number
        # Sort by: 1) original word length, 2) alphabetically
        unique_variations = []
        seen = set()
        for var in variations:
            if var not in seen and var != text:
                seen.add(var)
                unique_variations.append(var)

        # Sort: single substitutions first, then multiples
        def variation_score(v):
            # Count how many characters differ from original
            diff_count = sum(1 for a, b in zip(text, v) if a != b)
            return diff_count

        unique_variations.sort(key=variation_score)

        return unique_variations[:20]  # Return first 20 unique variations

    def _generate_hebrew_variations_fallback(self, text):
        """Fallback variation generation if JSON file can't be loaded."""
        if not text or len(text) < 2:
            return []

        # Simple fallback with common variations
        fallback_variations = []

        # Common letter substitutions
        substitutions = {
            'ב': 'כ',
            'כ': 'ב',
            'ס': 'ם',
            'ם': 'ס',
            'ו': 'ן',
            'ן': 'ו',
            'ד': 'ס',
            'ר': 'נ'
        }

        text_chars = list(text)
        for i, char in enumerate(text_chars):
            if char in substitutions:
                variation_chars = text_chars.copy()
                variation_chars[i] = substitutions[char]
                variation = ''.join(variation_chars)
                if variation != text:
                    fallback_variations.append(variation)

        # Add common suffixes
        for suffix in ['ים', 'ס', 'ם']:
            if not text.endswith(suffix):
                fallback_variations.append(text + suffix)

        return fallback_variations[:10]

    def _select_suggestion(self, suggestions_list, hebrew_entry):
        """Select a suggestion from the list and put it in the Hebrew entry."""
        selection = suggestions_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a suggestion from the list.")
            return

        selected_text = suggestions_list.get(selection[0])
        hebrew_entry.delete(0, tk.END)
        hebrew_entry.insert(0, selected_text)

    def _save_new_vendor(self, name_entry, hebrew_entry, dialog):
        """Save the new vendor to merchants_mapping.json."""
        english_name = name_entry.get().strip()
        hebrew_name = hebrew_entry.get().strip()

        if not english_name:
            messagebox.showerror("Error", "English name is required")
            return

        # Auto-generate vendor slug
        vendor_slug = english_name.lower().replace(" ", "_")

        # Load or create merchants mapping
        import json
        from pathlib import Path
        mapping_path = Path(__file__).parent.parent / "merchants_mapping.json"
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)
        except:
            mapping = {}

        # Check if vendor already exists (by English name, not slug)
        vendor_exists = False
        existing_slug = None
        for slug, names_list in mapping.items():
            if english_name in names_list:
                vendor_exists = True
                existing_slug = slug
                break

        if vendor_exists:
            response = messagebox.askyesno("Vendor Exists",
                f"Vendor '{english_name}' already exists. Update it?")
            if not response:
                return
            vendor_slug = existing_slug  # Use existing slug

        # Add vendor in correct format (list of names)
        names = []
        if hebrew_name:
            names.append(hebrew_name)
        names.append(english_name)  # English name usually last

        mapping[vendor_slug] = names

        # Save
        try:
            with open(mapping_path, "w", encoding="utf-8") as f:
                json.dump(mapping, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Success", f"Vendor '{english_name}' added successfully!")
            dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def do_add_schema(self):
        """Add/edit schema for an existing vendor."""
        # First, let user select vendor from merchants_mapping
        import json
        from pathlib import Path

        mapping_path = Path(__file__).parent.parent / "merchants_mapping.json"
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)
        except:
            mapping = {}

        if not mapping:
            messagebox.showinfo("No Vendors", "No vendors found. Please add a vendor first.")
            return

        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Vendor for Schema")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        theme.configure_styles(dialog)

        content = theme.create_frame(dialog, padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        title = theme.create_label(
            content,
            text="Select Vendor for Schema",
            font=theme.FONT_TITLE
        )
        title.pack(anchor=tk.W, pady=(0, 15))

        # Vendor list
        list_frame = theme.create_frame(content)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Treeview for vendors
        columns = ("slug", "english", "hebrew")
        tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        tree.heading("slug", text="Vendor Slug")
        tree.heading("english", text="English Name")
        tree.heading("hebrew", text="Hebrew Name")

        tree.column("slug", width=150)
        tree.column("english", width=150)
        tree.column("hebrew", width=150)

        # Add vendors
        for slug, data in mapping.items():
            # Handle different data formats:
            # 1. List format: ["hebrew1", "hebrew2", "english_name", ...]
            # 2. Dict format: {"english": "...", "hebrew": "..."}
            english = ""
            hebrew = ""

            if isinstance(data, list):
                # List format - find English name (usually the last or contains English chars)
                for item in data:
                    if isinstance(item, str):
                        # Check if item looks like English (no Hebrew chars)
                        has_hebrew = any('\u0590' <= c <= '\u05FF' for c in item)
                        if not has_hebrew and item.strip():
                            english = item
                        elif has_hebrew and not hebrew:
                            hebrew = item
                # If no English found, use slug
                if not english:
                    english = slug
            elif isinstance(data, dict):
                # Dict format
                english = data.get("english", "")
                hebrew = data.get("hebrew", "")

            tree.insert("", tk.END, values=(slug, english, hebrew), tags=(slug,))

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        button_frame = theme.create_frame(content)
        button_frame.pack(fill=tk.X)

        def open_schema_editor():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a vendor.")
                return

            item = tree.item(selection[0])
            vendor_slug = item['values'][0]

            # Check if vendor already has cache entry
            cache_path = Path(__file__).parent.parent / "data" / "vendor_cache.json"
            vendor_data = None
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                    if vendor_slug in cache:
                        vendor_data = cache[vendor_slug]
            except:
                pass

            # Open schema editor with this vendor
            from .schema_editor_window import SchemaEditorWindow
            dialog.destroy()
            SchemaEditorWindow(self.root, vendor_slug, vendor_data)

        btn_select = theme.create_button(
            button_frame, "Edit Schema", command=open_schema_editor,
            style="primary", emoji="📋"
        )
        btn_select.pack(side=tk.LEFT, padx=(0, 10))

        btn_cancel = theme.create_button(
            button_frame, "Cancel", command=dialog.destroy,
            style="secondary"
        )
        btn_cancel.pack(side=tk.LEFT)

    def do_manage_vendor_cache(self):
        """Manage vendor cache (opens cache manager window)."""
        from .cache_manager_window import CacheManagerWindow
        CacheManagerWindow(self.root)

    # Layout review is automatically triggered by pipeline when confidence is low

    def do_improve_cache(self):
        """Improve cache for current vendor."""
        if self.last_vendor_info:
            vendor_slug = self.last_vendor_info.get('vendor_slug')
            if vendor_slug:
                # Open cache editor with this vendor
                from .cache_manager_window import CacheManagerWindow
                window = CacheManagerWindow(self.root)
                window.edit_vendor(vendor_slug)
        else:
            messagebox.showinfo("No Vendor", "No vendor detected to improve cache.")

    def _show_replace_schema_dialog(self, vendor_name, current_score, new_score):
        """
        Show dialog asking if user wants to replace schema with better one.

        Args:
            vendor_name: Vendor name
            current_score: Current trust score
            new_score: New trust score

        Returns:
            True if user wants to replace, False if user wants to keep current
        """
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Better Schema Detected")
        dialog.geometry("500x200")
        dialog.transient(self.root)
        dialog.grab_set()

        theme.configure_styles(dialog)

        # Content frame
        content = theme.create_frame(dialog, padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        # Title
        title = theme.create_label(
            content,
            text="📊 Better Schema Detected",
            font=theme.FONT_TITLE
        )
        title.pack(anchor=tk.W, pady=(0, 15))

        # Message
        message = f"Found better schema for '{vendor_name}'.\n\n"
        message += f"Current trust score: {current_score:.2f}\n"
        message += f"New trust score: {new_score:.2f}\n\n"
        message += "Replace with better schema?"

        msg_label = theme.create_label(
            content,
            text=message,
            font=theme.FONT_BODY,
            fg=theme.CLR_TEXT
        )
        msg_label.pack(anchor=tk.W, pady=(0, 20))

        # Button frame
        button_frame = theme.create_frame(content)
        button_frame.pack(fill=tk.X)

        # Variable to store user's choice
        user_choice = None
        choice_event = threading.Event()

        def on_replace():
            nonlocal user_choice
            user_choice = True
            dialog.destroy()
            choice_event.set()

        def on_keep():
            nonlocal user_choice
            user_choice = False
            dialog.destroy()
            choice_event.set()

        btn_replace = theme.create_button(
            button_frame, f"Replace ({new_score:.2f})", command=on_replace,
            style="primary", emoji="🔄"
        )
        btn_replace.pack(side=tk.LEFT, padx=(0, 10))

        btn_keep = theme.create_button(
            button_frame, f"Keep ({current_score:.2f})", command=on_keep,
            style="secondary"
        )
        btn_keep.pack(side=tk.LEFT)

        # Wait for user choice
        dialog.wait_window()  # This blocks until dialog is destroyed
        choice_event.wait()   # Ensure choice is set

        return user_choice

    def _show_edit_schema_low_confidence_dialog(self, vendor_name, current_score, new_score, schema_data):
        """
        Show dialog for low-confidence schema with three options: Edit, Replace, Keep.

        Args:
            vendor_name: Vendor name
            current_score: Current trust score
            new_score: New trust score
            schema_data: Pre-filled schema data for editor (dict)

        Returns:
            None/False: Keep current schema
            True: Replace with better schema
            dict: Edited schema data (when user chooses Edit)
        """
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Low Confidence Schema")
        dialog.geometry("550x250")
        dialog.transient(self.root)
        dialog.grab_set()

        theme.configure_styles(dialog)

        # Content frame
        content = theme.create_frame(dialog, padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        # Title
        title = theme.create_label(
            content,
            text="⚠️ Low Confidence Schema Detected",
            font=theme.FONT_TITLE
        )
        title.pack(anchor=tk.W, pady=(0, 15))

        # Message
        message = f"Both schemas for '{vendor_name}' have low confidence.\n\n"
        message += f"Current trust score: {current_score:.2f}\n"
        message += f"New trust score: {new_score:.2f}\n\n"
        message += "What would you like to do?"

        msg_label = theme.create_label(
            content,
            text=message,
            font=theme.FONT_BODY,
            fg=theme.CLR_TEXT
        )
        msg_label.pack(anchor=tk.W, pady=(0, 20))

        # Button frame
        button_frame = theme.create_frame(content)
        button_frame.pack(fill=tk.X)

        # Variable to store user's choice
        user_choice = None
        choice_event = threading.Event()

        def on_edit():
            nonlocal user_choice
            # Open SchemaEditorWindow with pre-filled data
            from .schema_editor_window import SchemaEditorWindow

            # Generate vendor slug from name (similar to phase6_vendor_cache)
            vendor_slug = vendor_name.lower().replace(" ", "_").replace("/", "_").replace("\\", "_")

            # Open editor
            editor = SchemaEditorWindow(self.root, vendor_slug, schema_data)

            # Wait for editor to close (editor handles its own window)
            # The editor saves directly to cache when user clicks Save
            dialog.destroy()
            choice_event.set()

            # Return special value to indicate "edited"
            user_choice = {"action": "edited", "vendor_slug": vendor_slug}

        def on_replace():
            nonlocal user_choice
            user_choice = True  # Replace
            dialog.destroy()
            choice_event.set()

        def on_keep():
            nonlocal user_choice
            user_choice = False  # Keep (False or None)
            dialog.destroy()
            choice_event.set()

        # Three buttons
        btn_edit = theme.create_button(
            button_frame, "Edit Cache", command=on_edit,
            style="primary", emoji="✏️"
        )
        btn_edit.pack(side=tk.LEFT, padx=(0, 10))

        btn_replace = theme.create_button(
            button_frame, f"Replace Anyway ({new_score:.2f})", command=on_replace,
            style="secondary"
        )
        btn_replace.pack(side=tk.LEFT, padx=(0, 10))

        btn_keep = theme.create_button(
            button_frame, f"Keep Current ({current_score:.2f})", command=on_keep,
            style="tertiary"
        )
        btn_keep.pack(side=tk.LEFT)

        # Wait for user choice
        dialog.wait_window()
        choice_event.wait()

        # If user chose "Edit", we need to indicate that schema was edited
        # The SchemaEditorWindow already saved it, so just return a dict
        if user_choice and isinstance(user_choice, dict) and user_choice.get("action") == "edited":
            return {"edited": True, "vendor_slug": user_choice.get("vendor_slug")}

        return user_choice

    def _show_create_cache_dialog(self, vendor_name, trust_score, column_info, quantity_pattern):
        """
        Show dialog asking if user wants to create cache entry for new vendor.

        Args:
            vendor_name: Vendor name
            trust_score: Calculated trust score (0.0-1.0)
            column_info: Column detection results
            quantity_pattern: Detected quantity pattern

        Returns:
            True if user wants to create cache, False if not
        """
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Create Cache Entry")
        dialog.geometry("550x300")
        dialog.transient(self.root)
        dialog.grab_set()

        theme.configure_styles(dialog)

        # Content frame
        content = theme.create_frame(dialog, padx=20, pady=20)
        content.pack(fill=tk.BOTH, expand=True)

        # Title
        title = theme.create_label(
            content,
            text="📋 Create Cache Entry for New Vendor",
            font=theme.FONT_TITLE
        )
        title.pack(anchor=tk.W, pady=(0, 15))

        # Message
        score_color = "🟢" if trust_score >= 0.6 else "🟡" if trust_score >= 0.4 else "🔴"
        message = f"New vendor detected: '{vendor_name}'\n\n"
        message += f"Trust score: {trust_score:.2f} {score_color} ("
        if trust_score >= 0.6:
            message += "Good"
        elif trust_score >= 0.4:
            message += "Low"
        else:
            message += "Very Low"
        message += ")\n\n"

        # Add column info if available
        if column_info and column_info.get('success'):
            detected_cols = column_info.get('detected_columns', [])
            if detected_cols:
                message += f"Detected {len(detected_cols)} columns:\n"
                for col in detected_cols[:3]:  # Show first 3 columns
                    message += f"  • {col.get('hebrew_text', '?')} → {col.get('assigned_field', '?')}\n"
                if len(detected_cols) > 3:
                    message += f"  • ... and {len(detected_cols) - 3} more\n"

        message += f"\nQuantity pattern: {quantity_pattern}\n\n"
        message += "Create cache entry for future receipts?"

        msg_label = theme.create_label(
            content,
            text=message,
            font=theme.FONT_BODY,
            fg=theme.CLR_TEXT,
            justify=tk.LEFT
        )
        msg_label.pack(anchor=tk.W, pady=(0, 20), fill=tk.X)

        # Button frame
        button_frame = theme.create_frame(content)
        button_frame.pack(fill=tk.X)

        # Variable to store user's choice
        user_choice = None
        choice_event = threading.Event()

        def on_create():
            nonlocal user_choice
            user_choice = True
            dialog.destroy()
            choice_event.set()

        def on_skip():
            nonlocal user_choice
            user_choice = False
            dialog.destroy()
            choice_event.set()

        btn_create = theme.create_button(
            button_frame, "Create Cache Entry", command=on_create,
            style="primary", emoji="💾"
        )
        btn_create.pack(side=tk.LEFT, padx=(0, 10))

        btn_skip = theme.create_button(
            button_frame, "Skip (Don't Create)", command=on_skip,
            style="secondary"
        )
        btn_skip.pack(side=tk.LEFT)

        # Wait for user choice
        dialog.wait_window()  # This blocks until dialog is destroyed
        choice_event.wait()   # Ensure choice is set

        return user_choice