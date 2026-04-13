"""
OCR Recognition Service - Unified Interface.
Provides a single interface for receipt OCR with swappable backends.

Usage:
    from stages.recognition import recognize_receipt

    # Use Mindee (primary)
    result = recognize_receipt(
        image_path='receipt.pdf',
        provider='mindee',
        api_key='your-mindee-key'
    )

    # Swap with Azure
    result = recognize_receipt(
        image_path='receipt.pdf',
        provider='azure',
        endpoint='your-endpoint',
        api_key='your-azure-key'
    )

Supported providers:
- mindee: Best for receipts (purpose-built)
- azure: Good for tables/layout
- google: Good alternative
- tesseract: Free option
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import os

# Default API keys (should be in environment or config)
DEFAULT_MINDEE_KEY = os.environ.get('MINDEE_API_KEY', 'md_QWugkCswh_7PVgoRm-PcGv-K6J2J-wCDi8JNLwr9avg')
DEFAULT_AZURE_KEY = os.environ.get('AZURE_DOCUMENT_KEY', '')
DEFAULT_AZURE_ENDPOINT = os.environ.get('AZURE_DOCUMENT_ENDPOINT', '')
DEFAULT_GOOGLE_KEY = os.environ.get('GOOGLE_VISION_KEY', '')


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
        provider: OCR provider ('mindee', 'azure', 'google', 'tesseract')
        api_key: Provider API key
        **kwargs: Additional provider-specific params:
            - azure: endpoint
            - google: endpoint
            - mindee: model_id (for custom models)

    Returns:
        OCRResult with boxes and raw text
    """
    if provider == 'mindee':
        return _recognize_mindee(image_path, image_bytes, api_key or DEFAULT_MINDEE_KEY, **kwargs)
    elif provider == 'azure':
        return _recognize_azure(image_path, image_bytes, api_key or DEFAULT_AZURE_KEY,
                          kwargs.get('endpoint', DEFAULT_AZURE_ENDPOINT))
    elif provider == 'google':
        return _recognize_google(image_path, image_bytes, api_key or DEFAULT_GOOGLE_KEY,
                              kwargs.get('endpoint', ''))
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


def _recognize_azure(image_path, image_bytes, api_key, endpoint):
    """Azure Document Intelligence OCR."""
    from stages.recognition.azure_ocr import recognize_with_azure
    import cv2
    import numpy as np

    # Load image if path provided
    if image_path:
        image = cv2.imread(image_path)
    elif image_bytes:
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        raise ValueError("Need image_path or image_bytes")

    result = recognize_with_azure(image, endpoint, api_key)

    boxes = [
        OCRBox(
            box=b.box,
            page=b.page,
            text_raw=b.text_raw,
            text_normalized=b.text_normalized,
            confidence=b.confidence
        )
        for b in result.boxes
    ]

    return OCRResult(
        boxes=boxes,
        raw_text='\n'.join(b.text_raw for b in boxes),
        provider='azure'
    )


def _recognize_google(image_path, image_bytes, api_key, endpoint):
    """Google Cloud Vision OCR."""
    from stages.recognition.google_cloud_ocr import recognize_with_google
    import cv2
    import numpy as np

    if image_path:
        image = cv2.imread(image_path)
    elif image_bytes:
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        raise ValueError("Need image_path or image_bytes")

    result = recognize_with_google(image, api_key, endpoint)

    boxes = [
        OCRBox(
            box=b.box,
            page=b.page,
            text_raw=b.text_raw,
            text_normalized=b.text_normalized,
            confidence=b.confidence
        )
        for b in result.boxes
    ]

    return OCRResult(
        boxes=boxes,
        raw_text='\n'.join(b.text_raw for b in boxes),
        provider='google'
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


# Convenience functions
def recognize_with_mindee(image_path: str = None, image_bytes: bytes = None, **kwargs):
    """Quick Mindee recognition."""
    return recognize_receipt(image_path, image_bytes, provider='mindee', **kwargs)


def recognize_with_azure_image(image, endpoint: str, key: str):
    """Quick Azure recognition from numpy image."""
    return _recognize_azure(None, None, key, endpoint)


# Keep backward compatibility with old import paths
try:
    from stages.recognition.mindee_ocr import MindeeItem
except ImportError:
    pass

try:
    from stages.recognition.azure_ocr import AzureRecognizedBox, AzureOCRResult
except ImportError:
    pass

try:
    from stages.recognition.google_cloud_ocr import CloudOCRResult
    GoogleOCRResult = CloudOCRResult  # Alias for compatibility
except ImportError:
    pass

try:
    from stages.recognition.tesseract_client import TesseractResult
except ImportError:
    pass