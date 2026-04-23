"""
Mindee API client - handles all API calls.
"""
from typing import Optional, Dict, Any
from mindee import ClientV2, InferenceParameters, InferenceResponse, PathInput, OCRParameters, OCRResponse


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

    def raw_text(self, image_path: str) -> str:
        """
        Get raw OCR text from OCR model.

        Replaces get_raw_text() + extract_text_from_response().
        Uses OCR model from MINDEE_OCR_MODEL_ID in .env
        """
        try:
            import os
            from dotenv import load_dotenv
            load_dotenv()
            ocr_model_id = os.environ.get("MINDEE_OCR_MODEL_ID")
            if not ocr_model_id:
                raise ValueError("MINDEE_OCR_MODEL_ID not found in .env file")
            params = OCRParameters(model_id=ocr_model_id)
            input_source = PathInput(image_path)
            response = self._client.enqueue_and_get_result(OCRResponse, input_source, params)

            # Extract text from OCR response
            if hasattr(response.inference.result, 'pages'):
                pages = response.inference.result.pages
                text_parts = []
                for page in pages:
                    if hasattr(page, 'content'):
                        text_parts.append(page.content)
                return '\n'.join(text_parts)
            return ""
        except Exception:
            return ""

    
    