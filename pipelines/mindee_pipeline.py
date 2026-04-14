"""
Mindee Pipeline - Receipt extraction using Mindee API.

Usage:
    from pipelines.mindee_pipeline import process_receipt
    result = process_receipt("receipt.pdf")
"""
from dataclasses import dataclass
from typing import List, Optional
import os

# Load .env for API keys
from dotenv import load_dotenv
load_dotenv()

# API Configuration - support both env var names
if not os.environ.get("MINDEE_V2_API_KEY") and os.environ.get("MINDEE_API_KEY"):
    os.environ["MINDEE_V2_API_KEY"] = os.environ["MINDEE_API_KEY"]

API_KEY = os.environ.get("MINDEE_API_KEY", "")
MODEL_ID = os.environ.get("MINDEE_MODEL_ID", "2794301c-25bd-402a-bebe-5295a67416e6")


@dataclass
class MindeeItem:
    """Item extracted from receipt."""
    description: str
    quantity: float
    unit_price: float
    total: float


def process_receipt(
    image_path: str,
    api_key: str = None,
    model_id: str = None,
    save_to_output: bool = True,
) -> dict:
    """
    Process receipt using Mindee 2-scan method.

    Args:
        image_path: Path to receipt file (PDF, PNG, JPG)
        api_key: Mindee API key
        model_id: Mindee model ID
        save_to_output: Save result to output/ folder

    Returns:
        GDocument dict with items
    """
    from pipelines._mindee import MindeeClient, MindeeParser, MindeeFormatter
    from utils.post_processor import process_items

    key = api_key or API_KEY
    mid = model_id or MODEL_ID

    client = MindeeClient(key, mid)
    parser = MindeeParser()
    formatter = MindeeFormatter()

    # === SCAN 1: Receipt Model ===
    response = client.scan_receipt_model(image_path)
    fields = parser.parse_fields(response.inference.result.fields)

    header = parser.extract_header(fields)
    items = parser.extract_items(fields)

    # === SCAN 2: Raw OCR (fallback if needed) ===
    try:
        raw_response = client.scan_raw_ocr(image_path)
        if raw_response and hasattr(raw_response, 'ocr') and raw_response.ocr:
            raw_items = parser.parse_raw_ocr(raw_response.ocr)
            if raw_items:
                items = raw_items
    except Exception:
        pass

    # === Post-process items ===
    try:
        fixed_items = process_items(items)
    except Exception:
        fixed_items = items if isinstance(items, list) else []

    if not fixed_items:
        fixed_items = items if isinstance(items, list) else []

    # === Format output ===
    receipt_name = formatter.generate_receipt_name(
        header['vendor'], header['date'], image_path
    )
    gdoc = formatter.format(fixed_items, header['vendor'], header['date'], receipt_name)

    if save_to_output:
        formatter.save_to_output(gdoc, receipt_name)

    return gdoc


def extract_items(image_path: str) -> List[MindeeItem]:
    """Extract just the items list from a receipt."""
    result = process_receipt(image_path)
    groups = result.get("GDocument", {}).get("groups", [])
    if groups and len(groups) > 0:
        table_items = groups[0].get("groups", [])
        return [
            MindeeItem(
                description=self._get_field_value(item, "description"),
                quantity=self._get_field_value(item, "quantity"),
                unit_price=self._get_field_value(item, "price"),
                total=self._get_field_value(item, "linetotal"),
            )
            for item in table_items
        ]
    return []

def _get_field_value(item: dict, field_name: str) -> float:
    """Get numeric value from item fields."""
    fields = item.get("fields", [])
    for f in fields:
        if f.get("name") == field_name:
            try:
                return float(f.get("value", 0))
            except ValueError:
                return 0
    return 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python mindee_pipeline.py <receipt_file>")
        sys.exit(1)

    result = process_receipt(sys.argv[1])
    print("Extracted successfully!")