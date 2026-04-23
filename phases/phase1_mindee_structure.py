"""
OBSOLETE - NOT USED BY MAIN PIPELINE
=====================================
Phase 1: Inspect Mindee response structure

Before writing any parsing code, run one test receipt through Mindee and
print the complete structure of the response object.

Show every available field, how words are represented, what the polygon
coordinate format looks like, and what coordinate ranges are used.
Do this for both Scan A and Scan B calls.

Print the raw output. Do not interpret or summarize.
"""

import json
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from pipelines._mindee.client import MindeeClient
    MINDEE_AVAILABLE = True
except ImportError:
    MINDEE_AVAILABLE = False


def inspect_mindee_response(image_path: str) -> Dict[str, Any]:
    """
    Run both scans on a receipt and return detailed response structure.

    Args:
        image_path: Path to receipt image/PDF

    Returns:
        Dictionary with inspection results for both scans
    """
    if not MINDEE_AVAILABLE:
        return {"error": "Mindee client not available"}

    api_key = os.environ.get("MINDEE_API_KEY", "")
    model_id = os.environ.get("MINDEE_MODEL_ID", "2794301c-25bd-402a-bebe-5295a67416e6")

    if not api_key:
        return {"error": "MINDEE_API_KEY not set in .env"}

    client = MindeeClient(api_key, model_id)

    result = {
        "scan_a_json": {},
        "scan_b_raw_text": {},
        "file": image_path,
        "api_key_exists": bool(api_key)
    }

    # === SCAN A: JSON Scan ===
    print("\n" + "="*80)
    print("PHASE 1: SCAN A - JSON RESPONSE STRUCTURE")
    print("="*80)

    try:
        json_response = client.scan_receipt_model(image_path)
        result["scan_a_json"]["success"] = True

        # Convert to dict for inspection
        json_dict = response_to_dict(json_response)
        result["scan_a_json"]["response"] = json_dict

        # Print key structure details
        print("\n=== JSON Scan Response Structure ===")
        print(f"Response type: {type(json_response)}")

        if hasattr(json_response, 'inference'):
            print(f"Has inference attribute: Yes")
            if hasattr(json_response.inference, 'result'):
                print(f"Has inference.result attribute: Yes")
                if hasattr(json_response.inference.result, 'fields'):
                    print(f"Has inference.result.fields attribute: Yes")
                    fields = json_response.inference.result.fields
                    print(f"Fields type: {type(fields)}")

                    # Check if fields is a list
                    if isinstance(fields, list):
                        print(f"Number of fields: {len(fields)}")
                        print("\nField names and types:")
                        for i, field in enumerate(fields[:10]):  # First 10 fields
                            if hasattr(field, 'name'):
                                print(f"  [{i}] {field.name}: {type(field)}")
                        if len(fields) > 10:
                            print(f"  ... and {len(fields) - 10} more fields")

                    # Look for line_items specifically
                    print("\nLooking for line_items field...")
                    if isinstance(fields, dict):
                        line_items = fields.get('line_items')
                        if line_items:
                            print(f"Found line_items field: {type(line_items)}")
                            if hasattr(line_items, 'items'):
                                items = line_items.items
                                print(f"line_items.items type: {type(items)}")
                                if isinstance(items, list):
                                    print(f"Number of line items: {len(items)}")
                                    if items:
                                        print("\nFirst line item structure:")
                                        print(f"  Type: {type(items[0])}")
                                        if hasattr(items[0], 'fields'):
                                            item_fields = items[0].fields
                                            print(f"  Has fields attribute: Yes")
                                            print(f"  Item fields: {list(item_fields.keys()) if isinstance(item_fields, dict) else 'N/A'}")

    except Exception as e:
        result["scan_a_json"]["success"] = False
        result["scan_a_json"]["error"] = str(e)
        print(f"\nJSON Scan Error: {e}")

    # === SCAN B: Raw Text Scan ===
    print("\n" + "="*80)
    print("PHASE 1: SCAN B - RAW TEXT RESPONSE STRUCTURE")
    print("="*80)

    try:
        raw_response = client.get_raw_text(image_path)
        if raw_response:
            result["scan_b_raw_text"]["success"] = True

            # Convert to dict for inspection
            raw_dict = response_to_dict(raw_response)
            result["scan_b_raw_text"]["response"] = raw_dict

            print(f"\nRaw text response type: {type(raw_response)}")

            # Check for OCR data with raw_text=True
            if hasattr(raw_response, 'ocr'):
                print(f"Has ocr attribute: Yes")
                ocr = raw_response.ocr
                print(f"ocr type: {type(ocr)}")

                # Check for pages
                if hasattr(ocr, 'pages'):
                    pages = ocr.pages
                    print(f"Number of pages: {len(pages) if isinstance(pages, list) else 'N/A'}")

                    if pages and isinstance(pages, list) and len(pages) > 0:
                        first_page = pages[0]
                        print(f"\nFirst page type: {type(first_page)}")

                        # Check for words/mrz/data
                        for attr in ['words', 'mrz', 'data']:
                            if hasattr(first_page, attr):
                                attr_value = getattr(first_page, attr)
                                print(f"  Has {attr}: Yes (type: {type(attr_value)})")
                                if isinstance(attr_value, list):
                                    print(f"    Number of {attr}: {len(attr_value)}")
                                    if attr_value and len(attr_value) > 0:
                                        print(f"    First {attr} element: {type(attr_value[0])}")

                        # Check for full_text with raw_text=True
                        if hasattr(first_page, 'full_text'):
                            full_text = first_page.full_text
                            print(f"  Has full_text: Yes")
                            print(f"  full_text type: {type(full_text)}")
                            if full_text:
                                # Show first 200 chars
                                preview = str(full_text)[:200]
                                print(f"  Full text preview (first 200 chars):")
                                print(f"    {preview}")
                                if len(str(full_text)) > 200:
                                    print(f"    ... and {len(str(full_text)) - 200} more characters")
            else:
                print("No ocr attribute found in raw response")

        else:
            result["scan_b_raw_text"]["success"] = False
            result["scan_b_raw_text"]["error"] = "get_raw_text returned None"
            print("get_raw_text returned None")

    except Exception as e:
        result["scan_b_raw_text"]["success"] = False
        result["scan_b_raw_text"]["error"] = str(e)
        print(f"\nRaw Text Scan Error: {e}")

    return result


