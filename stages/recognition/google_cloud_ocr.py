"""
Google Cloud Vision OCR integration for receipt processing.
Uses cloud OCR as fallback when local Tesseract fails.
"""
from __future__ import annotations

import io
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path

# Lazy import - only needed when using cloud OCR
_google_cloud = None
_vision_client = None


def _get_vision_client():
    """Lazy load Google Cloud Vision client."""
    global _vision_client, _google_cloud
    if _vision_client is None:
        from google import cloud as _google_cloud
        from google.cloud import vision as _vision_client
    return _vision_client


@dataclass
class CloudOCRResult:
    """Result from cloud OCR."""
    text: str
    confidence: float
    bounding_box: Optional[List[float]] = None


def recognize_with_cloud_vision(
    image_path: str,
    credentials_path: str,
) -> List[CloudOCRResult]:
    """
    Perform OCR using Google Cloud Vision API.

    Args:
        image_path: Path to the image file
        credentials_path: Path to Google service account JSON key

    Returns:
        List of CloudOCRResult with detected text and positions
    """
    from google.cloud import vision
    from google.cloud.vision_v1 import types

    # Set credentials
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

    # Create client
    client = vision.ImageAnnotatorClient()

    # Load image
    with io.open(image_path, 'rb') as f:
        image_content = f.read()

    image = types.Image(content=image_content)

    # Perform text detection
    response = client.text_detection(image=image)
    texts = response.text_annotations

    results = []
    for text in texts:
        results.append(CloudOCRResult(
            text=text.description,
            confidence=text.confidence if hasattr(text, 'confidence') else 0.0,
            bounding_box=None  # Can add vertex positions if needed
        ))

    return results


def extract_text_with_cloud_vision(
    image_path: str,
    credentials_path: str,
) -> str:
    """
    Extract all text from image using Google Cloud Vision.

    Args:
        image_path: Path to image file
        credentials_path: Path to Google service account JSON key

    Returns:
        Full text content
    """
    results = recognize_with_cloud_vision(image_path, credentials_path)
    # First result contains all text
    if results:
        return results[0].text
    return ""


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python google_cloud_ocr.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    # Default credentials path
    credentials_path = r"C:\Users\Kfir Ezer\Downloads\receipt-ocr-492912-885f182e9abb.json"

    print(f"Processing: {image_path}")
    text = extract_text_with_cloud_vision(image_path, credentials_path)
    print(f"\nExtracted text:\n{text}")
