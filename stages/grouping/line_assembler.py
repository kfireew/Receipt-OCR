from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple
from utils.confidence_utils import combine_confidences
from stages.recognition.tesseract_client import RecognizedBox
from stages.post_process.fuzzy_corrector import fuzzy_correct_line

@dataclass
class RawLine:
    index: int
    page: int
    bbox: List[float]  # [x1, y1, x2, y2]
    text_raw: str
    text_normalized: str
    confidence: float
    boxes: List[RecognizedBox] = None

def _boxes_to_lines(
    boxes: Sequence[RecognizedBox],
    y_overlap_thresh: float = 1.2,
) -> List[RawLine]:
    """Group individual word/box recognitions into line-level structures."""
    def _center_and_height(b: RecognizedBox) -> Tuple[float, float]:
        x1, y1, x2, y2 = b.box
        return (y1 + y2) / 2.0, (y2 - y1)

    grouped: List[List[RecognizedBox]] = []
    sorted_boxes = sorted(boxes, key=lambda b: (b.page, _center_and_height(b)[0]))

    for b in sorted_boxes:
        y_center, h = _center_and_height(b)
        placed = False
        for line in grouped:
            ly_center, lh = _center_and_height(line[0])
            max_h = max(lh, h, 1.0)
            if abs(y_center - ly_center) <= y_overlap_thresh * max_h:
                line.append(b)
                placed = True
                break
        if not placed:
            grouped.append([b])

    raw_lines: List[RawLine] = []
    for idx, line_boxes in enumerate(grouped):
        # Sort boxes within line from RIGHT to LEFT (descending x-center).
        # Hebrew is RTL: the rightmost word on the visual line is the first word logically.
        # Tesseract scans left-to-right internally, so original_index gives reversed Hebrew order.
        line_boxes_sorted = sorted(
            line_boxes,
            key=lambda b: -((b.box[0] + b.box[2]) / 2.0),
        )

        texts_raw = []
        texts_norm = []
        last_norm = None
        
        for b in line_boxes_sorted:
            if not b.text_raw and not b.text_normalized:
                continue
            
            # Simple deduplication: skip if the normalized text is identical to the previous one
            # and they belong to the same line (already guaranteed here).
            current_norm = b.text_normalized or ""
            if last_norm and current_norm == last_norm:
                continue
            
            texts_raw.append(b.text_raw)
            texts_norm.append(current_norm)
            last_norm = current_norm

        if not texts_raw and not texts_norm:
            continue

        x1s = [b.box[0] for b in line_boxes_sorted]
        y1s = [b.box[1] for b in line_boxes_sorted]
        x2s = [b.box[2] for b in line_boxes_sorted]
        y2s = [b.box[3] for b in line_boxes_sorted]
        bbox = [float(min(x1s)), float(min(y1s)), float(max(x2s)), float(max(y2s))]

        confs = [b.confidence for b in line_boxes_sorted if b.confidence is not None]
        conf_summary = combine_confidences(confs) if confs else None
        line_conf = float(conf_summary["mean"]) if conf_summary is not None else 0.0

        raw_lines.append(
            RawLine(
                index=idx,
                page=line_boxes_sorted[0].page,
                bbox=bbox,
                text_raw=" ".join(texts_raw) if texts_raw else "",
                text_normalized=" ".join(texts_norm) if texts_norm else "",
                confidence=line_conf,
                boxes=line_boxes_sorted,
            )
        )
    return raw_lines
