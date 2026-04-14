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
import os
from typing import List, Dict, Any


def _get_english_vendor(hebrew_vendor: str) -> str:
    """Convert Hebrew vendor to English using merchants_mapping.json.

    Uses fuzzy matching:
    1. Exact match (100%)
    2. Partial match (keyword in vendor or vendor in keyword)
    3. Fuzzy match (character overlap >= 50%)
    """
    if not hebrew_vendor:
        return hebrew_vendor

    mapping_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "merchants_mapping.json")
    try:
        with open(mapping_path, 'rb') as f:
            content = f.read().decode('utf-8')
        mapping = json.loads(content)
    except Exception:
        return hebrew_vendor

    # Build reverse mapping: Hebrew keyword -> English vendor name
    hebrew_to_english = {}
    for english_name, hebrew_keywords in mapping.items():
        for kw in hebrew_keywords:
            hebrew_to_english[kw] = english_name

    # 1. Exact match
    if hebrew_vendor in hebrew_to_english:
        return hebrew_to_english[hebrew_vendor]

    # 2. Partial match (keyword in vendor OR vendor in keyword)
    for keyword, english_name in hebrew_to_english.items():
        if keyword in hebrew_vendor or hebrew_vendor in keyword:
            return english_name

    # 3. Fuzzy match - find keyword with highest character overlap
    best_match = None
    best_score = 0

    for keyword, english_name in hebrew_to_english.items():
        score = _char_overlap(hebrew_vendor, keyword)
        if score > best_score and score >= 0.5:  # At least 50% overlap
            best_score = score
            best_match = english_name

    if best_match:
        return best_match

    return hebrew_vendor


def _char_overlap(s1: str, s2: str) -> float:
    """Calculate character overlap between two strings (0.0 to 1.0)."""
    set1 = set(s1)
    set2 = set(s2)
    if not set1 or not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union


def mindee_to_abbey(items: List[Dict], receipt_name: str = "Receipt", vendor: str = "", date: str = "") -> Dict:
    """
    Convert Mindee items to ABBYY GDocument format.

    Args:
        items: List of items from Mindee [{"description": ..., "quantity": ..., "unit_price": ..., "line_total": ...}]
        receipt_name: Name for the receipt
        vendor: Vendor name (optional)
        date: Date string (optional)

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

    # Calculate total from items
    total = sum(float(item.get('line_total', 0)) for item in items)

    # Build full GDocument with top-level fields for PHP compatibility
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
            # Top-level fields for PHP compatibility
            # Format: [InvoiceNo, ?, VendorName, ?, Date, ?, Total, ?]
            "fields": [
                {"name": "InvoiceNo", "value": ""},
                {"name": "Field1", "value": ""},
                {"name": "VendorName", "value": _get_english_vendor(vendor)},
                {"name": "Field3", "value": ""},
                {"name": "Date", "value": date},
                {"name": "Field5", "value": ""},
                {"name": "Total", "value": str(total)},
                {"name": "Field7", "value": ""},
            ],
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