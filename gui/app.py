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
    HAS_DND = False  # Disabled for stability
except ImportError:
    HAS_DND = False

# New structure imports
from stages.preprocess.image_loader import PreprocessConfig
from stages.preprocess.image_processor import preprocess_image
from stages.parsing.receipt_parser import parse_receipt
from stages.recognition.tesseract_client import recognize_boxes
from utils.io_utils import get_nested, load_config
from utils.text_normalization import load_confusion_map


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
            background=self._CLR_BG,
            lightcolor=self._CLR_BORDER,
            troughcolor=self._CLR_BG,
            bordercolor=self._CLR_BG,
            arrowcolor=self._CLR_TEXT,
            width=16,
        )
        style.map(
            "Vertical.TScrollbar",
            background=[("active", self._CLR_ACCENT)],
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

        # OCR method selector
        self.ocr_method = tk.StringVar(value="mindee")
        ttk.Label(bar, text="OCR:").pack(side=tk.LEFT, padx=(0, 5))
        self.cb_ocr = ttk.Combobox(bar, textvariable=self.ocr_method, values=["mindee", "tesseract", "google"], state="readonly", width=10)
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

        self.lbl_status = ttk.Label(
            bar, text="Ready", style="Status.TLabel"
        )
        self.lbl_status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Drop zone
        self.drop_zone = tk.Frame(
            self.root, bg=self._CLR_SURFACE, relief=tk.GROOVE, bd=2,
        )
        self.drop_zone.pack(fill=tk.BOTH, expand=True, padx=24, pady=8)
        tk.Label(
            self.drop_zone,
            text="Drag & drop image / PDF here\nor click Browse above",
            fg=self._CLR_SUBTEXT, font=("Segoe UI", 12), bg=self._CLR_SURFACE,
            justify=tk.CENTER,
        ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        if HAS_DND:
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)

        # Result panel
        self.result_pane = tk.Frame(self.root, bg=self._CLR_BG)
        self.result_pane.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 12))

        self.text_out = tk.Text(
            self.result_pane, wrap=tk.WORD, bg=self._CLR_SURFACE,
            fg=self._CLR_TEXT, font=("Consolas", 10),
            insertbackground=self._CLR_TEXT,
            selectbackground=self._CLR_ACCENT,
            relief=tk.FLAT, padx=14, pady=10,
        )
        self.text_out.pack(fill=tk.BOTH, expand=True)

        # Scrollbar
        sb = ttk.Scrollbar(self.result_pane, orient=tk.VERTICAL,
                           command=self.text_out.yview)
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
                ocr_method = self.ocr_method.get()

                if ocr_method == "mindee":
                    # Use combined pipeline (Google Vision for header + Mindee for items)
                    from stages.parsing import parse_receipt_combined
                    result = parse_receipt_combined(file_path, header_ocr='google')
                    self.last_result = result.to_gdocument_dict()
                    self.last_input_path = file_path

                    self.root.after(0, lambda: self._log(json.dumps(result.to_gdocument_dict(), indent=2, ensure_ascii=False)))
                    self.root.after(0, lambda: self._set_busy(False))
                    self.root.after(0, lambda: self.lbl_status.config(text="Done \u2705"))
                    return
                    self.root.after(0, lambda: self._log(json.dumps(result, indent=2, ensure_ascii=False)))
                    self.root.after(0, lambda: self._set_busy(False))
                    self.root.after(0, lambda: self.lbl_status.config(text="Done \u2705"))
                    return

                elif ocr_method == "google":
                    # Use Google Cloud pipeline
                    from pipelines.google_pipeline import process_receipt
                    credentials_path = get_nested(self.cfg, "google.credentials_path", "")
                    if not credentials_path:
                        raise ValueError("Google credentials not configured in config")
                    result = process_receipt(file_path, credentials_path=credentials_path)
                    self.last_result = result
                    self.last_input_path = file_path

                    items = result.get("GDocument", {}).get("fields", {}).get("items", [])
                    self.root.after(0, lambda: self._log(f"Google extracted {len(items)} items"))
                    self.root.after(0, lambda: self._log(json.dumps(result, indent=2, ensure_ascii=False)))
                    self.root.after(0, lambda: self._set_busy(False))
                    self.root.after(0, lambda: self.lbl_status.config(text="Done \u2705"))
                    return

                else:
                    # Use Tesseract pipeline
                    from pipelines.tesseract_pipeline import process_receipt
                    result = process_receipt(file_path)
                    self.last_result = result
                    self.last_input_path = file_path

                    items = result.get("GDocument", {}).get("fields", {}).get("items", [])
                    self.root.after(0, lambda: self._log(f"Tesseract extracted {len(items)} items"))
                    self.root.after(0, lambda: self._log(json.dumps(result, indent=2, ensure_ascii=False)))
                    self.root.after(0, lambda: self._set_busy(False))
                    self.root.after(0, lambda: self.lbl_status.config(text="Done \u2705"))
                    return

            except Exception as e:
                import traceback
                self.root.after(0, lambda: self._log(f"Error: {e}"))
                self.root.after(0, lambda: self._log(traceback.format_exc()))
                self.root.after(0, self._set_busy)
                self.root.after(0, lambda: self.lbl_status.config(text="Error \u274c"))

        threading.Thread(target=run, daemon=True).start()

    def do_save_folder(self):
        if not self.last_result:
            messagebox.showwarning("No result", "Process a receipt first.")
            return

        # Get vendor and date from GDocument result
        vendor = None
        date = None
        for f in self.last_result.get("GDocument", {}).get("fields", []):
            if f.get("name") == "VendorNameS":
                vendor = f.get("value", "")
            elif f.get("name") == "Date":
                date = f.get("value", "")

        if not vendor:
            vendor = "Unknown"
        if not date:
            date = "Unknown"

        # Generate filename: Vendor_Date (e.g., "StraussCool_18.08.2024")
        # Format date as DD.MM.YYYY
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

        # Copy original file
        dst_file = output / Path(self.last_input_path).name
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


def main():
    root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    app = ReceiptOCRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()