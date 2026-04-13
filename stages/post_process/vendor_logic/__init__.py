"""Vendor-specific post-processing rules.

Contains special handling for vendors with unique receipt layouts.
"""
from __future__ import annotations

import re
from typing import List, Optional, Sequence, Dict, Any

from stages.grouping.line_assembler import RawLine
from stages.parsing.shared import LineItem, ParsedStringField, ParsedAmountField


# Weight patterns (kg, gram, etc.)
_WEIGHT_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s*(ק"ג|קג|גרם|גר\'|кг|kг|kg)', re.IGNORECASE)


def is_vendor_match(vendor: Optional[ParsedStringField], vendor_names: List[str]) -> bool:
    """Check if vendor matches any of the given names (case-insensitive)."""
    if not vendor or not vendor.value:
        return False
    vendor_lower = vendor.value.lower()
    for name in vendor_names:
        if name.lower() in vendor_lower or vendor_lower in name.lower():
            return True
    return False


def process_shufersal_items(
    items: List[LineItem],
    vendor: Optional[ParsedStringField] = None,
    ocr_lines: Optional[Sequence[RawLine]] = None,
) -> List[LineItem]:
    """Process items for Shufersal receipts.

    Shufersal receipts have a special layout where weight-based items
    show the unit weight (e.g., "0.450 ק\"ג") in the description.
    The quantity is 1, but the line_total should be:
    line_total = unit_price * weight (not unit_price * quantity)

    Args:
        items: Extracted line items
        vendor: Vendor name
        ocr_lines: OCR lines for additional lookup

    Returns:
        Updated line items with corrected amounts
    """
    if not is_vendor_match(vendor, ['shufersal', 'שופרסל']):
        return items

    for item in items:
        # Skip if no description or invalid prices
        if not item.description or item.unit_price <= 0:
            continue

        # Check if line_total matches price * quantity
        if item.quantity and item.quantity > 0:
            expected = item.quantity * item.unit_price
            if item.line_total and abs(expected - item.line_total) < 0.5:
                continue  # Standard calculation is fine

        # Try to find weight in item description
        weight_match = _WEIGHT_RE.search(item.description)
        if weight_match:
            weight_str = weight_match.group(1).replace(',', '.')
            try:
                weight = float(weight_str)
                # Calculate amount based on weight
                if weight > 0:
                    item.line_total = round(item.unit_price * weight, 2)
                    item.quantity = 1.0  # Normalize to unit quantity
            except ValueError:
                pass

    return items


def apply_vendor_rules(
    items: List[LineItem],
    vendor: Optional[ParsedStringField] = None,
    ocr_lines: Optional[Sequence[RawLine]] = None,
) -> List[LineItem]:
    """Apply all vendor-specific post-processing rules.

    Args:
        items: Extracted line items
        vendor: Vendor name
        ocr_lines: OCR lines for additional lookup

    Returns:
        Updated line items with all vendor rules applied
    """
    # Shufersal rules
    items = process_shufersal_items(items, vendor, ocr_lines)

    return items


# Vendor registry for extensibility
_VENDOR_RULES: Dict[str, callable] = {
    'shufersal': process_shufersal_items,
}


def register_vendor_rule(vendor_name: str, rule_func: callable) -> None:
    """Register a vendor-specific processing rule."""
    _VENDOR_RULES[vendor_name.lower()] = rule_func


def get_vendor_rule(vendor_name: str) -> Optional[callable]:
    """Get a registered vendor-specific rule."""
    return _VENDOR_RULES.get(vendor_name.lower())


__all__ = [
    "is_vendor_match",
    "process_shufersal_items",
    "apply_vendor_rules",
    "register_vendor_rule",
    "get_vendor_rule",
]