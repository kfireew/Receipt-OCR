"""TDD Tests for Math Validation Service (Service 3)"""
from __future__ import annotations

import sys
sys.path.insert(0, r'C:\Users\Kfir Ezer\Desktop\Receipt OCR')

import pytest
from stages.parsing.items.math_validator_service import (
    validate_items,
    fix_math_mismatches,
    MathStatus,
    ValidatedItem,
    calculate_receipt_totals,
)
from stages.parsing.items.table_reader_service import TableItem


class TestMathValidation:
    """Tests for math validation."""

    def test_valid_item_passes(self):
        """Item with correct math should pass validation."""
        item = TableItem(
            description="חלב",
            quantity=2.0,
            unit_price=10.00,
            line_total=20.00,
            catalog_no=None,
            confidence=90.0,
            line_index=0
        )

        validated = validate_items([item])
        assert len(validated) == 1
        assert validated[0].math_status == MathStatus.VALID

    def test_small_mismatch_within_tolerance(self):
        """Small mismatches (<5%) should be considered valid."""
        item = TableItem(
            description="חלב",
            quantity=3.0,
            unit_price=10.00,
            line_total=30.01,  # 0.03% off
            catalog_no=None,
            confidence=90.0,
            line_index=0
        )

        validated = validate_items([item])
        assert validated[0].math_status == MathStatus.VALID

    def test_large_mismatch_fails(self):
        """Large mismatches should fail validation."""
        item = TableItem(
            description="חלב",
            quantity=2.0,
            unit_price=10.00,
            line_total=25.00,  # 25% off!
            catalog_no=None,
            confidence=90.0,
            line_index=0
        )

        validated = validate_items([item])
        assert validated[0].math_status == MathStatus.INVALID

    def test_zero_total_with_zero_expected(self):
        """Zero total with zero expected should be valid."""
        item = TableItem(
            description="מוצר חינם",
            quantity=1.0,
            unit_price=0.0,
            line_total=0.0,
            catalog_no=None,
            confidence=90.0,
            line_index=0
        )

        validated = validate_items([item])
        assert validated[0].math_status == MathStatus.VALID

    def test_multiple_items_validated(self):
        """Multiple items should all be validated."""
        items = [
            TableItem(description="חלב", quantity=2.0, unit_price=10.00, line_total=20.00, catalog_no=None, confidence=90.0, line_index=0),
            TableItem(description="גבינה", quantity=1.0, unit_price=25.00, line_total=25.00, catalog_no=None, confidence=90.0, line_index=1),
            TableItem(description="לחם", quantity=3.0, unit_price=8.00, line_total=24.00, catalog_no=None, confidence=90.0, line_index=2),
        ]

        validated = validate_items(items)
        assert len(validated) == 3
        assert all(v.math_status == MathStatus.VALID for v in validated)


