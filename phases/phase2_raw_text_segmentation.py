"""
OBSOLETE - NOT USED BY MAIN PIPELINE
=====================================
PHASE 2: RAW TEXT SEGMENTATION USING PRICE + NAME ANCHORS

Implements Phase 2 from AGENT_GUIDE.md:

For EACH JSON line item:
1. PRIMARY ANCHOR: Item NAME from JSON (description field)
   - Normalize Hebrew: remove OCR artifacts, keep Hebrew letters/numbers
   - Fuzzy match against raw text lines (token_sort_ratio ≥ 30)

2. SECONDARY ANCHOR: PRICE from JSON (line_total OR unit_price)
   - Use line_total first, fallback to unit_price
   - Float comparison with 0.05 tolerance

3. FIND ITEM BLOCK: Lines around anchor containing:
   - Purely numeric lines (295.22, 298.20, 4.97, 60)
   - Product code + Hebrew (7290011194246 קוטג 5% 250 ג 5)

4. TWO LAYOUT PATTERNS:
   PATTERN A - Multiline:
   295.22        ← numeric line 1
   298.20        ← numeric line 2
   4.97          ← numeric line 3
   60            ← numeric line 4 (QUANTITY)
   7290011194246 קוטג 5% 250 ג 5  ← product code + Hebrew

   PATTERN B - Single line:
   62.02 2.58 14.99 3.04 24 1    ← all values on one line
   7290121290043 קוטג 5% 250 ג    ← product code + Hebrew
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from rapidfuzz import fuzz


class Phase2RawTextSegmentation:
    """
    Phase 2: Raw text segmentation using price + name anchors.

    Uses JSON item names as primary anchors to find corresponding
    regions in raw text.
    """

    def __init__(self, name_match_threshold: int = 20, price_tolerance: float = 0.05):
        """
        Args:
            name_match_threshold: Minimum fuzzy match score (0-100) for name matching
            price_tolerance: Tolerance for price comparison
        """
        self.name_match_threshold = name_match_threshold
        self.price_tolerance = price_tolerance

    def _safe_print(self, message: str):
        """Safely print messages that may contain Hebrew characters."""
        try:
            print(message)
        except UnicodeEncodeError:
            # Fall back to ASCII-safe representation
            print(message.encode('ascii', 'replace').decode('ascii'))

    def segment_raw_text_by_prices(
        self,
        json_items: List[Dict[str, Any]],
        raw_text: str
    ) -> List[Dict[str, Any]]:
        """
        Main entry point: Segment raw text using JSON item names and prices as anchors.

        Args:
            json_items: Items from JSON scan with description, quantity, unit_price, line_total
            raw_text: Full text from raw text scan

        Returns:
            List of enhanced items with raw text context
        """
        if not json_items or not raw_text:
            print("No JSON items or raw text to segment")
            return []

        raw_lines = raw_text.splitlines()
        print(f"Phase 2: Segmenting {len(json_items)} JSON items against {len(raw_lines)} raw text lines")

        segmented_items = []

        for i, json_item in enumerate(json_items):
            print(f"\nProcessing item {i+1}/{len(json_items)}")

            enhanced_item = self._find_item_block_enhanced(json_item, raw_lines)
            if enhanced_item:
                segmented_items.append(enhanced_item)
            else:
                # Keep original JSON item if no match found
                json_item['segmentation_success'] = False
                segmented_items.append(json_item)

        print(f"\nPhase 2 complete: Successfully segmented {len([i for i in segmented_items if i.get('segmentation_success', False)])}/{len(json_items)} items")
        return segmented_items

    def _find_item_block_enhanced(
        self,
        json_item: Dict[str, Any],
        raw_lines: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Enhanced item block finder using BOTH name + price anchors.

        Args:
            json_item: JSON item with description, prices
            raw_lines: List of raw text lines

        Returns:
            Enhanced item with raw text context, or None if no match found
        """
        description = json_item.get('description', '').strip()
        if not description:
            print("  No description in JSON item, skipping")
            return None

        # Normalize Hebrew description
        normalized_desc = self._normalize_hebrew(description)
        self._safe_print(f"  Looking for: '{normalized_desc[:50]}...'")

        # Get price anchors
        line_total = json_item.get('line_total')
        unit_price = json_item.get('unit_price')
        price_to_match = line_total if line_total else unit_price

        # 1. Find best matching line using name anchor
        best_line_idx, name_score = self._calculate_name_match_score(normalized_desc, raw_lines)

        # DYNAMIC THRESHOLD: Lower threshold for short queries
        query_words = len(normalized_desc.split())
        dynamic_threshold = self.name_match_threshold

        if query_words < 3:
            # Very short queries (1-2 words) need lower threshold
            dynamic_threshold = max(15, self.name_match_threshold - 5)  # Min 15
            print(f"  Short query ({query_words} words), using dynamic threshold: {dynamic_threshold}")

        if best_line_idx is None or name_score < dynamic_threshold:
            print(f"  X No good name match (score: {name_score}, threshold: {dynamic_threshold})")
            return None

        print(f"  V Name match found at line {best_line_idx+1} (score: {name_score})")

        # 3. Collect item block around anchor
        item_block = self._collect_item_block(raw_lines, best_line_idx)
        print(f"  Collected block of {len(item_block)} lines")

        # 4. Analyze block pattern
        block_pattern = self._analyze_block_pattern(item_block)
        print(f"  Block pattern: {block_pattern}")

        # Create enhanced item
        enhanced_item = json_item.copy()
        enhanced_item.update({
            'segmentation_success': True,
            'name_match_score': name_score,
            'matched_line': raw_lines[best_line_idx] if best_line_idx < len(raw_lines) else '',
            'item_block': item_block,
            'block_pattern': block_pattern,
            'raw_lines_around': self._get_lines_around(raw_lines, best_line_idx, context_lines=3)
        })

        # Extract additional data from block
        self._extract_data_from_block(enhanced_item, item_block)

        return enhanced_item

    def _normalize_hebrew(self, text: str) -> str:
        """
        Normalize Hebrew text for better matching.

        Removes OCR artifacts, extra spaces, and common variations.
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

    def _calculate_name_match_score(
        self,
        query: str,
        lines: List[str],
        max_lines_to_search: int = 50
    ) -> Tuple[Optional[int], float]:
        """
        Calculate best name match score using fuzzy matching.

        Args:
            query: Normalized query text
            lines: List of text lines
            max_lines_to_search: Limit search to first N lines

        Returns:
            Tuple of (line_index, match_score) or (None, 0) if no match
        """
        if not query or not lines:
            return None, 0

        search_lines = lines[:max_lines_to_search]

        best_idx = None
        best_score = 0

        for idx, line in enumerate(search_lines):
            if not line.strip():
                continue

            normalized_line = self._normalize_hebrew(line)

            # HYBRID MATCHING ALGORITHM
            # For short queries (<3 words), use partial matching
            # For longer queries, use token_set_ratio
            query_words = len(query.split())

            if query_words < 3:
                # Short query: use best of token_set and weighted partial
                token_set_score = fuzz.token_set_ratio(query, normalized_line)
                partial_score = fuzz.partial_ratio(query, normalized_line)
                # partial_ratio can be too generous, weight it down
                score = max(token_set_score, partial_score * 0.8)
            else:
                # Longer query: use token_set_ratio (good for OCR variations)
                score = fuzz.token_set_ratio(query, normalized_line)

            if score > best_score:
                best_score = score
                best_idx = idx

        return best_idx, best_score

    
    def _collect_item_block(
        self,
        lines: List[str],
        anchor_line_idx: int,
        max_block_size: int = 10
    ) -> List[str]:
        """
        Collect item block around anchor line.

        Args:
            lines: All lines
            anchor_line_idx: Index of anchor line
            max_block_size: Maximum lines in block

        Returns:
            List of lines in the item block
        """
        # Start from anchor line and collect lines that look like part of item
        block_lines = []
        collected_indices = set()

        # First, add the anchor line
        if anchor_line_idx < len(lines):
            block_lines.append(lines[anchor_line_idx])
            collected_indices.add(anchor_line_idx)

        # Look for lines above (collect up to 4 lines above, be selective)
        lines_above = 1
        consecutive_non_item_lines_above = 0

        for i in range(1, min(5, anchor_line_idx + 1)):  # Collect up to 4 lines above
            check_idx = anchor_line_idx - i
            if check_idx < 0 or check_idx in collected_indices:
                break

            line = lines[check_idx]

            # STRATEGY: Collect lines that are likely part of item
            if self._is_item_block_line(line):
                block_lines.insert(0, line)  # Add to beginning (preserve order)
                collected_indices.add(check_idx)
                lines_above += 1
                consecutive_non_item_lines_above = 0  # Reset counter
            else:
                # For lines 1-2 above anchor, still collect (might be spacing)
                if i <= 2:
                    block_lines.insert(0, line)
                    collected_indices.add(check_idx)
                    lines_above += 1
                    consecutive_non_item_lines_above += 1
                else:
                    consecutive_non_item_lines_above += 1

                    # Stop if we hit 2 consecutive non-item lines
                    if consecutive_non_item_lines_above >= 2:
                        break

        # Look for lines below (collect up to 4 lines below, but be smarter)
        lines_below = 0
        consecutive_non_item_lines = 0

        for i in range(1, max_block_size - lines_above + 1):
            check_idx = anchor_line_idx + i
            if check_idx >= len(lines) or check_idx in collected_indices:
                break

            line = lines[check_idx]

            # STRATEGY: Collect lines that are likely part of item
            if self._is_item_block_line(line):
                block_lines.append(line)
                collected_indices.add(check_idx)
                lines_below += 1
                consecutive_non_item_lines = 0  # Reset counter
            else:
                # For lines 1-2 below anchor, still collect (might be spacing)
                if i <= 2:
                    block_lines.append(line)
                    collected_indices.add(check_idx)
                    lines_below += 1
                    consecutive_non_item_lines += 1
                else:
                    consecutive_non_item_lines += 1

                    # Stop if we hit 2 consecutive non-item lines
                    if consecutive_non_item_lines >= 2:
                        break

        return block_lines

    def _is_item_block_line(self, line: str) -> bool:
        """
        Identify numeric/Hebrew lines that belong to item block.

        Returns True for:
        - Purely numeric lines (295.22, 298.20, 4.97, 60)
        - Lines with numbers (even with currency symbols ₪ $ €)
        - Product code + Hebrew (7290011194246 קוטג 5% 250 ג 5)
        - Lines with mixed Hebrew and numbers
        - Hebrew product descriptions (for context)
        """
        line = line.strip()
        if not line:
            return False

        # IMPROVED: Check for lines with numbers (including currency symbols)
        # Extract all numbers from the line
        numbers = self._extract_numbers(line)
        has_numbers = len(numbers) > 0

        # Check for purely or mostly numeric line (handles currency symbols)
        # Remove spaces and common non-numeric characters first
        cleaned = line.replace(' ', '').replace(',', '')
        # Remove common currency symbols and units
        cleaned = re.sub(r'[₪$€£יחידותגרםקלגמ\'\"״]', '', cleaned)

        if re.match(r'^[\d\.]+$', cleaned) and has_numbers:
            return True

        # Check for product code pattern (12-13 digits plus optional Hebrew)
        if re.search(r'\b\d{12,13}\b', line):
            return True

        # Check for Hebrew (product descriptions)
        has_hebrew = bool(re.search(r'[\u0590-\u05FF]', line))

        # Return True for:
        # 1. Any line with numbers (price, quantity, etc.)
        # 2. Hebrew lines (product descriptions, even without numbers for context)
        # 3. Product codes
        return has_numbers or has_hebrew

    def _analyze_block_pattern(self, block_lines: List[str]) -> str:
        """
        Analyze block pattern (Multiline vs Single line).

        Returns:
            'multiline', 'single_line', or 'unknown'
        """
        if not block_lines:
            return 'unknown'

        # Count different types of lines
        numeric_line_count = 0
        hebrew_with_numbers_count = 0
        total_numbers_in_block = 0
        lines_with_numbers_count = 0

        for line in block_lines:
            # Extract numbers from this line
            numbers_in_line = self._extract_numbers(line)
            has_numbers = len(numbers_in_line) > 0
            total_numbers_in_block += len(numbers_in_line)

            if has_numbers:
                lines_with_numbers_count += 1

            # IMPROVED: Check for "mostly numeric" line (handles currency symbols)
            # Remove common currency symbols and units before checking
            cleaned = line.replace(' ', '').replace(',', '')
            # Remove common currency symbols: ₪, $, €, £
            cleaned = re.sub(r'[₪$€£]', '', cleaned)
            # Remove common unit abbreviations
            cleaned = re.sub(r'[יחידותגרםקלגמ\'\"״]', '', cleaned)

            if re.match(r'^[\d\.]+$', cleaned) and has_numbers:
                numeric_line_count += 1

            # Check for Hebrew with numbers (product description)
            if re.search(r'[\u0590-\u05FF]', line) and has_numbers:
                hebrew_with_numbers_count += 1

        # DEBUG: Print analysis for troubleshooting
        debug_info = f"Pattern analysis: lines={len(block_lines)}, numeric={numeric_line_count}, hebrew+nums={hebrew_with_numbers_count}, lines_with_nums={lines_with_numbers_count}, total_nums={total_numbers_in_block}"
        if len(block_lines) <= 8:  # Only debug for reasonable-sized blocks
            self._safe_print(f"  DEBUG: {debug_info}")

        # ENHANCED PATTERN DETECTION:

        # 1. MULTILINE: Multiple lines with numbers (more flexible)
        if lines_with_numbers_count >= 2:
            self._safe_print(f"  Pattern: multiline (lines_with_numbers_count >= 2)")
            return 'multiline'

        # 2. SINGLE_LINE: One line with multiple numbers (at least 3)
        if len(block_lines) == 1:
            line = block_lines[0]
            numbers = self._extract_numbers(line)
            if len(numbers) >= 3:  # At least 3 numbers on one line
                self._safe_print(f"  Pattern: single_line (single line with >= 3 numbers)")
                return 'single_line'

        # 3. SINGLE_LINE: Few lines but lots of numbers total
        if total_numbers_in_block >= 3:  # Reduced from 4 to 3
            self._safe_print(f"  Pattern: single_line (total_numbers_in_block >= 3)")
            return 'single_line'

        # 4. FALLBACK: If we have at least 2 numbers somewhere, assume single_line
        if total_numbers_in_block >= 2:
            self._safe_print(f"  Pattern: single_line (fallback: total_numbers >= 2)")
            return 'single_line'

        self._safe_print(f"  Pattern: unknown (insufficient data)")
        return 'unknown'

    def _get_lines_around(
        self,
        lines: List[str],
        center_idx: int,
        context_lines: int = 3
    ) -> List[str]:
        """Get lines around center index for context."""
        start = max(0, center_idx - context_lines)
        end = min(len(lines), center_idx + context_lines + 1)
        return lines[start:end]

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

    def _extract_data_from_block(self, item: Dict[str, Any], block_lines: List[str]):
        """Extract additional data from item block."""
        all_numbers = []
        barcode = None

        for line in block_lines:
            # Extract numbers
            numbers = self._extract_numbers(line)
            all_numbers.extend(numbers)

            # Look for barcode
            if not barcode:
                barcode_match = re.search(r'\b(\d{12,13})\b', line)
                if barcode_match:
                    barcode = barcode_match.group(1)

        # Store extracted data
        if all_numbers:
            item['extracted_numbers'] = all_numbers

        if barcode:
            item['barcode'] = barcode

        # Try to identify quantity from numbers
        if 'quantity' not in item or item['quantity'] <= 0:
            # Look for small integers (likely quantities)
            small_ints = [n for n in all_numbers if n == int(n) and 1 <= n <= 100]
            if small_ints:
                item['estimated_quantity'] = small_ints[0]


# Test function
def test_phase2_segmentation():
    """Test Phase 2 segmentation."""
    print("Testing Phase 2: Raw Text Segmentation")
    print("=" * 60)

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

    # Sample raw text
    raw_text = """תנובה
סניף: מרכז
קופה: 5

קוטג 5% 250 גרם
4.97

חלב 3% 1 ליטר
6.50
13.00

סה"כ: 17.97"""

    print("Sample JSON items:", len(json_items))
    print("Raw text length:", len(raw_text), "chars")

    segmenter = Phase2RawTextSegmentation()
    segmented = segmenter.segment_raw_text_by_prices(json_items, raw_text)

    print(f"\nSegmented {len(segmented)} items:")
    for i, item in enumerate(segmented):
        success = item.get('segmentation_success', False)
        status = "V" if success else "X"
        print(f"{status} Item {i+1}: {item.get('description', 'N/A')}")
        if success:
            print(f"    Match score: {item.get('name_match_score', 0)}")
            print(f"    Block lines: {len(item.get('item_block', []))}")

    return segmented


if __name__ == "__main__":
    test_phase2_segmentation()