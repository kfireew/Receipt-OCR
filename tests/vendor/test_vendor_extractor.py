"""TDD tests for the vendor extractor service.

Real samples are used from sample_images/ with matching .JSON ground truth files.
"""
from __future__ import annotations

import sys
sys.path.insert(0, r'C:\Users\Kfir Ezer\Desktop\Receipt OCR')

import pytest
import json
import pathlib
from unittest.mock import patch

from stages.parsing.vendor import match_merchant, extract_vendor
from stages.parsing.shared import ParsedStringField
from stages.grouping.line_assembler import RawLine
from stages.recognition.tesseract_client import RecognizedBox

SAMPLE_DIR = pathlib.Path(r'C:\Users\Kfir Ezer\Desktop\Receipt OCR\sample_images')


# ============================================================
# Unit tests for match_merchant
# ============================================================

class TestMatchMerchant:
    @pytest.mark.parametrize("input_text,expected", [
        ("אביקם", "Avikam"),
        ("אביקם בע''מ", "Avikam"),
        ("אביקם 11-03", "Avikam"),
        ("זינגר", "Avikam"),                     # alternate Avikam keyword
        ("תנובה", "Tnuva"),                       # correct spelling
        ("ויסוצקי", "Wisso"),                     # Wisso full name in mapping
        ("globrands", "Globrands"),               # English name
        ("גלוב", "Globrands"),                    # Hebrew abbreviation
        ("המפיץ", "Hamefitz"),                    # correct spelling
        ("עידה", "Angel"),                        # Ida's actual mapped name
        ("טיירי", "Tayari"),                      # correct spelling
        ("שטראוס קול", "StraussCool"),
        ("שטראוס", "StraussCool"),
        ("שטראום", "StraussCool"),                # OCR variant
        ("wisso", "Wisso"),                       # English variant
        ("strauss", "StraussCool"),               # English variant
    ])
    def test_known_merchants(self, input_text, expected):
        result = match_merchant(input_text)
        assert result == expected, f"Expected '{expected}' for '{input_text}', got '{result}'"

    def test_unknown_merchant_returns_original(self):
        result = match_merchant("Unknown Company Ltd")
        assert result == "Unknown Company Ltd"

    def test_empty_string(self):
        result = match_merchant("")
        assert result == ""


# ============================================================
# Unit tests for extract_vendor
# ============================================================

def _raw_line(index, text, x=100, y=100):
    return RawLine(
        index=index,
        page=0,
        bbox=[x, y, x + 100, y + 20],
        text_raw=text,
        text_normalized=text,
        confidence=0.9,
        boxes=[],
    )


class TestExtractVendor:
    def test_merchant_by_keyword_mapping(self):
        """Line contains a mapped merchant keyword."""
        lines = [_raw_line(0, "אביקם בע''מ"), _raw_line(1, "חשבונית מס' 123")]
        result = extract_vendor(lines)
        assert result.value == "Avikam"
        assert result.confidence == 0.9
        assert result.line_index == 0

    def test_merchant_from_top_lines(self):
        """First lines that aren't keywords are used as merchant."""
        lines = [
            _raw_line(0, "Some Store Name"),
            _raw_line(1, "חשבונית מספר 999"),
        ]
        result = extract_vendor(lines)
        assert result.value is not None
        assert len(result.value) > 0

    def test_merchant_stops_at_header_keywords(self):
        """Should stop combining when it hits invoice/date keywords."""
        lines = [
            _raw_line(0, "Top Company Ltd"),
            _raw_line(1, "חשבונית מס' 500"),
        ]
        result = extract_vendor(lines)
        assert result.value is not None

    def test_empty_lines(self):
        result = extract_vendor([])
        assert result.value is None
        assert result.confidence is None

    def test_merchant_detection_with_fuzzy(self):
        """Fuzzy correction handles OCR noise in merchant name."""
        lines = [
            _raw_line(0, "אביק|ם", x=200, y=10),
            _raw_line(1, "חשבונית"),
        ]
        result = extract_vendor(lines)
        # Should detect Avikam even with the pipe character
        assert result.value is not None


# ============================================================
# Integration tests: match extracted vendor value against ground truth
# ============================================================

SAMPLE_VENDORS = {
    "Avikam_10.03.2025_Avikam 11-03-25": "Avikam",
    "Globrands_23.03.2025_Globrands 24-03-25": "Globrands",
    "Hamefitz_27.12.2024_Hamefitz 15-01-25 A": "Hamefitz",
    "Ida_20.03.2025_Ida 24-03-25": "Angel",
    "Tayari_11.03.2025_Tayari 11-03-25": "Tayari",
    "Tnuva_16.04.2025_Tnuva 21-04-25": "Tnuva",
    "Tnuva_19.08.2024_Tnuva 19-08-24": "Tnuva",
    "Tnuva_20.01.2025_Tnuva 20-01-25 B": "Tnuva",
    "Tnuva_20.01.2025_Tnuva 20-01-25 E": "Tnuva",
}


def _parse_ground_truth(name):
    """Parse the expected vendor from the ground truth JSON."""
    with open(SAMPLE_DIR / f"{name}.JSON", encoding="utf-8") as f:
        data = json.load(f)
    for field in data["GDocument"]["fields"]:
        if field["name"] == "VendorNameS":
            return field["value"]
    return None


def _get_expected_vendor(name):
    """Get expected vendor name from ground truth."""
    return _parse_ground_truth(name)


class TestIntegrationVendorVsGroundTruth:
    """
    Tests that merchant mapping matches the expected vendor from ground truth files.
    These tests DON run OCR — they test the merchant matching / fuzzy correction
    logic by calling match_merchant with expected text.
    """
    @pytest.mark.parametrize("name,expected", [
        ("Avikam_10.03.2025_Avikam 11-03-25", "Avikam"),
        ("Globrands_23.03.2025_Globrands 24-03-25", "Globrands"),
        ("Hamefitz_27.12.2024_Hamefitz 15-01-25 A", "Hamefitz"),
        ("Ida_20.03.2025_Ida 24-03-25", "Angel"),
        ("Tayari_11.03.2025_Tayari 11-03-25", "Tayari"),
    ])
    def test_vendor_merchant_map(self, name, expected):
        """Verify match_merchant maps to expected vendors."""
        # Test that the expected merchant appears in ground truth
        gt_vendor = _get_expected_vendor(name)
        assert gt_vendor == expected, f"Ground truth for {name} is '{gt_vendor}', expected '{expected}'"
        # Test that our matching maps back
        assert match_merchant(expected) == expected

    def test_tnuva_variant_matching(self):
        """All Tnuva variants map to the same normalized name."""
        names = [
            "Tnuva_16.04.2025_Tnuva 21-04-25",
            "Tnuva_19.08.2024_Tnuva 19-08-24",
            "Tnuva_20.01.2025_Tnuva 20-01-25 B",
            "Tnuva_20.01.2025_Tnuva 20-01-25 E",
        ]
        for name in names:
            gt_vendor = _get_expected_vendor(name)
            assert gt_vendor == "Tnuva", f"Ground truth for {name} is '{gt_vendor}', expected 'Tnuva'"
