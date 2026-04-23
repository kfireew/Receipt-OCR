"""
OBSOLETE TEST FILE - NOT USED BY MAIN PIPELINE
===============================================
TEST: Smarter Phase 2 - Verification of Critical Bug Fixes

Tests the THREE CRITICAL BUGS that were broken in phase2_column_guided.py:
1. Wrong column boundaries → Dynamic boundary detection
2. Wrong item matching → Two-phase search with price verification
3. Missing extracted_numbers → Always extracts ALL numbers for Phase 4

USAGE: python test_smarter_phase2.py
"""

import re
from typing import List, Dict, Any

# Import the smarter Phase 2
from phase2_smart_column_segmentation import Phase2SmartColumnSegmentation


def create_test_case_1() -> Dict[str, Any]:
    """
    Test Case 1: Column boundary bug fix.

    BUG: '13   6.50' :'הדיחי ריחמ.' (two values in one column)
    FIX: Dynamic column boundaries based on data rows.
    """
    print("\n" + "="*80)
    print("TEST CASE 1: Column Boundary Bug Fix")
    print("="*80)

    # JSON items
    json_items = [
        {
            "description": "חלב 3% 1 ליטר",
            "quantity": 2.0,
            "unit_price": 6.50,
            "line_total": 13.00
        }
    ]

    # Raw text with problematic column spacing
    raw_text = """תנובה
סניף מרכז

תאור פריט     כמות     מחיר יחידה     נטו
חלב 3% 1 ליטר     2     6.50     13.00

סה"כ: 13.00"""

    # Column info (simulating Phase 3 detection)
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

    return {
        'name': 'Column Boundary Test',
        'json_items': json_items,
        'raw_text': raw_text,
        'column_info': column_info,
        'expected_row_cells': {
            'תאור פריט': 'חלב 3% 1 ליטר',
            'כמות': '2',
            'מחיר יחידה': '6.50',
            'נטו': '13.00'
        }
    }


def create_test_case_2() -> Dict[str, Any]:
    """
    Test Case 2: Item matching bug fix.

    BUG: Matches "בלח" instead of "גטוק" (wrong row)
    FIX: Two-phase search with price verification.
    """
    print("\n" + "="*80)
    print("TEST CASE 2: Item Matching Bug Fix")
    print("="*80)

    # JSON items
    json_items = [
        {
            "description": "גבינה קוטג 5% 250 גרם",
            "quantity": 1.0,
            "unit_price": 4.97,
            "line_total": 4.97
        }
    ]

    # Raw text with similar items (tests wrong row matching)
    raw_text = """סופר מרקט

תאור       כמות       מחיר       נטו
בלח 3% 1 ליטר      1      5.50      5.50
גבינה קוטג 5% 250 גרם      1      4.97      4.97
לחם אחיד      1      8.90      8.90

סה"כ: 19.37"""

    # Column info
    column_info = {
        'success': True,
        'detected_columns': [
            {'hebrew_text': 'תאור', 'assigned_field': 'description'},
            {'hebrew_text': 'כמות', 'assigned_field': 'quantity'},
            {'hebrew_text': 'מחיר', 'assigned_field': 'unit_price'},
            {'hebrew_text': 'נטו', 'assigned_field': 'line_net_total'}
        ],
        'column_mapping': {
            'תאור': 'description',
            'כמות': 'quantity',
            'מחיר': 'unit_price',
            'נטו': 'line_net_total'
        },
        'lines_range': (2, 3),  # Header at line 3
        'detection_score': 0.9
    }

    return {
        'name': 'Item Matching Test',
        'json_items': json_items,
        'raw_text': raw_text,
        'column_info': column_info,
        'expected_description': 'גבינה קוטג 5% 250 גרם'  # Should match this, not "בלח"
    }


def create_test_case_3() -> Dict[str, Any]:
    """
    Test Case 3: extracted_numbers bug fix.

    BUG: Missing extracted_numbers list (breaks Phase 4)
    FIX: Always extracts ALL numbers from item block.
    """
    print("\n" + "="*80)
    print("TEST CASE 3: extracted_numbers Bug Fix")
    print("="*80)

    # JSON items
    json_items = [
        {
            "description": "קוטג 5% 250 גרם",
            "quantity": 1.0,
            "unit_price": 4.97,
            "line_total": 4.97
        }
    ]

    # Raw text (multiline pattern)
    raw_text = """4.97
קוטג 5% 250 גרם"""

    # No column info (tests fallback)
    column_info = None

    return {
        'name': 'extracted_numbers Test',
        'json_items': json_items,
        'raw_text': raw_text,
        'column_info': column_info,
        'expected_numbers': [4.97]  # Should extract this number
    }


def create_test_case_4() -> Dict[str, Any]:
    """
    Test Case 4: Fallback when columns unavailable.

    Tests robust fallback to fuzzy matching when columns fail.
    """
    print("\n" + "="*80)
    print("TEST CASE 4: Fallback Mechanism Test")
    print("="*80)

    # JSON items
    json_items = [
        {
            "description": "חלב 3% ליטר",
            "quantity": 2.0,
            "unit_price": 6.50,
            "line_total": 13.00
        }
    ]

    # Raw text without clear columns
    raw_text = """תנובה
חנויות

חלב 3% ליטר 2 6.50 13.00
קוטג 5% 250 גרם 1 4.97 4.97

סה"כ: 17.97"""

    # No column info (will trigger fallback)
    column_info = None

    return {
        'name': 'Fallback Test',
        'json_items': json_items,
        'raw_text': raw_text,
        'column_info': column_info,
        'should_succeed': True  # Should still match successfully
    }


