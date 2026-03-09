from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import re

from .recognize_tesseract import RecognizedBox
from .utils.confidence_utils import combine_confidences


@dataclass
class RawLine:
    index: int
    page: int
    bbox: List[float]  # [x1, y1, x2, y2]
    text_raw: str
    text_normalized: str
    confidence: float


@dataclass
class LineItem:
    description: str
    quantity: float
    unit_price: float
    line_total: float
    confidence: float
    line_index: int


@dataclass
class ParsedAmountField:
    value: Optional[float]
    raw_text: Optional[str]
    confidence: Optional[float]
    line_index: Optional[int]


@dataclass
class ParsedStringField:
    value: Optional[str]
    confidence: Optional[float]
    line_index: Optional[int]


@dataclass
class ParsedReceipt:
    merchant: ParsedStringField
    date: ParsedStringField
    subtotal: ParsedAmountField
    vat: ParsedAmountField
    total: ParsedAmountField
    currency: ParsedStringField
    items: List[LineItem]
    raw_lines: List[RawLine]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "merchant": asdict(self.merchant),
            "date": asdict(self.date),
            "subtotal": asdict(self.subtotal),
            "vat": asdict(self.vat),
            "total": asdict(self.total),
            "currency": asdict(self.currency),
            "items": [asdict(it) for it in self.items],
            "raw_lines": [asdict(ln) for ln in self.raw_lines],
        }


def _boxes_to_lines(
    boxes: Sequence[RecognizedBox],
    y_overlap_thresh: float = 0.5,
) -> List[RawLine]:
    """
    Group individual word/box recognitions into line-level structures.

    The grouping is intentionally simple:
    - Boxes are first sorted by page, then by vertical center.
    - Boxes whose vertical centers overlap sufficiently are placed on the same line.
    - Within each line, boxes are sorted from right to left (Hebrew reading order).
    """

    def _center_and_height(b: RecognizedBox) -> Tuple[float, float]:
        x1, y1, x2, y2 = b.box
        return (y1 + y2) / 2.0, (y2 - y1)

    grouped: List[List[RecognizedBox]] = []

    # Sort by page then by vertical center.
    sorted_boxes = sorted(
        boxes,
        key=lambda b: (b.page, _center_and_height(b)[0]),
    )

    for b in sorted_boxes:
        y_center, h = _center_and_height(b)
        placed = False
        for line in grouped:
            ly_center, lh = _center_and_height(line[0])
            # Heuristic: centers close enough relative to height.
            max_h = max(lh, h, 1.0)
            if abs(y_center - ly_center) <= y_overlap_thresh * max_h:
                line.append(b)
                placed = True
                break
        if not placed:
            grouped.append([b])

    raw_lines: List[RawLine] = []
    for idx, line_boxes in enumerate(grouped):
        # Sort boxes within line from right to left (descending x-center).
        line_boxes_sorted = sorted(
            line_boxes,
            key=lambda b: -((b.box[0] + b.box[2]) / 2.0),
        )

        texts_raw = [b.text_raw for b in line_boxes_sorted if b.text_raw]
        texts_norm = [b.text_normalized for b in line_boxes_sorted if b.text_normalized]
        if not texts_raw and not texts_norm:
            continue

        x1s = [b.box[0] for b in line_boxes_sorted]
        y1s = [b.box[1] for b in line_boxes_sorted]
        x2s = [b.box[2] for b in line_boxes_sorted]
        y2s = [b.box[3] for b in line_boxes_sorted]
        bbox = [float(min(x1s)), float(min(y1s)), float(max(x2s)), float(max(y2s))]

        confs = [b.confidence for b in line_boxes_sorted if b.confidence is not None]
        conf_summary = combine_confidences(confs) if confs else None
        line_conf = float(conf_summary["mean"]) if conf_summary is not None else 0.0

        raw_lines.append(
            RawLine(
                index=idx,
                page=line_boxes_sorted[0].page,
                bbox=bbox,
                text_raw=" ".join(texts_raw) if texts_raw else "",
                text_normalized=" ".join(texts_norm) if texts_norm else "",
                confidence=line_conf,
            )
        )

    return raw_lines


_DATE_PATTERNS = [
    # dd.mm.yyyy, dd/mm/yy, dd-mm-yy, etc.
    re.compile(r"\b(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\b"),
]


def _parse_date_from_lines(lines: Sequence[RawLine]) -> ParsedStringField:
    for line in lines:
        text = line.text_normalized or line.text_raw
        if not text:
            continue
        for pat in _DATE_PATTERNS:
            m = pat.search(text)
            if not m:
                continue
            raw_date = m.group(1)
            iso_value: Optional[str] = None
            for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%y", "%d/%m/%y", "%d-%m-%y"):
                try:
                    dt = datetime.strptime(raw_date, fmt)
                    iso_value = dt.date().isoformat()
                    break
                except ValueError:
                    continue
            # Fall back to the raw string if we could not parse.
            if iso_value is None:
                iso_value = raw_date
            return ParsedStringField(
                value=iso_value,
                confidence=line.confidence,
                line_index=line.index,
            )
    return ParsedStringField(value=None, confidence=None, line_index=None)


