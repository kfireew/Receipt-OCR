import cv2
import numpy as np
from pathlib import Path
from receipt_ocr.ocr_preprocess import _load_image_any, _deskew

img_path = Path("sample_images/Avikam_10.03.2025_Avikam 11-03-25.pdf")
original = _load_image_any(img_path)
print(f"Original shape: {original.shape}, mean: {np.mean(original)}")

deskewed = _deskew(original)
print(f"Deskewed shape: {deskewed.shape}, mean: {np.mean(deskewed)}")

cv2.imwrite("debug/test_original.png", original)
cv2.imwrite("debug/test_deskewed.png", deskewed)
