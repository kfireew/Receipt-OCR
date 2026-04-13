"""
Table Detection Service - Service 1 of 3

Detects the product table region in a receipt using geometric analysis.
Uses column alignment and vertical consistency to identify table boundaries.

Service Interface:
    detect_table(raw_lines: List[RawLine]) -> Optional[DetectedTable]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Dict, Tuple
from collections import defaultdict
import math

from stages.grouping.line_assembler import RawLine
from stages.recognition.tesseract_client import RecognizedBox


@dataclass
class TableCell:
    """A cell in the detected table."""
    text: str
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    line_index: int


@dataclass
class DetectedTableRow:
    """A row in the detected table."""
    cells: List[TableCell]
    y_position: float
    line_index: int


@dataclass
class DetectedTable:
    """
    Result of table detection.

    Contains the detected table with proper column structure.
    """
    rows: List[DetectedTableRow]
    column_count: int
    start_line_index: int
    end_line_index: int
    confidence: float = 0.0

    @property
    def is_valid(self) -> bool:
        """Table has at least 2 rows with consistent columns."""
        return len(self.rows) >= 2 and self.column_count >= 2


def detect_table(raw_lines: Sequence[RawLine]) -> Optional[DetectedTable]:
    """
    Detect the product table in a receipt.

    Strategy:
    1. Find lines with multiple numeric values (potential table rows)
    2. Group lines into contiguous blocks
    3. Analyze column alignment across lines
    4. Verify consistent column structure

    Args:
        raw_lines: List of assembled RawLine objects from OCR

    Returns:
        DetectedTable if table found, None otherwise
    """
    if not raw_lines:
        return None

    # Step 1: Identify candidate table rows
    # A table row typically has: description text + multiple numeric values
    candidate_rows = _find_candidate_rows(raw_lines)

    if not candidate_rows:
        return None

    # Step 2: Group into contiguous blocks
    blocks = _group_into_blocks(candidate_rows)

    if not blocks:
        return None

    # Step 3: Find the best block (most rows, consistent columns)
    best_block = _select_best_block(blocks, raw_lines)

    if not best_block:
        return None

    # Step 4: Build the detected table with proper column structure
    table = _build_table(best_block, raw_lines)

    return table


def _find_candidate_rows(raw_lines: Sequence[RawLine]) -> List[int]:
    """Find lines that look like table rows.

    Balance between being permissive enough for OCR errors
    but strict enough to avoid over-extraction.
    """
    candidates = []

    for line in raw_lines:
        # Skip lines with too few boxes
        if len(line.boxes) < 2:
            continue

        text = (line.text_raw or "").lower()

        # Skip obvious non-table lines (header/footer/totals)
        skip_patterns = [
            "חשבונית", "תאריך", "לקוח", "עמוד", "מחלק", "מספר",
            "לכבוד", "כתובת", "טלפון", "מיקוד", "טל.", "ע.מ",
            "ח.פ", "סה''כ", "סהכ", "מע\"מ", "מעמ", "לתשלום",
            "invoice", "תעודת", "bn", "שובר",
            "לפני מעמ", "אחרי מעמ", "סיכום", "סביבה",
            # "הנחה" should NOT be skipped - item lines often have discounts
        ]
        if any(p in text for p in skip_patterns):
            continue

        # Skip lines that are just keywords without real content
        if len(text.strip()) < 5:
            continue

        # Must have at least one box with meaningful text (description)
        # and at least one box with numbers
        has_description = False
        has_number = False

        for box in line.boxes:
            box_text = box.text_raw or ""
            # Check if it's primarily text (description)
            digit_count = sum(c.isdigit() for c in box_text)
            alpha_count = sum(c.isalpha() for c in box_text)
            is_text = alpha_count > digit_count and alpha_count >= 2
            # Check if it's primarily numbers
            is_numeric = digit_count >= 2 and len(box_text) >= 3

            if is_text:
                has_description = True
            if is_numeric:
                has_number = True

        if has_description and has_number:
            candidates.append(line.index)

    return candidates


def _group_into_blocks(candidate_indices: List[int]) -> List[List[int]]:
    """Group consecutive candidate indices into blocks.

    Only keeps blocks with 2+ rows to form a proper table.
    """
    if not candidate_indices:
        return []

    blocks = []
    current_block = [candidate_indices[0]]

    for i in range(1, len(candidate_indices)):
        curr = candidate_indices[i]
        prev = candidate_indices[i - 1]

        # Allow small gaps (max 2 lines between table rows)
        if curr - prev <= 3:
            current_block.append(curr)
        else:
            if len(current_block) >= 2:  # Only keep blocks with 2+ rows
                blocks.append(current_block)
            current_block = [curr]

    # Don't forget the last block
    if len(current_block) >= 2:
        blocks.append(current_block)

    return blocks


def _select_best_block(
    blocks: List[List[int]],
    raw_lines: Sequence[RawLine]
) -> Optional[List[int]]:
    """Select the best table block based on consistency."""
    best_block = None
    best_score = -1

    for block in blocks:
        # Score based on:
        # - Number of rows (more is better)
        # - Consistency of box count across rows
        # - Presence of numeric patterns

        lines = [raw_lines[i] for i in block if i < len(raw_lines)]

        if not lines:
            continue

        # Row count score (more rows = higher score)
        row_score = len(lines) * 10

        # Consistency score (penalize varying box counts)
        box_counts = [len(l.boxes) for l in lines]
        if box_counts:
            most_common_count = max(set(box_counts), key=box_counts.count)
            consistency_score = sum(1 for c in box_counts if c == most_common_count) * 5
        else:
            consistency_score = 0

        total_score = row_score + consistency_score

        if total_score > best_score:
            best_score = total_score
            best_block = block

    # Return best block even if score is low (at least we found something)
    return best_block


def _build_table(
    block_indices: List[int],
    raw_lines: Sequence[RawLine]
) -> DetectedTable:
    """Build the detected table from a block of line indices."""
    rows = []
    column_count = 0

    for line_idx in block_indices:
        if line_idx >= len(raw_lines):
            continue

        line = raw_lines[line_idx]

        # Merge close boxes and create cells
        cells = _line_to_cells(line)

        if cells:
            row = DetectedTableRow(
                cells=cells,
                y_position=line.bbox[1] if line.bbox else 0,
                line_index=line_idx
            )
            rows.append(row)

            # Track max column count
            if len(cells) > column_count:
                column_count = len(cells)

    # Calculate confidence based on consistency
    confidence = _calculate_table_confidence(rows, column_count)

    return DetectedTable(
        rows=rows,
        column_count=column_count,
        start_line_index=block_indices[0] if block_indices else 0,
        end_line_index=block_indices[-1] if block_indices else 0,
        confidence=confidence
    )


def _line_to_cells(line: RawLine) -> List[TableCell]:
    """Convert a RawLine into table cells."""
    if not line.boxes:
        return []

    cells = []

    # Sort boxes by x position (left to right)
    # For RTL: rightmost box is first
    sorted_boxes = sorted(
        line.boxes,
        key=lambda b: -(b.box[0] + b.box[2]) / 2  # center from right
    )

    for box in sorted_boxes:
        text = box.text_normalized or box.text_raw or ""

        # Skip empty boxes
        if not text.strip():
            continue

        cell = TableCell(
            text=text.strip(),
            x1=box.box[0],
            y1=box.box[1],
            x2=box.box[2],
            y2=box.box[3],
            confidence=box.confidence or 0.0,
            line_index=line.index
        )
        cells.append(cell)

    return cells


def _calculate_table_confidence(rows: List[DetectedTableRow], column_count: int) -> float:
    """Calculate confidence score for the detected table."""
    if not rows:
        return 0.0

    # Base confidence on row count (more rows = higher confidence)
    row_conf = min(len(rows) / 5.0, 1.0) * 40

    # Consistency of column count
    if rows:
        col_counts = [len(r.cells) for r in rows]
        most_common = max(set(col_counts), key=col_counts.count)
        consistency = sum(1 for c in col_counts if c == most_common) / len(col_counts)
        consistency_conf = consistency * 40
    else:
        consistency_conf = 0

    # Average confidence of cells
    if rows:
        cell_confs = [c.confidence for r in rows for c in r.cells]
        avg_conf = sum(cell_confs) / len(cell_confs) if cell_confs else 0
        cell_conf = avg_conf * 0.2  # Max 20 points
    else:
        cell_conf = 0

    return min(row_conf + consistency_conf + cell_conf, 100.0)