_AMOUNT_RE = re.compile(r"(\d[\d.,]*)")


def _parse_amount(text: str) -> Optional[float]:
    m = _AMOUNT_RE.search(text)
    if not m:
        return None
    num_str = m.group(1)
    # Remove thousands separators and normalise decimal point.
    num_str = num_str.replace(" ", "").replace(",", "")
    try:
        return float(num_str)
    except ValueError:
        return None


def _find_amount_field(
    lines: Sequence[RawLine],
    keywords: Sequence[str],
) -> ParsedAmountField:
    for line in lines:
        txt = (line.text_normalized or line.text_raw or "").lower()
        if not txt:
            continue
        if not any(kw in txt for kw in keywords):
            continue
        amount = _parse_amount(txt)
        return ParsedAmountField(
            value=amount,
            raw_text=line.text_raw,
            confidence=line.confidence,
            line_index=line.index,
        )
    return ParsedAmountField(value=None, raw_text=None, confidence=None, line_index=None)


def _detect_currency(lines: Sequence[RawLine]) -> ParsedStringField:
    for line in lines:
        txt = (line.text_normalized or line.text_raw or "").lower()
        if not txt:
            continue
        if any(sym in txt for sym in ("₪", "nis", "ש\"ח", "שח", "ש״ח")):
            return ParsedStringField(
                value="ILS",
                confidence=line.confidence,
                line_index=line.index,
            )
    return ParsedStringField(value=None, confidence=None, line_index=None)


def _extract_items(lines: Sequence[RawLine], used_line_indices: Sequence[int]) -> List[LineItem]:
    used_set = set(used_line_indices)
    items: List[LineItem] = []

    for line in lines:
        if line.index in used_set:
            continue
        txt = line.text_normalized or line.text_raw
        if not txt:
            continue

        # Heuristic: only consider lines that contain at least one amount.
        amounts = [m.group(1) for m in _AMOUNT_RE.finditer(txt)]
        if not amounts:
            continue

        # Use the last amount on the line as the line total.
        total_str = amounts[-1].replace(" ", "").replace(",", "")
        try:
            line_total = float(total_str)
        except ValueError:
            continue

        quantity = 1.0
        unit_price = line_total

        # If we have more than one amount, try to treat the first small integer as quantity.
        if len(amounts) >= 2:
            first = amounts[0].replace(" ", "").replace(",", "")
            try:
                q_val = float(first)
                if 0 < q_val <= 10 and float(int(q_val)) == q_val:
                    quantity = q_val
                    unit_price = line_total / quantity if quantity > 0 else line_total
            except ValueError:
                pass

        # Derive a crude description: strip trailing amount-like tokens.
        desc = txt
        desc = _AMOUNT_RE.sub("", desc).strip()

        if not desc:
            continue

        items.append(
            LineItem(
                description=desc,
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total,
                confidence=line.confidence,
                line_index=line.index,
            )
        )

    return items


def _guess_merchant(lines: Sequence[RawLine]) -> ParsedStringField:
    if not lines:
        return ParsedStringField(value=None, confidence=None, line_index=None)
    first = lines[0]
    return ParsedStringField(
        value=first.text_raw or first.text_normalized,
        confidence=first.confidence,
        line_index=first.index,
    )


def parse_receipt(recognized_boxes: Iterable[RecognizedBox]) -> ParsedReceipt:
    """
    Entry point for rule-based parsing.

    Takes a sequence of `RecognizedBox` instances and returns a structured
    `ParsedReceipt` containing merchant, date, totals, items, currency, and
    raw lines with coordinates and confidences.
    """
    boxes_list = list(recognized_boxes)
    raw_lines = _boxes_to_lines(boxes_list)

    date_field = _parse_date_from_lines(raw_lines)
    subtotal_field = _find_amount_field(
        raw_lines,
        keywords=("סך הכל", "סכום ביניים", "ביניים"),
    )
    vat_field = _find_amount_field(
        raw_lines,
        keywords=("מע\"מ", "מעמ"),
    )
    total_field = _find_amount_field(
        raw_lines,
        keywords=("סה\"כ", "סהכ", "לתשלום", "לשלם"),
    )
    currency_field = _detect_currency(raw_lines)

    used_indices: List[int] = []
    for fld in (subtotal_field, vat_field, total_field):
        if fld.line_index is not None:
            used_indices.append(fld.line_index)

    items = _extract_items(raw_lines, used_indices)
    merchant_field = _guess_merchant(raw_lines)

    return ParsedReceipt(
        merchant=merchant_field,
        date=date_field,
        subtotal=subtotal_field,
        vat=vat_field,
        total=total_field,
        currency=currency_field,
        items=items,
        raw_lines=raw_lines,
    )

