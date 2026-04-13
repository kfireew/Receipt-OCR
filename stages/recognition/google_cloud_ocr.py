"""
Google Cloud Vision OCR integration for receipt processing.
Uses cloud OCR as fallback when local Tesseract fails.
"""
from __future__ import annotations

import io
import os
import base64
import requests
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path

# Lazy import - only needed when using cloud OCR
_google_cloud = None
_vision_client = None

# Default API key - set via GOOGLE_VISION_KEY env var
GOOGLE_VISION_KEY = os.environ.get('GOOGLE_VISION_KEY', '')


@dataclass
class CloudOCRResult:
    """Result from cloud OCR."""
    text: str
    confidence: float
    bounding_box: Optional[List[float]] = None


@dataclass
class GoogleBox:
    """A recognized box from Google Cloud Vision."""
    box: List[float]  # [x1, y1, x2, y2]
    text: str
    confidence: float


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


# ====== NEW: Google Cloud Vision API for header extraction ======

# Default credentials path - can be set via GOOGLE_APPLICATION_CREDENTIALS env var
import os
DEFAULT_GOOGLE_CREDS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')


def _load_image_for_vision(image_path: str) -> bytes:
    """Load image bytes, converting PDF to image if needed."""
    import fitz  # PyMuPDF

    # Check file type
    with open(image_path, 'rb') as f:
        header = f.read(10)

    if header[:4] == b'%PDF':
        # Convert PDF first page to image
        doc = fitz.open(image_path)
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x resolution
        doc.close()
        return pix.tobytes("png")
    else:
        # Regular image
        with open(image_path, 'rb') as f:
            return f.read()


def extract_header_with_google_vision(
    image_path: str,
    credentials_path: str = None,
) -> Dict[str, Any]:
    """Extract vendor and date from receipt using Google Cloud Vision API.

    Uses the Vision API to OCR the full receipt and extract vendor + date.
    Handles both images and PDFs (converts first page to image).

    Args:
        image_path: Path to receipt image or PDF
        credentials_path: Path to Google service account JSON

    Returns:
        Dict with 'vendor' and 'date' ParsedStringField objects
    """
    from stages.parsing.shared import ParsedStringField

    creds_path = credentials_path or DEFAULT_GOOGLE_CREDS

    # Set credentials env var
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path

    # Import and create client
    from google.cloud import vision
    client = vision.ImageAnnotatorClient()

    # Load image (handles PDF conversion)
    image_bytes = _load_image_for_vision(image_path)
    image = vision.Image(content=image_bytes)

    # Perform text detection with Hebrew language hint
    response = client.text_detection(
        image=image,
        image_context=vision.ImageContext(language_hints=["he"])
    )

    annotations = response.text_annotations
    if not annotations:
        raise ValueError("No text detected")

    # First annotation contains all text
    all_text = annotations[0].description

    # Split into lines
    lines = []
    for line_text in all_text.split('\n'):
        if line_text.strip():
            lines.append(_GoogleLine(
                text=line_text.strip(),
                confidence=0.9
            ))

    # Use existing parsers
    vendor = extract_vendor_from_google_lines(lines)
    date = _parse_date_from_google_lines(lines)

    return {
        'vendor': vendor,
        'date': date,
    }


class _GoogleLine:
    """Simple line object compatible with vendor/date extractors."""
    def __init__(self, text: str, confidence: float):
        self.text_raw = text
        self.text_normalized = text
        self.confidence = confidence
        self.index = 0
        self.page = 0
        self.bbox = [0, 0, 0, 0]


def extract_vendor_from_google_lines(lines: List[_GoogleLine]) -> ParsedStringField:
    """Extract vendor from Google OCR lines."""
    from stages.parsing.vendor import extract_vendor as _extract_vendor
    return _extract_vendor(lines)


def _parse_date_from_google_lines(lines: List[_GoogleLine]):
    """Extract date from Google OCR lines."""
    from stages.parsing.dates import _parse_date_from_lines
    return _parse_date_from_lines(lines)
