#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Mindee Receipt OCR Integration.

Usage:
    from stages.recognition.mindee_ocr import MindeeOCR

    ocr = MindeeOCR(api_key="md_...")
    items = ocr.extract_items("receipt.pdf")
"""
from dataclasses import dataclass
from typing import List
import os

# Load .env first to get API keys
from dotenv import load_dotenv
load_dotenv()

@dataclass
class MindeeItem:
    """Extracted item from receipt."""
    description: str
    quantity: float
    unit_price: float
    total: float


class MindeeOCR:
    """Mindee API client for receipt extraction."""

    API_KEY = os.environ.get("MINDEE_API_KEY", "")
    MODEL_ID = os.environ.get("MINDEE_MODEL_ID", "2794301c-25bd-402a-bebe-5295a67416e6")

    def __init__(self, api_key: str = None, model_id: str = None):
        """
        Initialize Mindee OCR client.

        Args:
            api_key: Mindee API key. Uses default if not provided.
            model_id: Mindee model ID. Uses default if not provided.
        """
        self.api_key = api_key or self.API_KEY
        self.model_id = model_id or self.MODEL_ID

    def extract_items(self, image_path: str) -> List[MindeeItem]:
        """
        Extract line items from a receipt image.

        Args:
            image_path: Path to receipt file (PNG, JPG, PDF)

        Returns:
            List of extracted items
        """
        from mindee import ClientV2, InferenceParameters, InferenceResponse, PathInput

        client = ClientV2(api_key=self.api_key)
        params = InferenceParameters(model_id=self.model_id)
        input_source = PathInput(image_path)
        response = client.enqueue_and_get_result(InferenceResponse, input_source, params)

        result = response.inference.result
        fields = result.fields

        # Get line items
        line_items_field = fields.get('line_items')
        items = line_items_field.items

        extracted = []
        for item in items:
            item_fields = item.fields

            desc_field = item_fields.get('description')
            desc = desc_field.value if desc_field and desc_field.value else ''

            qty_field = item_fields.get('quantity')
            qty = qty_field.value if qty_field and qty_field.value else 1.0

            unit_price_field = item_fields.get('unit_price')
            unit_price = unit_price_field.value if unit_price_field and unit_price_field.value else 0.0

            total_field = item_fields.get('total_price')
            total = total_field.value if total_field and total_field.value else 0.0

            if desc:
                extracted.append(MindeeItem(
                    description=desc,
                    quantity=qty,
                    unit_price=unit_price,
                    total=total,
                ))

        return extracted

    def get_total(self, image_path: str) -> float:
        """
        Get receipt total.

        Args:
            image_path: Path to receipt file

        Returns:
            Receipt total amount
        """
        from mindee import ClientV2, InferenceParameters, InferenceResponse, PathInput

        client = ClientV2(api_key=self.api_key)
        params = InferenceParameters(model_id=self.model_id)
        input_source = PathInput(image_path)
        response = client.enqueue_and_get_result(InferenceResponse, input_source, params)

        total_field = response.inference.result.fields.get('total_amount')
        return total_field.value if total_field and total_field.value else 0.0


# Convenience function
def extract_receipt_items(image_path: str, api_key: str = None) -> List[MindeeItem]:
    """Extract items from receipt using Mindee."""
    ocr = MindeeOCR(api_key=api_key)
    return ocr.extract_items(image_path)