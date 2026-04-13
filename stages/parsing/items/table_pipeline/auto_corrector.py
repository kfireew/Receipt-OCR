"""
Auto-Correction Service - Service 3 of 3

Automatically corrects extracted items using heuristics:
- Fix math errors (qty * price ≠ total)
- Split lines with qty > 10
- Discard noise (total < 1)
- Fix common OCR misreads
- Infer missing values

Usage:
    corrected = auto_correct_items(items, receipt_total=None)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum

from .line_extractor import ExtractedLineItem


class CorrectionType(Enum):
    """Type of correction applied."""
    NONE = "none"
    FIXED_MATH = "fixed_math"
    SPLIT_LINE = "split_line"
    DISCARD_NOISE = "discard_noise"
    FIXED_PRICE = "fixed_price"
    INFERRED_QTY = "inferred_qty"


@dataclass
class CorrectedItem:
    """An item after auto-correction."""
    description: str
    quantity: float
    unit_price: float
    line_total: float
    catalog_no: Optional[str]
    confidence: float
    line_index: int
    corrections: List[CorrectionType]


def auto_correct_items(
    items: List[ExtractedLineItem],
    receipt_total: float = None,
    receipt_subtotal: float = None
) -> List[CorrectedItem]:
    """
    Auto-correct extracted items.

    Args:
        items: Raw extracted items
        receipt_total: Known receipt total (if available)
        receipt_subtotal: Known subtotal (if available)

    Returns:
        List of corrected items
    """
    corrected = []

    for item in items:
        c = _correct_single_item(item, receipt_total, receipt_subtotal)
        if c:
            corrected.append(c)

    return corrected


def _correct_single_item(
    item: ExtractedLineItem,
    receipt_total: float,
    receipt_subtotal: float
) -> Optional[CorrectedItem]:
    """Apply corrections to a single item. CONSERVATIVE approach."""
    corrections = []

    quantity = item.quantity
    unit_price = item.unit_price
    line_total = item.line_total
    description = item.description

    # Adaptive thresholds based on receipt_total
    if receipt_total and receipt_total > 0:
        max_threshold = min(1000, receipt_total * 0.25)  # Capped at 25% of receipt
    else:
        max_threshold = 1000

    # Filter 1: Discard noise (total too small)
    if line_total < 1.0:
        corrections.append(CorrectionType.DISCARD_NOISE)
        return None

    # Filter 2: Discard if quantity is unreasonable (> 50)
    if quantity > 50:
        corrections.append(CorrectionType.DISCARD_NOISE)
        return None

    # Filter 3: Adaptive max threshold
    if line_total > max_threshold:
        corrections.append(CorrectionType.DISCARD_NOISE)
        return None

    # ONLY fix if VERY wrong (> 30% off)
    expected = quantity * unit_price
    if expected > 0:
        ratio = abs(expected - line_total) / line_total
        if ratio > 0.30:  # Only fix if MORE than 30% off
            # Only fix if we can clearly tell what's wrong
            fixed = _fix_math_mismatch(quantity, unit_price, line_total)
            if fixed and abs(fixed[0] * fixed[1] - line_total) / line_total < 0.05:
                # Only apply if the fix is clearly better (< 5% off)
                quantity, unit_price = fixed
                corrections.append(CorrectionType.FIXED_MATH)

    # DON'T swap qty/price - causes more harm than good
    # The original extraction is usually correct

    # Recalculate to ensure consistency
    if quantity > 0:
        line_total = round(quantity * unit_price, 2)

    # Fix 4: Clean description
    description = _clean_description(description)

    return CorrectedItem(
        description=description,
        quantity=quantity,
        unit_price=unit_price,
        line_total=line_total,
        catalog_no=item.catalog_no,
        confidence=item.confidence,
        line_index=item.line_index,
        corrections=corrections
    )


def _fix_math_mismatch(
    quantity: float,
    unit_price: float,
    line_total: float
) -> Optional[Tuple[float, float]]:
    """
    Fix math mismatch.

    Returns: (fixed_qty, fixed_price) or None if can't fix
    """
    # Case 1: qty * price > total → price is too high
    # Keep qty, recalculate price
    if quantity > 0 and quantity <= 10:
        new_price = round(line_total / quantity, 2)
        if new_price > 0:
            return (quantity, new_price)

    # Case 2: qty might be wrong
    # Try common quantities
    for test_qty in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
        test_price = round(line_total / test_qty, 2)
        if test_price > 0 and test_price < 1000:  # Reasonable price
            return (float(test_qty), test_price)

    # Case 3: prices might be swapped
    # If current price is small int and qty is large, swap
    if unit_price <= 10 and unit_price == int(unit_price):
        if quantity > 10:
            new_price = quantity
            new_qty = unit_price
            return (float(new_qty), float(new_price))

    return None


def _clean_description(desc: str) -> str:
    """Clean up description text."""
    if not desc:
        return ""

    # Remove common OCR noise
    desc = re.sub(r'[{}\[\]|~^]+', '', desc)
    desc = re.sub(r'\s+', ' ', desc)
    desc = desc.strip()

    # Trim to reasonable length
    if len(desc) > 40:
        desc = desc[:40]

    return desc


def validate_with_receipt_total(
    items: List[CorrectedItem],
    receipt_total: float
) -> Tuple[List[CorrectedItem], float]:
    """
    Validate items against receipt total.

    Returns: (adjusted_items, difference)
    """
    if not items or not receipt_total:
        return items, 0.0

    current_sum = sum(i.line_total for i in items)
    diff = receipt_total - current_sum

    # If difference is small, adjust the largest item
    if abs(diff) > 0.01 and abs(diff) < 10:
        if items:
            # Find largest item
            largest = max(items, key=lambda x: x.line_total)
            largest.line_total = round(largest.line_total + diff, 2)
            current_sum = sum(i.line_total for i in items)

    return items, current_sum - receipt_total
