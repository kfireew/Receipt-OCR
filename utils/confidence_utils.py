from __future__ import annotations

from typing import List, Optional, Sequence, Dict

def combine_confidences(confidences: Sequence[float]) -> Optional[Dict[str, float]]:
    if not confidences:
        return None
    return {
        "mean": sum(confidences) / len(confidences),
        "min": min(confidences),
        "max": max(confidences),
    }
