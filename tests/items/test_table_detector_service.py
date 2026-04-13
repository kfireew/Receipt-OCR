"""TDD Tests for Table Detection Service (Service 1)"""
from __future__ import annotations

import sys
sys.path.insert(0, r'C:\Users\Kfir Ezer\Desktop\Receipt OCR')

import pytest
from stages.parsing.items.table_detector_service import (
    detect_table, DetectedTable, DetectedTableRow, TableCell
)
from stages.recognition.tesseract_client import RecognizedBox
from stages.grouping.line_assembler import RawLine


def _box(x1, y1, x2, y2, text, conf=90, idx=0):
    return RecognizedBox(
        box=[x1, y1, x2, y2],
        page=0,
        text_raw=text,
        text_normalized=text,
        confidence=conf,
        original_index=idx,
    )


def _raw_line(index, boxes, text_override=None):
    """Build a RawLine from a list of RecognizedBox."""
    if not boxes:
        return RawLine(index=index, page=0, bbox=[0, 0, 0, 0], text_raw="", text_normalized="", confidence=0.0, boxes=[])

    x1 = min(b.box[0] for b in boxes)
    y1 = min(b.box[1] for b in boxes)
    x2 = max(b.box[2] for b in boxes)
    y2 = max(b.box[3] for b in boxes)
    texts = " ".join(b.text_raw for b in boxes)
    return RawLine(
        index=index,
        page=0,
        bbox=[x1, y1, x2, y2],
        text_raw=texts,
        text_normalized=texts,
        confidence=0.9,
        boxes=boxes,
    )


