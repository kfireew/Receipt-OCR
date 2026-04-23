"""
OBSOLETE - NOT USED BY MAIN PIPELINE
=====================================
PHASE 2: COLUMN-GUIDED SEGMENTATION

Implements column-guided segmentation for Phase 2:
- Uses column positions from Phase 3 to find item rows
- Extracts row cells using column boundaries
- Falls back to fuzzy matching when column detection fails

NEW ALGORITHM FLOW:
1. Get column positions from header lines (via Phase 3)
2. For each JSON item, search in "description" column area
3. Extract entire row using column boundaries
4. Map cell values to fields using column_mapping
5. Enhance JSON items with extracted row data
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from rapidfuzz import fuzz


class Phase2ColumnGuidedSegmentation:
    """
    Phase 2: Column-guided segmentation using column structure.

    Uses column positions detected by Phase 3 to find item rows
    in raw text, extracting cell values using column boundaries.
    """

    def __init__(self, name_match_threshold: int = 20):
        """
        Args:
            name_match_threshold: Minimum fuzzy match score (0-100) for fallback matching
        """
        self.name_match_threshold = name_match_threshold

    def segment_with_columns(
        self,
        json_items: List[Dict[str, Any]],
        raw_text: str,
        column_info: Dict[str, Any],
        raw_lines: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Main entry point: Segment raw text using column structure.

        Args:
            json_items: Items from JSON scan with description, quantity, unit_price, line_total
            raw_text: Full text from raw text scan
            column_info: Column detection results from Phase 3
                - detected_columns: List of dicts with hebrew_text and assigned_field
                - column_mapping: Dict mapping Hebrew keywords to column types
                - lines_range: Tuple of (start_line_idx, end_line_idx) for headers
                - detection_score: Confidence score (0.0-1.0)
            raw_lines: Optional pre-split lines for efficiency

        Returns:
            List of enhanced items with column-aligned data
        """
        if not json_items or not raw_text:
            print("No JSON items or raw text to segment")
            return []

        if raw_lines is None:
            raw_lines = raw_text.splitlines()

        print(f"Phase 2 (Column-Guided): Segmenting {len(json_items)} JSON items against {len(raw_lines)} raw text lines")
        print(f"  Column detection: success={column_info.get('success', False)}, score={column_info.get('detection_score', 0)}")

        # Check if we can use column-guided approach
        column_mapping = column_info.get('column_mapping', {})
        detected_columns = column_info.get('detected_columns', [])
        lines_range = column_info.get('lines_range')

        if not column_mapping or not detected_columns:
            print("  No column mapping available, falling back to fuzzy matching")
            return self._fallback_to_fuzzy_matching(json_items, raw_lines)

        if lines_range is None:
            print("  No header lines range provided, cannot determine column positions")
            return self._fallback_to_fuzzy_matching(json_items, raw_lines)

        # Find column positions in raw text
        header_start, header_end = lines_range
        if header_start >= len(raw_lines) or header_end > len(raw_lines):
            print(f"  Invalid header lines range {lines_range}, max lines={len(raw_lines)}")
            return self._fallback_to_fuzzy_matching(json_items, raw_lines)

        column_positions = self._find_column_positions(
            raw_lines, header_start, header_end, detected_columns
        )

        if not column_positions:
            print("  Could not determine column positions, falling back to fuzzy matching")
            return self._fallback_to_fuzzy_matching(json_items, raw_lines)

        print(f"  Found {len(column_positions)} column positions")

        # Process each JSON item
        segmented_items = []
        for i, json_item in enumerate(json_items):
            print(f"\nProcessing item {i+1}/{len(json_items)}")

            enhanced_item = self._process_item_with_columns(
                json_item, raw_lines, column_positions, column_mapping, column_info
            )

            if enhanced_item:
                segmented_items.append(enhanced_item)
            else:
                # Try fuzzy matching as last resort
                print("  Column-guided search failed, trying fuzzy match...")
                fuzzy_item = self._try_fuzzy_match(json_item, raw_lines)
                if fuzzy_item:
                    segmented_items.append(fuzzy_item)
                else:
                    # Keep original JSON item
                    json_item['segmentation_success'] = False
                    segmented_items.append(json_item)

        success_count = len([i for i in segmented_items if i.get('segmentation_success', False)])
        print(f"\nPhase 2 (Column-Guided) complete: Successfully segmented {success_count}/{len(json_items)} items")

        return segmented_items

    def _find_column_positions(
        self,
        raw_lines: List[str],
        header_start: int,
        header_end: int,
        detected_columns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Find character positions of columns in raw text.

        Args:
            raw_lines: List of raw text lines
            header_start: Start line index of header region
            header_end: End line index of header region (exclusive)
            detected_columns: List of column dicts with hebrew_text

        Returns:
            List of column position dicts with keys:
                - column: Hebrew text
                - start: Character start position (0-indexed)
                - end: Character end position (exclusive)
        """
        # Extract header lines
        header_lines = raw_lines[header_start:header_end]
        if not header_lines:
            return []

        # Use the longest header line (usually has all columns)
        header_text = max(header_lines, key=len)

        # Simple approach: Find positions of column headers in the header text
        column_positions = []

        for col_dict in detected_columns:
            hebrew_text = col_dict.get('hebrew_text')
            if not hebrew_text:
                continue

            # Try to find the column header in the header text
            pos = header_text.find(hebrew_text)
            if pos >= 0:
                column_positions.append({
                    'column': hebrew_text,
                    'start': pos,
                    'end': pos + len(hebrew_text)
                })
                continue

            # Try with normalized text (remove diacritics, etc.)
            normalized_hebrew = self._normalize_hebrew(hebrew_text)
            normalized_header = self._normalize_hebrew(header_text)
            pos = normalized_header.find(normalized_hebrew)
            if pos >= 0:
                # Find actual position in original text
                # This is approximate but should work for most cases
                column_positions.append({
                    'column': hebrew_text,
                    'start': pos,  # Approximate position
                    'end': pos + len(hebrew_text)  # Approximate end
                })
                continue

            # Try fuzzy matching as last resort
            # Look for similar substrings
            for i in range(len(normalized_header) - len(normalized_hebrew) + 1):
                substring = normalized_header[i:i + len(normalized_hebrew)]
                if len(substring) < 3:  # Too short for meaningful match
                    continue

                # Simple similarity check
                if self._simple_text_similarity(substring, normalized_hebrew) > 0.7:
                    column_positions.append({
                        'column': hebrew_text,
                        'start': i,
                        'end': i + len(hebrew_text)
                    })
                    break

        if not column_positions:
            # Fallback: Use whitespace clustering to find columns
            return self._find_column_positions_by_whitespace(header_text, detected_columns)

        # Sort by start position
        column_positions.sort(key=lambda x: x['start'])

        # Adjust end positions to not overlap with next column start
        # Use whitespace as column boundary
        for i in range(len(column_positions) - 1):
            current = column_positions[i]
            next_col = column_positions[i + 1]

            # Current column ends at next column start (or whitespace before it)
            # Find last non-whitespace before next column
            if next_col['start'] > current['end']:
                # Look for whitespace boundary
                for j in range(next_col['start'] - 1, current['end'], -1):
                    if j < len(header_text) and header_text[j].isspace():
                        current['end'] = j
                        break

        # For last column, extend to end of typical row length
        # Use average row length from data rows to estimate
        if column_positions:
            last_col = column_positions[-1]
            # Estimate typical row length from first few data rows
            data_row_lengths = []
            for line_idx in range(header_end, min(header_end + 10, len(raw_lines))):
                if raw_lines[line_idx].strip():  # Non-empty line
                    data_row_lengths.append(len(raw_lines[line_idx]))

            if data_row_lengths:
                avg_row_length = sum(data_row_lengths) / len(data_row_lengths)
                last_col['end'] = max(last_col['end'], int(avg_row_length * 0.8))

        return column_positions

    def _process_item_with_columns(
        self,
        json_item: Dict[str, Any],
        raw_lines: List[str],
        column_positions: List[Dict[str, Any]],
        column_mapping: Dict[str, str],
        column_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single JSON item using column positions.

        Returns:
            Enhanced item with column-aligned data, or None if not found
        """
        description = json_item.get('description', '').strip()
        if not description:
            print("  No description in JSON item")
            return None

        # Find description column position
        description_column = None
        for col_pos in column_positions:
            hebrew_col = col_pos['column']
            assigned_field = None

            # Find assigned field for this column
            for col_dict in column_info.get('detected_columns', []):
                if col_dict.get('hebrew_text') == hebrew_col:
                    assigned_field = col_dict.get('assigned_field')
                    break

            if assigned_field == 'description':
                description_column = col_pos
                break

        if not description_column:
            print("  No description column found in column positions")
            return None

        # Search for item in description column area
        row_idx = self._search_item_in_column(
            description, raw_lines, description_column
        )

        if row_idx is None:
            print(f"  Item not found in description column (col: {description_column['start']}-{description_column['end']})")
            return None

        print(f"  Found item at row {row_idx+1}")

        # Extract row cells using column positions
        row_text = raw_lines[row_idx]
        row_cells = self._extract_row_cells(row_text, column_positions)

        if not row_cells:
            print("  Could not extract row cells")
            return None

        # Enhance item with row data
        enhanced_item = self._enhance_item_with_row_data(
            json_item, row_cells, row_idx, row_text, column_positions, column_mapping, column_info
        )

        return enhanced_item

    def _search_item_in_column(
        self,
        item_name: str,
        raw_lines: List[str],
        description_column: Dict[str, Any]
    ) -> Optional[int]:
        """
        Search for item name in description column area.

        Args:
            item_name: Item description from JSON
            raw_lines: List of raw text lines
            description_column: Column position dict with start/end

        Returns:
            Row index where item found, or None
        """
        normalized_name = self._normalize_hebrew(item_name)

        # Skip header region (first 10 lines typically)
        search_start = min(10, len(raw_lines) - 1)

        best_match_idx = None
        best_match_score = 0

        for idx in range(search_start, len(raw_lines)):
            line = raw_lines[idx]
            if len(line) <= description_column['start']:
                continue

            # Extract text from description column area
            col_start = description_column['start']
            col_end = min(description_column['end'], len(line))
            col_text = line[col_start:col_end].strip()

            if not col_text:
                continue

            normalized_col = self._normalize_hebrew(col_text)

            # Try exact match first
            if normalized_col == normalized_name:
                return idx

            # Try fuzzy match
            score = fuzz.token_sort_ratio(normalized_name, normalized_col)
            if score > best_match_score and score >= self.name_match_threshold:
                best_match_score = score
                best_match_idx = idx

        if best_match_idx is not None:
            print(f"    Fuzzy match found (score: {best_match_score})")

        return best_match_idx

    def _extract_row_cells(
        self,
        row_text: str,
        column_positions: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Extract cell values from a row using column positions.

        Args:
            row_text: Raw text of the row
            column_positions: List of column position dicts

        Returns:
            Dict mapping column Hebrew text to cell value
        """
        row_cells = {}

        for col_pos in column_positions:
            hebrew_col = col_pos['column']
            start = col_pos['start']
            end = col_pos['end']

            if start >= len(row_text):
                cell_value = ""
            elif end > len(row_text):
                cell_value = row_text[start:].strip()
            else:
                cell_value = row_text[start:end].strip()

            row_cells[hebrew_col] = cell_value

        return row_cells

    def _enhance_item_with_row_data(
        self,
        json_item: Dict[str, Any],
        row_cells: Dict[str, str],
        row_idx: int,
        row_text: str,
        column_positions: List[Dict[str, Any]],
        column_mapping: Dict[str, str],
        column_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance JSON item with extracted row data.

        Returns:
            Enhanced item with column-aligned data
        """
        enhanced_item = json_item.copy()

        # Map Hebrew column headers to field names
        mapped_cells = {}
        for hebrew_col, cell_value in row_cells.items():
            field_name = column_mapping.get(hebrew_col)
            if field_name:
                mapped_cells[field_name] = cell_value
            else:
                # Try to find field assignment from detected_columns
                for col_dict in column_info.get('detected_columns', []):
                    if col_dict.get('hebrew_text') == hebrew_col:
                        field_name = col_dict.get('assigned_field')
                        if field_name:
                            mapped_cells[field_name] = cell_value
                        break

        enhanced_item.update({
            'segmentation_success': True,
            'column_mapping_used': column_mapping,
            'row_cells': row_cells,
            'mapped_cells': mapped_cells,
            'raw_row_text': row_text,
            'row_index': row_idx,
            'column_positions': column_positions
        })

        # Try to extract numeric values from cells
        self._extract_numeric_values(enhanced_item, mapped_cells)

        return enhanced_item

    def _extract_numeric_values(
        self,
        enhanced_item: Dict[str, Any],
        mapped_cells: Dict[str, str]
    ):
        """
        Extract numeric values from mapped cells and update item.
        """
        for field_name, cell_value in mapped_cells.items():
            if not cell_value:
                continue

            # Try to extract numeric value
            # Remove currency symbols, commas, etc.
            clean_value = re.sub(r'[^\d\.\-]', '', cell_value)
            if clean_value:
                try:
                    numeric_value = float(clean_value)
                    enhanced_item[f'extracted_{field_name}'] = numeric_value
                except ValueError:
                    pass

    def _fallback_to_fuzzy_matching(
        self,
        json_items: List[Dict[str, Any]],
        raw_lines: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Fallback to fuzzy matching when column detection fails.

        This is a simplified version of the old Phase 2 logic.
        """
        print("  Falling back to fuzzy matching (old Phase 2 logic)")

        segmented_items = []
        for json_item in json_items:
            enhanced_item = self._try_fuzzy_match(json_item, raw_lines)
            if enhanced_item:
                segmented_items.append(enhanced_item)
            else:
                json_item['segmentation_success'] = False
                segmented_items.append(json_item)

        return segmented_items

    def _try_fuzzy_match(
        self,
        json_item: Dict[str, Any],
        raw_lines: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Try to match item using fuzzy matching (old Phase 2 logic).

        Returns:
            Enhanced item if match found, None otherwise
        """
        description = json_item.get('description', '').strip()
        if not description:
            return None

        normalized_desc = self._normalize_hebrew(description)

        best_match_idx = None
        best_match_score = 0

        for idx, line in enumerate(raw_lines):
            normalized_line = self._normalize_hebrew(line)
            score = fuzz.token_sort_ratio(normalized_desc, normalized_line)

            if score > best_match_score and score >= self.name_match_threshold:
                best_match_score = score
                best_match_idx = idx

        if best_match_idx is None:
            return None

        enhanced_item = json_item.copy()
        enhanced_item.update({
            'segmentation_success': True,
            'name_match_score': best_match_score,
            'matched_line': raw_lines[best_match_idx],
            'row_index': best_match_idx,
            'fallback_method': 'fuzzy_matching'
        })

        return enhanced_item

    def _normalize_hebrew(self, text: str) -> str:
        """
        Normalize Hebrew text for better matching.

        Reuses logic from old Phase 2.
        """
        if not text:
            return ""

        # Remove common OCR artifacts and special characters
        # Keep Hebrew letters (0590-05FF), digits, spaces, %, ., -
        text = re.sub(r'[^\w\u0590-\u05FF\d\s%\.\-]', ' ', text)

        # Normalize multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove common prefixes/suffixes
        prefixes = ['פריט:', 'מוצר:', 'תיאור:', 'תאור:', ':', '-', '•']
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()

        # Remove trailing punctuation
        text = text.rstrip('.,;:!?')

        return text

    def _simple_text_similarity(self, text1: str, text2: str) -> float:
        """
        Simple text similarity measure (0.0 to 1.0).

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0 = no similarity, 1.0 = identical)
        """
        if not text1 or not text2:
            return 0.0

        # Convert to sets of characters (ignoring order)
        set1 = set(text1)
        set2 = set(text2)

        # Jaccard similarity
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        if union == 0:
            return 0.0

        return intersection / union

    def _find_column_positions_by_whitespace(
        self,
        header_text: str,
        detected_columns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Fallback method: Find column positions by analyzing whitespace patterns.

        Args:
            header_text: Header line text
            detected_columns: List of column dicts with hebrew_text

        Returns:
            List of column position dicts
        """
        if not header_text.strip():
            return []

        # Find positions of whitespace clusters (column boundaries)
        whitespace_positions = []
        in_whitespace = False
        whitespace_start = 0

        for i, char in enumerate(header_text):
            if char.isspace():
                if not in_whitespace:
                    in_whitespace = True
                    whitespace_start = i
            else:
                if in_whitespace:
                    in_whitespace = False
                    whitespace_positions.append((whitespace_start, i))

        # Also add end of string if trailing whitespace
        if in_whitespace:
            whitespace_positions.append((whitespace_start, len(header_text)))

        # Use whitespace clusters to define column boundaries
        # Assuming columns are separated by multiple spaces
        column_positions = []
        start_pos = 0

        for ws_start, ws_end in whitespace_positions:
            # Check if this is a significant whitespace cluster (≥2 spaces)
            if ws_end - ws_start >= 2:
                # This likely marks a column boundary
                column_text = header_text[start_pos:ws_start].strip()

                # Try to match with detected columns
                for col_dict in detected_columns:
                    hebrew_text = col_dict.get('hebrew_text')
                    if not hebrew_text:
                        continue

                    if hebrew_text in column_text or column_text in hebrew_text:
                        column_positions.append({
                            'column': hebrew_text,
                            'start': start_pos,
                            'end': ws_start  # End at whitespace
                        })
                        break
                else:
                    # No match found, still add as unknown column
                    if column_text:
                        column_positions.append({
                            'column': column_text,
                            'start': start_pos,
                            'end': ws_start
                        })

                start_pos = ws_end

        # Add last column if any text remains
        if start_pos < len(header_text):
            column_text = header_text[start_pos:].strip()
            if column_text:
                # Try to match with detected columns
                for col_dict in detected_columns:
                    hebrew_text = col_dict.get('hebrew_text')
                    if not hebrew_text:
                        continue

                    if hebrew_text in column_text or column_text in hebrew_text:
                        column_positions.append({
                            'column': hebrew_text,
                            'start': start_pos,
                            'end': len(header_text)
                        })
                        break
                else:
                    # No match found
                    column_positions.append({
                        'column': column_text,
                        'start': start_pos,
                        'end': len(header_text)
                    })

        return column_positions

    def _safe_print(self, message: str):
        """Safely print messages that may contain Hebrew characters."""
        try:
            print(message)
        except UnicodeEncodeError:
            # Fall back to ASCII-safe representation
            print(message.encode('ascii', 'replace').decode('ascii'))