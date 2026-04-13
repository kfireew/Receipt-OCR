"""
Table Reading Service - Service 2 of 3

Reads the detected table and extracts individual line items.
Maps cells to: description, quantity, unit_price, line_total, catalog_no.

Service Interface:
    read_table(detected_table: DetectedTable) -> List[TableItem]
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
import re

from .table_detector_service import DetectedTable, DetectedTableRow, TableCell


@dataclass
class TableItem:
    """A single item extracted from a table row."""
    description: str
    quantity: float
    unit_price: float
    line_total: float
    catalog_no: Optional[str]
    confidence: float
    line_index: int


def read_table(detected_table: DetectedTable) -> List[TableItem]:
    """
    Read items from a detected table.

    Strategy:
    1. For each row, identify description vs numeric cells
    2. Map numeric cells to qty/price/total based on patterns
    3. Extract catalog numbers from text
    4. Validate qty * price ≈ total

    Args:
        detected_table: The detected table structure

    Returns:
        List of TableItem objects
    """
    if not detected_table or not detected_table.is_valid:
        return []

    items = []

    for row in detected_table.rows:
        item = _read_row(row, detected_table.column_count)
        if item is not None:
            items.append(item)

    return items


def _read_row(row: DetectedTableRow, expected_columns: int) -> Optional[TableItem]:
    """Read a single row and extract item data."""
    cells = row.cells
    n = len(cells)

    if n < 2:
        return None

    # Identify description cell (rightmost, has Hebrew text)
    desc_idx = _find_description_index(cells)
    if desc_idx is None:
        return None

    description = cells[desc_idx].text

    # Get numeric values from cells
    numeric_data = _extract_numeric_data(cells, desc_idx)

    if not numeric_data:
        return None

    # Map values to fields
    total, unit_price, quantity = _map_fields(numeric_data)

    # Skip if total is zero or invalid
    if total <= 0:
        return None

    # Find catalog number
    catalog_no = _find_catalog_number(cells, desc_idx)

    # Calculate confidence
    confidence = _calculate_item_confidence(cells, numeric_data, total, unit_price, quantity)

    return TableItem(
        description=description,
        quantity=quantity,
        unit_price=unit_price,
        line_total=total,
        catalog_no=catalog_no,
        confidence=confidence,
        line_index=row.line_index
    )


def _find_description_index(cells: List[TableCell]) -> Optional[int]:
    """
    Find the description cell index.

    In RTL layout:
    - Rightmost cell (index 0) is typically description
    - Description contains Hebrew text
    """
    for i, cell in enumerate(cells):
        text = cell.text
        # Check for Hebrew characters
        if any("\u0590" <= c <= "\u05FF" for c in text):
            # Also check it's not just a number
            if len(text) > 2 or not text.isdigit():
                return i

    # Fallback: rightmost cell that's not purely numeric
    for i in range(len(cells)):
        text = cells[i].text
        if not text.replace(".", "").replace(",", "").isdigit():
            return i

    return None


def _extract_numeric_data(
    cells: List[TableCell],
    desc_idx: int
) -> List[Tuple[float, float, int]]:
    """
    Extract numeric values from non-description cells.

    Returns list of (value, confidence, cell_index) tuples.
    """
    numeric_data = []

    for i, cell in enumerate(cells):
        if i == desc_idx:
            continue

        text = cell.text
        value = _parse_number(text)

        if value is not None and value >= 0:
            numeric_data.append((value, cell.confidence, i))

    return numeric_data


def _parse_number(text: str) -> Optional[float]:
    """Parse a number from text, handling Hebrew/European formats."""
    if not text:
        return None

    # Clean the text
    cleaned = text.strip()

    # Handle Hebrew thousands separator (space)
    cleaned = cleaned.replace(" ", "")

    # Handle decimal separators: ', . and '
    if "'" in cleaned:
        cleaned = cleaned.replace("'", ".")
    elif "," in cleaned and "." in cleaned:
        # Ambiguous - assume dot is decimal
        cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    # Remove any remaining non-numeric except dot
    cleaned = re.sub(r"[^\d.]", "", cleaned)

    if not cleaned or cleaned == ".":
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def _map_fields(
    numeric_data: List[Tuple[float, float, int]]
) -> Tuple[float, float, float]:
    """
    Map numeric values to total, unit_price, quantity.

    Strategy:
    - Last numeric value is typically the line total
    - Small integers (1-10) are likely quantities
    - Remaining value is unit price

    Returns (total, unit_price, quantity)
    """
    if not numeric_data:
        return 0.0, 0.0, 1.0

    if len(numeric_data) == 1:
        val = numeric_data[0][0]
        return val, val, 1.0

    # Sort by position: last cell is total
    sorted_data = sorted(numeric_data, key=lambda x: x[2])

    total = sorted_data[-1][0]

    if len(sorted_data) == 2:
        first_val = sorted_data[0][0]
        if 0 < first_val <= 10 and first_val == int(first_val):
            # First is quantity
            quantity = first_val
            unit_price = total / quantity if quantity > 0 else total
            return total, unit_price, quantity
        else:
            # First is unit price
            return total, first_val, 1.0

    # 3+ values
    first_val = sorted_data[0][0]
    second_val = sorted_data[1][0] if len(sorted_data) > 1 else 0

    # Check if first is quantity (small integer)
    if 0 < first_val <= 10 and first_val == int(first_val):
        quantity = first_val
        unit_price = second_val
        # Verify: qty * price ≈ total
        if abs(quantity * unit_price - total) > 0.1:
            unit_price = total / quantity if quantity > 0 else total
        return total, unit_price, quantity

    # Check if second is quantity
    if 0 < second_val <= 10 and second_val == int(second_val):
        quantity = second_val
        unit_price = first_val
        return total, unit_price, quantity

    # Default: first is price, qty = 1
    return total, first_val, 1.0


def _find_catalog_number(cells: List[TableCell], desc_idx: int) -> Optional[str]:
    """Find a catalog number (5+ digit integer) in non-description cells."""
    for i, cell in enumerate(cells):
        if i == desc_idx:
            continue

        text = cell.text
        # Look for long numbers (catalog numbers)
        cleaned = re.sub(r"[^\d]", "", text)
        if len(cleaned) >= 5 and len(cleaned) <= 14:
            # Make sure it's not a price
            try:
                val = float(cleaned)
                if val > 1000:  # Catalog numbers are typically > 1000
                    return cleaned
            except ValueError:
                pass

    return None


def _calculate_item_confidence(
    cells: List[TableCell],
    numeric_data: List[Tuple[float, float, int]],
    total: float,
    unit_price: float,
    quantity: float
) -> float:
    """Calculate confidence score for the extracted item."""
    # Base confidence from OCR
    if numeric_data:
        avg_conf = sum(c[1] for c in numeric_data) / len(numeric_data)
    else:
        avg_conf = 0.0

    # Penalty for math mismatch
    math_penalty = 0.0
    if quantity > 0:
        expected_total = quantity * unit_price
        if total > 0:
            ratio = abs(expected_total - total) / total
            if ratio > 0.05:  # More than 5% difference
                math_penalty = min(ratio * 50, 30)  # Up to 30 point penalty

    # Penalty for missing fields
    missing_penalty = 0.0
    if quantity == 1.0 and len(numeric_data) < 2:
        missing_penalty = 10.0

    return max(0.0, avg_conf * 100 - math_penalty - missing_penalty)