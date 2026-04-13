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


# API Configuration
API_KEY = "md_1o31rOriCtDKdFNUEh4aWLIj57Ns7D8Kz9hp33rj1m0"
MODEL_ID = "2794301c-25bd-402a-bebe-5295a67416e6"

# Sample images directory for training data
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_images")


def process_receipt(
    image_path: str,
    api_key: str = None,
    model_id: str = None,
    save_to_samples: bool = True,
) -> dict:
    """
    Process receipt using Mindee API.

    Args:
        image_path: Path to receipt file (PDF, PNG, JPG)
        api_key: Mindee API key (uses default if not provided)
        model_id: Mindee model ID (uses default if not provided)

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

    # Build GDocument format
    gdoc = {
        "GDocument": {
            "fields": {
                "items": [
                    {
                        "description": item.description,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "line_total": item.total,
                    }
                    for item in extracted_items
                ]
            }
        }
    }

    # Save JSON to samples folder if enabled and file is new
    if save_to_samples and os.path.exists(SAMPLES_DIR):
        _save_to_samples(image_path, gdoc, extracted_items)

    return gdoc


def _save_to_samples(image_path: str, gdoc: dict, items: List[MindeeItem]):
    """Save output to sample_images folder if it's a new receipt."""
    import json
    import shutil
    import re

    # Get base name without extension
    basename = os.path.splitext(os.path.basename(image_path))[0]

    # Strip page suffixes like _page-0001 to get the original name
    base_name_clean = re.sub(r'_page-\d+$', '', basename)

    # Check existing files in samples (use clean name for comparison)
    existing_files = os.listdir(SAMPLES_DIR)
    existing_bases = {re.sub(r'_page-\d+$', '', os.path.splitext(f)[0]) for f in existing_files if f.endswith('.JSON')}

    # If this receipt is new, save it
    if base_name_clean not in existing_bases and items:
        # Save JSON with clean name
        json_filename = base_name_clean + ".JSON"
        json_path = os.path.join(SAMPLES_DIR, json_filename)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(gdoc, f, indent=2, ensure_ascii=False)

        # Copy original file with clean name if it exists
        ext = os.path.splitext(os.path.basename(image_path))[1]
        clean_image_name = base_name_clean + ext
        dst_path = os.path.join(SAMPLES_DIR, clean_image_name)

        if not os.path.exists(dst_path):
            src_path = os.path.join(SAMPLES_DIR, os.path.basename(image_path))
            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_path)
            elif os.path.exists(image_path):
                # Copy from source with clean name
                shutil.copy2(image_path, dst_path)


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