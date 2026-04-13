"""
Google Cloud Pipeline - Receipt extraction using Google Cloud Vision + our parsing.

Usage:
    from pipelines.google_pipeline import process_receipt

    result = process_receipt("receipt.pdf", credentials_path="path/to/credentials.json")
    # Returns: GDocument dict with items
"""
import os
from pathlib import Path
from stages.preprocess.image_loader import PreprocessConfig
from stages.preprocess.image_processor import preprocess_image
from stages.parsing.receipt_parser import parse_receipt
from stages.recognition.google_cloud_ocr import recognize_with_cloud_vision


def process_receipt(
    image_path: str,
    credentials_path: str = None,
    config: dict = None,
) -> dict:
    """
    Process receipt using Google Cloud Vision OCR + our parsing pipeline.

    Args:
        image_path: Path to receipt file
        credentials_path: Path to Google service account JSON key
        config: Optional configuration dict

    Returns:
        GDocument dict with items
    """
    cfg = config or {}

    # Preprocess (for layout detection)
    pp_cfg = PreprocessConfig(
        target_height=cfg.get("target_height", 2400),
        target_width=cfg.get("target_width", 1800),
    )
    pres = preprocess_image(image_path, cfg=pp_cfg)

    # Use Google Cloud Vision for OCR
    creds = credentials_path or cfg.get("credentials_path")
    if not creds:
        raise ValueError("Google credentials_path required")

    # Get all text/boxes from Google Cloud Vision
    results = recognize_with_cloud_vision(image_path, creds)

    # Convert to our box format
    from stages.recognition.tesseract_client import TesseractBox

    boxes = []
    for i, result in enumerate(results):
        boxes.append(TesseractBox(
            text=result.text,
            confidence=result.confidence,
            box=result.bounding_box or [0, 0, 0, 0],
            page=0,
        ))

    # Parse
    parsed = parse_receipt(boxes)
    return parsed.to_gdocument_dict()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python google_pipeline.py <receipt_file> <credentials_json>")
        sys.exit(1)

    result = process_receipt(sys.argv[1], sys.argv[2])
    items = result.get("GDocument", {}).get("fields", {}).get("items", [])
    print(f"Extracted {len(items)} items")