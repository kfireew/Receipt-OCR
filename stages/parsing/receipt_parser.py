"""Receipt parser orchestrator.

Thin layer that calls the 5 extractor services and assembles the result.
"""
from __future__ import annotations

from typing import Iterable, Optional
import numpy as np

from stages.grouping.line_assembler import RawLine, _boxes_to_lines
from stages.recognition.tesseract_client import RecognizedBox
from stages.recognition.box_refiner import deduplicate_boxes
from stages.post_process.math_validator import validate_math
from stages.parsing.vendor import extract_vendor
from stages.parsing.dates import _parse_date_from_lines
from stages.parsing.invoices import _parse_invoice_no
from stages.parsing.amounts import _find_amount_field
from stages.parsing.shared import (
    ParsedReceipt, ParsedStringField, ParsedAmountField, LineItem, ExtractedItem
)


def _match_merchant(combined_val: str) -> str:
    """Backward-compat alias to vendor_extractor.match_merchant.

    Kept for any external code that imports this function directly.
    """
    from stages.parsing.vendor.vendor_extractor import match_merchant as _mm
    return _mm(combined_val)


def parse_receipt(recognized_boxes: Iterable[RecognizedBox], images: dict = None) -> ParsedReceipt:
    boxes_list = deduplicate_boxes(list(recognized_boxes))
    raw_lines = _boxes_to_lines(boxes_list)

    # -- Date extractor --
    date_field = _parse_date_from_lines(raw_lines)

    # -- Header amounts extractor --
    subtotal_field = _find_amount_field(raw_lines, keywords=("סך הכל", "סכום ביניים", "ביניים"))
    vat_field = _find_amount_field(raw_lines, keywords=("מע\"מ", "מעמ"))
    total_field = _find_amount_field(raw_lines, keywords=("סה\"כ", "סהכ", "לתשלום", "לשלם", "סך הכל"))

    # -- Currency detection --
    currency_field = ParsedStringField(value=None, confidence=None, line_index=None)
    for ln in raw_lines:
        txt = (ln.text_normalized or ln.text_raw or "").lower()
        if any(sym in txt for sym in ("₪", "nis", "ש\"ח", "שח", "ש״ח")):
            currency_field = ParsedStringField(value="ILS", confidence=ln.confidence, line_index=ln.index)
            break

    # -- Vendor extractor --
    merchant_field = extract_vendor(raw_lines)

    # -- Invoice extractor --
    invoice_field = _parse_invoice_no(raw_lines)

    # -- Items extractor (new table pipeline with column inference) --
    from stages.parsing.items.table_pipeline import process_table_pipeline

    receipt_total = total_field.value if total_field and total_field.value else None
    receipt_subtotal = subtotal_field.value if subtotal_field and subtotal_field.value else None

    # Disable column inference - heuristic extraction works better for receipts
    # with non-aligned columns (most Hebrew receipts)
    table_result = process_table_pipeline(
        raw_lines,
        receipt_total=receipt_total,
        receipt_subtotal=receipt_subtotal,
        detect_columns=False  # Was True, now disabled for better results
    )

    # Convert CorrectedItem to LineItem for ParsedReceipt
    items = [
        LineItem(
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.line_total,
            catalog_no=item.catalog_no,
            confidence=item.confidence,
            line_index=item.line_index
        )
        for item in table_result.items
    ]

    parsed = ParsedReceipt(
        merchant=merchant_field, date=date_field, subtotal=subtotal_field,
        vat=vat_field, total=total_field, currency=currency_field,
        items=items, raw_lines=raw_lines, invoice_no=invoice_field
    )

    return validate_math(parsed)
