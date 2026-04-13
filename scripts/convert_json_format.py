#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Convert between JSON formats:
1. Detailed ABBYY format (sample_images) → Simple Mindee-like format
2. Mindee OCR output → Detailed ABBYY format (for compatibility)

Usage:
    # Convert ABBYY format to simple format
    python convert_json_format.py input.JSON output.JSON --to-simple

    # Convert Mindee format to detailed format
    python convert_json_format.py input.JSON output.JSON --to-detailed
"""
import json
import os
import sys


def abbyy_to_simple(input_path: str, output_path: str = None) -> dict:
    """
    Convert detailed ABBYY JSON format to simple format.

    ABBYY format has:
        {"GDocument": {"fields": {"items": [...]}}}

    Simple format:
        {"GDocument": {"fields": {"items": [
            {"description": "...", "quantity": 1, "unit_price": 10, "line_total": 10}
        ]}}}
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    gdoc = data.get('GDocument', {})
    groups = gdoc.get('groups', [])

    # Find Table group
    items = []
    for group in groups:
        if group.get('name') == 'Table':
            for subgroup in group.get('groups', []):
                fields = subgroup.get('fields', [])

                # Extract fields
                item = {}
                for field in fields:
                    name = field.get('name')
                    value = field.get('value')
                    if name and value:
                        item[name] = value

                if item:
                    # Convert to simple format
                    simple_item = {
                        'description': item.get('CatalogNo', item.get('description', '')),
                        'quantity': float(item.get('Quantity', 1)),
                        'unit_price': float(item.get('Price', 0)),
                        'line_total': float(item.get('LineTotal', 0)),
                    }
                    items.append(simple_item)

    # Build simple format
    simple = {
        "GDocument": {
            "fields": {
                "items": items
            }
        }
    }

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(simple, f, indent=2, ensure_ascii=False)

    return simple


def simple_to_abbey(input_path: str, output_path: str = None) -> dict:
    """
    Convert simple Mindee-like format to detailed ABBYY format.
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    items = data.get('GDocument', {}).get('fields', {}).get('items', [])

    # Build detailed format
    table_items = []
    field_id = 8

    for item in items:
        table_items.append({
            "id": field_id,
            "name": "Price",
            "value": str(item.get('unit_price', 0)),
        })
        field_id += 1
        table_items.append({
            "id": field_id,
            "name": "Quantity",
            "value": str(item.get('quantity', 1)),
        })
        field_id += 1
        table_items.append({
            "id": field_id,
            "name": "CatalogNo",
            "value": item.get('description', ''),
        })
        field_id += 1
        table_items.append({
            "id": field_id,
            "name": "LineTotal",
            "value": str(item.get('line_total', 0)),
        })
        field_id += 1

    detailed = {
        "GDocument": {
            "id": "1",
            "documentDefinition": "InnoventoryTech",
            "batchId": 2340,
            "isAssembled": True,
            "isVerified": True,
            "groups": [{
                "name": "Table",
                "groups": [{
                    "name": "Table",
                    "fields": table_items
                }]
            }]
        }
    }

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(detailed, f, indent=2, ensure_ascii=False)

    return detailed


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    if '--to-simple' in sys.argv:
        abbyy_to_simple(input_path, output_path)
        print(f"Converted to simple format: {output_path or 'returned'}")
    elif '--to-detailed' in sys.argv:
        simple_to_abbey(input_path, output_path)
        print(f"Converted to detailed format: {output_path or 'returned'}")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()