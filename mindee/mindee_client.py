#!/usr/bin/env python
"""
Mindee Receipt OCR Client.

Requires a Mindee API key with "receipt" model enabled.
Get a platform key from: https://platform.mindee.com

API Key format: "your-key-here" (NOT starting with md_)

Usage:
    from mindee_client import MindeeClient

    client = MindeeClient(api_key="your-key-here")
    items = client.extract_items("receipt.pdf")
"""
from dataclasses import dataclass
from typing import List, Optional
import os


@dataclass
class MindeeItem:
    """Extracted item from receipt."""
    description: str
    quantity: float
    unit_price: float
    total: float
    confidence: float


class MindeeClient:
    """Mindee API client for receipt extraction."""

    def __init__(self, api_key: str = None):
        """
        Initialize client.

        Args:
            api_key: Mindee API key. Uses MINDEE_API_KEY env var if not provided.
        """
        self.api_key = api_key or os.environ.get('MINDEE_API_KEY')
        if not self.api_key:
            raise ValueError("API key required. Set MINDEE_API_KEY env var or pass api_key.")

    def extract_items(self, image_path: str) -> List[MindeeItem]:
        """
        Extract items from a receipt image.

        Args:
            image_path: Path to receipt file (PNG, JPG, PDF)

        Returns:
            List of extracted items
        """
        from mindee import ClientV2, InferenceParameters, InferenceResponse, PathInput

        client = ClientV2(api_key=self.api_key)
        input_source = PathInput(image_path)
        params = InferenceParameters(model_id='receipt')

        response = client.enqueue_and_get_result(InferenceResponse, input_source, params)

        items = []
        for line in response.inference.pages[0].prediction.line_items:
            items.append(MindeeItem(
                description=line.description.value if line.description else '',
                quantity=line.quantity.value if line.quantity else 1.0,
                unit_price=line.unit_price.value if line.unit_price else 0.0,
                total=line.total.value if line.total else 0.0,
                confidence=line.confidence.value if line.confidence else 0.0,
            ))

        return items


def main():
    """Test the client."""
    import sys

    api_key = os.environ.get('MINDEE_API_KEY')
    if not api_key:
        print("Error: Set MINDEE_API_KEY environment variable")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python mindee_client.py <receipt_file>")
        sys.exit(1)

    client = MindeeClient(api_key)
    items = client.extract_items(sys.argv[1])

    print(f"Extracted {len(items)} items:")
    for item in items:
        print(f"  {item.description[:40]}: {item.quantity}x {item.unit_price} = {item.total}")


if __name__ == "__main__":
    main()