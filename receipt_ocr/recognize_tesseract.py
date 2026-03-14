from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import cv2
import numpy as np
import pytesseract

from .utils.bidi_utils import normalize_bidi_for_parsing
from .utils.confidence_utils import combine_confidences
from .utils.text_normalization import apply_confusion_map, normalize_for_parsing


@dataclass
class RecognizedBox:
    """
    A single detected box with associated OCR result.
    """

    box: List[float]  # [x1, y1, x2, y2] in pixel coordinates
    page: int
    text_raw: str
    text_normalized: str
    confidence: float


def _configure_tesseract(executable_path: Optional[str]) -> None:
    if executable_path:
        pytesseract.pytesseract.tesseract_cmd = executable_path


def _crop_box(image: np.ndarray, box: Sequence[float]) -> np.ndarray:
    x1, y1, x2, y2 = box
    h, w = image.shape[:2]
    x1_i = max(int(round(x1)), 0)
    y1_i = max(int(round(y1)), 0)
    x2_i = min(int(round(x2)), w)
    y2_i = min(int(round(y2)), h)
    if x2_i <= x1_i or y2_i <= y1_i:
        # Degenerate crop; return a minimal patch to avoid errors.
        return image[max(0, y1_i - 1) : min(h, y1_i + 1), max(0, x1_i - 1) : min(w, x1_i + 1)]
    return image[y1_i:y2_i, x1_i:x2_i]


def _ocr_single_box(
    image: np.ndarray,
    box: Any,
    lang: str = "heb",
    psm: int = 7,
    extra_config: str = "",
) -> Tuple[str, float]:
    """
    Run Tesseract on a single cropped box and return (text, confidence).

    Uses `image_to_data` so we can derive a per-box confidence.
    """
    crop = _crop_box(image, box.box)
    if crop.ndim == 3:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = crop

    config = f"-l {lang} --psm {psm} {extra_config}".strip()
    data = pytesseract.image_to_data(gray, config=config, output_type=pytesseract.Output.DICT)

    texts: List[str] = []
    confs: List[float] = []
    for txt, conf in zip(data.get("text", []), data.get("conf", [])):
        if not txt or txt.isspace():
            continue
        try:
            conf_f = float(conf)
        except Exception:
            conf_f = -1.0
        texts.append(txt)
        if conf_f >= 0:
            confs.append(conf_f / 100.0)

    if texts:
        text = " ".join(texts)
    else:
        text = ""

    if confs:
        summary = combine_confidences(confs)
        assert summary is not None
        confidence = float(summary["mean"])
    else:
        confidence = 0.0
    return text, confidence


def _ocr_full_page(
    image: np.ndarray,
    page_num: int = 0,
    lang: str = "heb",
    psm: int = 6,
    extra_config: str = "",
) -> List[Tuple[List[float], str, float]]:
    """
    Run Tesseract on the full page image, extracting word bounding boxes and text directly.
    """
    config = f"-l {lang} --psm {psm} {extra_config}".strip()
    data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)

    boxes: List[Tuple[List[float], str, float]] = []
    
    for i in range(len(data.get("text", []))):
        txt = data["text"][i]
        if not txt or txt.isspace():
            continue
            
        try:
            conf_f = float(data["conf"][i])
        except Exception:
            conf_f = -1.0
            
        if conf_f >= 0:
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            box = [float(x), float(y), float(x + w), float(y + h)]
            boxes.append((box, txt, conf_f / 100.0))
            
    return boxes


def recognize_boxes(
    preprocessed_image: np.ndarray,
    detected_boxes: Optional[Iterable[Any]] = None,
    *,
    tesseract_executable: Optional[str] = None,
    confusion_map: Optional[Dict[str, str]] = None,
    lang: str = "heb",
    psm: int = 7, # if boxes provided
    full_page_psm: int = 6, # if detecting natively
    extra_config: str = "",
    page_idx: int = 0,
) -> List[RecognizedBox]:
    """
    Run Tesseract-based recognition for each detected box or the full page.

    - Uses the (binarized) `preprocessed_image` from the preprocessing stage.
    - Applies bidi-aware normalization and confusion-map substitutions.
    - Returns `RecognizedBox` objects that can be merged into lines later.
    """
    _configure_tesseract(tesseract_executable)

    # Ensure 2D / 3D image is accepted.
    if preprocessed_image.ndim == 2:
        work_img = preprocessed_image
    else:
        work_img = cv2.cvtColor(preprocessed_image, cv2.COLOR_BGR2GRAY)

    results: List[RecognizedBox] = []
    confusion_map = confusion_map or {}

    if not detected_boxes:
        # Tesseract native detection
        native_boxes = _ocr_full_page(
            work_img,
            page_num=page_idx,
            lang=lang,
            psm=full_page_psm,
            extra_config=extra_config
        )
        
        for box_coords, text_raw, conf in native_boxes:
            norm = normalize_for_parsing(text_raw)
            norm = apply_confusion_map(norm, confusion_map)
            norm = normalize_bidi_for_parsing(norm, fallback_normalizer=None)
            
            results.append(
                RecognizedBox(
                    box=box_coords,
                    page=page_idx,
                    text_raw=text_raw,
                    text_normalized=norm,
                    confidence=conf,
                )
            )
            
    else:
        for box in detected_boxes:
            text_raw, conf = _ocr_single_box(
                work_img,
                box,
                lang=lang,
                psm=psm,
                extra_config=extra_config,
            )
            # First, normalized for parsing (strip diacritics, lowercase, etc.).
            norm = normalize_for_parsing(text_raw)
            # Apply confusion map, then an optional bidi-aware wrapper.
            norm = apply_confusion_map(norm, confusion_map)
            norm = normalize_bidi_for_parsing(norm, fallback_normalizer=None)
    
            results.append(
                RecognizedBox(
                    box=list(box.box),
                    page=box.page,
                    text_raw=text_raw,
                    text_normalized=norm,
                    confidence=conf,
                )
            )

    # region agent log
    import json as _json_recognize
    import time as _time_recognize

    try:
        with open(
            r"c:\Users\Kfir Ezer\Desktop\Receipt OCR\debug-4cbdb5.log",
            "a",
            encoding="utf-8",
        ) as _f:
            _f.write(
                _json_recognize.dumps(
                    {
                        "sessionId": "4cbdb5",
                        "runId": "pre-fix",
                        "hypothesisId": "H_ocr_output",
                        "location": "receipt_ocr/recognize_tesseract.py:recognize_boxes",
                        "message": "Tesseract recognition summary",
                        "data": {
                            "num_results": len(results),
                            "sample": [
                                {
                                    "page": r.page,
                                    "text_raw": r.text_raw,
                                    "text_normalized": r.text_normalized,
                                    "confidence": r.confidence,
                                }
                                for r in results[:10]
                            ],
                        },
                        "timestamp": int(_time_recognize.time() * 1000),
                    },
                    default=str,
                )
                + "\n"
            )
    except Exception:
        # Logging must never break the pipeline
        pass
    # endregion

    return results

