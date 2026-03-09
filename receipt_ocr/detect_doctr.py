from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from doctr.io import DocumentFile
from doctr.models import detection_predictor


_DETECTOR_CACHE = {}


@dataclass
class DetectedBox:
    box: List[float]  # [x1, y1, x2, y2] in pixel coordinates
    score: float
    page: int


def _get_detector(model_name: str):
    if model_name not in _DETECTOR_CACHE:
        _DETECTOR_CACHE[model_name] = detection_predictor(model_name)
    return _DETECTOR_CACHE[model_name]


def detect_text_boxes(
    preprocessed_image: np.ndarray,
    detector_model_name: str,
    page_index_offset: int = 0,
    debug_dir: Optional[Path] = None,
    debug_enabled: bool = False,
    debug_basename: str = "detect",
) -> List[DetectedBox]:
    """
    Run docTR detection on the preprocessed image and return a flat list of boxes.

    The input is expected to be a single-page, binarized/grayscale or RGB numpy array.
    """
    if preprocessed_image.ndim == 2:
        rgb = cv2.cvtColor(preprocessed_image, cv2.COLOR_GRAY2RGB)
    else:
        rgb = cv2.cvtColor(preprocessed_image, cv2.COLOR_BGR2RGB)

    # docTR expects a DocumentFile; from_images accepts numpy arrays.
    doc = DocumentFile.from_images([rgb])
    detector = _get_detector(detector_model_name)
    det_result = detector(doc)
    exported = det_result.export()

    boxes: List[DetectedBox] = []

    for page_idx, page in enumerate(exported.get("pages", [])):
        page_num = page_index_offset + page_idx
        height = page.get("dimensions", [rgb.shape[0], rgb.shape[1]])[0]
        width = page.get("dimensions", [rgb.shape[0], rgb.shape[1]])[1]

        for block in page.get("blocks", []):
            for line in block.get("lines", []):
                for word in line.get("words", []):
                    loc = word.get("geometry") or word.get("box")
                    if loc is None:
                        continue
                    # geometry is relative [x_min, y_min, x_max, y_max] in [0, 1]
                    x_min_rel, y_min_rel, x_max_rel, y_max_rel = loc
                    x1 = float(x_min_rel * width)
                    y1 = float(y_min_rel * height)
                    x2 = float(x_max_rel * width)
                    y2 = float(y_max_rel * height)
                    score = float(word.get("confidence", 1.0))

                    boxes.append(
                        DetectedBox(
                            box=[x1, y1, x2, y2],
                            score=score,
                            page=page_num,
                        )
                    )

    if debug_enabled and debug_dir is not None:
        debug_dir.mkdir(parents=True, exist_ok=True)
        overlay = _draw_boxes_overlay(rgb, boxes)
        debug_path = debug_dir / f"{debug_basename}_boxes.png"
        cv2.imwrite(str(debug_path), cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))

    return boxes


def _draw_boxes_overlay(image_rgb: np.ndarray, boxes: List[DetectedBox]) -> np.ndarray:
    """Return an RGB image with bounding boxes drawn on top."""
    overlay = image_rgb.copy()
    for det in boxes:
        x1, y1, x2, y2 = map(int, det.box)
        color = (255, 0, 0)  # red in RGB
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
    return overlay

