from __future__ import annotations

"""
Utilities for combining confidence scores.
"""

from statistics import mean, median
from typing import Iterable, Mapping, Optional


def combine_confidences(values: Iterable[float]) -> Optional[Mapping[str, float]]:
    """
    Combine a list of confidence values into summary statistics.

    Returns a mapping with at least:
    - "mean"
    - "median"
    - "min"
    - "max"
    or None if `values` is empty.
    """
    vals = [float(v) for v in values]
    if not vals:
        return None
    return {
        "mean": float(mean(vals)),
        "median": float(median(vals)),
        "min": float(min(vals)),
        "max": float(max(vals)),
    }

