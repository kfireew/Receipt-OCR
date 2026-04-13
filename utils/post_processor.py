"""
Post-processor for fixing common OCR mistakes.

Fixes:
1. Quantity = Weight (e.g., "250g" → qty=250 instead of count)
2. Missing discount field
3. Duplicate items
"""
import re
from typing import List, Dict, Any


# Common Hebrew weight patterns
WEIGHT_PATTERNS = [
    r'(\d+)\s*גרם?',      # 250גרם, 250 גרם
    r'(\d+)\s*גר',         # 200גר
    r'(\d+)\s*ק"ג',        # 1ק"ג (kilo)
    r'(\d+)\s*קילו',       # קילו
]

# Patterns that indicate a discount line
DISCOUNT_PATTERNS = [
    r'^הנחה',
    r'הנחה\s*\d+%',
    r'discount',
    r'מבצע',
]

# Percentage patterns like "5%" in description
PERCENT_PATTERN = r'(\d+)\s*%'


def has_weight_in_description(description: str) -> tuple[bool, int]:
    """
    Check if description contains weight and return the weight value.

    Returns: (has_weight, weight_value)
    """
    if not description:
        return False, 0

    for pattern in WEIGHT_PATTERNS:
        match = re.search(pattern, description)
        if match:
            weight = int(match.group(1))
            # Convert kilos to grams
            if 'ק"ג' in description or 'קילו' in description:
                weight *= 1000
            return True, weight

    return False, 0


def is_likely_weight_quantity(quantity: float, unit_price: float, line_total: float) -> bool:
    """
    Determine if quantity is actually wrong (weight in grams).

    Returns True ONLY if:
    - quantity is a common weight like 250, 200, 100, etc (in grams)

    DO NOT fix when:
    - qty * unit_price != line_total (that's a discount, not an error)
    - price looks wrong (like 720 instead of 7.20) - just calculate discount from line_total

    The line_total is the source of truth - we fix quantities, not prices.
    """
    # Only fix obvious weight patterns like 250g, 200g, 100g
    if quantity > 50:
        common_weights = {50, 100, 150, 200, 250, 300, 400, 500, 750, 1000, 1500, 2000}
        if int(quantity) in common_weights:
            return True

    return False


# Common discount percentages in Israeli receipts
# Prioritized: 10% and 23.5% are most common
COMMON_DISCOUNTS = {0, 5, 10, 15, 20, 23.5, 25, 30, 40, 50}
# Super common discounts to prioritize
SUPER_COMMON = {10, 23.5}


def fix_quantity_from_price(quantity: float, unit_price: float, line_total: float) -> float:
    """
    Calculate actual item count from line_total and unit_price.

    Algorithm:
    1. Find all candidate qties where qty * unit_price >= line_total
    2. Calculate discount for each candidate
    3. Prefer ROUND discounts (10%, 23.5%) even if higher
    4. Among round discounts, prefer HIGHER qty (more items with bigger discount)
    5. Fall back to lowest non-round discount
    """
    if unit_price <= 0:
        return quantity

    calculated = line_total / unit_price
    start_qty = int(calculated)
    if start_qty < 1:
        start_qty = 1

    round_options = []
    non_round_options = []

    # Check candidates
    max_qty = start_qty + 5

    for q in range(start_qty, max_qty + 1):
        expected = q * unit_price
        if expected >= line_total:
            discount_pct = ((expected - line_total) / expected) * 100
            if discount_pct > 50:
                continue

            is_round = round(discount_pct, 1) in COMMON_DISCOUNTS
            if is_round:
                round_options.append((q, discount_pct))
            else:
                non_round_options.append((q, discount_pct))

    # Prefer round discounts
    if round_options:
        # Prioritize super common discounts (10%, 23.5%)
        super_common = [(q,d) for q,d in round_options if round(d,1) in SUPER_COMMON]
        if super_common:
            # Prefer super common, then lower discount
            super_common.sort(key=lambda x: x[1])
            return super_common[0][0]
        # Otherwise any round discount
        round_options.sort(key=lambda x: x[1])
        return round_options[0][0]

    # Fall back to lowest non-round
    if non_round_options:
        non_round_options.sort(key=lambda x: x[1])
        return non_round_options[0][0]

    return start_qty


