import json
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

# Must install tkinterdnd2 to use drag and drop
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False
    print("tkinterdnd2 not installed. Drag and drop will be disabled.")

from receipt_ocr.ocr_preprocess import PreprocessConfig, preprocess_image
from receipt_ocr.parse_receipt import parse_receipt
from receipt_ocr.recognize_tesseract import recognize_boxes
from receipt_ocr.cli import _load_confusion_map_from_config
from receipt_ocr.utils.io_utils import get_nested, load_config
import test_accuracy.cli as test_cli

class ReceiptOCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Receipt OCR & Evaluator")
        self.root.geometry("800x600")

        self.cfg = load_config("config.yml")
        
        self.build_ui()

    def build_ui(self):
        # Top Frame for buttons
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        self.btn_browse = ttk.Button(top_frame, text="Browse Image/PDF", command=self.do_browse)
        self.btn_browse.pack(side=tk.LEFT, padx=5)

        self.btn_test = ttk.Button(top_frame, text="Run Test Evaluation", command=self.do_test)
        self.btn_test.pack(side=tk.LEFT, padx=5)

        if HAS_DND:
            lbl_dnd = ttk.Label(top_frame, text="[Drag & Drop supported below]")
            lbl_dnd.pack(side=tk.RIGHT, padx=5)

        # Main Text Area
        self.text_out = tk.Text(self.root, wrap=tk.WORD, bg="#f4f4f4", font=("Consolas", 10))
        self.text_out.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # DND Support
        if HAS_DND:
            self.text_out.drop_target_register(DND_FILES)
            self.text_out.dnd_bind('<<Drop>>', self.on_drop)

    def log(self, message):
        self.text_out.insert(tk.END, message + "\n")
        self.text_out.see(tk.END)

    def clear_log(self):
        self.text_out.delete(1.0, tk.END)

    def on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        if files:
            self.process_file(files[0])

    def do_browse(self):
        file_path = filedialog.askopenfilename(
            title="Select Receipt Image",
            filetypes=[("Image/PDF files", "*.pdf *.png *.jpg *.jpeg"), ("All files", "*.*")]
        )
        if file_path:
            self.process_file(file_path)

    def process_file(self, file_path):
        self.clear_log()
        self.log(f"Processing: {file_path}...\n")
        
        def run():
            try:
                pp_cfg = PreprocessConfig(
                    target_height=int(get_nested(self.cfg, "preprocess.target_height", default=1600)),
                    target_width=int(get_nested(self.cfg, "preprocess.target_width", default=1200)),
                    adaptive_threshold_block_size=int(get_nested(self.cfg, "preprocess.adaptive_threshold_block_size", default=31)),
                    adaptive_threshold_C=int(get_nested(self.cfg, "preprocess.adaptive_threshold_C", default=10)),
                )
                pres = preprocess_image(file_path, cfg=pp_cfg, debug_enabled=False)
                tesseract_executable = get_nested(self.cfg, "tesseract.executable_path", default=None)
                confusion_map = _load_confusion_map_from_config(self.cfg)
                
                all_recognized_boxes = []
                for page_idx, pre in enumerate(pres):
                    recognized_boxes = recognize_boxes(
                        preprocessed_image=pre.preprocessed,
                        detected_boxes=[],
                        tesseract_executable=tesseract_executable,
                        confusion_map=confusion_map,
                        page_idx=page_idx,
                    )
                    all_recognized_boxes.extend(recognized_boxes)
                
                parsed = parse_receipt(all_recognized_boxes)
                res = parsed.to_gdocument_dict()
                self.root.after(0, self.log, json.dumps(res, indent=2, ensure_ascii=False))
            except Exception as e:
                self.root.after(0, self.log, f"Error: {e}")
        
        threading.Thread(target=run, daemon=True).start()

    def do_test(self):
        self.clear_log()
        self.log("Running Evaluation on sample_images folder...\nThis may take a minute.")
        
        def run():
            try:
                # Mock args to run the CLI programmatically
                import sys
                old_stdout = sys.stdout
                from io import StringIO
                captured = StringIO()
                sys.stdout = captured
                
                try:
                    sys.argv = ["--images-dir", "sample_images", "--config", "config.yml"]
                    test_cli.main(sys.argv)
                except SystemExit:
                    pass
                finally:
                    sys.stdout = old_stdout
                
                output = captured.getvalue()
                self.root.after(0, self.log, output)
            except Exception as e:
                self.root.after(0, self.log, f"Error: {e}")
                
        threading.Thread(target=run, daemon=True).start()

def main():
    if HAS_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = ReceiptOCRApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
