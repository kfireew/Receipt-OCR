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

def ocr_number_crop(
    image: np.ndarray,
    box: Sequence[float],
    tesseract_executable: Optional[str] = None,
) -> Tuple[str, float]:
    """Perform a targeted OCR pass on a specific bounding box for numbers."""
    _configure_tesseract(tesseract_executable)
    crop = _crop_box(image, box)
    if crop.size == 0:
        return "", 0.0
        
    if crop.ndim == 3:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = crop

    # Enlarge the crop slightly and optionally binarize
    height = gray.shape[0]
    if height < 30:
        scale = 30.0 / height
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Use eng language and whitelist for numbers and commas/dots
    config = "-l eng --psm 7 -c tessedit_char_whitelist=0123456789.,₪-"
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
        # clean up any dangling punctuation
        txt = txt.strip(".,-")
        if not txt:
            continue
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
            
        # Add a 90-degree rotation specifically targeting the right side of the image.
        H, W = work_img.shape[:2]
        # Crop the rightmost 30% of the image for performance and context isolation
        right_cutoff = int(W * 0.70)
        right_side = work_img[:, right_cutoff:W]
        
        # Test both counter-clockwise and clockwise 90-degree rotations
        for rot in [cv2.ROTATE_90_COUNTERCLOCKWISE, cv2.ROTATE_90_CLOCKWISE]:
            rot_img = cv2.rotate(right_side, rot)
            rot_boxes = _ocr_full_page(rot_img, page_num=page_idx, lang=lang, psm=6, extra_config=extra_config)
            
            for (rx1, ry1, rx2, ry2), txt, conf in rot_boxes:
                # Map back to right_side coordinates:
                if rot == cv2.ROTATE_90_COUNTERCLOCKWISE:
                    orig_x1 = rot_img.shape[0] - ry2
                    orig_x2 = rot_img.shape[0] - ry1
                    orig_y1 = rx1
                    orig_y2 = rx2
                else: # CLOCKWISE
                    orig_x1 = ry1
                    orig_x2 = ry2
                    orig_y1 = rot_img.shape[1] - rx2
                    orig_y2 = rot_img.shape[1] - rx1
                
                # Check bounds
                orig_x1 = max(0, min(orig_x1, right_side.shape[1]))
                orig_x2 = max(0, min(orig_x2, right_side.shape[1]))
                orig_y1 = max(0, min(orig_y1, right_side.shape[0]))
                orig_y2 = max(0, min(orig_y2, right_side.shape[0]))

                # Add right_cutoff to X coordinates to map back to work_img
                abs_x1 = orig_x1 + right_cutoff
                abs_x2 = orig_x2 + right_cutoff
                abs_y1 = orig_y1
                abs_y2 = orig_y2
                
                if abs_x2 > abs_x1 and abs_y2 > abs_y1:
                    all_native_boxes.append(([float(abs_x1), float(abs_y1), float(abs_x2), float(abs_y2)], txt, conf))
        
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


def extract_header_fields(
    image_path: str,
    tesseract_executable: Optional[str] = None,
    confusion_map: Optional[Dict[str, str] | str] = None,
) -> Dict[str, Any]:
    """Extract vendor and date from receipt header using Tesseract.

    Runs full receipt OCR with Tesseract, then extracts vendor + date
    from the OCR lines. Designed to be called alongside Mindee for items.

    Args:
        image_path: Path to receipt image
        tesseract_executable: Optional path to tesseract executable
        confusion_map: Optional confusion map for OCR corrections

    Returns:
        Dict with 'vendor' and 'date' ParsedStringField objects
    """
    from stages.preprocess.image_processor import preprocess_image
    from stages.grouping.line_assembler import _boxes_to_lines
    from stages.parsing.vendor import extract_vendor
    from stages.parsing.dates import _parse_date_from_lines

    # 1. Preprocess the image
    results = preprocess_image(image_path)

    # 2. Run Tesseract OCR on all pages
    all_boxes: List[RecognizedBox] = []
    for i, res in enumerate(results):
        boxes = recognize_boxes(
            res.preprocessed,
            page_idx=i,
            tesseract_executable=tesseract_executable,
            confusion_map=confusion_map,
            use_multi_psm=True,
        )
        all_boxes.extend(boxes)

    # 3. Convert boxes to lines
    raw_lines = _boxes_to_lines(all_boxes)

    # 4. Extract vendor and date using existing parsers
    vendor = extract_vendor(raw_lines)
    date = _parse_date_from_lines(raw_lines)

    return {
        'vendor': vendor,
        'date': date,
    }


