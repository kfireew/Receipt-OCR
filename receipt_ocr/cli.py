from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .ocr_preprocess import PreprocessConfig, preprocess_image
from .parse_receipt import parse_receipt
from .recognize_tesseract import recognize_boxes
from .utils.io_utils import get_nested, load_config, resolve_debug_dir, write_json
from .utils.text_normalization import load_confusion_map


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Hebrew receipt OCR pipeline (preprocess → detect → recognize → parse)."
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Path to a receipt image (or PDF; first page is used).",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to YAML config file (defaults to config.yml in project root).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug outputs (intermediate images and overlays).",
    )
    parser.add_argument(
        "--debug-dir",
        default=None,
        help="Override debug directory (otherwise taken from config.paths.debug_dir).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write resulting JSON (otherwise printed to stdout).",
    )
    return parser


def _load_confusion_map_from_config(cfg: Dict[str, Any]) -> Dict[str, str]:
    # Allow overriding confusion map path from config, fall back to package default.
    path_str: Optional[str] = get_nested(cfg, "paths.confusion_map", default=None)
    if path_str:
        path = Path(path_str)
    else:
        # Default to the confusion map shipped with the package.
        pkg_root = Path(__file__).resolve().parent
        path = pkg_root / "utils" / "confusion_map.json"
    if not path.is_file():
        return {}
    return load_confusion_map(path)


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    # region agent log
    import json as _json_cli_entry
    import time as _time_cli_entry
    import sys as _sys_cli_entry
    from pathlib import Path as _Path_cli_entry

    try:
        with open(
            r"c:\Users\Kfir Ezer\Desktop\Receipt OCR\debug-4cbdb5.log",
            "a",
            encoding="utf-8",
        ) as _f:
            _f.write(
                _json_cli_entry.dumps(
                    {
                        "sessionId": "4cbdb5",
                        "runId": "pre-fix",
                        "hypothesisId": "H_entrypoint_used",
                        "location": "receipt_ocr/cli.py:main:entry",
                        "message": "receipt_ocr.cli main entry called",
                        "data": {
                            "argv": argv,
                            "parsed_image": args.image,
                            "config": args.config,
                            "cwd": str(_Path_cli_entry.cwd()),
                            "python_executable": _sys_cli_entry.executable,
                            "module_file": __file__,
                            "sys_path_head": _sys_cli_entry.path[:5],
                        },
                        "timestamp": int(_time_cli_entry.time() * 1000),
                    },
                    default=str,
                )
                + "\n"
            )
    except Exception:
        # Logging must never break the CLI
        pass
    # endregion

    cfg = load_config(args.config)
    debug_default = bool(get_nested(cfg, "debug.enabled_default", default=False))
    debug_enabled = bool(args.debug or debug_default)
    debug_dir = resolve_debug_dir(cfg, override_dir=args.debug_dir)

    # Preprocessing configuration.
    pp_cfg = PreprocessConfig(
        target_height=int(get_nested(cfg, "preprocess.target_height", default=1600)),
        target_width=int(get_nested(cfg, "preprocess.target_width", default=1200)),
        adaptive_threshold_block_size=int(
            get_nested(cfg, "preprocess.adaptive_threshold_block_size", default=31)
        ),
        adaptive_threshold_C=int(
            get_nested(cfg, "preprocess.adaptive_threshold_C", default=10)
        ),
    )

    image_path = Path(args.image)
    if not image_path.is_file():
        parser.error(f"Image not found: {image_path}")

    # 1) Preprocess
    pres = preprocess_image(
        image_path=image_path,
        cfg=pp_cfg,
        debug_dir=debug_dir,
        debug_enabled=debug_enabled,
    )

    # 2) Detect (DocTR bypassed/optional, using native Tesseract in Recognize stage)
    # 3) Recognize
    tesseract_executable = get_nested(cfg, "tesseract.executable_path", default=None)
    confusion_map = _load_confusion_map_from_config(cfg)

    all_recognized_boxes = []
    for page_idx, pre in enumerate(pres):
        recognized_boxes = recognize_boxes(
            preprocessed_image=pre.preprocessed,
            detected_boxes=[],
            tesseract_executable=tesseract_executable,
            confusion_map=confusion_map,
            page_idx=page_idx,
        )
        all_recognized_boxes.extend(recognized_boxes)

    # 4) Parse into structured fields
    parsed = parse_receipt(all_recognized_boxes)
    result = parsed.to_gdocument_dict()

    if args.output:
        write_json(result, args.output)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

