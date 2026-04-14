"""
Mindee API client - handles all API calls.
"""
from typing import Optional, Dict, Any
from mindee import ClientV2, InferenceParameters, InferenceResponse, PathInput


class MindeeClient:
    """Client for Mindee API calls."""

    def __init__(self, api_key: str, model_id: str):
        self.api_key = api_key
        self.model_id = model_id
        self._client = ClientV2(api_key=api_key)

    def scan_receipt_model(self, image_path: str) -> InferenceResponse:
        """Scan 1: Receipt Model - gets structured fields."""
        params = InferenceParameters(model_id=self.model_id)
        input_source = PathInput(image_path)
        return self._client.enqueue_and_get_result(InferenceResponse, input_source, params)

    def scan_raw_ocr(self, image_path: str) -> Optional[InferenceResponse]:
        """Scan 2: Raw OCR - gets word positions (may fail on Starter tier)."""
        try:
            params = InferenceParameters(model_id=self.model_id, polygon=True)
            input_source = PathInput(image_path)
            return self._client.enqueue_and_get_result(InferenceResponse, input_source, params)
        except Exception:
            return None