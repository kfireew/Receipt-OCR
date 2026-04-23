"""
OBSOLETE - NOT USED BY MAIN PIPELINE
=====================================
Phase 4: Implement row reconstruction using JSON names as anchors.

KEY RULE: Use JSON item names as the anchor points.
Do not start by searching for barcode patterns.
Do not start by inventing name heuristics.
Do not start by trying to match every possible number pattern.

Instead:
1. Read the JSON scan.
2. Extract the item names that Mindee already identified.
3. Use those names as the main anchors for row alignment in the raw text.
4. Use the raw text only to confirm, refine, or recover details around those anchors.
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from rapidfuzz import fuzz, process


class JsonAnchorReconstructor:
    """
    Reconstruct receipt rows using JSON item names as anchors.

    Logic:
    - Take each item name from the JSON scan
    - Find the corresponding region in the raw text
    - Use that name as the anchor for the item row
    - Once the row is anchored, collect nearby numeric fields and related tokens
    - Confirm row structure using spacing, line layout, and local context
    """

    def __init__(self, fuzzy_threshold: int = 30):
        """
        Args:
            fuzzy_threshold: Minimum fuzzy match score (0-100) for name matching
        """
        self.fuzzy_threshold = fuzzy_threshold

    def reconstruct_rows_from_json_anchors(
        self,
        json_items: List[Dict[str, Any]],
        raw_text: str
    ) -> List[Dict[str, Any]]:
        """
        Reconstruct rows by anchoring to JSON item names.

        Args:
            json_items: Items from JSON scan with 'description' field
            raw_text: Full text from raw text scan

        Returns:
            List of reconstructed items with enhanced data from raw text
        """
        if not json_items or not raw_text:
            return []

        # Split raw text into lines
        raw_lines = raw_text.splitlines()
        print(f"Processing {len(json_items)} JSON items against {len(raw_lines)} raw text lines")

        reconstructed_items = []

        for i, json_item in enumerate(json_items):
            description = json_item.get('description', '').strip()
            if not description:
                print(f"  Item {i+1}: No description, skipping")
                continue

            # Normalize Hebrew description for matching
            normalized_desc = self._normalize_hebrew(description)
            print(f"  Item {i+1}: Looking for '{normalized_desc[:50]}...'")

            # Find best matching line in raw text
            matched_line_idx, match_score = self._find_best_matching_line(
                normalized_desc, raw_lines
            )

            if matched_line_idx is None or match_score < self.fuzzy_threshold:
                print(f"    ✗ No good match found (score: {match_score})")
                # Keep JSON item as-is if no good match
                reconstructed_items.append(json_item.copy())
                continue

            print(f"    ✓ Matched line {matched_line_idx+1} (score: {match_score})")

            # Get the matched line and surrounding context
            matched_line = raw_lines[matched_line_idx]

            # Collect block of lines around match
            item_block = self._collect_item_block(raw_lines, matched_line_idx)
            print(f"    Collected block of {len(item_block)} lines around match")

            # Extract enhanced data from block
            enhanced_item = self._enhance_item_from_block(
                json_item, matched_line, item_block
            )

            reconstructed_items.append(enhanced_item)

        print(f"\nReconstructed {len(reconstructed_items)} items using JSON anchors")
        return reconstructed_items

    def _normalize_hebrew(self, text: str) -> str:
        """
        Normalize Hebrew text for better matching.

        Removes OCR artifacts, extra spaces, and common variations.
        """
        if not text:
            return ""

        # Remove common OCR artifacts and special characters
        text = re.sub(r'[^\w\u0590-\u05FF\d\s%\.\-]', ' ', text)

        # Normalize Hebrew letters (remove diacritics if present)
        # Simple normalization: keep only Hebrew letters and numbers
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove common prefixes/suffixes
        prefixes = ['פריט:', 'מוצר:', 'תיאור:', 'תאור:']
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()

        return text

    def _find_best_matching_line(
        self,
        query: str,
        lines: List[str],
        max_lines_to_search: int = 50
    ) -> Tuple[Optional[int], float]:
        """
        Find the best matching line for a query using fuzzy matching.

        Args:
            query: Text to search for
            lines: List of text lines
            max_lines_to_search: Limit search to first N lines (receipts are top-heavy)

        Returns:
            Tuple of (line_index, match_score) or (None, 0) if no match
        """
        if not query or not lines:
            return None, 0

        # Limit search to first part of receipt (where items usually are)
        search_lines = lines[:max_lines_to_search]

        best_idx = None
        best_score = 0

        for idx, line in enumerate(search_lines):
            if not line.strip():
                continue

            normalized_line = self._normalize_hebrew(line)

            # Use token sort ratio (order doesn't matter)
            score = fuzz.token_sort_ratio(query, normalized_line)

            if score > best_score:
                best_score = score
                best_idx = idx

        return best_idx, best_score

    def _collect_item_block(
        self,
        lines: List[str],
        anchor_idx: int,
        lines_before: int = 3,
        lines_after: int = 3
    ) -> List[str]:
        """
        Collect a block of lines around an anchor line.

        Args:
            lines: All lines
            anchor_idx: Index of anchor line
            lines_before: Lines to include before anchor
            lines_after: Lines to include after anchor

        Returns:
            List of lines in the block
        """
        start = max(0, anchor_idx - lines_before)
        end = min(len(lines), anchor_idx + lines_after + 1)

        block_lines = []
        for i in range(start, end):
            line = lines[i].strip()
            if line:  # Skip empty lines
                block_lines.append(line)

        return block_lines

    def _enhance_item_from_block(
        self,
        json_item: Dict[str, Any],
        anchor_line: str,
        item_block: List[str]
    ) -> Dict[str, Any]:
        """
        Enhance JSON item with data from raw text block.

        Args:
            json_item: Original item from JSON scan
            anchor_line: The line that matched the item name
            item_block: Block of lines around anchor

        Returns:
            Enhanced item dictionary
        """
        enhanced = json_item.copy()

        # Extract all numbers from the block
        all_numbers = []
        for line in item_block:
            numbers_in_line = self._extract_numbers(line)
            for num in numbers_in_line:
                all_numbers.append(num)

        # Sort numbers for analysis
        all_numbers.sort()

        if all_numbers:
            print(f"    Found {len(all_numbers)} numbers in block: {all_numbers[:5]}...")

            # Try to identify quantities, prices, totals from number patterns
            numeric_data = self._analyze_number_patterns(all_numbers)

            # Update item with numeric data if found
            if numeric_data.get('line_total'):
                enhanced['line_total'] = numeric_data['line_total']
                print(f"    Updated line_total: {numeric_data['line_total']}")

            if numeric_data.get('unit_price'):
                enhanced['unit_price'] = numeric_data['unit_price']
                print(f"    Updated unit_price: {numeric_data['unit_price']}")

            if numeric_data.get('quantity'):
                enhanced['quantity'] = numeric_data['quantity']
                print(f"    Updated quantity: {numeric_data['quantity']}")

            # Add raw text context
            enhanced['raw_text_context'] = ' | '.join(item_block)
            enhanced['anchor_line'] = anchor_line

        return enhanced

    def _extract_numbers(self, text: str) -> List[float]:
        """Extract all numbers from text."""
        numbers = []
        # Match numbers with optional commas and decimal points
        matches = re.findall(r'[\d,]+\.?\d*', text)
        for match in matches:
            try:
                # Remove commas (thousand separators)
                clean = match.replace(',', '')
                num = float(clean)
                numbers.append(num)
            except ValueError:
                pass
        return numbers

    def _analyze_number_patterns(self, numbers: List[float]) -> Dict[str, float]:
        """
        Analyze number patterns to identify quantities, prices, totals.

        Basic heuristics for receipt numbers:
        - Largest number is often line total
        - Medium numbers are often unit prices
        - Small integers are often quantities
        - Numbers that look like barcodes (12-13 digits) are product codes
        """
        if not numbers:
            return {}

        result = {}

        # Sort numbers
        sorted_nums = sorted(numbers)

        # Heuristic 1: Largest reasonable number is likely line total
        # Filter out barcode-like numbers (very large counts)
        non_barcode_nums = [n for n in sorted_nums if n < 10000]  # Line totals < 10,000
        if non_barcode_nums:
            result['line_total'] = non_barcode_nums[-1]  # Largest non-barcode

        # Heuristic 2: Look for unit price (typically between 1 and 500)
        price_candidates = [n for n in sorted_nums if 1 <= n <= 500]
        if price_candidates:
            # Take a middle value (not smallest, not largest)
            idx = len(price_candidates) // 2
            result['unit_price'] = price_candidates[idx]

        # Heuristic 3: Look for quantity (small integer, typically 1-100)
        int_candidates = [n for n in sorted_nums if n == int(n) and 1 <= n <= 100]
        if int_candidates:
            # Often the smallest integer
            result['quantity'] = int_candidates[0]

        # Heuristic 4: If we have line_total and unit_price, calculate quantity
        if 'line_total' in result and 'unit_price' in result:
            if result['unit_price'] > 0:
                calculated_qty = result['line_total'] / result['unit_price']
                # Check if calculated quantity is reasonable
                if 0.1 <= calculated_qty <= 1000:
                    result['calculated_quantity'] = calculated_qty

        return result

    def _extract_barcode_from_block(self, item_block: List[str]) -> Optional[str]:
        """
        Extract barcode from item block if present.

        Looks for 12-13 digit sequences (standard barcodes).
        """
        for line in item_block:
            # Look for sequences of 12-13 digits
            matches = re.findall(r'\b\d{12,13}\b', line)
            if matches:
                return matches[0]

            # Also look for sequences with spaces/dashes
            matches = re.findall(r'\b\d[\d\s\-]{10,15}\d\b', line.replace(' ', '').replace('-', ''))
            if matches and len(matches[0].replace(' ', '').replace('-', '')) in [12, 13]:
                return matches[0].replace(' ', '').replace('-', '')

        return None


def test_json_anchor_reconstruction():
    """Test Phase 4 functionality with sample data."""
    print("Testing JSON Anchor Reconstruction (Phase 4)")
    print("=" * 60)

    # Sample JSON items (simulating Mindee output)
    sample_json_items = [
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
        },
        {
            "description": "לחם מחיטה מלאה",
            "quantity": 1.0,
            "unit_price": 8.90,
            "line_total": 8.90
        }
    ]

    # Sample raw text (simulating raw OCR output)
    sample_raw_text = """תנובה
    קופה: 5
    תאריך: 23.03.2025

    1. קוטג 5% 250 גרם
       4.97

    2. חלב 3% 1 ליטר
       6.50
       13.00

    3. לחם מחיטה מלאה
       8.90

    סה"כ: 26.87"""

    reconstructor = JsonAnchorReconstructor(fuzzy_threshold=30)

    print(f"Sample JSON items: {len(sample_json_items)}")
    print(f"Sample raw text length: {len(sample_raw_text)} chars")
    print()

    reconstructed = reconstructor.reconstruct_rows_from_json_anchors(
        sample_json_items, sample_raw_text
    )

    print("\n" + "="*60)
    print("Reconstruction Results:")
    print("="*60)

    for i, item in enumerate(reconstructed):
        print(f"\nItem {i+1}:")
        print(f"  Description: {item.get('description', '')}")
        print(f"  Quantity: {item.get('quantity', 'N/A')}")
        print(f"  Unit Price: {item.get('unit_price', 'N/A')}")
        print(f"  Line Total: {item.get('line_total', 'N/A')}")
        if 'raw_text_context' in item:
            context = item['raw_text_context'][:80] + "..." if len(item['raw_text_context']) > 80 else item['raw_text_context']
            print(f"  Context: {context}")

    print(f"\nTotal items reconstructed: {len(reconstructed)}")
    return reconstructed


if __name__ == "__main__":
    test_json_anchor_reconstruction()