"""Post-processing for receipt data.

Generic post-processing for line items that works across all vendors.
Vendor-specific rules are kept in vendor_logic module.
"""
from __future__ import annotations

import re
from typing import List, Optional, Any

# Weight patterns - generic (kg, gram, lb, oz, etc.)
_WEIGHT_RE = re.compile(
    r'(\d+(?:[.,]\d+)?)\s*'
    r'(ק"ג|קג|גרם|גר\'|кг|kг|kg|lb|lbs|oz)',
    re.IGNORECASE
)

# Produce code (PLU) patterns - typically 4-7 digit codes
_PLUS_RE = re.compile(r'\b(\d{4,7})\b')


def extract_produce_codes_from_lines(
    lines: list,
) -> list:
    """Extract produce codes (PLU codes) from OCR lines.

    Scans OCR lines for 4-5 digit codes that could be produce codes.
    Returns list of dicts with value, confidence, line_index.

    Args:
        lines: OCR lines from receipt

    Returns:
        List of produce code dicts
    """
    if not lines:
        return []

    code_candidates = []
    for line in lines:
        txt = getattr(line, 'text_normalized', None) or getattr(line, 'text_raw', '') or ''
        for m in _PLUS_RE.finditer(txt):
            code = m.group(1)
            # Skip common non-PLU numbers (dates, prices, quantities)
            if len(code) == 8 and code.startswith('20'):
                continue
            try:
                num_val = float(code)
                if num_val > 100000:
                    continue
            except ValueError:
                pass
            code_candidates.append({
                'value': code,
                'confidence': 0.7,
                'line_index': getattr(line, 'index', 0),
            })

    return code_candidates


def extract_produce_codes_from_descriptions(
    descriptions: list,
) -> list:
    """Extract produce codes from Mindee item descriptions.

    Mindee descriptions may contain PLU codes at the end or embedded.
    Looks for 4-7 digit codes in descriptions.

    Args:
        descriptions: List of item descriptions

    Returns:
        List of produce code dicts
    """
    if not descriptions:
        return []

    code_candidates = []
    for desc in descriptions:
        if not desc:
            code_candidates.append({'value': None, 'confidence': 0.0, 'line_index': 0})
            continue

        # Search for 4-7 digit codes in description
        # Common patterns: at end of line, after space, or as standalone
        matches = list(_PLUS_RE.finditer(desc))

        found_code = None
        for m in matches:
            code = m.group(1)
            # Filter out likely non-PLU codes
            if len(code) == 8 and code.startswith('20'):
                continue  # Skip dates
            # Skip if looks like a very large quantity (> 1000 units) or price (> 10000)
            try:
                val = float(code)
                # Skip 8-digit numbers that could be dates
                if len(code) == 8 and val > 20000000:
                    continue
                # Skip obvious prices (have decimal-like patterns in description context)
                if val > 10000000:
                    continue
            except ValueError:
                pass
            found_code = code
            break

        code_candidates.append({
            'value': found_code,
            'confidence': 0.7 if found_code else 0.0,
            'line_index': 0,
        })

    return code_candidates


def assign_produce_codes_to_items(
    items: list,
    produce_codes: list,
) -> list:
    """Assign produce codes to line items.

    Maps extracted produce codes to items. Simple position-based assignment.

    Args:
        items: Line items
        produce_codes: Extracted produce codes

    Returns:
        Items with catalog_no populated
    """
    for i, item in enumerate(items):
        if i < len(produce_codes):
            item.catalog_no = produce_codes[i]['value'] if produce_codes[i] else None
    return items


def calculate_weight_amount(
    description: str,
    unit_price: float,
) -> Optional[float]:
    """Calculate amount for weight-based items from description.

    Looks for weight information in item description (e.g., "0.450 ק\"ג")
    and calculates: amount = unit_price * weight

    Args:
        description: Item description text
        unit_price: Price per unit

    Returns:
        Calculated amount if weight detected, None otherwise
    """
    if not description or unit_price <= 0:
        return None

    weight_match = _WEIGHT_RE.search(description)
    if weight_match:
        weight_str = weight_match.group(1).replace(',', '.')
        try:
            weight = float(weight_str)
            if weight > 0:
                return round(unit_price * weight, 2)
        except ValueError:
            pass

    return None


def fix_incorrect_amounts(
    items: list,
    tolerance: float = 0.5,
) -> list:
    """Fix items where line_total doesn't match price * quantity.

    Generic fix that checks if line_total is consistent with price * quantity.
    If not, tries to recalculate using weight-based calculation.

    Args:
        items: Line items
        tolerance: Acceptable difference threshold

    Returns:
        Items with corrected line_total values
    """
    for item in items:
        if not getattr(item, 'description', None) or getattr(item, 'unit_price', 0) <= 0:
            continue

        # Check expected value
        qty = getattr(item, 'quantity', None) or 1
        expected = item.unit_price * qty
        actual = getattr(item, 'line_total', None) or 0

        if actual > 0 and expected > 0:
            diff = abs(expected - actual)
            if diff > tolerance:
                # Try weight-based calculation first
                weight_amount = calculate_weight_amount(
                    getattr(item, 'description', '') or '',
                    item.unit_price,
                )
                if weight_amount:
                    item.line_total = weight_amount
                    item.quantity = 1.0

    return items


def post_process_items_generic(
    items: list,
    vendor: Optional[Any] = None,
    ocr_lines: Optional[list] = None,
    produce_codes: Optional[list] = None,
) -> list:
    """Generic post-processing for line items.

    Applies:
    1. Produce code assignment from OCR
    2. Weight-based amount fixes
    3. Amount consistency fixes

    Args:
        items: Extracted line items
        vendor: Vendor name (for vendor-specific rules)
        ocr_lines: OCR lines for produce code extraction
        produce_codes: Pre-extracted produce codes

    Returns:
        Processed line items
    """
    # Assign produce codes
    if produce_codes:
        items = assign_produce_codes_to_items(items, produce_codes)
    elif ocr_lines:
        codes = extract_produce_codes_from_lines(ocr_lines)
        items = assign_produce_codes_to_items(items, codes)

    # Apply generic fixes (weight-based amounts, consistency checks)
    items = fix_incorrect_amounts(items)

    # Apply vendor-specific rules (lazy import to avoid circular imports)
    try:
        from stages.post_process.vendor_logic import apply_vendor_rules
        items = apply_vendor_rules(items, vendor, ocr_lines)
    except ImportError:
        pass  # Vendor rules not available

    return items


__all__ = [
    "extract_produce_codes_from_lines",
    "assign_produce_codes_to_items",
    "calculate_weight_amount",
    "fix_incorrect_amounts",
    "post_process_items_generic",
]