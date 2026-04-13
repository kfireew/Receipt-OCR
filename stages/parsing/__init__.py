# Shared models/patterns must load before others due to circular import
from .shared import (
    ParsedReceipt, ParsedStringField, ParsedAmountField,
    LineItem, ExtractedItem, _DATE_PATTERNS, _AMOUNT_RE, parse_amount
)
from .receipt_parser import parse_receipt, _match_merchant
from .vendor import extract_vendor, match_merchant
from .dates import _parse_date_from_lines
from .invoices import _parse_invoice_no
from .amounts import _find_amount_field
# 3-Service Table Architecture
from .items import (
    detect_table, read_table, process_table,
    DetectedTable, TableItem, ValidatedItem,
    validate_items, fix_math_mismatches
)
# Combined Tesseract + Mindee
from stages.recognition.tesseract_client import parse_receipt_combined

__all__ = [
    "parse_receipt", "_match_merchant",
    "extract_vendor", "match_merchant",
    "_parse_date_from_lines",
    "_parse_invoice_no",
    "_find_amount_field",
    # Table processing (3-service architecture)
    "detect_table", "read_table", "process_table",
    "DetectedTable", "TableItem", "ValidatedItem",
    "validate_items", "fix_math_mismatches",
    # Shared
    "ParsedReceipt", "ParsedStringField", "ParsedAmountField",
    "LineItem", "ExtractedItem",
    "_DATE_PATTERNS", "_AMOUNT_RE", "parse_amount",
    # Combined OCR
    "parse_receipt_combined",
]
