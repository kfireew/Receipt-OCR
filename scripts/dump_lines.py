import json
import argparse
from pathlib import Path
from receipt_ocr.ocr_preprocess import PreprocessConfig, preprocess_image
from receipt_ocr.parse_receipt import parse_receipt
from receipt_ocr.recognize_tesseract import recognize_boxes
from receipt_ocr.utils.io_utils import load_config
from receipt_ocr.cli import _load_confusion_map_from_config

def get_raw_lines(pdf_name="Avikam_10.03.2025_Avikam 11-03-25.pdf"):
    image_path = Path(f"sample_images/{pdf_name}")
    cfg = load_config("config.yml")
    
    pre = preprocess_image(image_path=image_path, cfg=PreprocessConfig(target_height=1600, target_width=1200, adaptive_threshold_block_size=31, adaptive_threshold_C=10), debug_dir=None, debug_enabled=False)
    tesseract_executable = cfg.get("tesseract", {}).get("executable_path")
    confusion_map = _load_confusion_map_from_config(cfg)
    
    recognized_boxes = recognize_boxes(
        preprocessed_image=pre.preprocessed,
        detected_boxes=[],
        tesseract_executable=tesseract_executable,
        confusion_map=confusion_map,
    )
    
    parsed = parse_receipt(recognized_boxes)
    # write to file
    with open("lines_out.json", "w", encoding="utf-8") as f:
        json.dump(parsed.to_dict(), f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "Avikam_10.03.2025_Avikam 11-03-25.pdf"
    get_raw_lines(name)
