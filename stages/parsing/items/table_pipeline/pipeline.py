"""
Table Pipeline Orchestrator

Combines all 3 services:
1. Column Inference - detect column structure
2. Line Extraction - extract items from lines
3. Auto-Correction - fix errors and validate

Usage:
    result = process_table_pipeline(raw_lines, receipt_total=None)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from stages.grouping.line_assembler import RawLine

from .column_inferrer import infer_columns, ColumnLayout
from .line_extractor import extract_items_from_lines, ExtractedLineItem
from .auto_corrector import auto_correct_items, CorrectedItem


@dataclass
class TablePipelineResult:
    """Result of the table pipeline."""
    items: List[CorrectedItem]
    column_layout: Optional[ColumnLayout]
    is_valid: bool
    confidence: float
    items_extracted: int
    corrections_applied: int


def process_table_pipeline(
    raw_lines: Sequence[RawLine],
    receipt_total: float = None,
    receipt_subtotal: float = None,
    detect_columns: bool = True
) -> TablePipelineResult:
    """
    Process table using the new 3-service pipeline.

    Args:
        raw_lines: OCR lines
        receipt_total: Known total (optional, for validation)
        receipt_subtotal: Known subtotal (optional)
        detect_columns: Whether to infer column positions

    Returns:
        TablePipelineResult with corrected items
    """
    if not raw_lines:
        return TablePipelineResult(
            items=[],
            column_layout=None,
            is_valid=False,
            confidence=0.0,
            items_extracted=0,
            corrections_applied=0
        )

    # Service 1: Infer columns
    columns = None
    if detect_columns:
        columns = infer_columns(list(raw_lines))

    # Service 2: Extract items using columns
    raw_items = extract_items_from_lines(
        list(raw_lines),
        columns=columns,
        start_line=0,
        end_line=len(raw_lines),
        receipt_total=receipt_total
    )

    if not raw_items:
        return TablePipelineResult(
            items=[],
            column_layout=columns,
            is_valid=False,
            confidence=0.0,
            items_extracted=0,
            corrections_applied=0
        )

    # Auto-correct items to filter noise and fix math
    corrected = auto_correct_items(
        raw_items,
        receipt_total=receipt_total,
        receipt_subtotal=receipt_subtotal
    )
    corrections_applied = sum(len(c.corrections) for c in corrected if c.corrections)

    # Calculate confidence
    confidence = _calculate_confidence(corrected, columns)

    return TablePipelineResult(
        items=corrected,
        column_layout=columns,
        is_valid=len(corrected) > 0,
        confidence=confidence,
        items_extracted=len(corrected),
        corrections_applied=corrections_applied
    )


def _calculate_confidence(
    items: List[CorrectedItem],
    columns: Optional[ColumnLayout]
) -> float:
    """Calculate overall confidence score."""
    if not items:
        return 0.0

    # Base: item count (more items = higher confidence)
    count_score = min(len(items) / 20.0, 1.0) * 50

    # Average confidence from OCR
    avg_conf = sum(i.confidence for i in items) / len(items) if items else 0
    conf_score = avg_conf * 0.5 if avg_conf else 0

    # Column confidence if available
    column_score = (columns.confidence if columns else 0) * 0.2 if columns else 0

    return count_score + conf_score + column_score