def response_to_dict(response) -> Dict[str, Any]:
    """
    Convert Mindee response object to dictionary for inspection.
    Handles recursive conversion of nested objects.
    """
    if response is None:
        return None

    if isinstance(response, (str, int, float, bool)):
        return response

    if isinstance(response, list):
        return [response_to_dict(item) for item in response[:5]]  # Limit to first 5

    result = {}

    # Get all attributes that aren't private or methods
    for attr_name in dir(response):
        if not attr_name.startswith('_'):
            try:
                attr_value = getattr(response, attr_name)
                # Skip methods
                if callable(attr_value):
                    continue

                # Convert based on type
                if isinstance(attr_value, (str, int, float, bool, type(None))):
                    result[attr_name] = attr_value
                elif isinstance(attr_value, list):
                    # For lists, show type and length
                    result[attr_name] = {
                        "type": "list",
                        "length": len(attr_value),
                        "item_type": str(type(attr_value[0])) if attr_value else "empty"
                    }
                elif hasattr(attr_value, '__dict__'):
                    # For objects, show type
                    result[attr_name] = {
                        "type": str(type(attr_value)),
                        "has_dict": True
                    }
                else:
                    result[attr_name] = str(type(attr_value))

            except Exception:
                # Skip attributes that can't be accessed
                pass

    return result


def run_phase1_demo():
    """Run Phase 1 on a sample receipt if available."""
    sample_dir = "sample_images"
    if os.path.exists(sample_dir):
        # Look for any PDF or image file
        for ext in ['.pdf', '.png', '.jpg', '.jpeg']:
            files = [f for f in os.listdir(sample_dir) if f.lower().endswith(ext)]
            if files:
                sample_file = os.path.join(sample_dir, files[0])
                print(f"\nFound sample file: {sample_file}")
                print("Running Phase 1 inspection...")
                return inspect_mindee_response(sample_file)

    print(f"\nNo sample files found in {sample_dir}")
    print("To test, create a .env file with MINDEE_API_KEY and add a receipt to sample_images/")
    return {"error": "No sample file available"}


if __name__ == "__main__":
    result = run_phase1_demo()
    print("\n" + "="*80)
    print("PHASE 1 COMPLETE")
    print("="*80)