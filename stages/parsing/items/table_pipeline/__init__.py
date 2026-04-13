"""
Table Pipeline - New 3-Service Architecture

Services:
1. Column Inference - detect column structure via X-position clustering
2. Line Extraction - extract items from lines using heuristics
3. Auto-Correction - fix math errors, noise, and validate

Usage:
    from stages.parsing.items.table_pipeline import process_table_pipeline

    result = process_table_pipeline(raw_lines, receipt_total=total)
"""
from .pipeline import process_table_pipeline, TablePipelineResult
from .column_inferrer import infer_columns, ColumnLayout
from .line_extractor import extract_items_from_lines, ExtractedLineItem
from .auto_corrector import auto_correct_items, CorrectedItem, CorrectionType

__all__ = [
    "process_table_pipeline",
    "TablePipelineResult",
    "infer_columns",
    "ColumnLayout",
    "extract_items_from_lines",
    "ExtractedLineItem",
    "auto_correct_items",
    "CorrectedItem",
    "CorrectionType",
]
