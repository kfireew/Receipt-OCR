from __future__ import annotations

from typing import Optional

try:
    from bidi.algorithm import get_display
except Exception:
    get_display = None

def logical_to_visual(text: str) -> str:
    """Convert logical-order Hebrew text to visual order."""
    if not text:
        return text
    if get_display is None:
        return text
    return get_display(text)

def normalize_bidi_for_parsing(text: str, fallback_normalizer: Optional[callable] = None) -> str:
    """Prepare text for rule-based parsing.

    Keeps text in logical order (as Tesseract outputs it).
    get_display() must NOT be called here — it converts logical->visual for
    screen rendering, which reverses Hebrew when the input is already logical.
    """
    if not text:
        return text
    # Pass through unchanged; regex/field extractors operate on logical order.
    if fallback_normalizer is not None:
        return fallback_normalizer(text)
    return text
