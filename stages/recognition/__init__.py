"""
OCR Recognition Service - Unified Interface.

Provides a single interface for receipt OCR with Mindee.

Usage:
    from stages.recognition import recognize_receipt

    result = recognize_receipt(
        image_path='receipt.pdf',
        provider='mindee',
        api_key='your-mindee-key'
    )

Supported providers:
- mindee: Primary (receipt model + raw OCR for better parsing)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import os

# Default API keys (should be in environment)
DEFAULT_MINDEE_KEY = os.environ.get('MINDEE_API_KEY', '')


@dataclass
class OCRBox:
    """A recognized text box from OCR."""
    box: List[float]  # [x1, y1, x2, y2]
    page: int
    text_raw: str
    text_normalized: str
    confidence: float


@dataclass
class OCRResult:
    """Result from OCR recognition."""
    boxes: List[OCRBox]
    raw_text: str
    provider: str


def recognize_receipt(
    image_path: str = None,
    image_bytes: bytes = None,
    provider: str = 'mindee',
    api_key: str = None,
    **kwargs
) -> OCRResult:
    """
    Recognize receipt text using specified provider.

    Args:
        image_path: Path to receipt image (PNG, JPG, PDF)
        image_bytes: Image as bytes
        provider: OCR provider ('mindee' or 'tesseract')
        api_key: Provider API key
        **kwargs: Additional provider-specific params

    Returns:
        OCRResult with boxes and raw text
    """
    if provider == 'mindee':
        return _recognize_mindee(image_path, image_bytes, api_key or DEFAULT_MINDEE_KEY, **kwargs)
    elif provider == 'tesseract':
        return _recognize_tesseract(image_path, image_bytes, **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _recognize_mindee(image_path, image_bytes, api_key, **kwargs):
    """Mindee OCR."""
    from mindee_ocr import recognize_with_mindee

    items = recognize_with_mindee(
        image_path=image_path,
        image_bytes=image_bytes,
        model_id=kwargs.get('model_id'),
        api_key=api_key
    )

    # Convert to OCRResult format
    boxes = [
        OCRBox(
            box=[0, 0, 0, 0],  # Mindee doesn't provide boxes by default
            page=0,
            text_raw=item.description,
            text_normalized=item.description,
            confidence=item.confidence
        )
        for item in items
    ]

    return OCRResult(
        boxes=boxes,
        raw_text='\n'.join(b.text_raw for b in boxes),
        provider='mindee'
    )


def _recognize_tesseract(image_path, image_bytes, **kwargs):
    """Tesseract OCR."""
    from stages.recognition.tesseract_client import recognize_with_tesseract

    result = recognize_with_tesseract(image_path or image_bytes)

    boxes = [
        OCRBox(
            box=[b.box[0], b.box[1], b.box[2], b.box[3]],
            page=b.page,
            text_raw=b.text,
            text_normalized=b.text,
            confidence=b.confidence
        )
        for b in result.boxes
    ]

    return OCRResult(
        boxes=boxes,
        raw_text='\n'.join(b.text_raw for b in boxes),
        provider='tesseract'
    )


# Convenience function
def recognize_with_mindee(image_path: str = None, image_bytes: bytes = None, **kwargs):
    """Quick Mindee recognition."""
    return recognize_receipt(image_path, image_bytes, provider='mindee', **kwargs)


# Keep backward compatibility with old import paths
try:
    from stages.recognition.mindee_ocr import MindeeItem
except ImportError:
    pass