def detect_discount_line(description: str, quantity: float, line_total: float) -> bool:
    """
    Check if line is a discount/negative line.
    """
    # Negative total indicates discount
    if line_total < 0:
        return True

    # Check for discount keywords
    description_lower = description.lower() if description else ''
    for pattern in DISCOUNT_PATTERNS:
        if re.search(pattern, description_lower):
            return True

    return False


def extract_percent_discount(description: str) -> float:
    """
    Extract percentage discount from description if present.

    E.g., "5% צפתית" → 5.0
    """
    if not description:
        return 0.0

    match = re.search(PERCENT_PATTERN, description)
    if match:
        return float(match.group(1))

    return 0.0


def calculate_discount(quantity: float, unit_price: float, line_total: float) -> float:
    """
    Calculate discount percentage from actual vs expected total.

    Expected = quantity * unit_price
    Discount = (Expected - Actual) / Expected * 100
    """
    expected = quantity * unit_price
    if expected <= 0:
        return 0.0

    # If line_total is close to expected, no discount
    if abs(line_total - expected) < 0.01:
        return 0.0

    # If line_total is less than expected, there's a discount
    if line_total < expected:
        discount_amount = expected - line_total
        discount_pct = (discount_amount / expected) * 100
        return round(discount_pct, 1)

    return 0.0


def process_items(items: List[Dict]) -> List[Dict]:
    """
    Process items list to fix common OCR issues.

    Args:
        items: List of item dicts with keys:
            description, quantity, unit_price, line_total

    Returns:
        Fixed items list
    """
    fixed_items = []

    for item in items:
        description = item.get('description', '')
        quantity = item.get('quantity', 1)
        unit_price = item.get('unit_price', item.get('unit', 0))
        line_total = item.get('line_total', item.get('total', 0))

        # 1. Check for discount line
        if detect_discount_line(description, quantity, line_total):
            # Keep negative quantity for discount lines
            item['discount'] = abs(line_total) if line_total < 0 else extract_percent_discount(description)
            fixed_items.append(item)
            continue

        # 2. Check if quantity looks like weight - FIRST fix quantity
        has_weight, weight_val = has_weight_in_description(description)
        is_weight_qty = is_likely_weight_quantity(quantity, unit_price, line_total)

        fixed_quantity = quantity
        if has_weight or is_weight_qty:
            # Calculate actual item count from price
            fixed_quantity = fix_quantity_from_price(quantity, unit_price, line_total)
            item['quantity'] = fixed_quantity
            # Note: might be a weight item
            item['is_weight_item'] = True

        # 3. Calculate discount from line_total vs expected using FIXED quantity
        if 'discount' not in item or item['discount'] == 0.0:
            item['discount'] = calculate_discount(fixed_quantity, unit_price, line_total)

        fixed_items.append(item)

    # 4. Deduplicate by description (keep first occurrence)
    seen = {}
    deduplicated = []
    for item in fixed_items:
        desc = item.get('description', '')
        if desc not in seen:
            seen[desc] = len(deduplicated)
            deduplicated.append(item)
        else:
            # Merge quantities if duplicates
            existing_idx = seen[desc]
            existing = deduplicated[existing_idx]
            existing['quantity'] = existing.get('quantity', 0) + item.get('quantity', 0)

    return deduplicated


def process_abbey_items(table_items: List[Dict]) -> List[Dict]:
    """
    Process items from ABBYY format (table groups).

    ABBYY format: each item has fields with name/value
    """
    items = []

    for table_item in table_items:
        fields = table_item.get('fields', [])

        # Extract field values
        item_dict = {}
        for field in fields:
            name = field.get('name', '')
            value = field.get('value', '')

            if name == 'Description' or name == 'description':
                item_dict['description'] = value
            elif name == 'Quantity' or name == 'quantity':
                item_dict['quantity'] = float(value) if value else 1
            elif name == 'Price' or name == 'UnitPrice':
                item_dict['unit_price'] = float(value) if value else 0
            elif name == 'LineTotal':
                item_dict['line_total'] = float(value) if value else 0
            elif name in ('Discount1', 'Discount2', 'discount'):
                item_dict['discount'] = float(value) if value else 0

        if item_dict.get('description'):
            items.append(item_dict)

    return process_items(items)