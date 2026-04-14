"""
Mindee utilities - item conversion and extraction helpers.
"""
from typing import List, Dict, Any


def _items_to_dicts(items: list) -> list:
    """Convert Mindee items to dict format. Handles both object and dict formats."""
    result = []
    for item in items:
        # Handle dict format (Mindee plain dict response)
        if isinstance(item, dict):
            result.append({
                'description': item.get('description', item.get('Description', '')),
                'quantity': float(item.get('quantity', item.get('Quantity', 1))),
                'unit_price': float(item.get('unit_price', item.get('UnitPrice', 0))),
                'line_total': float(item.get('line_total', item.get('total', item.get('total_price', 0)))),
            })
        # Handle object format (Mindee SDK)
        elif hasattr(item, 'fields'):
            item_fields = item.fields
            desc = item_fields.get('description')
            qty = item_fields.get('quantity')
            unit_price = item_fields.get('unit_price')
            total_price = item_fields.get('total_price')

            result.append({
                'description': desc.value if desc and desc.value else '',
                'quantity': float(qty.value) if qty and qty.value else 1.0,
                'unit_price': float(unit_price.value) if unit_price and unit_price.value else 0.0,
                'line_total': float(total_price.value) if total_price and total_price.value else 0.0,
            })
    return result


def extract_items_from_result(result) -> List[Dict[str, Any]]:
    """Extract items from Mindee API result."""
    fields = result.inference.result.fields

    # Handle both dict and list formats from Mindee
    if isinstance(fields, list):
        fields_dict = {}
        for f in fields:
            if hasattr(f, 'name') and hasattr(f, 'value'):
                fields_dict[f.name] = f
        fields = fields_dict

    # Get line items
    line_items_field = fields.get('line_items')
    if line_items_field is None:
        return []
    elif hasattr(line_items_field, 'items'):
        items = line_items_field.items
    elif isinstance(line_items_field, list):
        items = line_items_field
    else:
        return []

    return _items_to_dicts(items)