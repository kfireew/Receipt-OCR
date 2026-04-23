#!/usr/bin/env python3
"""
PHASE 4: QUANTITY PATTERN DETECTION

Implements Phase 4 from AGENT_GUIDE.md:

THREE QUANTITY PATTERNS - Detect by checking ≥3 items:

PATTERN 1: SINGLE QUANTITY COLUMN
- One number is the quantity
- Take it directly
- Example: Quantity column shows "2"

PATTERN 2: TWO COLUMNS (UNITS-PER-BOX × BOX-COUNT)
- Column A: Units per box (e.g., 24)
- Column B: Number of boxes (e.g., 2)
- Real quantity = A × B = 48
- Both are typically small integers (≤100)

PATTERN 3: THREE COLUMNS (COL1 × COL2 = COL3)
- Column A: Units per box
- Column B: Box count
- Column C: Total quantity (A × B)
- Use Column C directly
- Verify: abs(A × B - C) < 0.1 tolerance

WEIGHT-BASED ITEMS SPECIAL CASE:
- Decimal quantities: 1.350, 0.750, 2.100
- DO NOT apply multiplication logic
- Detect: quantity candidate is non-integer decimal
- Range check: 0.1 ≤ quantity ≤ 20.0 kg
"""

import sys
import math
from typing import List, Dict, Any, Tuple, Optional

# Fix Windows console encoding for Hebrew text
if sys.platform == 'win32':
    try:
        # Python 3.7+ - reconfigure stdout/stderr
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Older Python - use codecs
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)


