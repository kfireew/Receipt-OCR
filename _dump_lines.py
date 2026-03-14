import sys, json, pathlib
sys.path.insert(0, r'C:\Users\Kfir Ezer\Desktop\Receipt OCR')

from stages.preprocess.image_processor import preprocess_image
from stages.recognition.tesseract_client import recognize_boxes
from stages.grouping.line_assembler import _boxes_to_lines
from stages.recognition.box_refiner import deduplicate_boxes

img_path = r'C:\Users\Kfir Ezer\Desktop\Receipt OCR\sample_images\Avikam_10.03.2025_Avikam 11-03-25.pdf'

pages = preprocess_image(img_path)
all_boxes = []
for pi, pg in enumerate(pages):
    boxes = recognize_boxes(
        pg.preprocessed,
        tesseract_executable=r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        confusion_map=str(pathlib.Path(r'C:\Users\Kfir Ezer\Desktop\Receipt OCR') / 'confusion_map.json'),
        lang='heb+eng',
        page_idx=pi,
    )
    all_boxes.extend(boxes)

deduped = deduplicate_boxes(all_boxes)
raw_lines = _boxes_to_lines(deduped)

print(f"Total boxes: {len(all_boxes)}, after dedup: {len(deduped)}, lines: {len(raw_lines)}")
print()
print("=== FIRST 20 LINES (raw_text) ===")
with open('raw_lines_dump.txt', 'w', encoding='utf-8') as f:
    for ln in raw_lines:
        f.write(f"[{ln.index}] raw: {ln.text_raw!r}\n")
        f.write(f"      norm:{ln.text_normalized!r}\n")
    
for ln in raw_lines[:20]:
    print(f"[{ln.index}] raw: {ln.text_raw!r}")
print()
print("Saved all lines to raw_lines_dump.txt")
