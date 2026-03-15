from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

from stages.preprocess.image_processor import preprocess_image
from stages.recognition.tesseract_client import recognize_boxes
from stages.parsing.receipt_parser import parse_receipt

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--config", default="config.yml")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)

    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    tesseract_cmd = config.get("tesseract", {}).get("executable_path")
    confusion_map_path = "confusion_map.json"

    results = preprocess_image(args.image, debug_enabled=args.debug)
    all_boxes = []
    for i, res in enumerate(results):
        boxes = recognize_boxes(res.preprocessed, page_idx=i, tesseract_executable=tesseract_cmd, confusion_map=confusion_map_path)
        all_boxes.extend(boxes)

    parsed = parse_receipt(all_boxes)
    out_dict = parsed.to_gdocument_dict()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out_dict, f, ensure_ascii=False, indent=2)
    else:
        print(json.dumps(out_dict, ensure_ascii=False, indent=2))

    return 0

if __name__ == "__main__":
    sys.exit(main())
