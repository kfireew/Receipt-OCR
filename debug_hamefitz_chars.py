import os
import sys
import yaml
from pathlib import Path
import pytesseract
import cv2

# Add current directory to path
sys.path.append(os.getcwd())

from receipt_ocr.ocr_preprocess import preprocess_image, PreprocessConfig
from receipt_ocr.recognize_tesseract import recognize_boxes
from receipt_ocr.parse_receipt import _boxes_to_lines

def main():
    with open("config.yml", "r") as f:
        config = yaml.safe_load(f)

    tesseract_cmd = config.get("tesseract", {}).get("executable_path")

    pdf_path = Path("sample_images/Hamefitz_27.12.2024_Hamefitz 15-01-25 A.pdf")
    preprocess_cfg = PreprocessConfig() 

    output_path = Path("debug_hamefitz_raw.txt")
    with open(output_path, "w", encoding="utf-8") as f_out:
        print(f"Analyzing {pdf_path.name} at resolution {preprocess_cfg.target_height}...")
        pages = preprocess_image(pdf_path, cfg=preprocess_cfg)
        for i, page in enumerate(pages):
            f_out.write(f"Page {i}:\n")
            boxes = recognize_boxes(page.preprocessed, page_idx=i, use_multi_psm=True, tesseract_executable=tesseract_cmd)
            lines = _boxes_to_lines(boxes)
            for j, line in enumerate(lines):
                f_out.write(f"Line {j}: {line.text_raw}\n")

    print(f"Done. Output written to {output_path}")

if __name__ == "__main__":
    main()
