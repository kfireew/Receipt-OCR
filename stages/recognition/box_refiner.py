"""Box utilities for OCR processing."""
from typing import List


def deduplicate_boxes(boxes: List) -> List:
    """Remove duplicate boxes based on text content and position."""
    seen = set()
    result = []

    for box in boxes:
        # Create a key from text and approximate position
        text = getattr(box, 'text', '') or getattr(box, 'text_raw', '') or ''
        key = (text[:20], int(getattr(box, 'page', 0)))

        if key not in seen:
            seen.add(key)
            result.append(box)

    return result