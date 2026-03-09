from __future__ import annotations

"""
Helpers for working with Hebrew bidi text.

These utilities keep a clear separation between:
- The raw logical text as produced by OCR engines.
- A normalized version used for parsing / regex.
"""

from typing import Optional

try:  # pragma: no cover - import is environment-dependent
    from bidi.algorithm import get_display
except Exception:  # pragma: no cover
    get_display = None  # type: ignore[assignment]


def logical_to_visual(text: str) -> str:
    """
    Convert logical-order Hebrew text to visual order for display.

    If `python-bidi` is not available, this is a no-op.
    """
    if not text:
        return text
    if get_display is None:
        return text
    return get_display(text)


def normalize_bidi_for_parsing(text: str, fallback_normalizer: Optional[callable] = None) -> str:
    """
    Prepare text for rule-based parsing.

    - Keeps the text in logical order.
    - Optionally applies an additional normalizer (e.g. lowercasing, diacritic stripping).
    """
    if not text:
        return text
    norm = text
    if fallback_normalizer is not None:
        norm = fallback_normalizer(norm)
    return norm

