"""
Azure Document Intelligence integration module.
Provides table extraction for structured receipts using the Layout model.
"""
import io
from typing import List, Optional
from dataclasses import dataclass

from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient


@dataclass
class AzureRecognizedBox:
    """Box representation from Azure OCR."""
    box: List[float]  # [x1, y1, x2, y2]
    page: int
    text_raw: str
    text_normalized: str
    confidence: float


@dataclass
class AzureOCRResult:
    """Result from Azure Document Intelligence."""
    boxes: List[AzureRecognizedBox]
    tables: List  # Azure table objects


# Azure client singleton
_azure_client = None


def get_azure_client(endpoint: str, key: str):
    """Get or create Azure Document Intelligence client."""
    global _azure_client
    if _azure_client is None:
        credential = AzureKeyCredential(key)
        _azure_client = DocumentAnalysisClient(endpoint=endpoint, credential=credential)
    return _azure_client


def recognize_with_azure(
    image,
    endpoint: str,
    key: str,
) -> AzureOCRResult:
    """
    Perform OCR using Azure Document Intelligence Layout model.

    Args:
        image: Preprocessed image (numpy array)
        endpoint: Azure endpoint URL
        key: Azure API key

    Returns:
        AzureOCRResult with boxes and tables
    """
    import cv2
    import numpy as np

    client = get_azure_client(endpoint, key)

    # Convert numpy array to bytes
    if isinstance(image, np.ndarray):
        success, buffer = cv2.imencode('.png', image)
        if success:
            image_bytes = buffer.tobytes()
        else:
            raise ValueError("Failed to encode image")
    else:
        image_bytes = image

    # Use prebuilt-layout model which extracts tables
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        document=image_bytes
    )
    result = poller.result()

    # Convert to our format
    boxes = []
    for page in result.pages:
        for line in page.lines:
            # Get bounding polygon
            if hasattr(line, 'polygon') and line.polygon:
                x_coords = [p.x for p in line.polygon]
                y_coords = [p.y for p in line.polygon]
                x1, x2 = min(x_coords), max(x_coords)
                y1, y2 = min(y_coords), max(y_coords)
            else:
                x1, y1, x2, y2 = 0, 0, 0, 0

            conf = line.confidence if hasattr(line, 'confidence') else 1.0

            boxes.append(AzureRecognizedBox(
                box=[float(x1), float(y1), float(x2), float(y2)],
                page=page.page_number - 1,  # 0-indexed
                text_raw=line.content,
                text_normalized=line.content,
                confidence=conf
            ))

    return AzureOCRResult(
        boxes=boxes,
        tables=result.tables if hasattr(result, 'tables') else []
    )