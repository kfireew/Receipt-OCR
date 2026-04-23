"""
PHASE 2: SMART COLUMN SEGMENTATION - THREE-LAYER INTELLIGENCE

Implements a smarter Phase 2 that combines:
1. COLUMN-AWARE SEGMENTATION: Uses column structure intelligently (when available)
2. ROBUST FALLBACK: Falls back to proven fuzzy matching when columns fail
3. DATA COMPLETENESS: Provides ALL data formats for downstream phases

FIXES CRITICAL BUGS FROM phase2_column_guided.py:
1. Wrong column boundaries → Dynamic boundary detection from data rows
2. Wrong item matching → Two-phase search with price verification
3. Missing extracted_numbers → Always extracts ALL numbers for Phase 4

ARCHITECTURE:
- LAYER 1: Column-aware segmentation with dynamic boundaries
- LAYER 2: Robust fallback to fuzzy matching + price anchoring
- LAYER 3: Data completeness guarantee (row_cells + extracted_numbers + item_block)
"""

import re
from typing import List, Dict, Any, Tuple, Optional, Set
from rapidfuzz import fuzz


class Phase2SmartColumnSegmentation:
    """
    Smarter Phase 2: Combines column awareness with robust fallback and data completeness.

    Key improvements over phase2_column_guided.py:
    1. Dynamic column boundaries based on actual data row analysis
    2. Two-phase item search (column-aware → full-line fallback)
    3. Price anchoring for verification
    4. Always creates extracted_numbers list for Phase 4 compatibility
    5. Preserves all data formats: row_cells, extracted_numbers, item_block
    """

    def __init__(self, name_match_threshold: int = 20, price_tolerance: float = 0.05):
        """
        Args:
            name_match_threshold: Minimum fuzzy match score (0-100)
            price_tolerance: Tolerance for price comparison
        """
        self.name_match_threshold = name_match_threshold
        self.price_tolerance = price_tolerance

    def segment_raw_text(
        self,
        json_items: List[Dict[str, Any]],
        raw_text: str,
        column_info: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Main entry point: Segment raw text using smarter column-aware approach.

        Args:
            json_items: Items from JSON scan with description, quantity, unit_price, line_total
            raw_text: Full text from raw text scan
            column_info: Column detection results from Phase 3 (optional)

        Returns:
            List of enhanced items with ALL required data:
            - row_cells: Dict mapping Hebrew columns to values (column context)
            - extracted_numbers: List of ALL numbers in item block (Phase 4 compatibility)
            - item_block: Raw text lines of the item block
            - segmentation_success: True/False
        """
        if not json_items or not raw_text:
            print("No JSON items or raw text to segment")
            return []

        raw_lines = raw_text.splitlines()
        print(f"Phase 2 (Smart Column): Segmenting {len(json_items)} items against {len(raw_lines)} lines")

        # Determine segmentation strategy
        can_use_columns = self._can_use_column_info(column_info)

        segmented_items = []

        for i, json_item in enumerate(json_items):
            print(f"\nProcessing item {i+1}/{len(json_items)}")

            enhanced_item = None

            if can_use_columns:
                # LAYER 1: Try smarter column-aware segmentation
                enhanced_item = self._process_item_with_smarter_columns(
                    json_item, raw_lines, column_info
                )

                # If column method failed or low confidence, fall back
                if not enhanced_item or enhanced_item.get('segmentation_confidence', 0) < 0.6:
                    print(f"  Column method failed (confidence: {enhanced_item.get('segmentation_confidence', 0) if enhanced_item else 0}), falling back...")
                    enhanced_item = self._process_item_with_fuzzy_fallback(json_item, raw_lines)
            else:
                # LAYER 2: Use robust fuzzy matching fallback
                enhanced_item = self._process_item_with_fuzzy_fallback(json_item, raw_lines)

            if enhanced_item:
                # LAYER 3: Ensure data completeness
                self._ensure_data_completeness(enhanced_item)
                segmented_items.append(enhanced_item)
            else:
                # Keep original with failure flag
                json_item['segmentation_success'] = False
                segmented_items.append(json_item)

        success_count = len([i for i in segmented_items if i.get('segmentation_success', False)])
        print(f"\nPhase 2 (Smart Column) complete: Successfully segmented {success_count}/{len(json_items)} items")

        return segmented_items

    def _can_use_column_info(self, column_info: Optional[Dict[str, Any]]) -> bool:
        """Check if column info is reliable enough to use."""
        if not column_info:
            return False

        if not column_info.get('success', False):
            return False

        # Need column mapping and detected columns
        column_mapping = column_info.get('column_mapping', {})
        detected_columns = column_info.get('detected_columns', [])

        if not column_mapping or not detected_columns:
            return False

        # Need at least description column for column-aware search
        has_description_column = False
        for col_dict in detected_columns:
            if col_dict.get('assigned_field') == 'description':
                has_description_column = True
                break

        if not has_description_column:
            print("  Cannot use column info: No description column found")
            return False

        # Need lines_range for finding column positions
        lines_range = column_info.get('lines_range')
        if not lines_range:
            print("  Cannot use column info: No lines_range provided")
            return False

        return True

    def _process_item_with_smarter_columns(
        self,
        json_item: Dict[str, Any],
        raw_lines: List[str],
        column_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Process item using smarter column-aware segmentation.

        Key improvements over phase2_column_guided.py:
        1. Dynamic column boundaries from data row analysis
        2. Two-phase search with price verification
        3. Confidence scoring for fallback decisions
        """
        description = json_item.get('description', '').strip()
        if not description:
            print("  No description in JSON item")
            return None

        # Get price anchors for verification
        line_total = json_item.get('line_total')
        unit_price = json_item.get('unit_price')
        price_to_match = line_total if line_total else unit_price

        # Find description column
        description_column_pos = self._find_description_column_position(
            raw_lines, column_info
        )

        if not description_column_pos:
            print("  Could not find description column position")
            return None

        # PHASE A: Search in description column area
        column_match_result = self._search_item_in_column_with_price_verification(
            description, raw_lines, description_column_pos, price_to_match
        )

        if column_match_result and column_match_result.get('confidence', 0) >= 0.7:
            print(f"  ✓ Strong column match (confidence: {column_match_result['confidence']:.2f})")
            return self._enhance_item_with_column_data(
                json_item, raw_lines, column_match_result, column_info
            )

        # PHASE B: If column search failed or low confidence, try full-line search
        print(f"  Column search failed (confidence: {column_match_result.get('confidence', 0) if column_match_result else 0}), trying full-line...")
        full_line_match = self._search_item_full_line_with_price(
            description, raw_lines, price_to_match
        )

        if full_line_match and full_line_match.get('confidence', 0) >= 0.6:
            print(f"  ✓ Full-line match with price verification (confidence: {full_line_match['confidence']:.2f})")
            return self._enhance_item_with_column_data(
                json_item, raw_lines, full_line_match, column_info
            )

        print("  Both column and full-line search failed")
        return None

    def _find_description_column_position(
        self,
        raw_lines: List[str],
        column_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Find description column position with DYNAMIC boundaries.

        Fixes bug: Column width should be based on DATA, not just header text.
        """
        detected_columns = column_info.get('detected_columns', [])
        lines_range = column_info.get('lines_range')

        if not lines_range:
            return None

        header_start, header_end = lines_range

        # Find description column in detected columns
        description_column_info = None
        for col_dict in detected_columns:
            if col_dict.get('assigned_field') == 'description':
                description_column_info = col_dict
                break

        if not description_column_info:
            return None

        # Get initial position from header (like phase2_column_guided.py)
        initial_position = self._find_initial_column_position(
            raw_lines, header_start, header_end, description_column_info
        )

        if not initial_position:
            return None

        # CRITICAL FIX: Adjust boundaries based on ACTUAL DATA ROWS
        # Analyze 5-10 data rows after header to find real column width
        dynamic_position = self._calculate_dynamic_column_boundaries(
            raw_lines, header_end, initial_position
        )

        return dynamic_position

    def _find_initial_column_position(
        self,
        raw_lines: List[str],
        header_start: int,
        header_end: int,
        column_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find initial column position in header (similar to phase2_column_guided.py)."""
        header_lines = raw_lines[header_start:header_end]
        if not header_lines:
            return None

        # Use longest header line
        header_text = max(header_lines, key=len)
        hebrew_text = column_info.get('hebrew_text', '')

        if not hebrew_text:
            return None

        # Try to find column in header
        pos = header_text.find(hebrew_text)
        if pos < 0:
            # Try normalized text
            normalized_hebrew = self._normalize_hebrew(hebrew_text)
            normalized_header = self._normalize_hebrew(header_text)
            pos = normalized_header.find(normalized_hebrew)

        if pos >= 0:
            return {
                'hebrew_text': hebrew_text,
                'start': pos,
                'end': pos + len(hebrew_text),
                'field': column_info.get('assigned_field')
            }

        return None

    def _calculate_dynamic_column_boundaries(
        self,
        raw_lines: List[str],
        data_start_idx: int,
        initial_position: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate DYNAMIC column boundaries based on actual data rows.

        FIXES BUG 1: Column width should accommodate DATA, not just header text.

        Strategy:
        1. Analyze whitespace patterns in data rows
        2. Adjust end boundary to include typical data width
        3. Ensure column can fit multiple values if needed
        """
        position = initial_position.copy()
        start_pos = position['start']

        # Analyze first 10 data rows (or as many as available)
        analysis_rows = min(10, len(raw_lines) - data_start_idx)
        if analysis_rows <= 0:
            # No data rows, keep initial boundaries
            return position

        # Collect text from this column in data rows
        column_texts = []
        for i in range(data_start_idx, data_start_idx + analysis_rows):
            line = raw_lines[i]
            if len(line) > start_pos:
                # Extract from start_pos to end of line (or until next whitespace cluster)
                # Look for next significant whitespace (≥2 spaces)
                line_from_start = line[start_pos:]

                # Find next whitespace cluster (≥2 spaces)
                whitespace_match = re.search(r'\s{2,}', line_from_start)
                if whitespace_match:
                    end_in_line = start_pos + whitespace_match.start()
                    cell_text = line[start_pos:end_in_line].strip()
                else:
                    # No whitespace cluster, take rest of line
                    cell_text = line[start_pos:].strip()

                if cell_text:
                    column_texts.append(cell_text)

        if not column_texts:
            # No data in this column, keep initial boundaries
            return position

        # Calculate needed width: max data length + some padding
        max_data_length = max(len(text) for text in column_texts)
        needed_width = max_data_length + 3  # Add padding

        # Adjust end position
        current_width = position['end'] - position['start']
        if needed_width > current_width:
            position['end'] = position['start'] + needed_width
            print(f"    Adjusted column width: {current_width} → {needed_width} chars")

        return position

    def _search_item_in_column_with_price_verification(
        self,
        item_name: str,
        raw_lines: List[str],
        column_position: Dict[str, Any],
        price_to_match: Optional[float]
    ) -> Optional[Dict[str, Any]]:
        """
        Search for item in column area WITH PRICE VERIFICATION.

        FIXES BUG 2: Uses price anchoring to verify correct row match.
        """
        normalized_name = self._normalize_hebrew(item_name)
        search_start = min(10, len(raw_lines) - 1)

        best_match = None
        best_confidence = 0

        for idx in range(search_start, len(raw_lines)):
            line = raw_lines[idx]
            if len(line) <= column_position['start']:
                continue

            # Extract from column area (with dynamic boundaries)
            col_start = column_position['start']
            col_end = min(column_position['end'], len(line))
            col_text = line[col_start:col_end].strip()

            if not col_text:
                continue

            normalized_col = self._normalize_hebrew(col_text)

            # Calculate name match score
            name_score = fuzz.token_sort_ratio(normalized_name, normalized_col) / 100.0

            # Calculate price verification score if price available
            price_score = 0.0
            if price_to_match:
                # Try to find price in this line or nearby lines
                price_found = self._find_price_in_context(raw_lines, idx, price_to_match)
                price_score = 0.5 if price_found else 0.0

            # Combined confidence
            confidence = (name_score * 0.7) + (price_score * 0.3)

            if confidence > best_confidence and name_score >= (self.name_match_threshold / 100.0):
                best_confidence = confidence
                best_match = {
                    'row_idx': idx,
                    'row_text': line,
                    'name_score': name_score,
                    'price_score': price_score,
                    'confidence': confidence,
                    'method': 'column_search'
                }

        return best_match

    def _search_item_full_line_with_price(
        self,
        item_name: str,
        raw_lines: List[str],
        price_to_match: Optional[float]
    ) -> Optional[Dict[str, Any]]:
        """
        Search for item in full line with price verification (fallback method).

        Reuses robust logic from old Phase 2.
        """
        normalized_name = self._normalize_hebrew(item_name)

        best_match = None
        best_confidence = 0

        for idx, line in enumerate(raw_lines):
            normalized_line = self._normalize_hebrew(line)

            # Calculate name match score
            name_score = fuzz.token_sort_ratio(normalized_name, normalized_line) / 100.0

            # Price verification
            price_score = 0.0
            if price_to_match:
                price_found = self._find_price_in_context(raw_lines, idx, price_to_match)
                price_score = 0.5 if price_found else 0.0

            # Combined confidence
            confidence = (name_score * 0.7) + (price_score * 0.3)

            if confidence > best_confidence and name_score >= (self.name_match_threshold / 100.0):
                best_confidence = confidence
                best_match = {
                    'row_idx': idx,
                    'row_text': line,
                    'name_score': name_score,
                    'price_score': price_score,
                    'confidence': confidence,
                    'method': 'full_line_search'
                }

        return best_match

    def _find_price_in_context(
        self,
        raw_lines: List[str],
        row_idx: int,
        price_to_match: float
    ) -> bool:
        """Check if price appears in or near the row (within tolerance)."""
        # Check current row and ±2 lines
        for offset in range(-2, 3):
            check_idx = row_idx + offset
            if 0 <= check_idx < len(raw_lines):
                line = raw_lines[check_idx]
                numbers = self._extract_numbers(line)

                for num in numbers:
                    if abs(num - price_to_match) <= self.price_tolerance:
                        return True

        return False

    def _enhance_item_with_column_data(
        self,
        json_item: Dict[str, Any],
        raw_lines: List[str],
        match_result: Dict[str, Any],
        column_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance item with column data and ensure completeness.

        Creates BOTH:
        1. row_cells: Column→value mapping (column context)
        2. extracted_numbers: All numbers from item block (Phase 4 compatibility)
        """
        enhanced_item = json_item.copy()

        row_idx = match_result['row_idx']
        row_text = match_result['row_text']

        # Extract item block (reuse logic from old Phase 2)
        item_block = self._collect_item_block(raw_lines, row_idx)

        # Try to extract row cells if column positions available
        row_cells = {}
        if column_info and column_info.get('success'):
            column_positions = self._get_column_positions(raw_lines, column_info)
            if column_positions:
                row_cells = self._extract_row_cells(row_text, column_positions)

        # Extract ALL numbers from item block (CRITICAL for Phase 4)
        all_numbers = []
        for line in item_block:
            numbers = self._extract_numbers(line)
            all_numbers.extend(numbers)

        # Also extract mapped numeric fields from row_cells
        mapped_numerics = {}
        for hebrew_col, cell_value in row_cells.items():
            numbers = self._extract_numbers(cell_value)
            if numbers:
                mapped_numerics[hebrew_col] = numbers[0]

        enhanced_item.update({
            'segmentation_success': True,
            'segmentation_confidence': match_result.get('confidence', 0),
            'segmentation_method': match_result.get('method', 'unknown'),
            'row_index': row_idx,
            'raw_row_text': row_text,
            'item_block': item_block,
            'row_cells': row_cells,
            'mapped_numerics': mapped_numerics,
            'extracted_numbers': all_numbers,  # MUST HAVE for Phase 4
            'name_match_score': match_result.get('name_score', 0),
            'price_match_score': match_result.get('price_score', 0)
        })

        return enhanced_item

    def _process_item_with_fuzzy_fallback(
        self,
        json_item: Dict[str, Any],
        raw_lines: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Robust fallback: Reuse proven logic from old Phase 2.

        This is the fuzzy matching + price anchoring that works reliably.
        """
        description = json_item.get('description', '').strip()
        if not description:
            return None

        normalized_desc = self._normalize_hebrew(description)

        # Get price anchors
        line_total = json_item.get('line_total')
        unit_price = json_item.get('unit_price')
        price_to_match = line_total if line_total else unit_price

        # Find best matching line (similar to old Phase 2)
        best_match_idx = None
        best_match_score = 0

        for idx, line in enumerate(raw_lines):
            normalized_line = self._normalize_hebrew(line)

            # Calculate match score
            score = fuzz.token_sort_ratio(normalized_desc, normalized_line)

            if score > best_match_score and score >= self.name_match_threshold:
                best_match_score = score
                best_match_idx = idx

        if best_match_idx is None:
            return None

        print(f"  Fuzzy fallback match found at line {best_match_idx+1} (score: {best_match_score})")

        # Collect item block
        item_block = self._collect_item_block(raw_lines, best_match_idx)

        # Extract ALL numbers (CRITICAL for Phase 4)
        all_numbers = []
        for line in item_block:
            numbers = self._extract_numbers(line)
            all_numbers.extend(numbers)

        enhanced_item = json_item.copy()
        enhanced_item.update({
            'segmentation_success': True,
            'segmentation_method': 'fuzzy_fallback',
            'name_match_score': best_match_score,
            'matched_line': raw_lines[best_match_idx],
            'row_index': best_match_idx,
            'item_block': item_block,
            'extracted_numbers': all_numbers,  # MUST HAVE for Phase 4
            'fallback_used': True
        })

        return enhanced_item

    def _ensure_data_completeness(self, item: Dict[str, Any]):
        """Ensure item has ALL required data formats."""
        # Make sure extracted_numbers exists (critical for Phase 4)
        if 'extracted_numbers' not in item:
            item['extracted_numbers'] = []

        # Make sure item_block exists
        if 'item_block' not in item:
            item['item_block'] = []

        # Extract numbers from item_block if not already done
        if not item['extracted_numbers'] and item['item_block']:
            all_numbers = []
            for line in item['item_block']:
                numbers = self._extract_numbers(line)
                all_numbers.extend(numbers)
            item['extracted_numbers'] = all_numbers

    def _get_column_positions(
        self,
        raw_lines: List[str],
        column_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get column positions with dynamic boundaries."""
        detected_columns = column_info.get('detected_columns', [])
        lines_range = column_info.get('lines_range')

        if not lines_range:
            return []

        header_start, header_end = lines_range

        # Get initial positions
        initial_positions = []
        for col_dict in detected_columns:
            initial_pos = self._find_initial_column_position(
                raw_lines, header_start, header_end, col_dict
            )
            if initial_pos:
                initial_positions.append(initial_pos)

        if not initial_positions:
            return []

        # Apply dynamic boundary adjustment to each column
        dynamic_positions = []
        for pos in initial_positions:
            dynamic_pos = self._calculate_dynamic_column_boundaries(
                raw_lines, header_end, pos
            )
            dynamic_positions.append(dynamic_pos)

        # Sort by start position
        dynamic_positions.sort(key=lambda x: x['start'])

        return dynamic_positions

    def _extract_row_cells(
        self,
        row_text: str,
        column_positions: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Extract cell values using column positions."""
        row_cells = {}

        for col_pos in column_positions:
            hebrew_col = col_pos.get('hebrew_text', '')
            if not hebrew_col:
                continue

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

    def _collect_item_block(
        self,
        lines: List[str],
        anchor_line_idx: int,
        max_block_size: int = 10
    ) -> List[str]:
        """
        Collect item block around anchor line.

        Reuses robust logic from old Phase 2.
        """
        block_lines = []
        collected_indices = set()

        # Add anchor line
        if anchor_line_idx < len(lines):
            block_lines.append(lines[anchor_line_idx])
            collected_indices.add(anchor_line_idx)

        # Look for lines above
        lines_above = 1
        consecutive_non_item_lines_above = 0

        for i in range(1, min(5, anchor_line_idx + 1)):
            check_idx = anchor_line_idx - i
            if check_idx < 0 or check_idx in collected_indices:
                break

            line = lines[check_idx]

            if self._is_item_block_line(line):
                block_lines.insert(0, line)
                collected_indices.add(check_idx)
                lines_above += 1
                consecutive_non_item_lines_above = 0
            else:
                if i <= 2:
                    block_lines.insert(0, line)
                    collected_indices.add(check_idx)
                    lines_above += 1
                    consecutive_non_item_lines_above += 1
                else:
                    consecutive_non_item_lines_above += 1

                    if consecutive_non_item_lines_above >= 2:
                        break

        # Look for lines below
        lines_below = 0
        consecutive_non_item_lines = 0

        for i in range(1, max_block_size - lines_above + 1):
            check_idx = anchor_line_idx + i
            if check_idx >= len(lines) or check_idx in collected_indices:
                break

            line = lines[check_idx]

            if self._is_item_block_line(line):
                block_lines.append(line)
                collected_indices.add(check_idx)
                lines_below += 1
                consecutive_non_item_lines = 0
            else:
                if i <= 2:
                    block_lines.append(line)
                    collected_indices.add(check_idx)
                    lines_below += 1
                    consecutive_non_item_lines += 1
                else:
                    consecutive_non_item_lines += 1

                    if consecutive_non_item_lines >= 2:
                        break

        return block_lines

    def _is_item_block_line(self, line: str) -> bool:
        """Check if line belongs to item block."""
        line = line.strip()
        if not line:
            return False

        # Check for numbers
        numbers = self._extract_numbers(line)
        has_numbers = len(numbers) > 0

        # Check for Hebrew
        has_hebrew = bool(re.search(r'[\u0590-\u05FF]', line))

        # Check for product code pattern
        has_product_code = bool(re.search(r'\b\d{12,13}\b', line))

        return has_numbers or has_hebrew or has_product_code

    def _normalize_hebrew(self, text: str) -> str:
        """Normalize Hebrew text for matching."""
        if not text:
            return ""

        # Remove OCR artifacts
        text = re.sub(r'[^\w\u0590-\u05FF\d\s%\.\-]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove common prefixes/suffixes
        prefixes = ['פריט:', 'מוצר:', 'תיאור:', 'תאור:', ':', '-', '•']
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()

        text = text.rstrip('.,;:!?')

        return text

    def _extract_numbers(self, text: str) -> List[float]:
        """Extract all numbers from text."""
        numbers = []
        matches = re.findall(r'[\d,]+\.?\d*', text)
        for match in matches:
            try:
                clean = match.replace(',', '')
                num = float(clean)
                numbers.append(num)
            except ValueError:
                pass
        return numbers

    def _safe_print(self, message: str):
        """Safely print messages that may contain Hebrew characters."""
        try:
            print(message)
        except UnicodeEncodeError:
            print(message.encode('ascii', 'replace').decode('ascii'))


# Test function
def test_phase2_smart_segmentation():
    """Test the smarter Phase 2 segmentation."""
    print("Testing Phase 2 (Smart Column Segmentation)")
    print("=" * 80)

    segmenter = Phase2SmartColumnSegmentation(name_match_threshold=20, price_tolerance=0.05)

    # Sample JSON items
    json_items = [
        {
            "description": "קוטג 5% 250 גרם",
            "quantity": 1.0,
            "unit_price": 4.97,
            "line_total": 4.97
        },
        {
            "description": "חלב 3% 1 ליטר",
            "quantity": 2.0,
            "unit_price": 6.50,
            "line_total": 13.00
        }
    ]

    # Sample raw text with columns
    raw_text = """תנובה
סניף מרכז

תאור פריט   כמות   מחיר יחידה   נטו
קוטג 5% 250 גרם   1   4.97   4.97
חלב 3% 1 ליטר   2   6.50   13.00

סה"כ: 17.97"""

    # Sample column info (mock)
    column_info = {
        'success': True,
        'detected_columns': [
            {'hebrew_text': 'תאור פריט', 'assigned_field': 'description'},
            {'hebrew_text': 'כמות', 'assigned_field': 'quantity'},
            {'hebrew_text': 'מחיר יחידה', 'assigned_field': 'unit_price'},
            {'hebrew_text': 'נטו', 'assigned_field': 'line_net_total'}
        ],
        'column_mapping': {
            'תאור פריט': 'description',
            'כמות': 'quantity',
            'מחיר יחידה': 'unit_price',
            'נטו': 'line_net_total'
        },
        'lines_range': (2, 3),  # Header at line 3
        'detection_score': 0.9
    }

    print("\nTest 1: With column info")
    print("-" * 40)
    result = segmenter.segment_raw_text(json_items, raw_text, column_info)

    print(f"\nSegmented {len(result)} items:")
    for i, item in enumerate(result):
        success = item.get('segmentation_success', False)
        method = item.get('segmentation_method', 'unknown')
        confidence = item.get('segmentation_confidence', 0)
        status = "V" if success else "X"

        print(f"{status} Item {i+1}: {item.get('description', 'N/A')}")
        if success:
            print(f"    Method: {method}, Confidence: {confidence:.2f}")
            print(f"    Extracted numbers: {len(item.get('extracted_numbers', []))} numbers")
            print(f"    Row cells: {len(item.get('row_cells', {}))} columns")

    print("\nTest 2: Without column info (fallback)")
    print("-" * 40)
    result2 = segmenter.segment_raw_text(json_items, raw_text, None)

    print(f"\nSegmented {len(result2)} items (fallback):")
    for i, item in enumerate(result2):
        success = item.get('segmentation_success', False)
        method = item.get('segmentation_method', 'unknown')
        status = "V" if success else "X"

        print(f"{status} Item {i+1}: {item.get('description', 'N/A')}")
        if success:
            print(f"    Method: {method}")
            print(f"    Extracted numbers: {len(item.get('extracted_numbers', []))} numbers")

    print("\n" + "=" * 80)
    print("Test completed!")

    return result


if __name__ == "__main__":
    test_phase2_smart_segmentation()