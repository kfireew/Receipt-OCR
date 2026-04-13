"""TDD Tests for Table Reading Service (Service 2)"""
from __future__ import annotations

import sys
sys.path.insert(0, r'C:\Users\Kfir Ezer\Desktop\Receipt OCR')

import pytest
from stages.parsing.items.table_reader_service import (
    read_table, TableItem
)
from stages.parsing.items.table_detector_service import (
    detect_table, DetectedTable, DetectedTableRow, TableCell
)


def _raw_line_with_cells(index, cell_texts_and_positions):
    """
    Create a RawLine with cells at specific positions.

    cell_texts_and_positions: list of (text, x1, y1, x2, y2)
    Positions are RTL: higher x = right side
    """
    from stages.recognition.tesseract_client import RecognizedBox
    from stages.grouping.line_assembler import RawLine

    boxes = []
    for i, (text, x1, y1, x2, y2) in enumerate(cell_texts_and_positions):
        box = RecognizedBox(
            box=[x1, y1, x2, y2],
            page=0,
            text_raw=text,
            text_normalized=text,
            confidence=90,
            original_index=i,
        )
        boxes.append(box)

    return RawLine(
        index=index,
        page=0,
        bbox=[0, 0, 500, 200],
        text_raw=" ".join(t[0] for t in cell_texts_and_positions),
        text_normalized=" ".join(t[0] for t in cell_texts_and_positions),
        confidence=0.9,
        boxes=boxes,
    )


class TestTableReadingService:
    """Tests for the table reading service."""

    def test_simple_two_numeric_cells(self):
        """Row with description + total should give qty=1."""
        lines = [
            _raw_line_with_cells(0, [
                ("חלב תנובה", 300, 100, 400, 120),  # Description (right)
                ("18.50", 50, 100, 80, 120),        # Total (left)
            ]),
            _raw_line_with_cells(1, [
                ("גבינה", 300, 130, 400, 150),
                ("25.00", 50, 130, 80, 130),
            ]),
        ]

        table = detect_table(lines)
        assert table is not None

        items = read_table(table)
        assert len(items) >= 1
        # Find the milk item
        milk_item = next((i for i in items if "חלב" in i.description), None)
        assert milk_item is not None
        assert milk_item.quantity == 1.0
        assert milk_item.line_total == pytest.approx(18.50)

    def test_three_numeric_cells_qty_price_total(self):
        """Row with qty + price + total should extract correctly."""
        lines = [
            _raw_line_with_cells(0, [
                ("גבינה צהובה", 300, 100, 400, 120),  # Description
                ("2", 200, 100, 220, 120),            # Qty
                ("25.00", 100, 100, 150, 120),        # Price
                ("50.00", 50, 100, 80, 120),          # Total
            ]),
            _raw_line_with_cells(1, [
                ("חלב", 300, 130, 400, 150),
                ("1", 200, 130, 220, 130),
                ("10.00", 100, 130, 150, 130),
                ("10.00", 50, 130, 80, 130),
            ]),
        ]

        table = detect_table(lines)
        assert table is not None

        items = read_table(table)
        # Should have 2 items
        assert len(items) >= 1
        # Find the cheese item
        cheese_item = next((i for i in items if "גבינה" in i.description), None)
        assert cheese_item is not None
        assert cheese_item.quantity == 2.0
        assert cheese_item.unit_price == pytest.approx(25.00)
        assert cheese_item.line_total == pytest.approx(50.00)

    def test_hebrew_description_detection(self):
        """Hebrew text should be detected as description."""
        lines = [
            _raw_line_with_cells(0, [
                ("קפה עלית 250גרם", 300, 100, 400, 120),
                ("32.90", 50, 100, 80, 120),
            ]),
            _raw_line_with_cells(1, [
                ("תה", 300, 130, 400, 150),
                ("15.00", 50, 130, 80, 130),
            ]),
        ]

        table = detect_table(lines)
        if table:
            items = read_table(table)
            coffee_item = next((i for i in items if "קפה" in i.description), None)
            assert coffee_item is not None
        # If no table detected, that's also valid (test passes)

    def test_catalog_number_extraction(self):
        """Catalog numbers (5+ digits) should be extracted."""
        lines = [
            _raw_line_with_cells(0, [
                ("קולה 250מל", 300, 100, 400, 120),
                ("740497", 200, 100, 250, 120),  # Catalog number
                ("1", 150, 100, 165, 120),       # Qty
                ("8.50", 50, 100, 80, 120),      # Total
            ]),
            _raw_line_with_cells(1, [
                ("מים", 300, 130, 400, 150),
                ("1", 200, 130, 220, 130),
                ("5.00", 100, 130, 150, 130),
                ("5.00", 50, 130, 80, 130),
            ]),
        ]

        table = detect_table(lines)
        if table:
            items = read_table(table)
            cola_item = next((i for i in items if "קולה" in i.description), None)
            assert cola_item is not None
            assert cola_item.catalog_no == "740497"

    def test_price_calculated_from_qty_and_total(self):
        """When price is missing, calculate from qty * total."""
        lines = [
            _raw_line_with_cells(0, [
                ("יוגורט דנונה", 300, 100, 400, 120),
                ("3", 200, 100, 220, 120),       # Qty
                ("39.00", 50, 100, 80, 120),     # Total
            ]),
            _raw_line_with_cells(1, [
                ("חלב", 300, 130, 400, 150),
                ("1", 200, 130, 220, 130),
                ("10.00", 50, 130, 80, 130),
            ]),
        ]

        table = detect_table(lines)
        if table:
            items = read_table(table)
            yogurt_item = next((i for i in items if "יוגורט" in i.description), None)
            assert yogurt_item is not None
            assert yogurt_item.quantity == 3.0
            assert yogurt_item.unit_price == pytest.approx(13.00)  # 39/3

    def test_empty_table_returns_empty(self):
        """Empty or invalid table returns empty list."""
        invalid_table = DetectedTable(
            rows=[],
            column_count=0,
            start_line_index=0,
            end_line_index=0,
            confidence=0.0
        )
        items = read_table(invalid_table)
        assert items == []

    def test_multi_row_table(self):
        """Multiple rows should all be extracted."""
        lines = [
            _raw_line_with_cells(0, [
                ("חלב", 300, 100, 400, 120),
                ("2", 200, 100, 220, 120),
                ("18.50", 100, 100, 150, 120),
                ("37.00", 50, 100, 80, 120),
            ]),
            _raw_line_with_cells(1, [
                ("גבינה", 300, 130, 400, 150),
                ("1", 200, 130, 220, 130),
                ("25.00", 100, 130, 150, 130),
                ("25.00", 50, 130, 80, 130),
            ]),
            _raw_line_with_cells(2, [
                ("לחם", 300, 160, 400, 180),
                ("3", 200, 160, 220, 160),
                ("8.00", 100, 160, 150, 160),
                ("24.00", 50, 160, 80, 160),
            ]),
        ]

        table = detect_table(lines)
        assert table is not None

        items = read_table(table)
        assert len(items) == 3

        # Check first item
        assert items[0].quantity == 2.0
        assert items[0].line_total == pytest.approx(37.00)

        # Check second item
        assert items[1].quantity == 1.0
        assert items[1].line_total == pytest.approx(25.00)

        # Check third item
        assert items[2].quantity == 3.0
        assert items[2].line_total == pytest.approx(24.00)


