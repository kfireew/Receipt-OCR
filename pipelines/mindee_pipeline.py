"""
Mindee Pipeline - Receipt extraction using Mindee API.

Usage:
    from pipelines.mindee_pipeline import process_receipt

    result = process_receipt("receipt.pdf")
    # Returns: {"GDocument": {"fields": {"items": [...]}}}
"""
from dataclasses import dataclass
from typing import List, Optional
import os


@dataclass
class MindeeItem:
    """Item extracted from receipt."""
    description: str
    quantity: float
    unit_price: float
    total: float


# API Configuration - Set via environment variables
import os

API_KEY = os.environ.get("MINDEE_API_KEY", "")
MODEL_ID = os.environ.get("MINDEE_MODEL_ID", "2794301c-25bd-402a-bebe-5295a67416e6")

# Output directory for processed receipts
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


def process_receipt(
    image_path: str,
    api_key: str = None,
    model_id: str = None,
    save_to_output: bool = True,
) -> dict:
    """
    Process receipt using Mindee 2-scan method:
    1. Receipt Model scan - gets structured fields (items, qty, prices)
    2. Raw OCR scan - gets word positions for better parsing

    Args:
        image_path: Path to receipt file (PDF, PNG, JPG)
        api_key: Mindee API key (uses default if not provided)
        model_id: Mindee model ID (uses default if not provided)
        save_to_output: Save result to output/ folder (default True)

    Returns:
        GDocument dict with items
    """
    from mindee import ClientV2, InferenceParameters, InferenceResponse, PathInput

    key = api_key or API_KEY
    mid = model_id or MODEL_ID

    client = ClientV2(api_key=key)

    # ===== SCAN 1: Receipt Model =====
    params = InferenceParameters(model_id=mid)
    input_source = PathInput(image_path)
    response = client.enqueue_and_get_result(InferenceResponse, input_source, params)

    result = response.inference.result
    fields = result.fields

    # Extract header from Mindee fields
    vendor_field = fields.get('supplier_name') or fields.get('merchant_name')
    vendor = vendor_field.value if vendor_field and vendor_field.value else ""

    date_field = fields.get('date')
    date = date_field.value if date_field and date_field.value else ""

    invoice_field = fields.get('invoice_number')
    invoice_no = invoice_field.value if invoice_field and invoice_field.value else ""

    total_field = fields.get('total_amount')
    total = total_field.value if total_field and total_field.value else 0.0

    # Get line items
    line_items_field = fields.get('line_items')
    items = line_items_field.items if line_items_field else []

    # ===== SCAN 2: Raw OCR for better item parsing =====
    # Use X-position based column detection for quantities
    raw_items, debug_info = _scan_raw_ocr_for_items(image_path, key, mid, items, fields)

    # Post-process to fix quantity=weight and add discounts
    from utils.post_processor import process_items
    fixed_items = process_items(raw_items)

    # Convert to ABBYY format
    from utils.format_converter import mindee_to_abbey

    # Generate filename from detected vendor and date
    if vendor and date:
        parts = date.split('.')
        if len(parts) == 3:
            date_dash = f"{parts[0]}-{parts[1]}-{parts[2][-2:]}"
        else:
            date_dash = date.replace('.', '-')
        receipt_name = f"{vendor}_{date}_{vendor} {date_dash}"
    else:
        receipt_name = normalize_filename(image_path)

    gdoc = mindee_to_abbey(fixed_items, receipt_name, vendor=vendor, date=date)

    # Save to output folder if enabled
    if save_to_output:
        _save_to_output(gdoc, receipt_name)

    return gdoc


def _scan_raw_ocr_for_items(image_path: str, api_key: str, model_id: str, structured_items: list, fields: dict) -> tuple:
    """
    Second scan: Get raw OCR with word positions for better column detection.

    Uses X-position bins to detect: LineTotal | Price | Quantity | CatalogNo
    Then calculates: unit_price = total / quantity (handles discounts)

    Returns:
        Tuple of (items list as dicts, debug_info)
    """
    from mindee import ClientV2, InferenceParameters, InferenceResponse, PathInput
    from collections import defaultdict
    import re

    client = ClientV2(api_key=api_key)

    # Scan 2: Raw OCR with polygon
    try:
        raw_params = InferenceParameters(model_id=model_id, polygon=True)
        raw_response = client.enqueue_and_get_result(InferenceResponse, PathInput(image_path), raw_params)
    except Exception:
        # Fallback: use structured items only
        return _items_to_dicts(structured_items), {'source': 'receipt_model'}

    # Parse raw OCR response
    if hasattr(raw_response, 'ocr') and raw_response.ocr:
        raw_items = _parse_raw_ocr_positions(raw_response.ocr)
        if raw_items:
            return raw_items, {'source': 'raw_ocr'}

    # Fallback to structured items
    return _items_to_dicts(structured_items), {'source': 'receipt_model'}


