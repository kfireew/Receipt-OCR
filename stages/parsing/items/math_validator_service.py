"""
Math Validation Service - Service 3 of 3

Validates that extracted item calculations are correct.
Can fix items where qty * price ≠ total by recalculating.

Service Interface:
    validate_items(items: List[TableItem]) -> List[ValidatedItem]
    fix_math_mismatches(items: List[TableItem]) -> List[TableItem]
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum

from .table_reader_service import TableItem


class MathStatus(Enum):
    """Status of math validation."""
    VALID = "valid"
    RECALCULATED_TOTAL = "recalculated_total"
    RECALCULATED_PRICE = "recalculated_price"
    RECALCULATED_QTY = "recalculated_qty"
    INVALID = "invalid"  # Could not fix


@dataclass
class ValidatedItem:
    """An item with math validation result."""
    description: str
    quantity: float
    unit_price: float
    line_total: float
    catalog_no: Optional[str]
    confidence: float
    line_index: int
    math_status: MathStatus
    original_total: Optional[float] = None
    notes: Optional[str] = None


def validate_items(items: List[TableItem]) -> List[ValidatedItem]:
    """
    Validate math for a list of items.

    Args:
        items: List of extracted table items

    Returns:
        List of ValidatedItem with math status
    """
    validated = []

    for item in items:
        result = _validate_item(item)
        validated.append(result)

    return validated


def fix_math_mismatches(items: List[TableItem]) -> List[TableItem]:
    """
    Fix items where the math doesn't add up.

    Strategy:
    1. If qty * price ≈ total (within tolerance): keep as-is
    2. If price * qty ≠ total but total is correct: recalculate price
    3. If total looks wrong but qty and price are reasonable: recalculate total
    4. If qty is unclear (1): set qty=1, price=total

    Args:
        items: List of extracted items

    Returns:
        List of items with corrected math
    """
    fixed = []

    for item in items:
        fixed_item = _fix_item_math(item)
        fixed.append(fixed_item)

    return fixed


def _validate_item(item: TableItem) -> ValidatedItem:
    """Validate a single item."""
    expected_total = item.quantity * item.unit_price
    tolerance = 0.05  # 5% tolerance

    if expected_total == 0:
        if item.line_total == 0:
            return ValidatedItem(
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
                catalog_no=item.catalog_no,
                confidence=item.confidence,
                line_index=item.line_index,
                math_status=MathStatus.VALID,
                notes="Zero total is valid"
            )
        else:
            return ValidatedItem(
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
                catalog_no=item.catalog_no,
                confidence=item.confidence,
                line_index=item.line_index,
                math_status=MathStatus.INVALID,
                notes="Expected non-zero total"
            )

    ratio = abs(expected_total - item.line_total) / item.line_total

    if ratio <= tolerance:
        return ValidatedItem(
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.line_total,
            catalog_no=item.catalog_no,
            confidence=item.confidence,
            line_index=item.line_index,
            math_status=MathStatus.VALID,
            notes=f"Math valid (ratio: {ratio:.2%})"
        )

    # Mismatch - determine what to fix
    price_ratio = abs(item.unit_price * item.quantity - item.line_total) / max(item.line_total, 0.01)
    if price_ratio <= tolerance:
        return ValidatedItem(
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.line_total,
            catalog_no=item.catalog_no,
            confidence=item.confidence,
            line_index=item.line_index,
            math_status=MathStatus.INVALID,
            original_total=item.line_total,
            notes=f"Price mismatch: {item.quantity} x {item.unit_price} ≠ {item.line_total}"
        )

    return ValidatedItem(
        description=item.description,
        quantity=item.quantity,
        unit_price=item.unit_price,
        line_total=item.line_total,
        catalog_no=item.catalog_no,
        confidence=item.confidence,
        line_index=item.line_index,
        math_status=MathStatus.INVALID,
        notes=f"Math mismatch: expected ~{expected_total:.2f}, got {item.line_total:.2f}"
    )


def _fix_item_math(item: TableItem) -> TableItem:
    """Fix math for a single item."""
    expected_total = item.quantity * item.unit_price

    if expected_total == 0:
        return item

    ratio = abs(expected_total - item.line_total) / max(item.line_total, 0.01)

    # If within tolerance, keep as-is
    if ratio <= 0.05:
        return item

    # Calculate what the price SHOULD be based on qty and total
    correct_price = item.line_total / item.quantity if item.quantity > 0 else 0

    # Calculate what the qty SHOULD be based on price and total
    correct_qty = item.line_total / item.unit_price if item.unit_price > 0 else 0

    # Determine the best fix strategy
    # Priority order:
    # 1. If qty is a small integer (1-10), fix the TOTAL (most common OCR error)
    # 2. If qty is unusual (0, negative, >20, decimal >1), fix QTY
    # 3. If price is clearly wrong, fix PRICE
    # 4. Fallback: recalculate based on most reasonable assumption

    # Check if qty is a "clean" integer (likely correct)
    is_qty_clean = (
        0 < item.quantity <= 10 and
        item.quantity == int(item.quantity)
    )

    # Check if qty is unusual (likely wrong)
    is_qty_unusual = (
        item.quantity <= 0 or
        item.quantity > 20 or
        (item.quantity != int(item.quantity) and item.quantity > 1)
    )

    if is_qty_clean and item.unit_price > 0:
        # Qty looks correct, total is most likely wrong
        return TableItem(
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=round(expected_total, 2),
            catalog_no=item.catalog_no,
            confidence=item.confidence * 0.9,
            line_index=item.line_index
        )

    if is_qty_unusual and item.unit_price > 0:
        # Qty looks wrong, fix it
        return TableItem(
            description=item.description,
            quantity=round(correct_qty, 2),
            unit_price=item.unit_price,
            line_total=item.line_total,
            catalog_no=item.catalog_no,
            confidence=item.confidence * 0.9,
            line_index=item.line_index
        )

    # For decimal quantities like 0.5, try to figure out which is wrong
    if 0 < item.quantity < 1 and item.unit_price > 0:
        # qty is a small decimal - likely correct (weight in kg?)
        # But price might be per unit, total is for the actual amount
        # Let's fix the price to match
        return TableItem(
            description=item.description,
            quantity=item.quantity,
            unit_price=round(correct_price, 2),
            line_total=item.line_total,
            catalog_no=item.catalog_no,
            confidence=item.confidence * 0.9,
            line_index=item.line_index
        )

    # Default: fix total
    return TableItem(
        description=item.description,
        quantity=item.quantity,
        unit_price=item.unit_price,
        line_total=round(expected_total, 2),
        catalog_no=item.catalog_no,
        confidence=item.confidence * 0.9,
        line_index=item.line_index
    )


def calculate_receipt_totals(items: List[TableItem]) -> Tuple[float, float, float]:
    """
    Calculate subtotal, VAT, and total from items.

    Args:
        items: List of validated items

    Returns:
        Tuple of (subtotal, vat_amount, total)
    """
    subtotal = sum(item.line_total for item in items if item.line_total > 0)

    # VAT is typically 17% in Israel
    vat_rate = 0.17
    vat_amount = round(subtotal * vat_rate, 2)
    total = round(subtotal + vat_amount, 2)

    return subtotal, vat_amount, total