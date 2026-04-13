"""
Convert Mindee output to ABBYY GDocument format.

ABBYY format structure:
{
  "GDocument": {
    "id": "1",
    "documentDefinition": "InnoventoryTech",
    "batchId": 2340,
    "isAssembled": true,
    "isVerified": true,
    "groups": [{
      "name": "Table",
      "groups": [{
        "name": "Table",
        "fields": [
          {"name": "Price", "value": "..."},
          {"name": "Quantity", "value": "..."},
          {"name": "CatalogNo", "value": "..."},
          {"name": "LineTotal", "value": "..."},
          {"name": "Discount1", "value": "..."},
          {"name": "Discount2", "value": "..."}
        ]
      }]
    }]
  }
}
"""
import json
from typing import List, Dict, Any


def mindee_to_abbey(items: List[Dict], receipt_name: str = "Receipt") -> Dict:
    """
    Convert Mindee items to ABBYY GDocument format.

    Args:
        items: List of items from Mindee [{"description": ..., "quantity": ..., "unit_price": ..., "line_total": ...}]
        receipt_name: Name for the receipt

    Returns:
        ABBYY format dict
    """
    # Build table groups
    table_groups = []
    field_id = 8

    for idx, item in enumerate(items):
        # Extract values
        description = item.get('description', '')
        quantity = item.get('quantity', 1)
        unit_price = item.get('unit_price', 0)
        line_total = item.get('line_total', item.get('total', 0))

        # Determine catalog number (from description if present)
        # Usually catalog numbers are at end of description or in parentheses
        catalog_no = _extract_catalog_no(description)

        # Discount field (if negative items exist)
        discount = item.get('discount', 0)

        fields = [
            {
                "id": field_id,
                "name": "Price",
                "value": str(unit_price),
            },
            {
                "id": field_id + 1,
                "name": "Quantity",
                "value": str(quantity),
            },
            {
                "id": field_id + 2,
                "name": "CatalogNo",
                "value": catalog_no,
            },
            {
                "id": field_id + 3,
                "name": "LineTotal",
                "value": str(line_total),
            },
            {
                "id": field_id + 4,
                "name": "Discount1",
                "value": str(discount) if discount else "",
            },
            {
                "id": field_id + 5,
                "name": "Discount2",
                "value": "",
            },
        ]

        table_groups.append({
            "name": "Table",
            "caption": "Table",
            "path": f"InnovatoryTech\\Table[{idx}]",
            "groups": [],
            "fields": fields
        })

        field_id += 6

    # Build full GDocument
    gdoc = {
        "GDocument": {
            "id": "1",
            "documentDefinition": "InnoventoryTech",
            "batchId": 2340,
            "isAssembled": True,
            "isVerified": True,
            "processingErrors": "",
            "processingWarnings": "",
            "totalSymbolsCount": len(items) * 10,
            "recognizedSymbolsCount": len(items) * 10,
            "uncertainSymbolsCount": "0",
            "name": receipt_name,
            "caption": receipt_name,
            "path": "",
            "groups": [
                {
                    "name": "Table",
                    "caption": "Table",
                    "path": "InnovatoryTech\\Table",
                    "groups": table_groups,
                    "fields": []
                }
            ],
            "fields": {},
            "errors": ""
        }
    }

    return gdoc


def _extract_catalog_no(description: str) -> str:
    """
    Extract catalog number from description.
    Looks for patterns like:
    - 729000xxxxxxx (Israeli barcodes)
    - Numbers in parentheses
    """
    if not description:
        return ""

    import re

    # Look for Israeli barcode pattern (7290...)
    match = re.search(r'7290\d{7,}', description)
    if match:
        return match.group()

    # Look for any 8+ digit number
    match = re.search(r'\d{8,}', description)
    if match:
        return match.group()

    return ""


def save_abbey_format(gdoc: Dict, output_path: str):
    """Save ABBYY format to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(gdoc, f, indent=2, ensure_ascii=False)