class TestMathFixing:
    """Tests for automatic math fixing."""

    def test_correct_math_unchanged(self):
        """Correct math should not be changed."""
        item = TableItem(
            description="חלב",
            quantity=2.0,
            unit_price=10.00,
            line_total=20.00,
            catalog_no=None,
            confidence=90.0,
            line_index=0
        )

        fixed = fix_math_mismatches([item])
        assert fixed[0].quantity == 2.0
        assert fixed[0].unit_price == 10.00
        assert fixed[0].line_total == 20.00

    def test_total_recalculated_from_qty_and_price(self):
        """When price and qty are correct but total is wrong, recalculate total."""
        item = TableItem(
            description="חלב",
            quantity=2.0,
            unit_price=10.00,
            line_total=25.00,  # Wrong!
            catalog_no=None,
            confidence=90.0,
            line_index=0
        )

        fixed = fix_math_mismatches([item])
        # Since qty is a small integer and price is reasonable, fix the total
        assert fixed[0].line_total == pytest.approx(20.00)
        assert fixed[0].quantity == 2.0
        assert fixed[0].unit_price == 10.00

    def test_qty_clean_but_price_suspicious(self):
        """When qty is a clean integer but price doesn't divide evenly, fix total."""
        item = TableItem(
            description="חלב",
            quantity=5.0,  # Clean integer qty
            unit_price=10.00,  # Doesn't divide evenly into 20
            line_total=20.00,
            catalog_no=None,
            confidence=90.0,
            line_index=0
        )

        fixed = fix_math_mismatches([item])
        # Since qty is clean (5), we fix the total to 50 (5*10)
        assert fixed[0].line_total == pytest.approx(50.00)
        assert fixed[0].quantity == 5.0
        assert fixed[0].unit_price == 10.00

    def test_fallback_recalculate_qty(self):
        """When qty is unusual (decimal < 1), fix price (assume qty is weight)."""
        item = TableItem(
            description="חלב",
            quantity=0.5,  # Decimal qty (< 1) - treated as weight
            unit_price=50.00,
            line_total=100.00,
            catalog_no=None,
            confidence=90.0,
            line_index=0
        )

        fixed = fix_math_mismatches([item])
        # Since qty is decimal < 1, we fix the price (qty is likely correct weight)
        # correct_price = 100 / 0.5 = 200
        assert fixed[0].quantity == 0.5
        assert fixed[0].unit_price == pytest.approx(200.00)

    def test_multiple_items_fixed(self):
        """Multiple items should all be fixed."""
        items = [
            TableItem(description="חלב", quantity=2.0, unit_price=10.00, line_total=25.00, catalog_no=None, confidence=90.0, line_index=0),
            TableItem(description="גבינה", quantity=3.0, unit_price=8.00, line_total=24.00, catalog_no=None, confidence=90.0, line_index=1),
        ]

        fixed = fix_math_mismatches(items)

        # First item: total fixed to 20
        assert fixed[0].line_total == pytest.approx(20.00)

        # Second item: math is correct (3*8=24), should remain unchanged
        assert fixed[1].line_total == pytest.approx(24.00)


class TestCalculateReceiptTotals:
    """Tests for calculating receipt totals from items."""

    def test_single_item_totals(self):
        """Single item should calculate correctly."""
        items = [
            TableItem(description="חלב", quantity=2.0, unit_price=10.00, line_total=20.00, catalog_no=None, confidence=90.0, line_index=0),
        ]

        subtotal, vat, total = calculate_receipt_totals(items)

        assert subtotal == pytest.approx(20.00)
        assert vat == pytest.approx(3.40)  # 17%
        assert total == pytest.approx(23.40)

    def test_multiple_items_totals(self):
        """Multiple items should sum correctly."""
        items = [
            TableItem(description="חלב", quantity=2.0, unit_price=10.00, line_total=20.00, catalog_no=None, confidence=90.0, line_index=0),
            TableItem(description="גבינה", quantity=1.0, unit_price=25.00, line_total=25.00, catalog_no=None, confidence=90.0, line_index=1),
            TableItem(description="לחם", quantity=3.0, unit_price=8.00, line_total=24.00, catalog_no=None, confidence=90.0, line_index=2),
        ]

        subtotal, vat, total = calculate_receipt_totals(items)

        assert subtotal == pytest.approx(69.00)
        assert vat == pytest.approx(11.73)  # 17% of 69
        assert total == pytest.approx(80.73)

    def test_empty_items(self):
        """Empty items list should return zeros."""
        subtotal, vat, total = calculate_receipt_totals([])
        assert subtotal == 0.0
        assert vat == 0.0
        assert total == 0.0


class TestValidatedItem:
    """Tests for ValidatedItem dataclass."""

    def test_valid_status(self):
        """Create valid validated item."""
        item = ValidatedItem(
            description="חלב",
            quantity=2.0,
            unit_price=10.00,
            line_total=20.00,
            catalog_no=None,
            confidence=90.0,
            line_index=0,
            math_status=MathStatus.VALID,
            notes="Math correct"
        )

        assert item.description == "חלב"
        assert item.math_status == MathStatus.VALID
        assert item.notes == "Math correct"

    def test_invalid_with_original(self):
        """Invalid item can store original total."""
        item = ValidatedItem(
            description="חלב",
            quantity=2.0,
            unit_price=10.00,
            line_total=25.00,
            catalog_no=None,
            confidence=90.0,
            line_index=0,
            math_status=MathStatus.INVALID,
            original_total=25.00,
            notes="Fixed: was 25.00"
        )

        assert item.original_total == 25.00


if __name__ == "__main__":
    pytest.main([__file__, "-v"])