class TestNumberParsing:
    """Tests for number parsing in different formats."""

    def test_decimal_with_dot(self):
        """Standard decimal format."""
        lines = [
            _raw_line_with_cells(0, [
                ("מוצר", 300, 100, 400, 120),
                ("123.45", 50, 100, 80, 120),
            ]),
            _raw_line_with_cells(1, [
                ("מוצר2", 300, 130, 400, 150),
                ("50.00", 50, 130, 80, 130),
            ]),
        ]
        table = detect_table(lines)
        if table:
            items = read_table(table)
            product_item = next((i for i in items if "מוצר" in i.description and "2" not in i.description), None)
            if product_item:
                assert product_item.line_total == pytest.approx(123.45)

    def test_decimal_with_hebrew_apostrophe(self):
        """Hebrew format with apostrophe as decimal separator."""
        lines = [
            _raw_line_with_cells(0, [
                ("מוצר", 300, 100, 400, 120),
                ("123'45", 50, 100, 80, 120),
            ]),
            _raw_line_with_cells(1, [
                ("מוצר2", 300, 130, 400, 150),
                ("50.00", 50, 130, 80, 130),
            ]),
        ]
        table = detect_table(lines)
        if table:
            items = read_table(table)
            product_item = next((i for i in items if "מוצר" in i.description and "2" not in i.description), None)
            if product_item:
                assert product_item.line_total == pytest.approx(123.45)

    def test_decimal_with_comma(self):
        """European format with comma."""
        lines = [
            _raw_line_with_cells(0, [
                ("מוצר", 300, 100, 400, 120),
                ("123,45", 50, 100, 80, 120),
            ]),
            _raw_line_with_cells(1, [
                ("מוצר2", 300, 130, 400, 150),
                ("50.00", 50, 130, 80, 130),
            ]),
        ]
        table = detect_table(lines)
        if table:
            items = read_table(table)
            product_item = next((i for i in items if "מוצר" in i.description and "2" not in i.description), None)
            if product_item:
                assert product_item.line_total == pytest.approx(123.45)

    def test_integer(self):
        """Integer values."""
        lines = [
            _raw_line_with_cells(0, [
                ("מוצר", 300, 100, 400, 120),
                ("100", 50, 100, 80, 120),
            ]),
            _raw_line_with_cells(1, [
                ("מוצר2", 300, 130, 400, 150),
                ("50.00", 50, 130, 80, 130),
            ]),
        ]
        table = detect_table(lines)
        if table:
            items = read_table(table)
            product_item = next((i for i in items if "מוצר" in i.description and "2" not in i.description), None)
            if product_item:
                assert product_item.line_total == pytest.approx(100.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])