"""
Line Extraction Service - Service 2 of 3
Extracts items from lines using column positions + heuristic matching.
Combines column inference with pattern matching for robust extraction.

Usage:
    items = extract_items_from_lines(raw_lines, columns)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from stages.grouping.line_assembler import RawLine, RecognizedBox
from stages.parsing.shared import _AMOUNT_RE, parse_amount

from .column_inferrer import ColumnLayout


@dataclass
class ExtractedLineItem:
    """An extracted item from a single line."""
    description: str
    quantity: float
    unit_price: float
    line_total: float
    catalog_no: Optional[str]
    confidence: float
    line_index: int
    raw_line: RawLine = None


# Header/footer patterns to skip (only at START of line)
SKIP_PATTERNS_START = [
    "חשבונית", "קלחמ", "דומע", "חוקל", "ךיראת", "תינובשח",
    "מ.ע", ".לט", "דוקימ", "ןופלט", "תבותכ", "דובכל",
    "םולשתל", "מעמ", "מ\"עמ", "כהס", "כ''הס", "פ.ח",
    "invoice", "תדועת", "bn", "רבוש",
    "םייניב םוכיס", "םוכיס", "מעמ ירחא", "מעמ ינפל",
    "סמ", "הלבק", "העש", "הפוק",
    # Skip specific header lines
    "שרפה", "םיטירפ", "תומכ",
    # Note: "החנה" is NOT skipped - item lines often have discounts
    "תינובשח",
]

# Patterns that indicate non-item anywhere in line
SKIP_PATTERNS_CONTAIN = [
    "רפסמ",  # number" - appears in headers but also in item info
]


def extract_items_from_lines(
    raw_lines: List[RawLine],
    columns: ColumnLayout = None,
    start_line: int = None,
    end_line: int = None,
    receipt_total: float = None
) -> List[ExtractedLineItem]:
    """
    Extract items from receipt lines.

    Args:
        raw_lines: All OCR lines
        columns: Inferred column positions
        start_line: First line index to process (optional)
        end_line: Last line index to process (optional)
        receipt_total: Known receipt total (for validation)

    Returns:
        List of extracted items
    """
    items = []

    # Determine range
    start = start_line if start_line is not None else 0
    end = end_line if end_line is not None else len(raw_lines)

    for i in range(start, min(end, len(raw_lines))):
        line = raw_lines[i]

        if columns and columns.is_valid:
            item = _extract_by_columns(line, columns, i, receipt_total)
        else:
            item = _extract_by_heuristic(line, i, receipt_total)

        if item:
            items.append(item)

    return items


def _extract_by_columns(
    line: RawLine,
    columns: ColumnLayout,
    line_idx: int,
    receipt_total: float = None
) -> Optional[ExtractedLineItem]:
    """Extract using column positions (more accurate)."""
    if not line.boxes:
        return None

    txt = (line.text_normalized or line.text_raw or "").lower()

    # Skip header/footer - check START of line for main patterns
    txt_stripped = txt.lstrip()
    if any(txt_stripped.startswith(p) for p in SKIP_PATTERNS_START):
        return None

    # Must have Hebrew
    if not any('\u0590' <= c <= '\u05FF' for c in txt):
        return None

    # Group boxes by column based on X position
    desc_boxes = []
    qty_boxes = []
    price_boxes = []
    total_boxes = []
    other_boxes = []

    for box in line.boxes:
        x_center = (box.box[0] + box.box[2]) / 2

        # Assign to column based on X position
        if columns.desc_x and columns.desc_x[0] <= x_center <= columns.desc_x[1]:
            desc_boxes.append(box)
        elif columns.qty_x and columns.qty_x[0] <= x_center <= columns.qty_x[1]:
            qty_boxes.append(box)
        elif columns.price_x and columns.price_x[0] <= x_center <= columns.price_x[1]:
            price_boxes.append(box)
        elif columns.total_x and columns.total_x[0] <= x_center <= columns.total_x[1]:
            total_boxes.append(box)
        else:
            # Try to determine if numeric
            text = box.text_normalized or box.text_raw or ""
            if _is_numeric(text):
                # Determine which is most likely
                if len(total_boxes) == 0:
                    total_boxes.append(box)
                elif len(price_boxes) == 0:
                    price_boxes.append(box)
                elif len(qty_boxes) == 0:
                    qty_boxes.append(box)
                else:
                    other_boxes.append(box)
            else:
                other_boxes.append(box)

    # Build description from non-numeric boxes
    if desc_boxes:
        desc_text = " ".join(b.text_normalized or b.text_raw or "" for b in desc_boxes)
    elif other_boxes:
        # Use other boxes that aren't clearly numeric
        non_numeric = [b for b in other_boxes if not _is_numeric(b.text_normalized or b.text_raw or "")]
        if non_numeric:
            desc_text = " ".join(b.text_normalized or b.text_raw or "" for b in non_numeric)
        else:
            desc_text = ""
    else:
        desc_text = ""

    if not desc_text or len(desc_text.strip()) < 2:
        return None

    # Must have Hebrew in description
    if not any('\u0590' <= c <= '\u05FF' for c in desc_text):
        return None

    # Get numeric values from columns
    def get_column_value(boxes):
        if not boxes:
            return None
        texts = [b.text_normalized or b.text_raw or "" for b in boxes]
        for t in texts:
            val = parse_amount(t)
            # FILTER: Skip catalog numbers (>10000)
            if val is not None and val > 0 and val <= 10000:
                return val
        return None

    total = get_column_value(total_boxes)
    price = get_column_value(price_boxes)
    qty = get_column_value(qty_boxes)

    # If we don't have enough numeric values, fall back to heuristic
    if not total or (not price and not qty):
        return None

    # Determine quantity and price
    if qty and price:
        # Both present - use them
        quantity = qty
        unit_price = price
    elif total and price:
        # Have total and price - calculate qty if reasonable
        quantity = 1.0
        unit_price = price
        if price > 0 and total > 0:
            calculated_qty = total / price
            if 0 < calculated_qty <= 10 and calculated_qty == int(calculated_qty):
                quantity = calculated_qty
    elif total and qty:
        # Have total and qty - calculate price
        quantity = qty
        if qty > 0:
            unit_price = round(total / qty, 2)
        else:
            unit_price = total
    else:
        # Fall back
        quantity = 1.0
        unit_price = total

    # Filter unrealistic values
    if total < 0.5:
        return None
    if quantity > 15:
        quantity = 1.0
    if unit_price > 2000 and quantity > 1:
        unit_price = total

    # Trim description
    desc = desc_text.strip()
    if len(desc) > 50:
        desc = desc[:50]

    # Find catalog number
    catalog_no = _find_catalog_number(txt, quantity, unit_price, total)

    return ExtractedLineItem(
        description=desc,
        quantity=quantity,
        unit_price=unit_price,
        line_total=total,
        catalog_no=catalog_no,
        confidence=line.confidence or 0.0,
        line_index=line_idx,
        raw_line=line
    )


def _extract_by_heuristic(
    line: RawLine,
    line_idx: int,
    receipt_total: float = None
) -> Optional[ExtractedLineItem]:
    """
    Extract using heuristics (fallback when columns not available).
    """
    if not line.boxes:
        return None

    txt = (line.text_normalized or line.text_raw or "").lower()
    if not txt:
        return None

    # Skip header/footer - check START of line for main patterns
    txt_stripped = txt.lstrip()
    if any(txt_stripped.startswith(p) for p in SKIP_PATTERNS_START):
        return None

    # Must have Hebrew
    if not any('\u0590' <= c <= '\u05FF' for c in txt):
        return None

    # Extract all amounts - MORE FLEXIBLE with receipt_total
    amounts = [m.group(1) for m in _AMOUNT_RE.finditer(txt)]

    # If we have receipt_total, be more flexible (accept even single amounts)
    if not amounts:
        return None

    # Accept line if we have any amounts + receipt_total
    if len(amounts) < 2 and not receipt_total:
        return None  # Without receipt_total, need ≥2 amounts

    # Parse amounts - MORE FLEXIBLE with receipt_total
    parsed_amounts = []
    for amt_str in amounts:
        amt = parse_amount(amt_str)
        if amt is not None:
            parsed_amounts.append(amt)

    # Accept if we have any parsed amounts + receipt_total
    if not parsed_amounts:
        return None
    if len(parsed_amounts) < 2 and not receipt_total:
        return None

    # Get line total - if only one amount, use it as total or derive from receipt_total
    valid_amounts = [a for a in parsed_amounts if 0.1 <= a <= 5000]
    if len(valid_amounts) == 0:
        return None
    if len(valid_amounts) < 2:
        # Only one valid amount - could be total or unit_price
        # If receipt_total is available, we can use it to estimate
        if receipt_total and len(parsed_amounts) >= 1:
            # Allow single amount but mark for follow-up validation
            line_total = valid_amounts[0]
        else:
            return None

    # Filter out catalog numbers - they appear as 5+ digit numbers
    # Also filter out discount amounts (usually < 0.5)
    non_catalog_amounts = [a for a in valid_amounts if a > 0.5]
    if not non_catalog_amounts:
        non_catalog_amounts = valid_amounts

    # For Tnuva receipts with discount format, the TOTAL is the LAST amount, not the largest
    # Format is: catalog, discount, item name, original_price, discounted_price, discount_%, final_total
    # We want the final_total which typically comes at the end
    line_total = non_catalog_amounts[-1] if len(non_catalog_amounts) > 1 else max(non_catalog_amounts)

    # For Tnuva receipts with discount format, the TOTAL is the LAST amount, not the largest
    # Format is: catalog, discount, item name, original_price, discounted_price, discount_%, final_total
    # We want the final_total which typically comes at the end
    line_total = non_catalog_amounts[-1] if len(non_catalog_amounts) > 1 else max(non_catalog_amounts)

    # Find quantity and price
    # For Tnuva receipts: quantity can be from 1-50 depending on the format
    # We need to find quantity by looking for small integers (1-50) that appear before the total
    quantity, unit_price = 1.0, line_total

    # Find quantity: look for small integers (1-50) that aren't the catalog number
    # They typically appear before the total
    for amt in parsed_amounts:
        if amt == line_total:
            continue
        try:
            if 1 <= amt <= 50 and float(int(amt)) == amt and amt != parsed_amounts[0]:
                quantity = amt
                unit_price = round(line_total / quantity, 2)
                break
        except (ValueError, TypeError):
            pass

    # Extract description (remove amounts and common noise)
    desc = _AMOUNT_RE.sub("", txt).strip()
    # Remove discount prefix "החנה" from description
    desc = re.sub(r"^החנה\s*", "", desc)
    desc = desc.strip(": ").strip()
    # Skip lines with clearly garbage descriptions
    if desc.startswith("רוקמ") or desc.startswith("==="):
        return None
    if not desc or len(desc) < 2:
        return None
    if not any('\u0590' <= c <= '\u05FF' for c in desc):
        return None
    if len(desc) > 50:
        desc = desc[:50]

    # Find catalog number
    catalog_no = _find_catalog_number(txt, quantity, unit_price, line_total)

    return ExtractedLineItem(
        description=desc,
        quantity=quantity,
        unit_price=unit_price,
        line_total=line_total,
        catalog_no=catalog_no,
        confidence=line.confidence or 0.0,
        line_index=line_idx,
        raw_line=line
    )


def _is_numeric(text: str) -> bool:
    """Check if text is numeric."""
    if not text:
        return False
    cleaned = text.replace(".", "").replace(",", "").replace("'", "").replace("-", "")
    return cleaned.isdigit()


def _find_catalog_number(
    text: str,
    quantity: float,
    unit_price: float,
    line_total: float
) -> Optional[str]:
    """Find catalog number (5+ digit number that's not a price/qty/total)."""
    for m in re.finditer(r"\b(\d{5,14})\b", text):
        num_str = m.group(1)
        try:
            num_val = float(num_str)
            if (abs(num_val - quantity) > 1 and
                abs(num_val - unit_price) > 1 and
                abs(num_val - line_total) > 1):
                return num_str
        except ValueError:
            pass
    return None


def _smart_select_total(
    amounts: List[float],
    receipt_total: float = None
) -> float:
    """
    Smart selection of line total from amounts.

    Uses multiple strategies:
    1. If receipt_total is available, find amount closest to expected (total / expected_item_count)
    2. Otherwise use the last amount (Tnuva format)
    3. If last is much larger than second last, use second last

    Args:
        amounts: Filtered amounts (no catalog numbers, no discounts)
        receipt_total: Known receipt total (if available)

    Returns:
        The most likely line total
    """
    if not amounts:
        return 0.0

    if len(amounts) == 1:
        return amounts[0]

    # Strategy 1: Use receipt_total if available
    # Estimate ~30 items on average for a receipt
    if receipt_total and receipt_total > 0:
        expected_item_total = receipt_total / 30
        # Find amount closest to expected
        closest = min(amounts, key=lambda a: abs(a - expected_item_total))
        return closest

    # Strategy 2: Use last amount (works for Tnuva format)
    last = amounts[-1]

    # But verify last isn't way bigger than second last (catalog number)
    if len(amounts) >= 2:
        second_last = amounts[-2]
        # If last is more than 5x second last, it's probably wrong
        if last > second_last * 5:
            return second_last

    return last
