from __future__ import annotations

from typing import List
from stages.recognition.tesseract_client import RecognizedBox

def deduplicate_boxes(boxes: List[RecognizedBox], iou_thresh: float = 0.5) -> List[RecognizedBox]:
    """
    Remove overlapping boxes produced by multiple PSM passes.
    Prefers higher confidence boxes.
    """
    if not boxes:
        return []
    
    # Sort by confidence descending
    sorted_boxes = sorted(boxes, key=lambda b: (b.confidence or 0), reverse=True)
    kept: List[RecognizedBox] = []
    
    for b in sorted_boxes:
        is_duplicate = False
        for k in kept:
            if b.page != k.page:
                continue
            # Simple IoU-like check
            bi = b.box
            ki = k.box
            inter_x1 = max(bi[0], ki[0])
            inter_y1 = max(bi[1], ki[1])
            inter_x2 = min(bi[2], ki[2])
            inter_y2 = min(bi[3], ki[3])
            
            inter_w = max(0, inter_x2 - inter_x1)
            inter_h = max(0, inter_y2 - inter_y1)
            inter_area = inter_w * inter_h
            
            b_area = (bi[2] - bi[0]) * (bi[3] - bi[1])
            if b_area > 0 and (inter_area / b_area) > iou_thresh:
                is_duplicate = True
                break
        if not is_duplicate:
            kept.append(b)
    return kept
