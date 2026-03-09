from __future__ import annotations

from receipt_ocr.parse_receipt import _boxes_to_lines, parse_receipt
from receipt_ocr.recognize_tesseract import RecognizedBox


def _make_box(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    text: str,
    page: int = 0,
    conf: float = 0.9,
) -> RecognizedBox:
    return RecognizedBox(
        box=[x1, y1, x2, y2],
        page=page,
        text_raw=text,
        text_normalized=text,
        confidence=conf,
    )


def test_boxes_grouped_into_single_line_rtl_order():
    # Two words on the same horizontal line, with different x positions.
    # For Hebrew we expect right-to-left order in the assembled line.
    boxes = [
        _make_box(10, 10, 20, 20, "שני"),
        _make_box(40, 10, 50, 20, "מילה"),
    ]
    lines = _boxes_to_lines(boxes)
    assert len(lines) == 1
    # Because of RTL ordering, we expect the rightmost box first.
    assert "מילה" in lines[0].text_raw.split()[0]


def test_parse_receipt_extracts_date_and_total_and_items():
    # Simulate a tiny receipt with merchant, date line, one item line, and total line.
    boxes = [
        _make_box(10, 10, 50, 20, "סופר כלשהו"),  # merchant (first line)
        _make_box(10, 30, 60, 40, "תאריך 16.04.2025"),  # date
        _make_box(10, 50, 80, 60, "חלב 1 5.00"),  # item: quantity 1, total 5.00
        _make_box(10, 70, 80, 80, 'סה"כ 5.00 ₪'),  # total with currency
    ]

    parsed = parse_receipt(boxes)
    data = parsed.to_dict()

    assert data["merchant"]["value"] is not None
    assert data["date"]["value"] is not None
    assert data["total"]["value"] == 5.0
    assert data["currency"]["value"] == "ILS"
    assert len(data["items"]) >= 1
    item = data["items"][0]
    assert item["line_total"] == 5.0
    assert item["quantity"] == 1.0

