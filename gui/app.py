import json
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
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
        self.root.title("Receipt OCR & Evaluator")
        self.root.geometry("800x700")

        try:
            self.cfg = load_config()
        except:
            self.cfg = {}
            
        self.last_result = None
        self.is_processing = False
        self.animation_frames = [
            "  [ Kfir .     ]  ", "  [ . Kfir .   ]  ", "  [ . . Kfir . ]  ",
            "  [ . . . Kfir ]  ", "  [ . . . . Kfir] ", "  [ . . . . . Kfir]",
            "  [ . . . . . Kfir ]", "  [ . . . . Kfir . ]", "  [ . . . Kfir . . ]",
            "  [ . . Kfir . . . ]", "  [ . Kfir . . . . ]", "  [ Kfir . . . . . ]"
        ]
        self.current_frame = 0
        self.build_ui()

    def build_ui(self):
        top_frame = ttk.Frame(self.root, padding=10); top_frame.pack(fill=tk.X)
        self.btn_browse = ttk.Button(top_frame, text="Browse Image/PDF", command=self.do_browse); self.btn_browse.pack(side=tk.LEFT, padx=5)
        self.btn_test = ttk.Button(top_frame, text="Run Test Evaluation", command=self.do_test); self.btn_test.pack(side=tk.LEFT, padx=5)
        self.btn_save = ttk.Button(top_frame, text="Download JSON", command=self.do_save_json, state=tk.DISABLED); self.btn_save.pack(side=tk.LEFT, padx=5)
        self.lbl_status = ttk.Label(top_frame, text="", font=("Consolas", 10, "bold")); self.lbl_status.pack(side=tk.LEFT, padx=10)
        
        self.text_out = tk.Text(self.root, wrap=tk.WORD, bg="#f4f4f4", font=("Consolas", 10)); self.text_out.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        footer_frame = ttk.Frame(self.root, padding=2); footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Label(footer_frame, text="All rights belong to Kfir Ezer", font=("Arial", 8)).pack(side=tk.RIGHT, padx=10)

        if HAS_DND:
            self.text_out.drop_target_register(DND_FILES)
            self.text_out.dnd_bind('<<Drop>>', self.on_drop)

    def update_animation(self):
        if self.is_processing:
            self.lbl_status.config(text=self.animation_frames[self.current_frame])
            self.current_frame = (self.current_frame + 1) % len(self.animation_frames)
            self.root.after(100, self.update_animation)
        else: self.lbl_status.config(text="")

    def start_processing(self):
        self.is_processing = True
        self.btn_browse.config(state=tk.DISABLED)
        self.btn_test.config(state=tk.DISABLED)
        self.btn_save.config(state=tk.DISABLED)
        self.update_animation()

    def stop_processing(self, has_result=False):
        self.is_processing = False
        self.btn_browse.config(state=tk.NORMAL)
        self.btn_test.config(state=tk.NORMAL)
        if has_result: self.btn_save.config(state=tk.NORMAL)

    def log(self, message): self.text_out.insert(tk.END, message + "\n"); self.text_out.see(tk.END)
    def clear_log(self): self.text_out.delete(1.0, tk.END)

    def on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        if files: self.process_file(files[0])

    def do_browse(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image/PDF files", "*.pdf *.png *.jpg *.jpeg"), ("All files", "*.*")])
        if file_path: self.process_file(file_path)

    def do_save_json(self):
        if not self.last_result: return
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], initialfile="result.json")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.last_result, f, indent=2, ensure_ascii=False)

    def process_file(self, file_path):
        self.clear_log(); self.log(f"Processing: {file_path}...\n"); self.start_processing()
        def run():
            try:
                pp_cfg = PreprocessConfig(
                    target_height=int(get_nested(self.cfg, "preprocess.target_height", 2400)),
                    target_width=int(get_nested(self.cfg, "preprocess.target_width", 1800)),
                )
                pres = preprocess_image(file_path, cfg=pp_cfg)
                tesseract_executable = get_nested(self.cfg, "tesseract.executable_path")
                
                # Dynamic path to confusion map
                conf_map_path = Path(__file__).resolve().parent.parent / "confusion_map.json"
                confusion_map = load_confusion_map(conf_map_path) if conf_map_path.is_file() else {}
                
                all_boxes = []
                for i, pre in enumerate(pres):
                    boxes = recognize_boxes(pre.preprocessed, tesseract_executable=tesseract_executable, confusion_map=confusion_map, page_idx=i)
                    all_boxes.extend(boxes)
                
                parsed = parse_receipt(all_boxes)
                self.last_result = parsed.to_gdocument_dict()
                self.root.after(0, self.log, json.dumps(self.last_result, indent=2, ensure_ascii=False))
                self.root.after(0, lambda: self.stop_processing(has_result=True))
            except Exception as e:
                self.root.after(0, self.log, f"Error: {e}")
                self.root.after(0, self.stop_processing)
        threading.Thread(target=run, daemon=True).start()

    def do_test(self):
        self.clear_log()
        self.log("Starting Automated Evaluation (this may take several minutes)...\n")
        self.start_processing()
        
        def run():
            import sys
            import io
            from test_accuracy.cli import main as test_main
            
            class StdoutRedirector:
                def __init__(self, log_func, root):
                    self.log_func = log_func
                    self.root = root
                def write(self, s):
                    if s:
                        self.root.after(0, lambda: self.log_func(s))
                def flush(self):
                    pass
            
            # Helper to log without adding extra newlines (since stdout already has them)
            def log_raw(text):
                self.text_out.insert(tk.END, text)
                self.text_out.see(tk.END)

            old_stdout = sys.stdout
            sys.stdout = StdoutRedirector(log_raw, self.root)
            try:
                # Run with default arguments (sample_images directory)
                test_main([])
            except Exception as e:
                self.root.after(0, lambda: self.log(f"\nEvaluation Error: {e}"))
            finally:
                sys.stdout = old_stdout
                self.root.after(0, lambda: self.stop_processing())
                self.root.after(0, lambda: self.log("\nEvaluation Complete."))
                
        threading.Thread(target=run, daemon=True).start()

def main():
    root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    app = ReceiptOCRApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
