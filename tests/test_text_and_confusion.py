from __future__ import annotations

from pathlib import Path

from receipt_ocr.utils.confidence_utils import combine_confidences
from receipt_ocr.utils.text_normalization import (
    apply_confusion_map,
    load_confusion_map,
    normalize_for_parsing,
    strip_diacritics,
)


def test_strip_diacritics_removes_hebrew_nikud():
    # Contains niqqud on the letters.
    text_with_nikud = "שָׁלוֹם"
    stripped = strip_diacritics(text_with_nikud)
    # Basic sanity: resulting string should be shorter or equal and not identical when niqqud present.
    assert stripped != text_with_nikud
    assert "ש" in stripped


def test_normalize_for_parsing_lowercases_and_cleans_spaces():
    raw = "  שָׁלוֹם   עוֹלָם  "
    norm = normalize_for_parsing(raw)
    # No leading/trailing spaces, lowercased.
    assert norm == norm.strip()
    assert norm == norm.lower()
    # Multiple spaces collapsed.
    assert "  " not in norm


def test_confusion_map_application_and_loading(tmp_path: Path):
    # Write a small confusion map JSON.
    cm_path = tmp_path / "confusion.json"
    cm_path.write_text('{"0": "O", "1": "I"}', encoding="utf-8")

    cm = load_confusion_map(cm_path)
    assert cm["0"] == "O"
    assert cm["1"] == "I"

    text = "10"
    out = apply_confusion_map(text, cm)
    assert out == "IO"


def test_combine_confidences_basic_stats():
    values = [0.2, 0.8, 0.6]
    stats = combine_confidences(values)
    assert stats is not None
    assert stats["min"] == min(values)
    assert stats["max"] == max(values)
    assert stats["mean"] == sum(values) / len(values)

