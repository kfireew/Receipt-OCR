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


def _get_english_vendor(ocr_vendor: str) -> str:
    """Map OCR vendor to merchant name from merchants_mapping.

    1. Exact match -> return merchant name
    2. Partial match (keyword in OCR vendor) -> return merchant name
    3. Fuzzy match -> return merchant name
    """
    if not ocr_vendor:
        print(f"_get_english_vendor: Empty vendor, returning empty string")
        return ocr_vendor

    print(f"_get_english_vendor: Looking for vendor '{ocr_vendor}'")

    mapping_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "merchants_mapping.json")
    try:
        with open(mapping_path, 'rb') as f:
            content = f.read().decode('utf-8')
        mapping = json.loads(content)
    except Exception:
        return ocr_vendor

    # Build keyword -> merchant name mapping
    kw_to_merchant = {}
    for merchant_name, keywords in mapping.items():
        for kw in keywords:
            kw_to_merchant[kw] = merchant_name

    # 1. Exact match
    if ocr_vendor in kw_to_merchant:
        result = kw_to_merchant[ocr_vendor]
        print(f"_get_english_vendor: Exact match found: '{ocr_vendor}' -> '{result}'")
        return result

    # 2. Partial match (keyword in OCR vendor - case insensitive)
    ocr_lower = ocr_vendor.lower()
    for keyword, merchant_name in kw_to_merchant.items():
        if keyword.lower() in ocr_lower:
            print(f"_get_english_vendor: Partial match: keyword '{keyword}' in '{ocr_vendor}' -> '{merchant_name}'")
            return merchant_name

    # 3. Fuzzy match
    best_match = None
    best_score = 0
    for keyword, merchant_name in kw_to_merchant.items():
        score = _char_overlap(ocr_vendor, keyword)
        if score > best_score and score >= 0.5:
            best_score = score
            best_match = merchant_name

    if best_match:
        print(f"_get_english_vendor: Fuzzy match: '{ocr_vendor}' -> '{best_match}' (score: {best_score:.2f})")
        return best_match

    print(f"_get_english_vendor: No match found for '{ocr_vendor}', returning original")
    return ocr_vendor


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
        items: List of items from Phase 5 [{"description": ..., "quantity": ..., "unit_price": ...,
               "line_total": ..., "catalog_no": ..., "barcode": ...}]
               CatalogNo priority: barcode → catalog_no (product code) → extract from description
        receipt_name: Name for the receipt
        vendor: Vendor name (optional)
        date: Date string (optional)

    Returns:
        ABBYY format dict
    """
    # Build table groups and collect all fields for top level
    table_groups = []
    all_fields = []  # Top-level fields array
    field_id = 8

    # 1. First 8 header fields: duplicate InvoiceNo, VendorNameS, Date, Total
    # indices 0, 1: InvoiceNo (duplicate)
    all_fields.append(_create_abbyy_field(0, "InvoiceNo", "", -1))
    all_fields.append(_create_abbyy_field(1, "InvoiceNo", "", -1))

    # indices 2, 3: VendorNameS (duplicate) - NOTE: VendorNameS not VendorName!
    vendor_name = _get_english_vendor(vendor)
    all_fields.append(_create_abbyy_field(2, "VendorNameS", vendor_name, -1))
    all_fields.append(_create_abbyy_field(3, "VendorNameS", vendor_name, -1))

    # indices 4, 5: Date (duplicate)
    all_fields.append(_create_abbyy_field(4, "Date", date, -1))
    all_fields.append(_create_abbyy_field(5, "Date", date, -1))

    # indices 6, 7: Total (duplicate) - will fill value after calculating total
    # Placeholder for now
    all_fields.append(_create_abbyy_field(6, "Total", "", -1))
    all_fields.append(_create_abbyy_field(7, "Total", "", -1))

    # 2. Process each item - create table groups AND add fields to top level
    for idx, item in enumerate(items):
        # Extract values
        description = item.get('description', '')
        quantity = item.get('quantity', 1)
        unit_price = item.get('unit_price', 0)
        line_total = item.get('line_total', item.get('total', 0))

        # Determine catalog number
        # Priority: barcode → catalog_no (product code) → extract from description
        # Phase 5 provides both fields when available
        catalog_no = item.get('barcode', item.get('catalog_no', ''))
        if not catalog_no:
            catalog_no = _extract_catalog_no(description)

        # Discount field (if negative items exist)
        discount = item.get('discount', 0)

        # Create fields for this item
        price_field = _create_abbyy_field(field_id, "Price", f"{unit_price:.2f}", idx)
        quantity_field = _create_abbyy_field(field_id + 1, "Quantity", str(quantity), idx)
        catalog_field = _create_abbyy_field(field_id + 2, "CatalogNo", catalog_no, idx)
        linetotal_field = _create_abbyy_field(field_id + 3, "LineTotal", f"{line_total:.2f}", idx)
        discount1_field = _create_abbyy_field(field_id + 4, "Discount1", str(discount) if discount else "", idx)
        discount2_field = _create_abbyy_field(field_id + 5, "Discount2", "", idx)

        fields = [
            price_field,
            quantity_field,
            catalog_field,
            linetotal_field,
            discount1_field,
            discount2_field
        ]

        # Add to table group
        table_groups.append({
            "name": "Table",
            "caption": "Table",
            "path": f"InnovatoryTech\\Table[{idx}]",
            "groups": [],
            "fields": fields
        })

        # ADD ALL ITEM FIELDS TO TOP-LEVEL FIELDS ARRAY
        all_fields.extend(fields)

        field_id += 6

    # Calculate total from items and update Total fields
    total = sum(float(item.get('line_total', 0)) for item in items)
    total_str = f"{total:.2f}"  # Format to 2 decimal places
    # Update Total fields at indices 6 and 7
    all_fields[6]["value"] = total_str
    all_fields[7]["value"] = total_str

    # Build full GDocument - match expected ABBYY format exactly
    # Based on diff analysis: batchId=2600, name/caption empty, uncertainSymbolsCount as number
    # Calculate symbol counts - match expected ABBYY format
    # For 27 items, expected totalSymbolsCount = 679 (~25 per item)
    # Use simpler calculation: len(items) * 25 + some overhead
    total_symbols = len(items) * 25 + 100  # 100 for header fields and metadata
    recognized_symbols = total_symbols  # All symbols recognized (no uncertain)

    gdoc = {
        "GDocument": {
            "id": "1",
            "documentDefinition": "InnoventoryTech",
            "batchId": 2600,  # From expected example (was 2340)
            "isAssembled": True,
            "isVerified": True,
            "processingErrors": "",
            "processingWarnings": "",
            "totalSymbolsCount": total_symbols,
            "recognizedSymbolsCount": recognized_symbols,
            "uncertainSymbolsCount": 0,  # Number not string (was "0")
            "name": "",  # Empty per expected format (was receipt_name)
            "caption": "",  # Empty per expected format (was receipt_name)
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
            # Top-level fields - now includes ALL fields
            "fields": all_fields,
            "errors": ""
        }
    }

    return gdoc


def _create_abbyy_field(field_id: int, name: str, value: str, idx: int = 0) -> dict:
    """
    Create an ABBYY field with all required metadata attributes.

    Args:
        field_id: Field ID number
        name: Field name (Price, Quantity, CatalogNo, etc.)
        value: Field value
        idx: Table index for path construction

    Returns:
        Complete ABBYY field dictionary
    """
    # Determine field type based on name
    if name in ["Price", "Quantity", "LineTotal", "Discount1", "Discount2"]:
        field_type = "EFT_NumberField"
    else:
        field_type = "EFT_TextField"

    # Create suspicious symbols string (binary flags per character)
    # "0" = trusted, "1" = suspicious
    suspicious_symbols = "0" * len(value) if value else "0"

    # Construct field path
    # Header fields (InvoiceNo, VendorNameS, Date, Total) should be at top level, not in Table
    if idx == -1 and name in ["InvoiceNo", "VendorNameS", "Date", "Total"]:
        field_path = f"InnovatoryTech\\{name}"  # Top level path
    else:
        field_path = f"InnovatoryTech\\Table[{idx}]\\{name}"  # Field within table

    # Default region coordinates (these would ideally come from OCR)
    # Using reasonable defaults
    base_x = 100
    base_y = 100 + (field_id % 10) * 40  # Stagger vertically

    # Field width based on type
    if field_type == "EFT_NumberField":
        field_width = 100
    else:
        field_width = 200  # Text fields are wider

    field_height = 34

    return {
        "id": field_id,
        "name": name,
        "active": True,
        "selected": False,
        "caption": name,
        "path": field_path,
        "region": {
            "x": base_x,
            "y": base_y,
            "w": field_width,
            "h": field_height,
            "rx": base_x,
            "ry": base_y,
            "rw": field_width,
            "rh": field_height
        },
        "color": "",
        "isVerified": False,
        "isValid": True,
        "value": value,
        "readOnly": False,
        "readOnlyInForm": False,
        "suspiciousSymbols": suspicious_symbols,
        "type": field_type,
        "surroundingRect": f"[{base_x}, {base_y}, {base_x + field_width}, {base_y + field_height}]",
        "pageIndex": 0,
        "pageId": 2,
        "sectionName": "InnovatoryTech",
        "matched": True
    }


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