def recognize_with_tesseract(image_path: str, **kwargs) -> List[RecognizedBox]:
    """Convenience function for full-page Tesseract OCR.

    Args:
        image_path: Path to receipt image
        **kwargs: Arguments passed to recognize_boxes()

    Returns:
        List of RecognizedBox objects
    """
    from stages.preprocess.image_processor import preprocess_image

    results = preprocess_image(image_path)
    all_boxes: List[RecognizedBox] = []

    for i, res in enumerate(results):
        boxes = recognize_boxes(res.preprocessed, page_idx=i, **kwargs)
        all_boxes.extend(boxes)

    return all_boxes


def parse_receipt_combined(
    image_path: str,
    header_ocr: str = "google",  # "google" or "tesseract"
    tesseract_executable: str = None,
    confusion_map: str = None,
    mindee_api_key: str = None,
    google_credentials_path: str = None,
) -> "ParsedReceipt":
    # Load environment variables for API keys
    from dotenv import load_dotenv
    load_dotenv()

    """Parse receipt using both OCR for header + Mindee for items.

    Runs full receipt through Tesseract or Google Vision for vendor + date,
    then through Mindee for items and totals.
    Combines results into a single ParsedReceipt.

    Args:
        image_path: Path to receipt image
        header_ocr: "google" for Cloud Vision, "tesseract" for local Tesseract
        tesseract_executable: Optional path to tesseract (if using tesseract)
        confusion_map: Optional confusion map path
        mindee_api_key: Optional Mindee API key
        google_credentials_path: Path to Google credentials JSON

    Returns:
        ParsedReceipt with vendor/date from OCR, items from Mindee
    """
    from stages.parsing.shared import ParsedReceipt, ParsedStringField, ParsedAmountField, LineItem
    from stages.grouping.line_assembler import RawLine

    # --- Step 1: Header OCR for vendor + date ---
    if header_ocr == "google":
        from stages.recognition.google_cloud_ocr import extract_header_with_google_vision
        header = extract_header_with_google_vision(
            image_path,
            credentials_path=google_credentials_path,
        )
    else:
        # Fallback to Tesseract
        header = extract_header_fields(
            image_path,
            tesseract_executable=tesseract_executable,
            confusion_map=confusion_map,
        )
    vendor = header['vendor']
    date = header['date']

    # --- Step 2: Mindee for items ---
    from stages.recognition.mindee_ocr import MindeeOCR
    ocr = MindeeOCR(api_key=mindee_api_key)
    mindee_items = ocr.extract_items(image_path)
    total_amount = ocr.get_total(image_path)

    # Convert Mindee items to LineItem format
    items = [
        LineItem(
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.total,
            confidence=0.8,  # Mindee doesn't provide per-item confidence
            line_index=i,
        )
        for i, item in enumerate(mindee_items)
    ]

    # --- Step 3: Build ParsedReceipt ---
    # Currency detection
    currency = ParsedStringField(value="ILS", confidence=0.9, line_index=0)

    # Total from Mindee
    total_field = ParsedAmountField(
        value=total_amount,
        raw_text=str(total_amount),
        confidence=0.9,
        line_index=0,
    )

    # Subtotal (Mindee doesn't always provide, estimate from items sum)
    items_sum = sum(item.line_total for item in items)
    subtotal_field = ParsedAmountField(
        value=items_sum if items_sum else None,
        raw_text=str(items_sum) if items_sum else None,
        confidence=0.7 if items_sum else 0.0,
        line_index=0,
    )

    # VAT (calculate if we have total)
    vat_field = ParsedAmountField(value=None, raw_text=None, confidence=None, line_index=None)
    if total_amount and items_sum and total_amount > items_sum:
        vat_field = ParsedAmountField(
            value=total_amount - items_sum,
            raw_text=str(total_amount - items_sum),
            confidence=0.8,
            line_index=0,
        )

    # Empty raw_lines since we don't have tesseract boxes here
    # (we only ran tesseract for header extraction)
    raw_lines: List[RawLine] = []

    parsed = ParsedReceipt(
        merchant=vendor,
        date=date,
        subtotal=subtotal_field,
        vat=vat_field,
        total=total_field,
        currency=currency,
        items=items,
        raw_lines=raw_lines,
        invoice_no=None,
    )

    return parsed
