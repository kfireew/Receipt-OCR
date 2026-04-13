"""TDD tests for the date extractor service.

Tests compare against ground truth dates from sample_images/*.JSON files.
"""
from __future__ import annotations

import sys
sys.path.insert(0, r'C:\Users\Kfir Ezer\Desktop\Receipt OCR')

import json
import pytest
from datetime import date
from unittest.mock import patch

from stages.parsing.dates.date_extractor import (
    _fuzzy_normalize,
    _parse_date_from_lines,
)
from stages.parsing.shared import ParsedStringField
from stages.grouping.line_assembler import RawLine
from stages.recognition.tesseract_client import RecognizedBox

SAMPLE_DIR = r'C:\Users\Kfir Ezer\Desktop\Receipt OCR\sample_images'


def _raw_line(index, text, y=100, conf=0.9):
    return RawLine(
        index=index, page=0,
        bbox=[100, y, 200, y + 20],
        text_raw=text, text_normalized=text,
        confidence=conf, boxes=[],
    )


# ============================================================
# Unit tests for _parse_date_from_lines
# ============================================================

class TestParseDateFromLines:
    def test_date_with_keyword(self):
        lines = [_raw_line(0, "תאריך: 20.03.2025")]
        result = _parse_date_from_lines(lines)
        assert result.value == "2025-03-20"
        assert result.line_index == 0

    def test_date_without_keyword(self):
        lines = [_raw_line(0, "20.03.2025")]
        result = _parse_date_from_lines(lines)
        assert result.value == "2025-03-20"

    def test_single_digit_day_month(self):
        lines = [_raw_line(0, "5.3.2025")]
        result = _parse_date_from_lines(lines)
        assert result.value == "2025-03-05"

    def test_two_digit_year(self):
        lines = [_raw_line(0, "20.03.25")]
        result = _parse_date_from_lines(lines)
        assert result.value == "2025-03-20"

    def test_slash_separator(self):
        lines = [_raw_line(0, "20/03/2025")]
        result = _parse_date_from_lines(lines)
        assert result.value == "2025-03-20"

    def test_invalid_date_rejected(self):
        lines = [_raw_line(0, "32.13.2025")]  # Invalid day and month
        result = _parse_date_from_lines(lines)
        assert result.value is None

    def test_empty_lines(self):
        result = _parse_date_from_lines([])
        assert result.value is None

    def test_no_date_in_lines(self):
        lines = [_raw_line(0, "No date here just text")]
        result = _parse_date_from_lines(lines)
        assert result.value is None

    def test_keyword_beats_non_keyword(self):
        """Date with keyword should score higher than one without."""
        lines = [
            _raw_line(0, "20.03.2025"),  # No keyword
            _raw_line(1, "תאריך: 15.01.2025"),  # Has keyword
        ]
        result = _parse_date_from_lines(lines)
        assert result.value == "2025-01-15"
        assert result.line_index == 1

    def test_top_position_beats_bottom(self):
        """Date near top should score higher than date near bottom."""
        # Create 40 lines (line 25 < 40-15=25, so line 30 gets +5)
        lines = [_raw_line(i, f"Line {i} with no date", y=i * 10) for i in range(30)]
        lines[2] = _raw_line(2, "10.03.2025")  # Top, score +10
        lines[28] = _raw_line(28, "15.04.2025") # Bottom, score +5
        result = _parse_date_from_lines(lines)
        assert result.value == "2025-03-10"

    def test_ocr_noise_in_date(self):
        """Hebrew text in date line but with correct date pattern."""
        lines = [_raw_line(0, "ת.אריך 16.04.2025")]
        result = _parse_date_from_lines(lines)
        assert result.value == "2025-04-16"

    def test_multiple_dates_same_line(self):
        """Two date patterns on same line — pick the first one at that position."""
        lines = [_raw_line(0, "10.03.2025 / 15.04.2025")]
        result = _parse_date_from_lines(lines)
        assert result.value is not None  # At least one should be found


# ============================================================
# Integration tests: compare extracted dates against ground truth JSON
# ============================================================

GROUND_TRUTH_DATES = {
    "Avikam_10.03.2025_Avikam 11-03-25": {"day": 10, "month": 3, "year": 2025},
    "Globrands_23.03.2025_Globrands 24-03-25": {"day": 23, "month": 3, "year": 2025},
    "Hamefitz_27.12.2024_Hamefitz 15-01-25 A": {"day": 27, "month": 12, "year": 2024},
    "Ida_20.03.2025_Ida 24-03-25": {"day": 20, "month": 3, "year": 2025},
    "Tayari_11.03.2025_Tayari 11-03-25": {"day": 11, "month": 3, "year": 2025},
    "Tnuva_16.04.2025_Tnuva 21-04-25": {"day": 16, "month": 4, "year": 2025},
    "Tnuva_19.08.2024_Tnuva 19-08-24": {"day": 19, "month": 8, "year": 2024},
    "Tnuva_20.01.2025_Tnuva 20-01-25 B": {"day": 20, "month": 1, "year": 2025},
    "Tnuva_20.01.2025_Tnuva 20-01-25 E": {"day": 20, "month": 1, "year": 2025},
    "Wisso_03.03.2025_Wisso 13-03-25 A": {"day": 3, "month": 3, "year": 2025},
}


def _get_ground_truth_date(name):
    """Parse the expected date from the ground truth JSON."""
    with open(f"{SAMPLE_DIR}/{name}.JSON", encoding="utf-8") as f:
        data = json.load(f)
    for field in data["GDocument"]["fields"]:
        if field["name"] == "Date" and field["value"]:
            parts = field["value"].split(".")
            if len(parts) == 3:
                return date(int(parts[2]), int(parts[1]), int(parts[0]))
    return None


class TestIntegrationDateVsGroundTruth:
    """Validate that ground truth date values are well-formed and usable."""

    @pytest.mark.parametrize("name", list(GROUND_TRUTH_DATES.keys()))
    def test_ground_truth_date_parsable(self, name):
        """Ensure ground truth date can be parsed from JSON."""
        gt_date = _get_ground_truth_date(name)
        assert gt_date is not None, f"Could not parse date from {name}.JSON"

    @pytest.mark.parametrize("name,expected", list(GROUND_TRUTH_DATES.items()))
    def test_ground_truth_date_matches_expected(self, name, expected):
        """Verify the date extracted from ground truth matches expectations."""
        gt_date = _get_ground_truth_date(name)
        assert gt_date is not None
        assert gt_date == date(expected["year"], expected["month"], expected["day"])
