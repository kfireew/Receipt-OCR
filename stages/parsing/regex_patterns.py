from __future__ import annotations

import re
from typing import List, Sequence, Tuple

_DATE_PATTERNS = [
    re.compile(r"(\d{1,2})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{2,4})"),
]

_AMOUNT_RE = re.compile(r"(\d[\d.,]*)")

def parse_amount(text: str) -> float | None:
    m = _AMOUNT_RE.search(text)
    if not m:
        return None
    num_str = m.group(1).replace(" ", "").replace(",", "")
    if "'" in num_str:
        num_str = num_str.replace("'", ".")
    try:
        return float(num_str)
    except ValueError:
        return None
