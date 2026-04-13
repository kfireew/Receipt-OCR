"""
Table Processing Service - Unified Service

Combines all 3 table services:
1. Table Detection Service - finds the table region
2. Table Reading Service - extracts items from the table
3. Math Validation Service - validates and fixes calculations

Hybrid approach: detect table rows, then extract from full line text (not individual cells).
This gives us row detection power + line-based extraction reliability.

Usage:
    from table_processor import process_table

    result = process_table(raw_lines)
    # result.items - list of extracted items
    # result.is_valid - whether table was found
    # result.confidence - detection confidence
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence

from stages.grouping.line_assembler import RawLine
from stages.parsing.shared import _AMOUNT_RE, parse_amount, LineItem as ParsingLineItem

from .table_detector_service import detect_table, DetectedTable
from .math_validator_service import fix_math_mismatches, validate_items, ValidatedItem
from .table_reader_service import TableItem


@dataclass
class TableProcessingResult:
    """Result of processing a receipt table."""
    items: List[TableItem]
    validated_items: List[ValidatedItem]
    is_valid: bool
    confidence: float
    table_rows_found: int
    items_extracted: int
    math_errors_fixed: int


def process_table(
    raw_lines: Sequence,
    validate_math: bool = True
) -> TableProcessingResult:
    """
    Process a receipt table: detect, read, and validate.

    Hybrid approach:
    1. detect_table() finds valid table row indices
    2. Extract items from full line text (more reliable than cell parsing)

    Args:
        raw_lines: List of RawLine from OCR
        validate_math: Whether to validate and fix math (default: True)

    Returns:
        TableProcessingResult with items and validation info
    """
    # Step 1: Detect the table
    detected_table = detect_table(raw_lines)

    if not detected_table or not detected_table.is_valid:
        return TableProcessingResult(
            items=[],
            validated_items=[],
            is_valid=False,
            confidence=0.0,
            table_rows_found=0,
            items_extracted=0,
            math_errors_fixed=0
        )

    # Step 2: Extract items from detected rows using line text
    raw_items = _extract_from_detected_rows(detected_table, raw_lines)

    if not raw_items:
        return TableProcessingResult(
            items=[],
            validated_items=[],
            is_valid=True,
            confidence=detected_table.confidence,
            table_rows_found=len(detected_table.rows),
            items_extracted=0,
            math_errors_fixed=0
        )

    math_errors_fixed = 0

    if validate_math:
        # Step 3: Fix math mismatches
        fixed_items = fix_math_mismatches(raw_items)

        # Count how many were different (and thus fixed)
        math_errors_fixed = sum(
            1 for orig, fixed in zip(raw_items, fixed_items)
            if (orig.line_total != fixed.line_total or
                orig.quantity != fixed.quantity or
                abs(orig.unit_price - fixed.unit_price) > 0.01)
        )
        raw_items = fixed_items

        # Validate and get detailed results
        validated_items = validate_items(raw_items)
    else:
        # Convert to ValidatedItem format
        validated_items = [
            ValidatedItem(
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
                catalog_no=item.catalog_no,
                confidence=item.confidence,
                line_index=item.line_index,
                math_status=None  # Not validated
            )
            for item in raw_items
        ]

    return TableProcessingResult(
        items=raw_items,
        validated_items=validated_items,
        is_valid=True,
        confidence=detected_table.confidence,
        table_rows_found=len(detected_table.rows),
        items_extracted=len(raw_items),
        math_errors_fixed=math_errors_fixed
    )


def _extract_from_detected_rows(
    detected_table: DetectedTable,
    raw_lines: Sequence[RawLine]
) -> List[TableItem]:
    """Extract items using EXACT same logic as old _extract_items.

    Just scan ALL lines - detector region filtering was causing issues.
    """
    items = []

    # Use EXACT same logic as old _extract_items - scan ALL lines
    skip_patterns = [
        "חשבונית", "תאריך", "לקוח", "עמוד", "מחלק", "מספר",
        "לכבוד", "כתובת", "טלפון", "מיקוד", "טל.", "ע.מ",
        "ח.פ", "סה''כ", "סהכ", "מע\"מ", "מעמ", "לתשלום",
        "invoice", "תעודת", "bn", "הנחה", "שובר",
        "לפני מעמ", "אחרי מעמ", "סיכום", "סיכום ביניים"
    ]

    for i, line in enumerate(raw_lines):
        txt = (line.text_normalized or line.text_raw or "").lower()

        # Skip header/footer
        if any(p in txt for p in skip_patterns):
            continue

        if not txt or len(txt.strip()) < 5:
            continue

        # Must have Hebrew
        if not any('\u0590' <= c <= '\u05FF' for c in txt):
            continue

        # Must have 2+ numeric values
        amounts = [m.group(1) for m in _AMOUNT_RE.finditer(txt)]
        if len(amounts) < 2:
            continue

        # Get line total (largest realistic value)
        line_total = None
        for amt_str in reversed(amounts):
            amt = parse_amount(amt_str)
            if amt is not None and 0.5 <= amt <= 5000:
                line_total = amt
                break

        if line_total is None:
            continue

        # FILTER: Discard very small totals (likely noise)
        if line_total < 1.5:
            continue

        # Find quantity and unit price
        quantity, unit_price = 1.0, line_total
        if len(amounts) >= 2:
            try:
                q_val = float(amounts[0].replace(" ", "").replace(",", ""))
                if 0 < q_val <= 10 and float(int(q_val)) == q_val:
                    quantity = q_val
                    unit_price = line_total / quantity if quantity > 0 else line_total
            except ValueError:
                pass

        # FILTER: Discard if quantity is unrealistic (> 15)
        if quantity > 15:
            continue

        # FILTER: If price is huge (> 2000) and qty > 1, probably wrong
        if unit_price > 2000 and quantity > 1:
            continue

        # Extract description (remove amounts)
        desc = _AMOUNT_RE.sub("", txt).strip()
        if not desc or len(desc) < 2:
            continue

        # Must have Hebrew in description
        if not any('\u0590' <= c <= '\u05FF' for c in desc):
            continue

        # Trim Hebrew description to reasonable length
        if len(desc) > 50:
            desc = desc[:50]

        # Find catalog number
        catalog_no = None
        for m in re.finditer(r"\b(\d{5,14})\b", txt):
            found_num = m.group(1)
            try:
                if float(found_num) not in (quantity, unit_price, line_total):
                    catalog_no = found_num
                    break
            except:
                pass

        items.append(TableItem(
            description=desc,
            quantity=quantity,
            unit_price=unit_price,
            line_total=line_total,
            catalog_no=catalog_no,
            confidence=line.confidence or 0.0,
            line_index=i
        ))

    return items


def process_table_simple(raw_lines: Sequence) -> List[TableItem]:
    """
    Simple table processing without math validation.

    Args:
        raw_lines: List of RawLine from OCR

    Returns:
        List of TableItem objects
    """
    result = process_table(raw_lines, validate_math=True)
    return result.items


# Backwards compatibility aliases
__all__ = [
    "process_table",
    "process_table_simple",
    "TableProcessingResult",
    "TableItem",
    "DetectedTable",
]