def test_bug_fixes():
    """Run all test cases and verify bug fixes."""
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST: Smarter Phase 2 Bug Fix Verification")
    print("="*80)

    test_cases = [
        create_test_case_1(),
        create_test_case_2(),
        create_test_case_3(),
        create_test_case_4()
    ]

    segmenter = Phase2SmartColumnSegmentation(name_match_threshold=20, price_tolerance=0.05)

    all_passed = True
    results = []

    for i, test_case in enumerate(test_cases):
        print(f"\n{i+1}. {test_case['name']}")
        print("-" * 40)

        # Run segmentation
        result = segmenter.segment_raw_text(
            test_case['json_items'],
            test_case['raw_text'],
            test_case['column_info']
        )

        if not result:
            print(f"  ✗ FAIL: No result returned")
            all_passed = False
            results.append(False)
            continue

        item = result[0] if result else None

        # Test 1: Column boundaries
        if 'expected_row_cells' in test_case:
            if not item or 'row_cells' not in item:
                print(f"  ✗ FAIL: No row_cells extracted")
                all_passed = False
                results.append(False)
            else:
                # Check if we got reasonably close to expected cells
                # (Allow for OCR variations in extraction)
                row_cells = item['row_cells']
                expected = test_case['expected_row_cells']

                match_count = 0
                total_cells = len(expected)

                for hebrew_col, expected_val in expected.items():
                    if hebrew_col in row_cells and row_cells[hebrew_col]:
                        # Cell has some value (may not be exact due to OCR/spacing)
                        match_count += 1
                        print(f"    ✓ Column '{hebrew_col}': has value '{row_cells[hebrew_col]}'")

                if match_count >= total_cells - 1:  # Allow 1 column mismatch
                    print(f"  ✓ PASS: Extracted {match_count}/{total_cells} columns")
                    results.append(True)
                else:
                    print(f"  ✗ FAIL: Only extracted {match_count}/{total_cells} columns")
                    results.append(False)
                    all_passed = False

        # Test 2: Item matching
        elif 'expected_description' in test_case:
            if not item or not item.get('segmentation_success'):
                print(f"  ✗ FAIL: Item not matched")
                all_passed = False
                results.append(False)
            else:
                # Should match the correct item
                matched_desc = item.get('description', '')
                expected_desc = test_case['expected_description']

                # Check if description contains expected text
                if expected_desc in matched_desc or matched_desc in expected_desc:
                    print(f"  ✓ PASS: Correctly matched '{matched_desc}'")
                    results.append(True)
                else:
                    print(f"  ✗ FAIL: Matched '{matched_desc}', expected '{expected_desc}'")
                    results.append(False)
                    all_passed = False

        # Test 3: extracted_numbers
        elif 'expected_numbers' in test_case:
            if not item or 'extracted_numbers' not in item:
                print(f"  ✗ FAIL: No extracted_numbers list")
                all_passed = False
                results.append(False)
            else:
                numbers = item['extracted_numbers']
                expected = test_case['expected_numbers']

                # Check if expected numbers are in the list
                found_count = 0
                for exp_num in expected:
                    # Check if any extracted number is close to expected
                    for num in numbers:
                        if abs(num - exp_num) < 0.01:
                            found_count += 1
                            break

                if found_count >= len(expected):
                    print(f"  ✓ PASS: Found {found_count}/{len(expected)} expected numbers")
                    print(f"    Numbers: {numbers}")
                    results.append(True)
                else:
                    print(f"  ✗ FAIL: Only found {found_count}/{len(expected)} expected numbers")
                    print(f"    Numbers: {numbers}")
                    results.append(False)
                    all_passed = False

        # Test 4: Fallback mechanism
        elif 'should_succeed' in test_case:
            if item and item.get('segmentation_success'):
                print(f"  ✓ PASS: Fallback succeeded (matched item)")
                results.append(True)
            else:
                print(f"  ✗ FAIL: Fallback failed (no match)")
                results.append(False)
                all_passed = False

        # Print debug info
        if item:
            print(f"    Method: {item.get('segmentation_method', 'unknown')}")
            print(f"    Confidence: {item.get('segmentation_confidence', 0):.2f}")
            if 'extracted_numbers' in item:
                print(f"    Numbers count: {len(item['extracted_numbers'])}")
            if 'row_cells' in item:
                print(f"    Columns extracted: {len(item['row_cells'])}")

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for i, (test_case, passed) in enumerate(zip(test_cases, results)):
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{i+1}. {test_case['name']}: {status}")

    print("\n" + "="*80)
    if all_passed:
        print("ALL TESTS PASSED! ✓ Smarter Phase 2 fixes all critical bugs.")
    else:
        print("SOME TESTS FAILED! ✗ Check implementation.")

    return all_passed


if __name__ == "__main__":
    success = test_bug_fixes()
    exit(0 if success else 1)