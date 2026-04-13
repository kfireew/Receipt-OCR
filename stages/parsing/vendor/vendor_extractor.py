"""Vendor extractor service.

Extracts the merchant/vendor name from raw OCR lines.
Uses keyword scanning + merchants_mapping.json for fuzzy matching.
"""
from __future__ import annotations

import os
import re
import json
import pathlib
from typing import Dict, List, Optional

from stages.post_process.fuzzy_corrector import fuzzy_correct_line
from stages.parsing.shared import ParsedStringField
from stages.grouping.line_assembler import RawLine

# Cache for the merchant mapping to avoid repeated file I/O
_merchant_map_cache: Optional[Dict[str, List[str]]] = None

_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]


def _load_merchant_mapping() -> Dict[str, List[str]]:
    global _merchant_map_cache
    if _merchant_map_cache is not None:
        return _merchant_map_cache
    try:
        mapping_path = _PROJECT_ROOT / "merchants_mapping.json"
        with open(mapping_path, "r", encoding="utf-8") as f:
            _merchant_map_cache = json.load(f)
    except Exception:
        _merchant_map_cache = {}
    return _merchant_map_cache


def match_merchant(text: str) -> str:
    """Map a text string to a normalized merchant name.

    Returns the normalized name if a keyword match is found,
    otherwise returns the input text unchanged.
    """
    if not text:
        return text
    lower_val = text.lower()
    mapping = _load_merchant_mapping()
    for normalized_name, keywords in mapping.items():
        if any(kw.lower() in lower_val for kw in keywords):
            return normalized_name
    return text


def extract_vendor(lines: List[RawLine]) -> ParsedStringField:
    """Extract vendor/merchant name from raw OCR lines.

    Two-pass approach:
    1. Scan ALL lines for known merchant keywords via merchants_mapping.json
    2. Fallback: combine first few non-keyword lines and fuzzy-correct
    """
    if not lines:
        return ParsedStringField(value=None, confidence=None, line_index=None)

    # Pass 1: Broad search — scan all lines for known merchant keywords
    for line in lines:
        txt = line.text_normalized or line.text_raw or ""
        if not txt or len(txt) < 3:
            continue

        fuzzy_txt = _clean_text(txt)
        mapped = match_merchant(fuzzy_txt)
        if mapped != fuzzy_txt:
            # Known merchant found!
            return ParsedStringField(
                value=mapped,
                confidence=line.confidence,
                line_index=line.index,
            )

    # Pass 2: Fallback — candidate lines that aren't mostly digits or known keywords
    candidates = []
    for i in range(min(5, len(lines))):
        txt = lines[i].text_normalized or lines[i].text_raw or ""
        # Stop if we hit a line that looks like an invoice header or date
        if any(kw in txt for kw in ("חשבונית", "תאריך", "מספר", "תעודת")):
            break
        if len(txt) > 3:
            candidates.append(txt)

    if not candidates:
        return ParsedStringField(
            value=lines[0].text_raw,
            confidence=lines[0].confidence,
            line_index=0,
        )

    combined_val = " ".join(candidates)
    combined_val = _clean_text(combined_val)
    normalized_merchant = match_merchant(combined_val)

    return ParsedStringField(
        value=normalized_merchant,
        confidence=lines[0].confidence,
        line_index=0,
    )


def _clean_text(text: str) -> str:
    """Apply fuzzy correction and remove OCR noise characters."""
    text = fuzzy_correct_line(text)
    text = re.sub(r'[\|\\/]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
