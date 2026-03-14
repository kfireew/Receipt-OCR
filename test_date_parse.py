import re
from datetime import datetime

_DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b"),
]

text = '1 | x`xTxx?xY x?x`x  x-x" x x x x?xT (47224) 6 | 3 0 | 27/12/2024 08:40'

candidates = []
for pat in _DATE_PATTERNS:
    for m in pat.finditer(text):
        raw_date = m.group(1)
        print(f"Found candidate: {raw_date}")
        iso_value = None
        for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%y", "%d/%m/%y", "%d-%m-%y"):
            try:
                dt = datetime.strptime(raw_date, fmt)
                iso_value = dt.date().isoformat()
                print(f"  Parsed to: {iso_value}")
                break
            except ValueError:
                continue

if not candidates and "27/12/2024" in text:
    print("Match failed despite string presence!")
