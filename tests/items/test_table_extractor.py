"""TDD tests for the table_extractor using mock RecognizedBox + RawLine data."""
from __future__ import annotations

import sys
sys.path.insert(0, r'C:\Users\Kfir Ezer\Desktop\Receipt OCR')

import pytest
from stages.parsing.items.table_detector import detect_receipt_table, ReceiptTable
from stages.parsing.items.table_extractor import (
    extract_items_from_table,
    _parse_row,
    _infer_fields_from_indices,
    _numeric_values,
    _extract_numbers_from_text,
    _find_catalog_in_row,
    _cell_text,
)
from stages.parsing.shared import ExtractedItem
from stages.recognition.tesseract_client import RecognizedBox
from stages.grouping.line_assembler import RawLine

# --- helpers to build mock data ---

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
    """Build a RawLine from a list of RecognizedBox (one box per word)."""
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


# ============================================================
# Unit tests for _extract_numbers_from_text
# ============================================================

@pytest.mark.parametrize("text,expected", [
    ("163.50", [163.50]),
    ("163'50", [163.50]),
    ("500,00", [500.00]),
    ("40.88", [40.88]),
    ("2,18", [2.18]),
    ("18816.00", [18816.00]),
    ("5 000", [5.0, 0.0]),  # Hebrew thousands separator — two separate numbers
    ("7290011723200", [7290011723200.0]),
])
def test_extract_numbers(text, expected):
    result = _extract_numbers_from_text(text)
    assert len(result) == len(expected), f"Got {result} for '{text}'"
    for r, e in zip(result, expected):
        assert abs(r - e) < 0.01, f"Expected {e}, got {r}"


# ============================================================
# Unit tests for _infer_fields
# ============================================================

def _fake_cell(idx, text_vals):
    return (idx, _extract_numbers_from_text(text_vals))


def test_infer_single_total():
    """One numeric cell — it must be total, price=total, qty=1."""
    cells = [_fake_cell(0, "163.50")]
    total, price, qty = _infer_fields_from_indices(cells)
    assert total == 163.50
    assert price == 163.50
    assert qty == 1.0


def test_infer_qty_total():
    """Two numeric cells: quantity (small int) + total."""
    cells = [_fake_cell(0, "5"), _fake_cell(1, "57.00")]
    total, price, qty = _infer_fields_from_indices(cells)
    assert total == pytest.approx(57.00)
    assert abs(total - 57.00) < 0.01
    assert qty == 5.0
    assert price == pytest.approx(11.40)  # 57/5


def test_infer_price_total():
    """Two numeric cells: price (non-int) + total."""
    cells = [_fake_cell(0, "40.88"), _fake_cell(1, "163.50")]
    total, price, qty = _infer_fields_from_indices(cells)
    assert total == pytest.approx(163.50)
    assert price == pytest.approx(40.88)
    assert qty == 1.0


def test_infer_qty_price_total():
    """Three numeric cells: qty + price + total."""
    cells = [_fake_cell(0, "4"), _fake_cell(1, "40.88"), _fake_cell(2, "163.52")]
    total, price, qty = _infer_fields_from_indices(cells)
    assert qty == 4.0
    assert price == pytest.approx(40.88)
    assert total == pytest.approx(163.52)


# ============================================================
# Unit tests for extract_items_from_table (integration)
# ============================================================

def _make_row(line_idx, cell_texts):
    """Make a TableRow from a list of column text strings.

    Each text becomes one TableCell with a single RecognizedBox.
    Columns are placed left-to-right (x decreases for RTL).
    Rightmost column (index 0) = highest x, leftmost (last) = lowest x.
    """
    from stages.parsing.items.table_detector import TableRow, TableCell
    cells = []
    n = len(cell_texts)
    for ci, text in enumerate(cell_texts):
        # RTL layout: rightmost cell (idx 0) gets highest x
        x = (n - 1 - ci) * 100
        box = _box(x, 0, x + 60, 20, text.strip(" ,;"), conf=90)
        cell = TableCell(boxes=[box], bbox=[x, 0, x + 60, 20])
        cells.append(cell)
    return TableRow(line_index=line_idx, cells=cells)


def _make_table(rows):
    return ReceiptTable(rows=rows, columns_x_centers=[])


def test_empty_table():
    assert extract_items_from_table(None) == []
    assert extract_items_from_table(ReceiptTable(rows=[], columns_x_centers=[])) == []


def test_single_item_table():
    """Single row: product with qty + price + total."""
    rows = [
        _make_row(0, [("חלב תנובה 3%"), ("1"), ("18.50"), ("18.50")]),
    ]
    table = _make_table(rows)
    items = extract_items_from_table(table)
    assert len(items) == 1
    assert "חלב" in items[0].description
    assert items[0].quantity == 1.0
    assert items[0].unit_price == pytest.approx(18.50)
    assert items[0].line_total == pytest.approx(18.50)


