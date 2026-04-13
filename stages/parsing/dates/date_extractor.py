"""Date extractor service.

Extracts the receipt date from raw OCR lines using date patterns
and keyword scoring.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence

from stages.grouping.line_assembler import RawLine
from stages.post_process.fuzzy_corrector import snap_to_keyword
from stages.parsing.shared import _DATE_PATTERNS, ParsedStringField


def _fuzzy_normalize(text: str) -> str:
    """Apply token-level keyword snapping before regex matching."""
    if not text:
        return text
    return " ".join(snap_to_keyword(tok) for tok in text.split())


def _parse_date_from_lines(lines: Sequence[RawLine]) -> ParsedStringField:
    """Find the best date candidate from all lines.

    Scans all lines for date patterns, scores candidates by:
    - Presence of date keyword (+15)
    - Position near top (+10 if within first 20 lines)
    - Position near bottom (+5 if within last 15 lines)
    - Highest confidence breaks ties
    """
    if not lines:
        return ParsedStringField(value=None, confidence=None, line_index=None)

    candidates = []
    for i, line in enumerate(lines):
        text = _fuzzy_normalize(line.text_normalized or line.text_raw or "")
        if not text:
            continue
        is_date_kw = any(
            kw in text
            for kw in ("תאריך", "תאר", "הופק", "יום", "חאריך", "חאר", "חאריד")
        )
        for pat in _DATE_PATTERNS:
            for m in pat.finditer(text):
                day, month, year = m.group(1), m.group(2), m.group(3)
                if len(year) == 2:
                    year = "20" + year
                iso_value = None
                try:
                    clean_date = f"{int(day):02d}.{int(month):02d}.{int(year):04d}"
                    dt = datetime.strptime(clean_date, "%d.%m.%Y")
                    iso_value = dt.date().isoformat()
                except ValueError:
                    continue
                if iso_value:
                    score = 0
                    if is_date_kw:
                        score += 15
                    if i < 20:
                        score += 10
                    if i > len(lines) - 15:
                        score += 5
                    candidates.append((score, iso_value, line.confidence, i))

    if candidates:
        candidates.sort(key=lambda x: (-x[0], x[3]))
        best = candidates[0]
        return ParsedStringField(
            value=best[1],
            confidence=best[2],
            line_index=best[3],
        )
    return ParsedStringField(value=None, confidence=None, line_index=None)
