from __future__ import annotations

import re
from typing import List, Sequence, Tuple

_DATE_PATTERNS = [
    re.compile(r"(\d{1,2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{2,4})"),
]

_AMOUNT_RE = re.compile(r"(\d[\d']*(?:[\.,]?\d+)?)")

def parse_amount(text: str) -> float | None:
    """Parse a numeric amount from text.

    Supports decimal separators: `'` (Hebrew apostrophe), `,`, `.`
    Heuristic: if there's exactly one `,` and no `.`, treat `,` as decimal.
    If there's exactly one `.` and no `,`, treat `.` as decimal.
    Multiple commas = thousands separator (remove them).
    """
    m = _AMOUNT_RE.search(text)
    if not m:
        return None
    num_str = m.group(1).replace(" ", "")
    if "'" in num_str:
        num_str = num_str.replace("'", ".")
    elif num_str.count(",") == 1 and "." not in num_str:
        # European decimal: 500,00 → 500.00
        num_str = num_str.replace(",", ".")
    elif num_str.count(",") > 1:
        # Thousands separator: 1,000,000 → 1000000
        num_str = num_str.replace(",", "")
    else:
        # No commas or already handled — '.' is decimal
        pass
    try:
        return float(num_str)
    except ValueError:
        return None
