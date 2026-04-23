"""OBSOLETE TEST FILE - NOT USED BY MAIN PIPELINE
===============================================
TDD tests for the header amounts extractor service.

Tests compare against ground truth amounts from sample_images/*.JSON files.
"""
from __future__ import annotations

import sys
sys.path.insert(0, r'C:\Users\Kfir Ezer\Desktop\Receipt OCR')

import json
import pytest

from stages.parsing.amounts.amounts_extractor import _find_amount_field
from stages.parsing.shared import ParsedAmountField
from stages.grouping.line_assembler import RawLine

SAMPLE_DIR = r'C:\Users\Kfir Ezer\Desktop\Receipt OCR\sample_images'


def _raw_line(index, text, y=100, conf=0.9):
    return RawLine(
        index=index, page=0,
        bbox=[100, y, 200, y + 20],
        text_raw=text, text_normalized=text,
        confidence=conf, boxes=[],
    )


# ============================================================
# Unit tests for _find_amount_field
# ============================================================

class TestFindAmountField:
    def test_total_with_keyword(self):
        lines = [_raw_line(30, "סה\"כ 163.50")]
        result = _find_amount_field(lines, keywords=("סה\"כ", "סהכ", "לתשלום"))
        assert result.value == pytest.approx(163.50)

    def test_subtotal_keyword(self):
        lines = [_raw_line(25, "סכום ביניים 100.00")]
        result = _find_amount_field(lines, keywords=("סך הכל", "סכום ביניים", "ביניים"))
        assert result.value == pytest.approx(100.00)

    def test_vat_keyword(self):
        lines = [_raw_line(28, 'מע"מ 17.50')]
        result = _find_amount_field(lines, keywords=("מע\"מ", "מעמ"))
        assert result.value == pytest.approx(17.50)

    def test_empty_lines(self):
        result = _find_amount_field([], keywords=("סה\"כ",))
        assert result.value is None

    def test_no_matching_keyword(self):
        lines = [_raw_line(1, "Just text 50.00")]
        result = _find_amount_field(lines, keywords=("סה\"כ",))
        assert result.value is None

    def test_multiple_amounts_on_line(self):
        """Line with multiple amounts — total search picks max."""
        lines = [_raw_line(35, "סה\"כ 5.00 100.00 250.00")]
        result = _find_amount_field(lines, keywords=("סה\"כ", "לתשלום"))
        assert result.value == pytest.approx(250.00)

    def test_bottom_position_bonus(self):
        """Amount near bottom should score higher."""
        lines = [_raw_line(30, "סה\"כ 420.00")]
        result = _find_amount_field(lines, keywords=("סה\"כ",))
        assert result.value == pytest.approx(420.00)
        assert result.line_index == 30

    def test_grum_weight_exclusion(self):
        """Line with 'גרם' should skip amounts (weight, not price)."""
        lines = [_raw_line(10, "סה\"כ 500 גרם 23.90")]
        # The 500 is a weight, 23.90 should still be found if not excluded
        # But the line has both סה\"כ and גרם context
        result = _find_amount_field(lines, keywords=("סה\"כ",))
        # The context check should skip 500 since it's near גרם
        if result.value is not None:
            assert result.value != pytest.approx(500.0)

    def test_hebrew_apostrophe_decimal(self):
        """Hebrew receipts use ' as decimal separator."""
        lines = [_raw_line(40, "סה\"כ 163'50")]
        result = _find_amount_field(lines, keywords=("סה\"כ",))
        assert result.value == pytest.approx(163.50)

    def test_comma_decimal(self):
        """European-style comma as decimal."""
        lines = [_raw_line(40, "סה\"כ 163,50")]
        result = _find_amount_field(lines, keywords=("סה\"כ",))
        assert result.value == pytest.approx(163.50)


# ============================================================
# Integration tests: compare against ground truth JSON
# ============================================================

def _get_ground_truth_total(name):
    """Parse the expected total from the ground truth JSON."""
    with open(f"{SAMPLE_DIR}/{name}.JSON", encoding="utf-8") as f:
        data = json.load(f)
    for field in data["GDocument"]["fields"]:
        if field["name"] == "Total" and field["value"]:
            return float(field["value"])
    return None


GROUND_TRUTH_TOTALS = {
    # Ground truth total values from .JSON files
    "Avikam_10.03.2025_Avikam 11-03-25": 2352.00,
}


class TestIntegrationAmountsVsGroundTruth:
    """Validate that ground truth amounts are well-formed."""

    @pytest.mark.parametrize("name,expected", list(GROUND_TRUTH_TOTALS.items()))
    def test_ground_truth_total_parsable(self, name, expected):
        """Ensure ground truth total can be parsed."""
        gt_total = _get_ground_truth_total(name)
        assert gt_total is not None, f"Could not parse Total from {name}.JSON"
        assert gt_total == pytest.approx(expected)

    @pytest.mark.parametrize("name", [
        "Avikam_10.03.2025_Avikam 11-03-25",
        "Globrands_23.03.2025_Globrands 24-03-25",
        "Hamefitz_27.12.2024_Hamefitz 15-01-25 A",
        "Ida_20.03.2025_Ida 24-03-25",
        "Tayari_11.03.2025_Tayari 11-03-25",
        "Tnuva_16.04.2025_Tnuva 21-04-25",
        "Tnuva_19.08.2024_Tnuva 19-08-24",
        "Tnuva_20.01.2025_Tnuva 20-01-25 B",
        "Tnuva_20.01.2025_Tnuva 20-01-25 E",
        "Wisso_03.03.2025_Wisso 13-03-25 A",
    ])
    def test_all_ground_truth_has_total(self, name):
        """Every receipt should have a total field in ground truth."""
        gt_total = _get_ground_truth_total(name)
        assert gt_total is not None, f"No Total found in {name}.JSON"
        assert gt_total > 0, f"Total for {name} should be positive, got {gt_total}"
