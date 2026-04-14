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

# Mindee SDK V2 needs MINDEE_V2_API_KEY
if not os.environ.get("MINDEE_V2_API_KEY") and os.environ.get("MINDEE_API_KEY"):
    os.environ["MINDEE_V2_API_KEY"] = os.environ["MINDEE_API_KEY"]

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


class ReceiptOCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Receipt OCR")
        self.root.geometry("900x750")
        self.root.minsize(700, 500)

        # Configure style/theme
        self._setup_theme()

        try:
            self.cfg = load_config()
        except Exception:
            self.cfg = {}

        self.last_result = None
        self.last_input_path = None
        self.is_processing = False
        self.spin_var = tk.IntVar(value=0)
        self.spin_frames = ["\u280b", "\u2819", "\u2839", "\u283d", "\u2836", "\u2826", "\u282b", "\u2827", "\u281f"]

        self._build_ui()

    # -- theme ----------------------------------------------------------

    def _setup_theme(self):
        self._CLR_BG = "#f0f0f0"
        self._CLR_SURFACE = "#ffffff"
        self._CLR_ACCENT = "#2563eb"
        self._CLR_TEXT = "#1f2937"
        self._CLR_SUBTEXT = "#6b7280"
        self._CLR_BORDER = "#e5e7eb"

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", font=("Segoe UI", 10))
        style.configure("TFrame", background=self._CLR_BG)
        style.configure("TLabel", background=self._CLR_BG, foreground=self._CLR_TEXT)
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Secondary.TButton")
        style.configure("Status.TLabel", foreground=self._CLR_SUBTEXT, font=("Segoe UI", 9))

        style.configure(
            "Vertical.TScrollbar",
            background=self._CLR_SURFACE,
            lightcolor=self._CLR_BORDER,
            troughcolor=self._CLR_BG,
            bordercolor=self._CLR_BORDER,
            arrowcolor=self._CLR_TEXT,
            width=14,
        )
        style.map(
            "Vertical.TScrollbar",
            background=[("active", self._CLR_SURFACE)],
        )

        self.root.configure(bg=self._CLR_BG)

    # -- layout ---------------------------------------------------------

    def _build_ui(self):
        # Header
        hdr = ttk.Frame(self.root, padding=(24, 20, 24, 10))
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr, text="Receipt OCR", font=("Segoe UI", 22, "bold"),
            fg=self._CLR_ACCENT, bg=self._CLR_BG,
        ).pack(anchor=tk.W)
        tk.Label(
            hdr, text="Upload an image or PDF — results can be saved as a folder",
            fg=self._CLR_SUBTEXT, font=("Segoe UI", 10), bg=self._CLR_BG,
        ).pack(anchor=tk.W, pady=(0, 4))

        # Action bar
        bar = ttk.Frame(self.root, padding=(24, 4))
        bar.pack(fill=tk.X)

        # OCR method selector (just Mindee now)
        self.ocr_method = tk.StringVar(value="mindee")
        ttk.Label(bar, text="OCR:").pack(side=tk.LEFT, padx=(0, 5))
        self.cb_ocr = ttk.Combobox(bar, textvariable=self.ocr_method, values=["mindee"], state="readonly", width=10)
        self.cb_ocr.pack(side=tk.LEFT, padx=(0, 15))
        self.cb_ocr.bind("<<ComboboxSelected>>", lambda e: self._log(f"OCR: {self.ocr_method.get()}"))

        self.btn_browse = ttk.Button(
            bar, text="\U0001f4c2 Browse", style="Primary.TButton",
            command=self.do_browse,
        )
        self.btn_browse.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_save_folder = ttk.Button(
            bar, text="\U0001f4be Save as Folder", style="Secondary.TButton",
            command=self.do_save_folder, state=tk.DISABLED,
        )
        self.btn_save_folder.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_add_vendor = ttk.Button(
            bar, text="\U0001f4dd Add Vendor", style="Secondary.TButton",
            command=self.do_add_vendor,
        )
        self.btn_add_vendor.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_status = ttk.Label(
            bar, text="Ready", style="Status.TLabel"
        )
        self.lbl_status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Drop zone - fixed height
        self.drop_zone = tk.Frame(
            self.root, bg=self._CLR_SURFACE, relief=tk.GROOVE, bd=2, height=100,
        )
        self.drop_zone.pack(fill=tk.X, padx=24, pady=8)
        self.drop_zone.pack_propagate(False)
        tk.Label(
            self.drop_zone,
            text="Drag & drop image / PDF here\nor click Browse above",
            fg=self._CLR_SUBTEXT, font=("Segoe UI", 12), bg=self._CLR_SURFACE,
            justify=tk.CENTER,
        ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        if HAS_DND:
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)

        # Result panel with fixed size to prevent resizing
        self.result_pane = tk.Frame(self.root, bg=self._CLR_BG)
        self.result_pane.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 12))
        self.result_pane.pack_propagate(False)

        # Text area
        self.text_out = tk.Text(
            self.result_pane, wrap=tk.WORD, bg=self._CLR_SURFACE,
            fg=self._CLR_TEXT, font=("Consolas", 10),
            insertbackground=self._CLR_TEXT,
            selectbackground=self._CLR_ACCENT,
            relief=tk.FLAT, padx=14, pady=10,
        )
        self.text_out.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar - properly linked
        sb = ttk.Scrollbar(self.result_pane, orient=tk.VERTICAL)
        sb.config(command=self.text_out.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_out.config(yscrollcommand=sb.set)

        # Footer
        tk.Label(
            self.root,
            text="All rights belong to Kfir Ezer",
            fg=self._CLR_SUBTEXT,
            font=("Segoe UI", 8),
            bg=self._CLR_BG,
        ).pack(pady=(0, 4))

    # -- state helpers --------------------------------------------------

    def _set_busy(self, busy: bool):
        self.is_processing = busy
        self.btn_browse.config(state=tk.DISABLED if busy else tk.NORMAL)
        self.btn_save_folder.config(
            state=tk.DISABLED if busy else (tk.NORMAL if self.last_result else tk.DISABLED),
        )

    def _log(self, message: str):
        self.text_out.config(state=tk.NORMAL)
        self.text_out.insert(tk.END, message + "\n")
        self.text_out.see(tk.END)
        self.text_out.config(state=tk.NORMAL)

    def _clear_log(self):
        self.text_out.config(state=tk.NORMAL)
        self.text_out.delete(1.0, tk.END)

    def _spin_animation(self):
        if self.is_processing:
            idx = self.spin_var.get()
            self.lbl_status.config(text=self.spin_frames[idx])
            self.spin_var.set((idx + 1) % len(self.spin_frames))
            self.root.after(120, self._spin_animation)
        else:
            self.lbl_status.config(text="Ready")

    # -- callbacks ------------------------------------------------------

    def _on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        if files:
            self._process_file(files[0])

    def do_browse(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Image/PDF files", "*.pdf *.png *.jpg *.jpeg"), ("All files", "*.*")],
        )
        if file_path:
            self._process_file(file_path)

    def _process_file(self, file_path: str):
        self._clear_log()
        self._set_busy(True)
        self._spin_animation()
        self._log(f"Processing: {file_path}")
        self._log(f"OCR method: {self.ocr_method.get()}")

        def run():
            try:
                # Use Mindee pipeline
                from pipelines.mindee_pipeline import process_receipt
                result = process_receipt(file_path)
                self.last_result = result
                self.last_input_path = file_path

                # Extract items from GDocument.groups[0].groups (table items)
                gdoc = result.get("GDocument", {})
                groups = gdoc.get("groups", [])
                items_count = 0
                if groups and len(groups) > 0:
                    table_group = groups[0]
                    table_items = table_group.get("groups", [])
                    items_count = len(table_items)

                self.root.after(0, lambda: self._log(f"Mindee extracted {items_count} items"))
                self.root.after(0, lambda: self._log(json.dumps(result, indent=2, ensure_ascii=False)))
                self.root.after(0, lambda: self._set_busy(False))
                self.root.after(0, lambda: self.lbl_status.config(text="Done \u2705"))
                return

            except Exception as e:
                import traceback
                self.root.after(0, lambda: self._log(f"Error: {e}"))
                self.root.after(0, lambda: self._log(traceback.format_exc()))
                self.root.after(0, lambda: self._set_busy(False))
                self.root.after(0, lambda: self.lbl_status.config(text="Error \u274c"))

        threading.Thread(target=run, daemon=True).start()

    def do_save_folder(self):
        if not self.last_result:
            messagebox.showwarning("No result", "Process a receipt first.")
            return

        # Get vendor and date from GDocument result
        gdoc = self.last_result.get("GDocument", {})
        vendor = ""
        date = ""

        # Vendor and date are in top-level fields
        for f in gdoc.get("fields", []):
            if f.get("name") == "VendorName":
                vendor = f.get("value", "")
            elif f.get("name") == "Date":
                date = f.get("value", "")

        if not vendor:
            vendor = "Unknown"
        if not date:
            date = "Unknown"

        # Generate filename: Vendor_Date (e.g., "StraussCool_18.08.2024")
        # Format date as DD.MM.YYYY
        receipt_name = None  # Initialize to avoid UnboundLocalError
        if vendor and date and date != "Unknown":
            # Convert date from DD-MM-YY to DD.MM.YYYY if needed
            date_clean = date.replace("-", ".")
            if len(date_clean.split('.')) == 3 and len(date_clean.split('.')[-1]) == 2:
                # Already has 2-digit year
                pass
            receipt_name = f"{vendor}_{date_clean}"
        else:
            receipt_name = f"{vendor}_{date}" if vendor else "Unknown"

        # Also create full filename for JSON: Vendor_Date_Vendor Date (e.g., "StraussCool_18.08.2024_StraussCool 18-08-24")
        if vendor and date and date != "Unknown":
            parts = date.split('.')
            if len(parts) == 3:
                date_dash = f"{parts[0]}-{parts[1]}-{parts[2][-2:]}"
            else:
                date_dash = date.replace('.', '-')
            full_name = f"{vendor}_{date}_{vendor} {date_dash}"
        else:
            full_name = receipt_name

        folder_path = filedialog.askdirectory(
            title="Choose where to save the folder",
        )
        if not folder_path:
            return

        output = Path(folder_path) / receipt_name
        output.mkdir(parents=True, exist_ok=True)

        # Rename PDF to Vendor_Date format
        ext = Path(self.last_input_path).suffix
        dst_file = output / f"{full_name}{ext}"
        shutil.copy2(self.last_input_path, dst_file)

        # Save JSON: Vendor_Date_Vendor Date.JSON
        json_path = output / f"{full_name}.JSON"
        json_path.write_text(
            json.dumps(self.last_result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # Also copy to clipboard in GDocument format
        self.root.clipboard_clear()
        self.root.clipboard_append(json.dumps(self.last_result, ensure_ascii=False))

        messagebox.showinfo("Saved", f"Folder created:\n{output}\n\nJSON copied to clipboard!")
        self._log(f"\nSaved to folder: {output}")

    def do_add_vendor(self):
        """Open dialog to add a new vendor to merchants_mapping.json"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Vendor")
        dialog.geometry("500x380")
        dialog.transient(self.root)
        dialog.grab_set()

        # Load current mapping
        mapping_path = PROJECT_ROOT / "merchants_mapping.json"
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                merchants = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load merchants_mapping.json: {e}")
            dialog.destroy()
            return

        # UI Elements
        main_frame = tk.Frame(dialog, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="Vendor Name (English):", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        entry_name = tk.Entry(main_frame, font=("Segoe UI", 11), width=30)
        entry_name.pack(anchor=tk.W, pady=(0, 15))

        # Debounce for suggestions
        suggestion_job = [None]

        tk.Label(main_frame, text="Keywords (Hebrew/English, comma separated):", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        entry_keywords = tk.Entry(main_frame, font=("Segoe UI", 11), width=40)
        entry_keywords.pack(anchor=tk.W, pady=(0, 10))

        # Suggested keywords label
        lbl_suggested = tk.Label(main_frame, text="", fg="#6b7280", font=("Segoe UI", 9))
        lbl_suggested.pack(anchor=tk.W, pady=(0, 5))

        # Build pattern lookup from existing merchants dynamically
        _NAME_PATTERNS = {}
        for vendor, kw_list in merchants.items():
            vendor_lower = vendor.lower()
            for kw in kw_list:
                # Extract first 2-4 chars as pattern
                if len(kw) >= 2:
                    _NAME_PATTERNS[vendor_lower] = kw[:4]
                    if len(vendor_lower) >= 3:
                        _NAME_PATTERNS[vendor_lower[:3]] = kw[:4]
                    break

        _EN_TO_HE = {
            'a': 'ה', 'b': 'ב', 'c': 'ק', 'd': 'ד', 'e': 'א', 'f': 'פ', 'g': 'ג', 'h': 'ה',
            'i': 'ע', 'j': 'ג', 'k': 'ק', 'l': 'ל', 'm': 'מ', 'n': 'נ', 'o': 'ו', 'p': 'פ',
            'q': 'ק', 'r': 'ר', 's': 'ס', 't': 'ט', 'u': 'יו', 'v': 'ו', 'w': 'ו', 'x': 'קס',
            'y': 'י', 'z': 'ז',
        }
        _CLUSTERS = {'sh': 'ש', 'ch': 'ח', 'th': 'ת', 'ou': 'או', 'ee': 'י', 'oo': 'ו'}

        def transliterate(name: str) -> str:
            """Fallback transliteration with smart patterns"""
            if not name:
                return ""
            name_lower = name.lower()

            # Check pattern lookup first
            if name_lower in _NAME_PATTERNS:
                return _NAME_PATTERNS[name_lower]
            for pattern, hebrew in _NAME_PATTERNS.items():
                if name_lower.startswith(pattern):
                    prefix = hebrew
                    remainder = ""
                    for c in name_lower[len(pattern):]:
                        remainder += _EN_TO_HE.get(c, c)
                    return prefix + remainder

            # Fallback letter by letter
            result = ""
            i = 0
            while i < len(name_lower):
                if i < len(name_lower) - 1:
                    cluster = name_lower[i:i+2]
                    if cluster in _CLUSTERS:
                        result += _CLUSTERS[cluster]
                        i += 2
                        continue
                c = name_lower[i]
                result += _EN_TO_HE.get(c, c)
                i += 1
            return result

        def translate_to_hebrew(name: str) -> str:
            """Translate English to Hebrew with fallback and retries"""
            # Try Google Translate up to 2 times
            if HAS_TRANSLATOR:
                for attempt in range(2):
                    try:
                        result = GoogleTranslator(source='en', target='iw').translate(name)
                        if result and len(result) > 1 and not result.startswith('http'):
                            return result
                    except Exception:
                        import time
                        time.sleep(0.3)
            # Fallback to transliteration
            return transliterate(name)

        # Patch stdout for Hebrew output
        import sys
        if sys.stdout.encoding != 'utf-8':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

        # Helper to generate suggestions
        def generate_suggestions():
            name = entry_name.get().strip()
            if not name:
                lbl_suggested.config(text="")
                return

            # Gather all used keywords from existing merchants
            used_keywords = set()
            for kw_list in merchants.values():
                used_keywords.update(kw_list)

            hebrew = translate_to_hebrew(name)
            suggestions = []

            if hebrew and len(hebrew) >= 3:
                # Short form (first 2-3 chars for short names)
                short = hebrew[:2] if len(hebrew) <= 3 else hebrew[:3]
                if short not in used_keywords:
                    suggestions.append(short)

            # Full form
            if hebrew and hebrew not in used_keywords:
                suggestions.append(hebrew)

            # English lowercase
            if name.lower() not in used_keywords:
                suggestions.append(name.lower())

            # Full English
            if name not in used_keywords:
                suggestions.append(name)

            # Dedupe while preserving order
            seen = set()
            unique = []
            for s in suggestions:
                if s not in seen:
                    seen.add(s)
                    unique.append(s)

            if not unique:
                lbl_suggested.config(text="(all keywords already exist)")
            else:
                lbl_suggested.config(text="Suggested: " + ", ".join(unique[:4]))

            # Auto-fill with suggestions
            entry_keywords.delete(0, tk.END)
            entry_keywords.insert(0, ", ".join(unique[:4]) if unique else "")

        def debounce_suggestions():
            if suggestion_job[0]:
                dialog.after_cancel(suggestion_job[0])
            suggestion_job[0] = dialog.after(300, lambda: generate_suggestions())

        entry_name.bind("<KeyRelease>", lambda e: debounce_suggestions())

        # Buttons
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        def save_vendor():
            name = entry_name.get().strip()
            keywords = entry_keywords.get().strip()

            if not name:
                messagebox.showwarning("Missing Name", "Please enter a vendor name.")
                return
            if not keywords:
                messagebox.showwarning("Missing Keywords", "Please enter at least one keyword.")
                return

            # Parse keywords
            kw_list = [k.strip() for k in keywords.split(",") if k.strip()]

            if name in merchants:
                if not messagebox.askyesno("Vendor Exists", f"'{name}' already exists. Overwrite?"):
                    return

            # Save to mapping
            merchants[name] = kw_list
            try:
                with open(mapping_path, "w", encoding="utf-8") as f:
                    json.dump(merchants, f, ensure_ascii=False, indent=2)
                messagebox.showinfo("Saved", f"Vendor '{name}' added to merchants_mapping.json")
                self._log(f"Added vendor: {name} -> {kw_list}")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {e}")

        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="Save", style="Primary.TButton", command=save_vendor).pack(side=tk.LEFT)


def main():
    root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    app = ReceiptOCRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()