"""Invoice/serial number extractor service.

Extracts the invoice number from raw OCR lines by scanning for
invoice keywords and nearby numeric patterns.
"""
from __future__ import annotations

import re
from typing import List, Optional, Sequence

from stages.grouping.line_assembler import RawLine
from stages.parsing.shared import ParsedStringField


def _parse_invoice_no(lines: Sequence[RawLine]) -> ParsedStringField:
    """Find the invoice number from raw OCR lines.

    Scans for invoice keywords and looks for nearby numeric values.
    Prefers candidates in the top 40% of the document.
    """
    invoice_kws = (
        "חשבונית", "מספר ח", "ח.מ", "מסרה", "מס '", "מס'", "ח-ן",
        "תעודת", "invoice",
    )
    candidates = []
    for i, line in enumerate(lines):
        txt = (line.text_normalized or line.text_raw or "").lower()
        if not txt:
            continue
        if any(kw in txt for kw in invoice_kws) and not any(
            kw in txt for kw in ("מיקוד", "zip", "zipcode")
        ):
            # Search nearby lines for numeric candidates
            for j in range(max(0, i - 2), min(len(lines), i + 3)):
                nj_txt = (lines[j].text_normalized or lines[j].text_raw or "").lower()
                if j == i and any(kw in txt for kw in ("לקוח", "לכבוד")):
                    continue
                for m in re.finditer(r"(\d{4,16})", nj_txt):
                    val = m.group(1)
                    # Skip 8-digit sequences that look like dates or IDs
                    if len(val) == 8 and (val.startswith("202") or val.startswith("05")):
                        continue
                    score = 10
                    if j < len(lines) * 0.4:
                        score += 15
                    if "חשבונית" in nj_txt:
                        score += 10
                    if any(kw in nj_txt for kw in ("לקוח", "לכבוד")):
                        score -= 20
                    candidates.append((
                        score,
                        ParsedStringField(
                            value=val,
                            confidence=lines[j].confidence,
                            line_index=j,
                        ),
                    ))
    if candidates:
        candidates.sort(key=lambda x: -x[0])
        return candidates[0][1]
    return ParsedStringField(value=None, confidence=None, line_index=None)
