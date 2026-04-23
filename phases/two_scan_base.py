"""
OBSOLETE - NOT USED BY MAIN PIPELINE
=====================================
Base functionality for two-scan receipt processing.

Step 1 of the algorithm: Call Mindee twice on every receipt.

Scan A — JSON scan: Call Mindee normally for structured JSON response
Scan B — Raw text scan: Call Mindee with raw_text=True for full plain text

Both scans are mandatory on every receipt. Never skip one.
"""

import os
from typing import Tuple, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from pipelines._mindee.client import MindeeClient
    MINDEE_AVAILABLE = True
except ImportError:
    MINDEE_AVAILABLE = False


class TwoScanProcessor:
    """Base processor that always performs both scans."""

    def __init__(self, api_key: Optional[str] = None, model_id: Optional[str] = None):
        """
        Initialize with API credentials.

        Args:
            api_key: Mindee API key (uses MINDEE_API_KEY from .env if not provided)
            model_id: Mindee model ID (uses default if not provided)
        """
        if not MINDEE_AVAILABLE:
            raise ImportError("Mindee client not available. Install with: pip install mindee")

        self.api_key = api_key or os.environ.get("MINDEE_API_KEY", "")
        self.model_id = model_id or os.environ.get(
            "MINDEE_MODEL_ID",
            "2794301c-25bd-402a-bebe-5295a67416e6"  # Default receipt model
        )

        if not self.api_key:
            raise ValueError("Mindee API key not found. Set MINDEE_API_KEY in .env file")

        self.client = MindeeClient(self.api_key, self.model_id)

    def perform_both_scans(self, image_path: str) -> Tuple[Any, Any]:
        """
        Perform both mandatory scans on a receipt.

        Args:
            image_path: Path to receipt file (PDF, PNG, JPG)

        Returns:
            Tuple of (json_response, raw_text)
            json_response: Response object from receipt model (or None)
            raw_text: String of OCR text from OCR model (or empty string)

        Raises:
            FileNotFoundError: If image_path doesn't exist
            ValueError: If API key is invalid
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Receipt file not found: {image_path}")

        print(f"\nProcessing receipt: {os.path.basename(image_path)}")
        print("-" * 60)

        # === SCAN A: JSON Scan ===
        print("Scan A: JSON scan (structured fields)...")
        json_response = None
        try:
            json_response = self.client.scan_receipt_model(image_path)
            print("  ✓ JSON scan completed")
        except Exception as e:
            print(f"  ✗ JSON scan failed: {e}")
            # Don't raise here - continue to attempt raw text scan

        # === SCAN B: Raw Text Scan ===
        print("Scan B: Raw text scan (full text)...")
        raw_text = ""
        try:
            raw_text = self.client.raw_text(image_path)
            if raw_text:
                print(f"  ✓ Raw text scan completed ({len(raw_text)} chars)")
            else:
                print("  ✗ Raw text scan returned empty")
        except Exception as e:
            print(f"  ✗ Raw text scan failed: {e}")
            raw_text = ""  # Ensure raw_text is set even on failure

        # Validation
        if json_response is None and raw_text_response is None:
            print("\n⚠️  WARNING: Both scans failed!")
        elif json_response is None:
            print("\n⚠️  WARNING: JSON scan failed (but raw text succeeded)")
        elif raw_text_response is None:
            print("\n⚠️  WARNING: Raw text scan failed (but JSON succeeded)")
        else:
            print("\n✓ Both scans completed successfully")

        return json_response, raw_text

    def extract_basic_info(self, json_response) -> Dict[str, Any]:
        """
        Extract basic receipt info from JSON response.

        Args:
            json_response: Response from scan_receipt_model()

        Returns:
            Dictionary with vendor, date, invoice_no, total
        """
        if json_response is None:
            return {
                "vendor": "",
                "date": "",
                "invoice_no": "",
                "total": 0.0
            }

        try:
            # Try to extract fields from the response structure
            vendor = ""
            date = ""
            invoice_no = ""
            total = 0.0

            if hasattr(json_response, 'inference') and hasattr(json_response.inference, 'result'):
                result = json_response.inference.result

                # Check for fields
                if hasattr(result, 'fields'):
                    fields = result.fields

                    # Extract vendor
                    for field_name in ['supplier_name', 'merchant_name', 'vendor']:
                        if hasattr(fields, field_name):
                            field = getattr(fields, field_name)
                            if field and hasattr(field, 'value') and field.value:
                                vendor = field.value
                                break

                    # Extract date
                    if hasattr(fields, 'date'):
                        date_field = fields.date
                        if date_field and hasattr(date_field, 'value') and date_field.value:
                            date = date_field.value

                    # Extract invoice number
                    if hasattr(fields, 'invoice_number'):
                        invoice_field = fields.invoice_number
                        if invoice_field and hasattr(invoice_field, 'value') and invoice_field.value:
                            invoice_no = invoice_field.value

                    # Extract total
                    for field_name in ['total_amount', 'total', 'total_price']:
                        if hasattr(fields, field_name):
                            total_field = getattr(fields, field_name)
                            if total_field and hasattr(total_field, 'value') and total_field.value:
                                try:
                                    total = float(total_field.value)
                                except (ValueError, TypeError):
                                    pass
                                break

            return {
                "vendor": vendor,
                "date": date,
                "invoice_no": invoice_no,
                "total": total
            }

        except Exception as e:
            print(f"Error extracting basic info: {e}")
            return {
                "vendor": "",
                "date": "",
                "invoice_no": "",
                "total": 0.0
            }

    def extract_json_items(self, json_response) -> list:
        """
        Extract line items from JSON response.

        Args:
            json_response: Response from scan_receipt_model()

        Returns:
            List of item dictionaries with description, quantity, unit_price, line_total
        """
        if json_response is None:
            return []

        items = []
        try:
            if hasattr(json_response, 'inference') and hasattr(json_response.inference, 'result'):
                result = json_response.inference.result

                if hasattr(result, 'fields') and hasattr(result.fields, 'line_items'):
                    line_items_field = result.fields.line_items

                    if hasattr(line_items_field, 'items'):
                        line_items = line_items_field.items
                        if isinstance(line_items, list):
                            for item in line_items:
                                if hasattr(item, 'fields'):
                                    fields = item.fields

                                    description = ""
                                    quantity = 1.0
                                    unit_price = 0.0
                                    line_total = 0.0

                                    # Extract description
                                    desc_field = fields.get('description') if isinstance(fields, dict) else getattr(fields, 'description', None)
                                    if desc_field and hasattr(desc_field, 'value') and desc_field.value:
                                        description = desc_field.value

                                    # Extract quantity
                                    qty_field = fields.get('quantity') if isinstance(fields, dict) else getattr(fields, 'quantity', None)
                                    if qty_field and hasattr(qty_field, 'value') and qty_field.value:
                                        try:
                                            quantity = float(qty_field.value)
                                        except (ValueError, TypeError):
                                            quantity = 1.0

                                    # Extract unit price
                                    price_field = fields.get('unit_price') if isinstance(fields, dict) else getattr(fields, 'unit_price', None)
                                    if price_field and hasattr(price_field, 'value') and price_field.value:
                                        try:
                                            unit_price = float(price_field.value)
                                        except (ValueError, TypeError):
                                            unit_price = 0.0

                                    # Extract line total
                                    total_field = fields.get('total_price') if isinstance(fields, dict) else getattr(fields, 'total_price', None)
                                    if total_field and hasattr(total_field, 'value') and total_field.value:
                                        try:
                                            line_total = float(total_field.value)
                                        except (ValueError, TypeError):
                                            line_total = 0.0

                                    # If line_total is 0 but we have quantity and price, calculate it
                                    if line_total == 0 and quantity > 0 and unit_price > 0:
                                        line_total = quantity * unit_price

                                    items.append({
                                        "description": description,
                                        "quantity": quantity,
                                        "unit_price": unit_price,
                                        "line_total": line_total,
                                        "source": "json_scan"
                                    })

        except Exception as e:
            print(f"Error extracting JSON items: {e}")

        print(f"Extracted {len(items)} items from JSON scan")
        return items

    

def test_two_scans():
    """Test the two-scan functionality."""
    try:
        processor = TwoScanProcessor()

        # Check for sample file
        sample_dir = "sample_images"
        if os.path.exists(sample_dir):
            for ext in ['.pdf', '.png', '.jpg', '.jpeg']:
                files = [f for f in os.listdir(sample_dir) if f.lower().endswith(ext)]
                if files:
                    sample_file = os.path.join(sample_dir, files[0])
                    print(f"Testing with: {sample_file}")

                    json_resp, raw_resp = processor.perform_both_scans(sample_file)

                    if json_resp:
                        basic_info = processor.extract_basic_info(json_resp)
                        print(f"\nBasic info: {basic_info}")

                        items = processor.extract_json_items(json_resp)
                        if items:
                            print(f"\nFirst JSON item: {items[0]}")

                    if raw_resp:
                        preview = raw_resp[:300] + "..." if len(raw_resp) > 300 else raw_resp
                        print(f"\nRaw text preview ({len(raw_resp)} chars):")
                        print(f"{preview}")

                    return True

        print(f"\nNo sample files found in {sample_dir}/")
        print("Add a receipt PDF or image to test.")
        return False

    except Exception as e:
        print(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing Two-Scan Base Functionality")
    print("=" * 60)
    success = test_two_scans()
    if success:
        print("\n✓ Two-scan test completed")
    else:
        print("\n✗ Two-scan test failed")