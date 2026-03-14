from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List
import fitz
import cv2
import numpy as np

@dataclass
class PreprocessConfig:
    target_height: int = 2400
    target_width: int = 1800
    adaptive_threshold_block_size: int = 31
    adaptive_threshold_C: int = 10

@dataclass
class PreprocessResult:
    original_bgr: np.ndarray
    preprocessed: np.ndarray
    scale_x: float
    scale_y: float
    debug_original_path: Optional[Path] = None
    debug_preprocessed_path: Optional[Path] = None

def _load_image_any(path: Path) -> List[np.ndarray]:
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        try:
            doc = fitz.open(path)
            images = []
            for page_num in range(len(doc)):
                # Increased DPI for PDFs
                pix = doc.load_page(page_num).get_pixmap(dpi=300)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                images.append(img_bgr)
            return images
        except Exception as exc:
            raise RuntimeError(f"Failed to read PDF: {path}") from exc
    else:
        try:
            img = cv2.imread(str(path))
            if img is None:
                raise ValueError(f"OpenCV could not read '{path}'.")
            return [img]
        except Exception as exc:
            raise RuntimeError(f"Failed to read image: {path}") from exc
