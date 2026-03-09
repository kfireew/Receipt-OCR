from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pytest

from receipt_ocr import cli


@pytest.mark.parametrize("debug_flag", [False])
def test_cli_smoke_runs_with_mocked_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, debug_flag: bool) -> None:
    """
    End-to-end-ISH smoke test for the CLI.

    This test avoids heavy docTR / Tesseract calls by monkeypatching the
    detection and recognition steps to return a small, synthetic receipt.
    """

    # Create a dummy config file pointing to default detector and no tesseract override.
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(
        "tesseract:\n"
        "  executable_path: null\n"
        "doctr:\n"
        "  detector_model: db_resnet50\n"
        "paths:\n"
        "  debug_dir: debug\n"
        "preprocess:\n"
        "  target_height: 100\n"
        "  target_width: 100\n"
        "  adaptive_threshold_block_size: 31\n"
        "  adaptive_threshold_C: 10\n"
        "debug:\n"
        "  enabled_default: false\n",
        encoding="utf-8",
    )

    # Create a tiny blank image as input.
    img_path = tmp_path / "dummy.png"
    try:
        from PIL import Image
    except Exception:  # pragma: no cover - environment specific
        pytest.skip("Pillow is required for CLI smoke test")
    img = Image.new("RGB", (100, 100), color="white")
    img.save(img_path)

    # Monkeypatch detect/recognize to avoid heavy models.
    from receipt_ocr import detect_doctr as detect_mod
    from receipt_ocr import recognize_tesseract as recog_mod
    from receipt_ocr.recognize_tesseract import RecognizedBox

    def fake_detect(*args, **kwargs) -> List[detect_mod.DetectedBox]:  # type: ignore[override]
        return []

    def fake_recognize(*args, **kwargs) -> List[RecognizedBox]:  # type: ignore[override]
        # Produce a minimal set of recognizable boxes for parsing.
        return [
            RecognizedBox(
                box=[10, 10, 50, 20],
                page=0,
                text_raw="סופר כלשהו",
                text_normalized="סופר כלשהו",
                confidence=0.9,
            )
        ]

    monkeypatch.setattr(detect_mod, "detect_text_boxes", fake_detect)
    monkeypatch.setattr(recog_mod, "recognize_boxes", fake_recognize)

    out_path = tmp_path / "out.json"
    argv = [
        "--image",
        str(img_path),
        "--config",
        str(cfg_path),
        "--output",
        str(out_path),
    ]
    if debug_flag:
        argv.append("--debug")

    code = cli.main(argv)
    assert code == 0
    assert out_path.is_file()

    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "merchant" in data
    assert "raw_lines" in data

