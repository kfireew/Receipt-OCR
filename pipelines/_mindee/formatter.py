"""
Mindee output formatter - converts to GDocument format.
"""
import os
import json
import re
from typing import Dict, Any, List
from utils.format_converter import mindee_to_abbey


OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


def _normalize_date(date: str) -> str:
    """Convert date to DD.MM.YY format."""
    if not date:
        return "Unknown"

    # YYYY-MM-DD -> DD.MM.YY
    if '-' in date and len(date.split('-')[0]) == 4:
        parts = date.split('-')
        return f"{parts[2]}.{parts[1]}.{parts[0][-2:]}"

    # DD.MM.YYYY -> DD.MM.YY
    if '.' in date:
        parts = date.split('.')
        if len(parts) == 3:
            return f"{parts[0]}.{parts[1]}.{parts[2][-2:]}"

    return date


class MindeeFormatter:
    """Formatter for Mindee output."""

    def format(self, items: List[Dict], vendor: str = "", date: str = "",
               receipt_name: str = None) -> Dict[str, Any]:
        """Convert items to GDocument format."""
        return mindee_to_abbey(items, receipt_name or "Receipt", vendor=vendor, date=date)

    def save_to_output(self, gdoc: Dict, receipt_name: str):
        """Save output to output/ folder."""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        json_path = os.path.join(OUTPUT_DIR, f"{receipt_name}.JSON")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(gdoc, f, indent=2, ensure_ascii=False)

    def generate_receipt_name(self, vendor: str, date: str, image_path: str) -> str:
        """Generate receipt filename from OCR vendor + date."""
        # Debug logging
        print(f"Formatter: Generating receipt name with vendor='{vendor}', date='{date}'")

        # Get English vendor using the same mapping as format_converter
        from utils.format_converter import _get_english_vendor
        safe_vendor = _get_english_vendor(vendor)

        print(f"Formatter: _get_english_vendor('{vendor}') returned '{safe_vendor}'")

        # Fallback: sanitize vendor
        if not safe_vendor:
            is_ascii = vendor.encode('ascii', 'ignore').decode('ascii') == vendor
            if is_ascii:
                safe_vendor = re.sub(r'[^a-zA-Z0-9]', '', vendor)

        if not safe_vendor:
            safe_vendor = "Unknown"

        normalized_date = _normalize_date(date)
        receipt_name = f"{safe_vendor}_{normalized_date}_{safe_vendor} {normalized_date.replace('.', '-')}"
        print(f"Formatter: Generated receipt name: '{receipt_name}'")
        return receipt_name