class Phase4QuantityPattern:
    """
    Phase 4: Quantity pattern detection.

    Detects quantity calculation patterns across multiple items
    and handles weight-based items specially.
    """

    def __init__(self, tolerance: float = 0.1):
        """
        Args:
            tolerance: Tolerance for multiplication verification
        """
        self.tolerance = tolerance

    def detect_quantity_pattern(
        self,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check all 3 quantity patterns across items.

        PATTERN DETECTION ORDER:
        1. Weight-based items (decimal quantities 0.1-20.0 kg)
        2. Pattern 1: Single quantity column
        3. Pattern 2: Two columns (units-per-box × box-count)
        4. Pattern 3: Three columns (A × B = C)

        DEFAULT BEHAVIOR (per TODO.md):
        - If <3 items or <3 items with numbers → return pattern 1 as default
        - extract_quantity_from_block() will use smallest integer as quantity

        Args:
            items: List of items with numeric data extracted

        Returns:
            Dictionary with detected pattern information
        """
        if len(items) < 3:
            print(f"Phase 4: Need at least 3 items for pattern detection, got {len(items)}")
            # PER TODO.md: Return pattern 1 as default when insufficient data
            return {
                'success': False,
                'pattern': 1,  # Changed from 'unknown' to 1 per TODO.md
                'reason': 'Need at least 3 items'
            }

        print(f"Phase 4: Analyzing quantity patterns across {len(items)} items")

        # Extract number arrays from items
        all_number_arrays = []
        for i, item in enumerate(items):
            numbers = item.get('extracted_numbers', [])
            if numbers:
                all_number_arrays.append((i, numbers))

        if len(all_number_arrays) < 3:
            print(f"  Only {len(all_number_arrays)} items have extracted numbers")
            # PER TODO.md: Return pattern 1 as default when insufficient data
            return {
                'success': False,
                'pattern': 1,  # Changed from 'unknown' to 1 per TODO.md
                'reason': 'Not enough items with numbers'
            }

        # Check for weight-based items first
        weight_items = self._detect_weight_items(items)
        if weight_items:
            print(f"  Detected {len(weight_items)} weight-based items")
            return {
                'success': True,
                'pattern': 'weight_based',
                'weight_items': weight_items,
                'message': 'Weight-based items detected (decimal quantities)'
            }

        # Try to detect patterns
        print("  Checking for quantity patterns...")

        # Pattern 1: Single quantity column
        pattern1_result = self._check_pattern1_single_column(items, all_number_arrays)
        if pattern1_result['success']:
            print(f"  ✓ Pattern 1 detected: Single quantity column")
            return pattern1_result

        # Pattern 2: Two columns (units-per-box × box-count)
        pattern2_result = self._check_pattern2_two_columns(items, all_number_arrays)
        if pattern2_result['success']:
            print(f"  ✓ Pattern 2 detected: Two columns (A × B)")
            return pattern2_result

        # Pattern 3: Three columns (A × B = C)
        pattern3_result = self._check_pattern3_three_columns(items, all_number_arrays)
        if pattern3_result['success']:
            print(f"  ✓ Pattern 3 detected: Three columns (A × B = C)")
            return pattern3_result

        print(f"  ✗ No quantity pattern detected")
        return {
            'success': False,
            'pattern': 'unknown',
            'reason': 'No pattern matched'
        }

    def _detect_weight_items(
        self,
        items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Identify decimal quantities for weight-based items.

        Args:
            items: List of items

        Returns:
            List of items identified as weight-based
        """
        weight_items = []

        for item in items:
            quantity = item.get('quantity')
            estimated_qty = item.get('estimated_quantity')

            # Check if quantity is a decimal
            qty_to_check = quantity if quantity else estimated_qty

            if qty_to_check and isinstance(qty_to_check, (int, float)):
                # Check if decimal (not integer)
                if not self._is_integer(qty_to_check):
                    # Check range (0.1 to 20.0 kg)
                    if 0.1 <= qty_to_check <= 20.0:
                        weight_items.append(item)

        return weight_items

    def _check_pattern1_single_column(
        self,
        items: List[Dict[str, Any]],
        number_arrays: List[Tuple[int, List[float]]]
    ) -> Dict[str, Any]:
        """
        Check for Pattern 1: Single quantity column.

        PATTERN LOGIC:
        - Each receipt item has a single quantity column
        - Quantity appears as a small integer (1-1000) in extracted_numbers
        - Different items have different quantities (e.g., 2 milk, 1 bread)
        - Quantities do NOT need to be similar across items (FIXED from original)

        DETECTION METHOD:
        1. For each item, find small integers (1-1000) in extracted_numbers
        2. If item has at least one small integer, take smallest as candidate
        3. If ≥70% of items have candidates, detect as Pattern 1

        EXAMPLE:
        Item 1: [295.22, 298.20, 4.97, 60] → candidate: 60
        Item 2: [150.00, 155.00, 5.50, 24] → candidate: 24
        Item 3: [200.00, 205.00, 6.75, 36] → candidate: 36
        Result: Pattern 1 detected (quantities: 60, 24, 36)
        """
        candidate_quantities = []

        for item_idx, numbers in number_arrays:
            # Look for small integers (likely quantities)
            small_ints = [n for n in numbers if self._is_integer(n) and 1 <= n <= 1000]  # Increased range

            if small_ints:
                # Take the smallest small integer (often quantity)
                candidate = min(small_ints)
                candidate_quantities.append((item_idx, candidate, small_ints))
            else:
                # No small integers in this item
                return {'success': False}

        if len(candidate_quantities) < 3:
            return {'success': False}

        # FIXED: Don't require quantities to be similar!
        # Different items have different quantities (2 milk, 1 bread, etc.)
        # Check that we found candidate quantities in all items
        quantities = [q for _, q, _ in candidate_quantities]
        success_rate = len(candidate_quantities) / len(number_arrays)

        # If we found candidates in most items, it's Pattern 1
        if success_rate >= 0.7:  # At least 70% of items have quantity candidates
            pattern_indices = self._analyze_pattern_indices(number_arrays, 'pattern1')

            return {
                'success': True,
                'pattern': 'pattern1',
                'description': 'Single quantity column',
                'quantities': quantities,
                'pattern_indices': pattern_indices,
                'success_rate': success_rate,
                'confidence': min(0.9, success_rate)
            }

        return {'success': False}

    def _check_pattern2_two_columns(
        self,
        items: List[Dict[str, Any]],
        number_arrays: List[Tuple[int, List[float]]]
    ) -> Dict[str, Any]:
        """
        Check for Pattern 2: Two columns (units-per-box × box-count).

        Looks for pairs of small integers whose product is reasonable.
        """
        valid_pairs = []

        for item_idx, numbers in number_arrays:
            # Need at least 2 numbers
            if len(numbers) < 2:
                continue

            # Look for pairs of small integers
            small_ints = [n for n in numbers if self._is_integer(n) and 1 <= n <= 100]

            if len(small_ints) >= 2:
                # Try all pairs
                for i in range(len(small_ints)):
                    for j in range(i + 1, len(small_ints)):
                        a, b = small_ints[i], small_ints[j]
                        product = a * b

                        # Product should be reasonable (not too large)
                        if 1 <= product <= 1000:
                            valid_pairs.append((item_idx, a, b, product))

        if len(valid_pairs) < 3:
            return {'success': False}

        # Check if pairs follow consistent pattern
        # For example, all have similar 'a' values (units per box)
        a_values = [a for _, a, _, _ in valid_pairs]
        b_values = [b for _, _, b, _ in valid_pairs]

        if self._are_values_similar(a_values) or self._are_values_similar(b_values):
            pattern_indices = self._analyze_pattern_indices(number_arrays, 'pattern2')

            return {
                'success': True,
                'pattern': 'pattern2',
                'description': 'Two columns (units-per-box × box-count)',
                'pairs': valid_pairs,
                'pattern_indices': pattern_indices,
                'confidence': self._calculate_confidence(a_values + b_values) * 0.8
            }

        return {'success': False}

    def _check_pattern3_three_columns(
        self,
        items: List[Dict[str, Any]],
        number_arrays: List[Tuple[int, List[float]]]
    ) -> Dict[str, Any]:
        """
        Check for Pattern 3: Three columns (A × B = C).

        Looks for three numbers where A × B ≈ C.
        """
        valid_triples = []

        for item_idx, numbers in number_arrays:
            # Need at least 3 numbers
            if len(numbers) < 3:
                continue

            # Look for small integers
            small_ints = [n for n in numbers if self._is_integer(n) and 1 <= n <= 100]

            if len(small_ints) >= 3:
                # Try all triples
                for i in range(len(small_ints)):
                    for j in range(i + 1, len(small_ints)):
                        for k in range(j + 1, len(small_ints)):
                            a, b, c = small_ints[i], small_ints[j], small_ints[k]

                            # Check if a × b ≈ c
                            if abs(a * b - c) <= self.tolerance:
                                valid_triples.append((item_idx, a, b, c))

        if len(valid_triples) < 3:
            return {'success': False}

        pattern_indices = self._analyze_pattern_indices(number_arrays, 'pattern3')

        return {
            'success': True,
            'pattern': 'pattern3',
            'description': 'Three columns (A × B = C)',
            'triples': valid_triples,
            'pattern_indices': pattern_indices,
            'confidence': min(0.9, len(valid_triples) / len(number_arrays))
        }

    def _analyze_pattern_indices(
        self,
        number_arrays: List[Tuple[int, List[float]]],
        pattern_type: str
    ) -> Dict[str, Any]:
        """
        Track which numbers form the pattern.

        Args:
            number_arrays: List of (item_index, numbers)
            pattern_type: Which pattern was detected

        Returns:
            Dictionary with pattern index information
        """
        analysis = {
            'pattern_type': pattern_type,
            'item_count': len(number_arrays),
            'items_with_pattern': [],
            'suggested_indices': {}
        }

        for item_idx, numbers in number_arrays:
            if not numbers:
                continue

            # For demonstration, suggest first small integer as quantity
            small_ints = [n for n in numbers if self._is_integer(n) and 1 <= n <= 100]
            if small_ints:
                analysis['items_with_pattern'].append(item_idx)
                analysis['suggested_indices'][item_idx] = {
                    'quantity_candidate': small_ints[0],
                    'small_integers': small_ints
                }

        return analysis

    def extract_quantity_from_block(
        self,
        item: Dict[str, Any],
        pattern_info: Dict[str, Any]
    ) -> float:
        """
        Apply pattern to extract quantity from item block.

        Args:
            item: Item dictionary
            pattern_info: Pattern information from detect_quantity_pattern()

        Returns:
            Extracted quantity, or original quantity if extraction fails
        """
        if not pattern_info.get('success'):
            # Check if pattern is 1 (default from insufficient data per TODO.md)
            pattern_type = pattern_info.get('pattern')
            if pattern_type == 1:  # Default pattern 1
                numbers = item.get('extracted_numbers', [])
                if numbers:
                    # Look for small integers as quantity candidates
                    small_ints = [n for n in numbers if self._is_integer(n) and 1 <= n <= 1000]
                    if small_ints:
                        return min(small_ints)  # Assume smallest is quantity
            return item.get('quantity', 1.0)

        pattern_type = pattern_info.get('pattern')
        numbers = item.get('extracted_numbers', [])

        if not numbers:
            return item.get('quantity', 1.0)

        # Pattern-specific extraction
        if pattern_type == 'pattern1':
            # Single quantity column - take smallest integer
            small_ints = [n for n in numbers if self._is_integer(n) and 1 <= n <= 100]
            if small_ints:
                return min(small_ints)

        elif pattern_type == 'pattern2':
            # Two columns - try to find pair that makes sense
            small_ints = [n for n in numbers if self._is_integer(n) and 1 <= n <= 100]
            if len(small_ints) >= 2:
                # Try to match with pattern info
                pairs = pattern_info.get('pairs', [])
                if pairs:
                    # Use average from pattern
                    avg_product = sum(p[3] for p in pairs) / len(pairs)
                    return avg_product

        elif pattern_type == 'pattern3':
            # Three columns - look for a × b ≈ c
            small_ints = [n for n in numbers if self._is_integer(n) and 1 <= n <= 100]
            if len(small_ints) >= 3:
                # Check all triples
                for i in range(len(small_ints)):
                    for j in range(i + 1, len(small_ints)):
                        for k in range(j + 1, len(small_ints)):
                            a, b, c = small_ints[i], small_ints[j], small_ints[k]
                            if abs(a * b - c) <= self.tolerance:
                                return c  # Use column C directly

        elif pattern_type == 'weight_based':
            # Weight-based - return decimal quantity
            quantity = item.get('quantity')
            if quantity and not self._is_integer(quantity) and 0.1 <= quantity <= 20.0:
                return quantity

        # Fallback to original quantity
        return item.get('quantity', 1.0)

    def _is_integer(self, value: float) -> bool:
        """Check if a float is effectively an integer."""
        return abs(value - round(value)) < 1e-9

    def _are_values_similar(self, values: List[float], threshold: float = 0.3) -> bool:
        """Check if values are similar (low coefficient of variation)."""
        if not values:
            return False

        mean = sum(values) / len(values)
        if mean == 0:
            return False

        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = math.sqrt(variance)
        coeff_var = std_dev / mean if mean != 0 else float('inf')

        return coeff_var < threshold

    def _calculate_confidence(self, values: List[float]) -> float:
        """Calculate confidence score based on value consistency."""
        if len(values) < 2:
            return 0.5

        mean = sum(values) / len(values)
        if mean == 0:
            return 0.5

        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = math.sqrt(variance)
        coeff_var = std_dev / mean

        # Lower coefficient of variation = higher confidence
        confidence = 1.0 / (1.0 + coeff_var * 5)
        return min(0.95, max(0.1, confidence))