def _parse_raw_ocr_positions(ocr) -> list:
    """Parse raw OCR to extract items using X-position column detection."""
    from collections import defaultdict
    import re

    words = []
    if hasattr(ocr, 'pages'):
        for page in ocr.pages:
            if hasattr(page, 'words'):
                for word in page.words:
                    if hasattr(word, 'polygon') and word.polygon:
                        words.append({
                            'content': word.content if hasattr(word, 'content') else str(word),
                            'polygon': [[p.x, p.y] for p in word.polygon] if hasattr(word.polygon[0], 'x') else word.polygon
                        })

    if not words:
        return []

    # Group by Y position (rows)
    rows = defaultdict(list)
    for w in words:
        polygon = w.get('polygon', [])
        if polygon:
            y = polygon[0][1]
            x = polygon[0][0]
            rows[y].append({'x': x, 'content': w['content']})

    # Skip header keywords
    skip_keywords = ['ךיראת', 'הלבק', 'םולשת', 'החנה', 'מ"עמ', 'כהס']

    items = []
    for y in sorted(rows.keys()):
        row_words = rows[y]
        row_text = ' '.join([w['content'] for w in row_words])

        if any(skip in row_text for skip in skip_keywords):
            continue
        if len(row_text) < 3:
            continue

        # Extract numbers with X positions
        numbers = []
        for w in row_words:
            nums = re.findall(r'[\d,]+\.?\d*', w['content'])
            for n in nums:
                try:
                    val = float(n.replace(',', ''))
                    if 0 < val < 1000000:
                        numbers.append((w['x'], val))
                except:
                    pass

        if len(numbers) >= 2:
            # Last number = total, second-to-last = unit_price
            numbers_sorted = sorted(numbers, key=lambda x: x[0])  # by X (left to right)
            total = numbers_sorted[-1][1]  # rightmost = total
            unit_price = numbers_sorted[-2][1]  # second-rightmost = unit_price

            # Calculate qty = total / unit_price
            qty = round(total / unit_price) if unit_price > 0 else 1

            # Extract description (right side text)
            desc_parts = []
            for w in row_words:
                if w['x'] >= 0.4 and not re.match(r'^[\d,\.]+$', w['content']):
                    desc_parts.append(w['content'])
            desc = ' '.join(desc_parts[:5])  # limit to 5 words

            if desc and len(desc) > 1:
                items.append({
                    'description': desc[:50],
                    'quantity': qty,
                    'unit_price': round(unit_price, 2),
                    'line_total': round(total, 2),
                })

    return items


def _items_to_dicts(items: list) -> list:
    """Convert Mindee items to dict format."""
    result = []
    for item in items:
        if hasattr(item, 'fields'):
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


def normalize_filename(image_path: str) -> str:
    """
    Normalize filename to format: Vendor_Date_Vendor Date

    Examples:
        - StraussCool_18.08.2024_StraussCool 18-08-24.pdf → StraussCool_18.08.2024_StraussCool 18-08-24
        - Avikam_10.03.2025_Avikam 11-03-25.pdf → Avikam_10.03.2025_Avikam 11-03-25
        - WhatsApp Scan 2026-04-09 at 11.32.13.pdf → WhatsApp_Scan_2026-04-09_at_11.32.13
    """
    import re

    # Get filename without extension
    filename = os.path.splitext(os.path.basename(image_path))[0]

    # Handle page suffixes like _page-0001
    filename = re.sub(r'_page-\d+$', '', filename)

    # Check if it matches known pattern: Vendor_Date_Vendor Date
    # Pattern: word_word.word.word_word word-word (with space)
    pattern = r'^(\w+)_(\d{2}\.\d{2}\.\d{4})_(\w+)\s+(\d{2}-\d{2}-\d{2})$'
    match = re.match(pattern, filename)

    if match:
        # Already in correct format - just return with underscore
        return filename

    # Try reverse pattern: Vendor Date_Vendor_Date
    # Example: "StraussCool 18.08.2024_StraussCool 18-08-24"
    pattern2 = r'^(\w+)\s+(\d{2}\.\d{2}\.\d{4})_(\w+)\s+(\d{2}-\d{2}-\d{2})$'
    match2 = re.match(pattern2, filename)

    if match2:
        # Convert: "Vendor Date_Vendor Date" → "Vendor_Date_Vendor Date"
        vendor1 = match2.group(1)
        date1 = match2.group(2)
        vendor2 = match2.group(3)
        date_dash = match2.group(4)
        # Format: Vendor_Date_Vendor Date (keep space between vendor and date)
        return f"{vendor1}_{date1}_{vendor2} {date_dash}"

    # Try another pattern: Vendor_Date_Vendor_Date (with underscores)
    # Example: "StraussCool_18.08.2024_StraussCool_18-08-24"
    pattern3 = r'^(\w+)_(\d{2}\.\d{2}\.\d{4})_(\w+)_(\d{2}-\d{2}-\d{2})$'
    match3 = re.match(pattern3, filename)

    if match3:
        # Convert underscores to space in second part
        # "Vendor_Date_Vendor_Date" → "Vendor_Date_Vendor Date"
        vendor1 = match3.group(1)
        date1 = match3.group(2)
        vendor2 = match3.group(3)
        date_dash = match3.group(4)
        return f"{vendor1}_{date1}_{vendor2} {date_dash}"

    # For other filenames, just normalize spaces to underscores
    return filename.replace(' ', '_')


