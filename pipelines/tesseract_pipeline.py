"""
Tesseract Pipeline - Receipt extraction using Tesseract OCR + our parsing.

Usage:
    from pipelines.tesseract_pipeline import process_receipt

    result = process_receipt("receipt.pdf")
    # Returns: GDocument dict with items
"""
import os
from pathlib import Path
from stages.preprocess.image_loader import PreprocessConfig
from stages.preprocess.image_processor import preprocess_image
from stages.parsing.receipt_parser import parse_receipt
from stages.recognition.tesseract_client import recognize_boxes


def process_receipt(
    image_path: str,
    config: dict = None,
) -> dict:
    """
    Process receipt using Tesseract OCR + our parsing pipeline.

    Args:
        image_path: Path to receipt file
        config: Optional configuration dict

    Returns:
        GDocument dict with items
    """
    cfg = config or {}

    # Preprocess
    pp_cfg = PreprocessConfig(
        target_height=cfg.get("target_height", 2400),
        target_width=cfg.get("target_width", 1800),
    )
    pres = preprocess_image(image_path, cfg=pp_cfg)

    # Get Tesseract executable path
    tesseract_executable = cfg.get("tesseract_executable")

    # Load confusion map
    conf_map_path = Path(__file__).resolve().parent.parent / "confusion_map.json"
    if conf_map_path.exists():
        from utils.text_normalization import load_confusion_map
        confusion_map = load_confusion_map(conf_map_path)
    else:
        confusion_map = {}

    # OCR all pages
    all_boxes = []
    for i, pre in enumerate(pres):
        boxes = recognize_boxes(
            pre.preprocessed,
            tesseract_executable=tesseract_executable,
            confusion_map=confusion_map,
            page_idx=i,
        )
        all_boxes.extend(boxes)

    # Parse
    parsed = parse_receipt(all_boxes)
    return parsed.to_gdocument_dict()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python tesseract_pipeline.py <receipt_file>")
        sys.exit(1)

    result = process_receipt(sys.argv[1])
    items = result.get("GDocument", {}).get("fields", {}).get("items", [])
    print(f"Extracted {len(items)} items")
    for item in items[:5]:
        print(f"  {item.get('description', 'N/A')[:30]}")