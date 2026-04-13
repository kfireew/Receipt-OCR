# 3-Service Architecture
# Service 1: Detection -> Service 2: Reading -> Service 3: Validation
from .table_detector_service import (
    detect_table, DetectedTable, DetectedTableRow, TableCell
)
from .table_reader_service import (
    read_table, TableItem
)
from .math_validator_service import (
    validate_items, fix_math_mismatches, MathStatus, ValidatedItem,
    calculate_receipt_totals
)
from .table_processor import (
    process_table, process_table_simple, TableProcessingResult
)

__all__ = [
    # Service 1: Detection
    "detect_table", "DetectedTable", "DetectedTableRow", "TableCell",
    # Service 2: Reading
    "read_table", "TableItem",
    # Service 3: Validation
    "validate_items", "fix_math_mismatches", "MathStatus", "ValidatedItem",
    "calculate_receipt_totals",
    # Orchestrator
    "process_table", "process_table_simple", "TableProcessingResult",
]