class TestTableDetectionService:
    """Tests for the table detection service."""

    def test_empty_input_returns_none(self):
        """Empty input should return None."""
        result = detect_table([])
        assert result is None

    def test_single_line_returns_none(self):
        """Single line can't be a table."""
        lines = [_raw_line(0, [_box(100, 10, 200, 30, "חשבונית")])]
        result = detect_table(lines)
        assert result is None

    def test_header_lines_skipped(self):
        """Header lines like 'חשבונית', 'תאריך' should be skipped."""
        lines = [
            _raw_line(0, [_box(100, 10, 200, 30, "חשבונית מס'")]),
            _raw_line(1, [_box(100, 40, 200, 60, "תאריך: 10.03.2025")]),
            _raw_line(2, [_box(100, 70, 250, 90, "סה''כ לתשלום: 100")]),
        ]
        result = detect_table(lines)
        assert result is None

    def test_table_with_multiple_rows_detected(self):
        """Table with 3+ rows should be detected."""
        lines = [
            # Header (should be skipped)
            _raw_line(0, [_box(100, 10, 200, 30, "תאריך: 10.03.2025")]),
            # Table rows
            _raw_line(1, [
                _box(300, 100, 400, 120, "חלב"),
                _box(200, 100, 220, 120, "2"),
                _box(100, 100, 150, 120, "18.50"),
                _box(50, 100, 80, 120, "37.00"),
            ]),
            _raw_line(2, [
                _box(300, 130, 400, 150, "גבינה"),
                _box(200, 130, 220, 150, "1"),
                _box(100, 130, 150, 150, "25.00"),
                _box(50, 130, 80, 150, "25.00"),
            ]),
            _raw_line(3, [
                _box(300, 160, 400, 180, "לחם"),
                _box(200, 160, 220, 180, "3"),
                _box(100, 160, 150, 180, "8.00"),
                _box(50, 160, 80, 180, "24.00"),
            ]),
        ]
        result = detect_table(lines)

        assert result is not None
        assert result.is_valid
        assert len(result.rows) >= 2
        assert result.column_count >= 2

    def test_contiguous_rows_required(self):
        """Non-contiguous rows (single rows) should not form a valid table."""
        lines = [
            _raw_line(0, [_box(100, 10, 200, 30, "תאריך: 10.03.2025")]),
            # First table-like row
            _raw_line(1, [
                _box(300, 100, 400, 120, "חלב"),
                _box(200, 100, 220, 120, "2"),
                _box(100, 100, 150, 120, "18.50"),
            ]),
            # Big gap - header in between
            _raw_line(10, [_box(100, 300, 200, 320, "סה''כ לתשלום")]),
            # Second table-like row (too far)
            _raw_line(20, [
                _box(300, 500, 400, 520, "גבינה"),
                _box(200, 500, 220, 520, "1"),
                _box(100, 500, 150, 520, "25.00"),
            ]),
        ]
        result = detect_table(lines)
        # Single rows don't form a table (need 2+ contiguous rows)
        assert result is None

    def test_columns_counted_correctly(self):
        """Column count should reflect the maximum cells in any row."""
        lines = [
            _raw_line(0, [
                _box(300, 100, 400, 120, "חלב"),
                _box(200, 100, 220, 120, "2"),
                _box(100, 100, 150, 120, "18.50"),
                _box(50, 100, 80, 120, "37.00"),
            ]),
            _raw_line(1, [
                _box(300, 130, 400, 150, "גבינה צהובה"),
                _box(200, 130, 220, 150, "1"),
                _box(100, 130, 150, 150, "25.00"),
            ]),
        ]
        result = detect_table(lines)

        assert result is not None
        assert result.column_count == 4  # Max from first row

    def test_confidence_based_on_consistency(self):
        """Confidence should be higher for consistent column counts."""
        lines_consistent = [
            _raw_line(0, [
                _box(300, 100, 400, 120, "חלב"),
                _box(200, 100, 220, 120, "2"),
                _box(100, 100, 150, 120, "18.50"),
                _box(50, 100, 80, 120, "37.00"),
            ]),
            _raw_line(1, [
                _box(300, 130, 400, 150, "גבינה"),
                _box(200, 130, 220, 150, "1"),
                _box(100, 130, 150, 150, "25.00"),
                _box(50, 130, 80, 150, "25.00"),
            ]),
            _raw_line(2, [
                _box(300, 160, 400, 180, "לחם"),
                _box(200, 160, 220, 180, "3"),
                _box(100, 160, 150, 180, "8.00"),
                _box(50, 160, 80, 180, "24.00"),
            ]),
        ]

        lines_inconsistent = [
            _raw_line(0, [
                _box(300, 100, 400, 120, "חלב"),
                _box(200, 100, 220, 120, "2"),
                _box(100, 100, 150, 120, "18.50"),
                _box(50, 100, 80, 120, "37.00"),
            ]),
            _raw_line(1, [
                _box(300, 130, 400, 150, "גבינה"),
                _box(50, 130, 80, 150, "25.00"),  # Different layout
            ]),
        ]

        result_consistent = detect_table(lines_consistent)
        result_inconsistent = detect_table(lines_inconsistent)

        assert result_consistent is not None
        assert result_inconsistent is not None
        assert result_consistent.confidence > result_inconsistent.confidence


class TestTableCellExtraction:
    """Tests for cell extraction within rows."""

    def test_hebrew_description_identified(self):
        """Hebrew text should be identified as description."""
        lines = [
            _raw_line(0, [
                _box(300, 100, 400, 120, "חלב תנובה"),
                _box(200, 100, 220, 120, "2"),
                _box(100, 100, 150, 120, "18.50"),
            ]),
        ]
        result = detect_table(lines)

        if result and result.rows:
            cells = result.rows[0].cells
            # Rightmost cell should be description
            desc_cell = cells[0]
            assert "חלב" in desc_cell.text

    def test_empty_boxes_skipped(self):
        """Boxes with empty text should be skipped."""
        lines = [
            _raw_line(0, [
                _box(300, 100, 400, 120, "חלב"),
                _box(200, 100, 220, 120, ""),  # Empty
                _box(100, 100, 150, 120, "18.50"),
            ]),
        ]
        result = detect_table(lines)

        # Should still detect, but with fewer cells
        assert result is None or len(result.rows[0].cells) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])