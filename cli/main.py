from __future__ import annotations

import argparse
import json
import logging
import sys
import io
from pathlib import Path

import yaml
import cv2

from stages.preprocess.image_processor import preprocess_image
from stages.preprocess.image_loader import _load_image_any
from stages.recognition.tesseract_client import recognize_boxes
from stages.recognition.box_refiner import deduplicate_boxes
from stages.grouping.line_assembler import _boxes_to_lines
from stages.parsing.receipt_parser import parse_receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--config", default="config.yml")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--credentials", default="C:/Users/Kfir Ezer/Downloads/receipt-ocr-492912-885f182e9abb.json",
                        help="Path to Google Cloud credentials JSON")
    args = parser.parse_args(argv)

    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    confusion_map_path = "confusion_map.json"

    # Preprocess image
    results = preprocess_image(args.image, debug_enabled=args.debug)

    # Use Google Cloud Vision OCR instead of Tesseract
    all_boxes = _recognize_with_cloud(args.image, args.credentials)

    parsed = parse_receipt(all_boxes)
    out_dict = parsed.to_gdocument_dict()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out_dict, f, ensure_ascii=False, indent=2)
    else:
        print(json.dumps(out_dict, ensure_ascii=False, indent=2))

    return 0


def _recognize_with_cloud(image_path: str, credentials_path: str):
    """
    Perform OCR using Google Cloud Vision API.
    Returns list of RecognizedBox objects.
    """
    import os
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

    from google.cloud import vision
    from stages.recognition.tesseract_client import RecognizedBox
    from utils.text_normalization import normalize_for_parsing
    from utils.bidi_utils import normalize_bidi_for_parsing

    # Load image (supports PDF via fitz)
    images = _load_image_any(Path(image_path))
    img = images[0]  # Take first page if PDF

    # Save temp image for cloud processing
    temp_path = "temp_cloud_ocr.png"
    cv2.imwrite(temp_path, img)

    try:
        # Initialize Cloud Vision client
        client = vision.ImageAnnotatorClient()

        with io.open(temp_path, 'rb') as f:
            image_content = f.read()

        image = vision.Image(content=image_content)
        response = client.text_detection(image=image)
        texts = response.text_annotations

        # Convert to RecognizedBox
        cloud_boxes = []
        for i, text in enumerate(texts[1:]):  # Skip first (full text)
            if not text.description:
                continue

            # Get bounding box
            if hasattr(text, 'bounding_poly') and text.bounding_poly and text.bounding_poly.vertices:
                verts = text.bounding_poly.vertices
                x1 = min(v.x for v in verts)
                y1 = min(v.y for v in verts)
                x2 = max(v.x for v in verts)
                y2 = max(v.y for v in verts)
            else:
                continue

            raw_text = text.description
            normalized = normalize_for_parsing(raw_text)
            normalized = normalize_bidi_for_parsing(normalized)
            conf = text.confidence if hasattr(text, 'confidence') and text.confidence else 0.8

            cloud_boxes.append(RecognizedBox(
                box=[float(x1), float(y1), float(x2), float(y2)],
                page=0,
                text_raw=raw_text,
                text_normalized=normalized,
                confidence=float(conf),
                original_index=i
            ))

        # Deduplicate and convert to lines
        deduped = deduplicate_boxes(cloud_boxes)
        return deduped

    finally:
        if Path(temp_path).exists():
            import os
            os.remove(temp_path)


if __name__ == "__main__":
    sys.exit(main())
