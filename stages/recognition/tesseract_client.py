from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Any

import cv2
import numpy as np
import pytesseract

from utils.bidi_utils import normalize_bidi_for_parsing
from utils.confidence_utils import combine_confidences
from utils.text_normalization import apply_confusion_map, normalize_for_parsing, load_confusion_map

@dataclass
class RecognizedBox:
    """A single detected box with associated OCR result."""
    box: List[float]  # [x1, y1, x2, y2]
    page: int
    text_raw: str
    text_normalized: str
    confidence: float
    original_index: int = 0

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
        return image[max(0, y1_i - 1) : min(h, y1_i + 1), max(0, x1_i - 1) : min(w, x1_i + 1)]
    return image[y1_i:y2_i, x1_i:x2_i]

def _ocr_single_box(
    image: np.ndarray,
    box: Any,
    lang: str = "heb",
    psm: int = 7,
    extra_config: str = "",
) -> Tuple[str, float]:
    crop = _crop_box(image, box.box if hasattr(box, 'box') else box)
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

    text = " ".join(texts) if texts else ""
    confidence = float(combine_confidences(confs)["mean"]) if confs else 0.0
    return text, confidence

def _ocr_full_page(
    image: np.ndarray,
    page_num: int = 0,
    lang: str = "heb",
    psm: int = 6,
    extra_config: str = "",
) -> List[Tuple[List[float], str, float]]:
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
    confusion_map: Optional[Dict[str, str] | str] = None,
    lang: str = "heb",
    psm: int = 7,
    full_page_psm: int = 6,
    extra_config: str = "",
    page_idx: int = 0,
    use_multi_psm: bool = True,  # multi-pass often helps with stylized merchant names
) -> List[RecognizedBox]:
    _configure_tesseract(tesseract_executable)

    if preprocessed_image.ndim == 2:
        work_img = preprocessed_image
    else:
        work_img = cv2.cvtColor(preprocessed_image, cv2.COLOR_BGR2GRAY)

    results: List[RecognizedBox] = []
    
    if isinstance(confusion_map, str):
        try:
            confusion_map = load_confusion_map(Path(confusion_map))
        except Exception as e:
            print(f"Warning: Failed to load confusion map from {confusion_map}: {e}")
            confusion_map = {}
    else:
        confusion_map = confusion_map or {}

    if not detected_boxes:
        psms = [3, 6] if use_multi_psm else [full_page_psm]
        all_native_boxes = []
        for p in psms:
            all_native_boxes.extend(_ocr_full_page(
                work_img,
                page_num=page_idx,
                lang=lang,
                psm=p,
                extra_config=extra_config
            ))
        
        for i, (box_coords, text_raw, conf) in enumerate(all_native_boxes):
            norm = normalize_for_parsing(text_raw)
            norm = apply_confusion_map(norm, confusion_map)
            norm = normalize_bidi_for_parsing(norm)
            
            results.append(
                RecognizedBox(
                    box=box_coords,
                    page=page_idx,
                    text_raw=text_raw,
                    text_normalized=norm,
                    confidence=conf,
                    original_index=i,
                )
            )
    else:
        for box in detected_boxes:
            text_raw, conf = _ocr_single_box(work_img, box, lang=lang, psm=psm, extra_config=extra_config)
            norm = normalize_for_parsing(text_raw)
            norm = apply_confusion_map(norm, confusion_map)
            norm = normalize_bidi_for_parsing(norm)
    
            results.append(
                RecognizedBox(
                    box=list(box.box) if hasattr(box, 'box') else list(box),
                    page=box.page if hasattr(box, 'page') else page_idx,
                    text_raw=text_raw,
                    text_normalized=norm,
                    confidence=conf,
                )
            )

    return results
