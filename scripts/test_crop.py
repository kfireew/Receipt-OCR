import cv2
from pathlib import Path
import numpy as np
from receipt_ocr.detect_doctr import detect_text_boxes
from receipt_ocr.ocr_preprocess import preprocess_image, PreprocessConfig, _deskew, _resize_keep_aspect
import pytesseract

img_path = Path("sample_images/Avikam_10.03.2025_Avikam 11-03-25.pdf")
pytesseract.pytesseract.tesseract_cmd = "C:/Program Files/Tesseract-OCR/tesseract.exe"

cfg = PreprocessConfig()
pre = preprocess_image(img_path, cfg)

deskewed = _deskew(pre.original_bgr)
resized_bgr, _, _ = _resize_keep_aspect(
    deskewed, cfg.target_height, cfg.target_width
)

boxes = detect_text_boxes(resized_bgr, "db_resnet50")
print(f"Detected {len(boxes)} boxes on BGR image")

if len(pre.preprocessed.shape) == 3:
    gray = cv2.cvtColor(pre.preprocessed, cv2.COLOR_BGR2GRAY)
else:
    gray = pre.preprocessed
h, w = gray.shape

for i, box in enumerate(boxes[:10]):
    x1, y1, x2, y2 = box.box
    pad = 0
    x1_p = max(int(x1) - pad, 0)
    y1_p = max(int(y1) - pad, 0)
    x2_p = min(int(x2) + pad, w)
    y2_p = min(int(y2) + pad, h)
    
    crop = gray[y1_p:y2_p, x1_p:x2_p]
    text_unpad = pytesseract.image_to_string(crop, lang="heb", config="--psm 7")
    
    pad = 8
    x1_p = max(int(x1) - pad, 0)
    y1_p = max(int(y1) - pad, 0)
    x2_p = min(int(x2) + pad, w)
    y2_p = min(int(y2) + pad, h)
    
    if y2_p <= y1_p or x2_p <= x1_p:
        continue
        
    crop_pad = gray[y1_p:y2_p, x1_p:x2_p]
    # To help tesseract, let's also add white border explicitly
    crop_pad_border = cv2.copyMakeBorder(gray[int(y1):int(y2), int(x1):int(x2)], pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[255,255,255])
    
    text_pad = pytesseract.image_to_string(crop_pad, lang="heb", config="--psm 7")
    text_border = pytesseract.image_to_string(crop_pad_border, lang="heb", config="--psm 7")
    
    print(f"Box {i}: size {int(x2-x1)}x{int(y2-y1)}")
    print(f"  Unpadded : {repr(text_unpad.strip())}")
    print(f"  Padded   : {repr(text_pad.strip())}")
    print(f"  Bordered : {repr(text_border.strip())}")