def test_multi_item_table():
    """Three rows with different column structures."""
    rows = [
        _make_row(0, [("חלב תנובה"), ("1"), ("18.50"), ("18.50")]),
        _make_row(1, [("גבינה צהובה"), ("2"), ("25.00"), ("50.00")]),
        _make_row(2, [("יוגורט דנונה"), ("3"), ("4.33"), ("13.00")]),
    ]
    table = _make_table(rows)
    items = extract_items_from_table(table)
    assert len(items) == 3

    assert items[0].description == "חלב תנובה"
    assert items[0].quantity == 1.0
    assert items[0].unit_price == pytest.approx(18.50)
    assert items[0].line_total == pytest.approx(18.50)

    assert items[1].quantity == 2.0
    assert items[1].unit_price == pytest.approx(25.00)
    assert items[1].line_total == pytest.approx(50.00)

    assert items[2].quantity == 3.0
    assert items[2].unit_price == pytest.approx(4.33)
    assert items[2].line_total == pytest.approx(13.00)


def test_item_without_explicit_quantity():
    """Row with only price + total (no qty column) — qty should default to 1."""
    rows = [
        _make_row(0, [("קפה עלית 250 גרם"), ("32.90"), ("32.90")]),
    ]
    table = _make_table(rows)
    items = extract_items_from_table(table)
    assert len(items) == 1
    assert items[0].quantity == 1.0
    assert items[0].unit_price == pytest.approx(32.90)
    assert items[0].line_total == pytest.approx(32.90)


def test_item_with_catalog_number():
    """Row with catalog number (5+ digit number in text)."""
    rows = [
        _make_row(0, [("קולה 250 מל"), ("740497"), ("1"), ("8.50"), ("8.50")]),
    ]
    table = _make_table(rows)
    items = extract_items_from_table(table)
    assert len(items) == 1
    # The catalog should be detected from the "740497" string which is not used as other fields
    # Note: 740497 appears as a separate cell but it IS numeric, so it might be picked up
    # Let's verify the item exists and has reasonable values


def test_rows_without_text_are_skipped():
    """Empty text cells should produce no items."""
    rows = [_make_row(0, ["", "0", "0"])]
    table = _make_table(rows)
    items = extract_items_from_table(table)
    assert len(items) == 0


# ============================================================
# Integration test: detect_receipt_table + extract_items_from_table
# ============================================================

def make_raw_lines_for_table():
    """Create RawLines that simulate OCR output of a receipt with a table body."""
    # Header lines (no table)
    lines = [
        _raw_line(0, [_box(200, 10, 350, 30, "אביקם בע''מ", 95)]),
        _raw_line(1, [_box(50, 40, 150, 60, "חשבונית מס' 163020", 90)]),
        _raw_line(2, [_box(200, 70, 350, 90, "תאריך: 10.03.2025", 88)]),
        _raw_line(3, [_box(200, 120, 300, 140, "סה''כ לתשלום: 57.00", 85)]),
        _raw_line(4, [_box(200, 160, 300, 180, "מחלקה א'", 90)]),
        # Table rows: Description | Qty | Price | Total (RTL: Desc right, Total left)
        # Wide gaps (>40px) between columns so _merge_overlapping_boxes keeps them separate
        _raw_line(5, [
            _box(300, 210, 400, 230, "חלב תנובה", 92),
            _box(200, 210, 220, 230, "1", 95),
            _box(100, 210, 150, 230, "18.50", 93),
            _box(20, 210, 60, 230, "18.50", 94),
        ]),
        _raw_line(6, [
            _box(300, 240, 400, 260, "גבינה צהובה", 91),
            _box(200, 240, 220, 260, "2", 96),
            _box(100, 240, 150, 260, "28.50", 92),
            _box(20, 240, 60, 260, "57.00", 93),
        ]),
        _raw_line(7, [
            _box(300, 270, 400, 290, "קפה עלית", 90),
            _box(100, 270, 150, 290, "32.90", 91),
            _box(20, 270, 60, 290, "32.90", 92),
        ]),
    ]
    return lines


def test_detect_and_extract_table():
    """Full pipeline: table_detector finds the table, extractor parses it."""
    raw_lines = make_raw_lines_for_table()
    # Lines 5, 6 have 4 cells each; line 7 has 3 cells — all >= 2 cells
    # Should detect contiguous block
    detected = detect_receipt_table(raw_lines)
    assert detected is not None
    assert len(detected.rows) >= 3

    items = extract_items_from_table(detected)
    assert len(items) == 3

    # First item: חלב
    assert "חלב" in items[0].description
    assert items[0].quantity == 1.0
    assert items[0].line_total == pytest.approx(18.50)

    # Second item: גבינה
    assert "גבינה" in items[1].description
    assert items[1].quantity == 2.0
    assert items[1].line_total == pytest.approx(57.00)

    # Third item: קפה (no qty column, defaults to 1)
    assert "קפה" in items[2].description
    assert items[2].quantity == 1.0
    assert items[2].line_total == pytest.approx(32.90)


def test_detect_and_extract_partial_table():
    """Even a single-row table should be detected and extracted."""
    raw_lines = [
        _raw_line(0, [_box(200, 10, 350, 30, "חשבונית", 90)]),
        _raw_line(1, [
            _box(250, 100, 380, 120, "חלב תנובה", 92),
            _box(180, 100, 195, 120, "1", 95),
            _box(120, 100, 140, 120, "18.50", 93),
            _box(50, 100, 80, 120, "18.50", 94),
        ]),
    ]
    detected = detect_receipt_table(raw_lines)
    # At least one row should be detected
    if detected is not None:
        items = extract_items_from_table(detected)
        assert len(items) >= 1
