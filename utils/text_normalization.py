from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict

HEBREW_NIKUD_RANGE = (0x0591, 0x05C7)

def strip_diacritics(text: str) -> str:
    """Remove Hebrew niqqud / cantillation marks."""
    if not text:
        return text

    def _filter(c: str) -> bool:
        code = ord(c)
        return not (HEBREW_NIKUD_RANGE[0] <= code <= HEBREW_NIKUD_RANGE[1])

    return "".join(ch for ch in text if _filter(ch))

def basic_cleanup(text: str) -> str:
    """Light cleanup."""
    if not text:
        return text
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text

def normalize_for_parsing(text: str) -> str:
    """Full normalization pipeline."""
    if not text:
        return text
    text = strip_diacritics(text)
    text = text.lower()
    text = basic_cleanup(text)
    return text

def load_confusion_map(path: Path) -> Dict[str, str]:
    """Load a confusion map from JSON."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Confusion map must be a JSON object: {path}")
    return {str(k): str(v) for k, v in data.items()}

def apply_confusion_map(text: str, confusion_map: Dict[str, str]) -> str:
    """Apply substitutions from a confusion map."""
    if not text or not confusion_map:
        return text
    out = text
    for src, dst in confusion_map.items():
        if src:
            out = out.replace(src, dst)
    return out