def extract_header_from_tesseract(image_path: str) -> tuple:
    """
    Extract vendor and date using tesseract OCR (for header parsing).

    Uses tesseract pipeline for header (vendor, date) - better for Hebrew text.
    Falls back to filename parsing if tesseract unavailable.

    Returns: (vendor, date) tuple
    """
    try:
        # Preprocess
        from stages.preprocess.image_loader import PreprocessConfig
        from stages.preprocess.image_processor import preprocess_image
        pp_cfg = PreprocessConfig(target_height=2400, target_width=1800)
        pres = preprocess_image(image_path, cfg=pp_cfg)

        # OCR with tesseract
        from stages.recognition.tesseract_client import recognize_boxes
        all_boxes = []
        for i, pre in enumerate(pres):
            boxes = recognize_boxes(pre.preprocessed, page_idx=i)
            all_boxes.extend(boxes)

        # Parse header using tesseract pipeline
        from stages.grouping.line_assembler import _boxes_to_lines
        raw_lines = _boxes_to_lines(all_boxes)

        # Extract vendor
        from stages.parsing.vendor import extract_vendor
        vendor_result = extract_vendor(raw_lines)
        vendor = vendor_result.value if vendor_result and vendor_result.value else ""

        # Extract date
        from stages.parsing.dates import _parse_date_from_lines
        date_result = _parse_date_from_lines(raw_lines)
        date = date_result.value if date_result and date_result.value else ""

        return vendor, date
    except Exception as e:
        # Fall back to filename parsing
        return extract_vendor_date_from_filename(image_path)


def extract_vendor_date_from_filename(image_path: str) -> tuple:
    """
    Extract vendor name and date from filename pattern.

    Pattern: Vendor_Date_Vendor Date
    Example: StraussCool_18.08.2024_StraussCool 18-08-24

    Returns: (vendor, date) tuple
    """
    import re

    filename = os.path.splitext(os.path.basename(image_path))[0]

    # Try pattern: Vendor_Date_Vendor Date
    pattern = r'^(\w+)_(\d{2}\.\d{2}\.\d{4})_(\w+)\s+(\d{2}-\d{2}-\d{2})$'
    match = re.match(pattern, filename)

    if match:
        vendor = match.group(1)  # First vendor
        date = match.group(2)    # Date in DD.MM.YYYY format
        return vendor, date

    # Try without space: Vendor_Date_Vendor_Date
    pattern2 = r'^(\w+)_(\d{2}\.\d{2}\.\d{4})_(\w+)_(\d{2}-\d{2}-\d{2})$'
    match2 = re.match(pattern2, filename)

    if match2:
        vendor = match2.group(1)
        date = match2.group(2)
        return vendor, date

    # Try reverse: Vendor Date_Vendor_Date
    pattern3 = r'^(\w+)\s+(\d{2}\.\d{2}\.\d{4})_(\w+)_(\d{2}-\d{2}-\d{2})$'
    match3 = re.match(pattern3, filename)

    if match3:
        vendor = match3.group(1)
        date = match3.group(2)
        return vendor, date

    # Try WhatsApp pattern: WhatsApp_Scan_YYYY-MM-DD
    pattern4 = r'^(WhatsApp[_\s]\w+)_(\d{4}-\d{2}-\d{2})'
    match4 = re.match(pattern4, filename)

    if match4:
        vendor = match4.group(1).replace('_', ' ')
        date = match4.group(2)
        return vendor, date

    # Default: return filename as vendor, empty date
    return filename, ""


def _save_to_output(gdoc: dict, receipt_name: str):
    """Save output to output/ folder."""
    import json

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save JSON
    json_path = os.path.join(OUTPUT_DIR, f"{receipt_name}.JSON")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(gdoc, f, indent=2, ensure_ascii=False)


def extract_items(image_path: str) -> List[MindeeItem]:
    """Extract just the items list."""
    result = process_receipt(image_path)
    items = result.get("GDocument", {}).get("fields", {}).get("items", [])
    return [
        MindeeItem(
            description=i.get("description", ""),
            quantity=i.get("quantity", 1),
            unit_price=i.get("unit_price", 0),
            total=i.get("line_total", 0),
        )
        for i in items
    ]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python mindee_pipeline.py <receipt_file>")
        sys.exit(1)

    result = process_receipt(sys.argv[1])
    items = result["GDocument"]["fields"]["items"]
    print(f"Extracted {len(items)} items:")
    for item in items[:5]:
        print(f"  {item['description'][:30]}: {item['quantity']}x {item['line_total']}")