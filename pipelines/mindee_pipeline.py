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
    Process receipt using Mindee API.

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
    params = InferenceParameters(model_id=mid)
    input_source = PathInput(image_path)
    response = client.enqueue_and_get_result(InferenceResponse, input_source, params)

    result = response.inference.result
    fields = result.fields
    line_items_field = fields.get('line_items')
    items = line_items_field.items

    # Convert to our format
    extracted_items = []
    for item in items:
        item_fields = item.fields
        desc = item_fields.get('description').value if item_fields.get('description') and item_fields.get('description').value else ''
        qty = item_fields.get('quantity').value if item_fields.get('quantity') and item_fields.get('quantity').value else 1.0
        unit_price = item_fields.get('unit_price').value if item_fields.get('unit_price') and item_fields.get('unit_price').value else 0.0
        total = item_fields.get('total_price').value if item_fields.get('total_price') and item_fields.get('total_price').value else 0.0

        if desc and total and total > 0:
            extracted_items.append(MindeeItem(
                description=desc,
                quantity=qty,
                unit_price=unit_price,
                total=total,
            ))

    # Convert raw items to dicts for post-processing
    raw_items = [
        {
            "description": item.description,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "line_total": item.total,
        }
        for item in extracted_items
    ]

    # Post-process to fix quantity=weight and add discounts
    from utils.post_processor import process_items
    fixed_items = process_items(raw_items)

    # Convert to ABBYY format
    from utils.format_converter import mindee_to_abbey

    receipt_name = os.path.splitext(os.path.basename(image_path))[0]
    receipt_name = receipt_name.replace('_page-', '_')

    gdoc = mindee_to_abbey(fixed_items, receipt_name)

    # Save to output folder if enabled
    if save_to_output:
        _save_to_output(gdoc, receipt_name)

    return gdoc


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