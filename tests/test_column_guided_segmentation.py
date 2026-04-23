"""
OBSOLETE TEST FILE - NOT USED BY MAIN PIPELINE
===============================================
Unit tests for Phase 2 Column-Guided Segmentation.
"""

import unittest
from phases.phase2_column_guided import Phase2ColumnGuidedSegmentation


class TestPhase2ColumnGuidedSegmentation(unittest.TestCase):
    """Test cases for Phase 2 column-guided segmentation."""

    def setUp(self):
        """Set up test fixtures."""
        self.segmenter = Phase2ColumnGuidedSegmentation(name_match_threshold=20)

        # Test data: Simple receipt with clear columns
        self.test_json_items = [
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

        self.test_raw_text = """
תאור          כמות   מחיר יחידה   נטו
קוטג 5% 250 גרם   60   4.97   298.20
חלב 3% 1 ליטר     2    6.50   13.00
לחם אחיד 750 גרם  1    8.90   8.90
"""

        self.test_column_info = {
            "success": True,
            "detected_columns": [
                {"hebrew_text": "תאור", "assigned_field": "description"},
                {"hebrew_text": "כמות", "assigned_field": "quantity"},
                {"hebrew_text": "מחיר יחידה", "assigned_field": "unit_price"},
                {"hebrew_text": "נטו", "assigned_field": "line_net_total"}
            ],
            "column_mapping": {
                "תאור": "description",
                "כמות": "quantity",
                "מחיר יחידה": "unit_price",
                "נטו": "line_net_total"
            },
            "lines_range": (0, 1),  # Header is on line 0
            "detection_score": 0.9
        }

    def test_normalize_hebrew(self):
        """Test Hebrew text normalization."""
        test_cases = [
            ("קוטג 5% 250 גרם", "קוטג 5% 250 גרם"),
            ("פריט: קוטג 5%", "קוטג 5%"),
            ("קוטג 5%!", "קוטג 5%"),
            ("  קוטג   5%  ", "קוטג 5%"),
        ]

        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                result = self.segmenter._normalize_hebrew(input_text)
                self.assertEqual(result, expected)

    def test_extract_row_cells_simple(self):
        """Test extracting cells from a simple row."""
        row_text = "קוטג 5% 250 גרם   60   4.97   298.20"
        column_positions = [
            {"column": "תאור", "start": 0, "end": 20},
            {"column": "כמות", "start": 25, "end": 30},
            {"column": "מחיר יחידה", "start": 35, "end": 45},
            {"column": "נטו", "start": 50, "end": 60}
        ]

        result = self.segmenter._extract_row_cells(row_text, column_positions)

        expected = {
            "תאור": "קוטג 5% 250 גרם",
            "כמות": "60",
            "מחיר יחידה": "4.97",
            "נטו": "298.20"
        }

        self.assertEqual(result, expected)

    def test_extract_row_cells_short_row(self):
        """Test extracting cells when row is shorter than column positions."""
        row_text = "קוטג 5% 250 גרם   60"
        column_positions = [
            {"column": "תאור", "start": 0, "end": 20},
            {"column": "כמות", "start": 25, "end": 30},
            {"column": "מחיר יחידה", "start": 35, "end": 45},
            {"column": "נטו", "start": 50, "end": 60}
        ]

        result = self.segmenter._extract_row_cells(row_text, column_positions)

        # Columns beyond row length should have empty values
        self.assertEqual(result.get("תאור"), "קוטג 5% 250 גרם")
        self.assertEqual(result.get("כמות"), "60")
        self.assertEqual(result.get("מחיר יחידה"), "")
        self.assertEqual(result.get("נטו"), "")

    def test_search_item_in_column_found(self):
        """Test searching for item in description column."""
        raw_lines = [
            "תאור          כמות   מחיר יחידה   נטו",
            "קוטג 5% 250 גרם   60   4.97   298.20",
            "חלב 3% 1 ליטר     2    6.50   13.00"
        ]

        description_column = {
            "column": "תאור",
            "start": 0,
            "end": 20
        }

        # Item should be found on line 1
        row_idx = self.segmenter._search_item_in_column(
            "קוטג 5% 250 גרם",
            raw_lines,
            description_column
        )

        self.assertEqual(row_idx, 1)

    def test_search_item_in_column_not_found(self):
        """Test searching for non-existent item."""
        raw_lines = [
            "תאור          כמות   מחיר יחידה   נטו",
            "קוטג 5% 250 גרם   60   4.97   298.20",
            "חלב 3% 1 ליטר     2    6.50   13.00"
        ]

        description_column = {
            "column": "תאור",
            "start": 0,
            "end": 20
        }

        row_idx = self.segmenter._search_item_in_column(
            "יינשוף 500 מ\"ל",
            raw_lines,
            description_column
        )

        self.assertIsNone(row_idx)

    def test_search_item_in_column_fuzzy_match(self):
        """Test fuzzy matching in column search."""
        raw_lines = [
            "תאור          כמות   מחיר יחידה   נטו",
            "קוטג 5% 250 גרם   60   4.97   298.20",
            "חלב 3% 1 ליטר     2    6.50   13.00"
        ]

        description_column = {
            "column": "תאור",
            "start": 0,
            "end": 20
        }

        # Slightly different description - should still match with fuzzy
        row_idx = self.segmenter._search_item_in_column(
            "קוטג 5% 250",
            raw_lines,
            description_column
        )

        self.assertEqual(row_idx, 1)

    def test_find_column_positions(self):
        """Test finding column positions in header."""
        raw_lines = [
            "תאור          כמות   מחיר יחידה   נטו",
            "קוטג 5% 250 גרם   60   4.97   298.20",
            "חלב 3% 1 ליטר     2    6.50   13.00"
        ]

        detected_columns = [
            {"hebrew_text": "תאור"},
            {"hebrew_text": "כמות"},
            {"hebrew_text": "מחיר יחידה"},
            {"hebrew_text": "נטו"}
        ]

        column_positions = self.segmenter._find_column_positions(
            raw_lines, 0, 1, detected_columns
        )

        # Should find 4 column positions
        self.assertEqual(len(column_positions), 4)

        # Columns should be in order
        column_names = [cp["column"] for cp in column_positions]
        self.assertEqual(column_names, ["תאור", "כמות", "מחיר יחידה", "נטו"])

        # Start positions should increase
        for i in range(len(column_positions) - 1):
            self.assertLess(
                column_positions[i]["start"],
                column_positions[i + 1]["start"]
            )

    def test_process_item_with_columns(self):
        """Test processing an item using column positions."""
        raw_lines = [
            "תאור          כמות   מחיר יחידה   נטו",
            "קוטג 5% 250 גרם   60   4.97   298.20",
            "חלב 3% 1 ליטר     2    6.50   13.00"
        ]

        column_positions = [
            {"column": "תאור", "start": 0, "end": 20},
            {"column": "כמות", "start": 25, "end": 30},
            {"column": "מחיר יחידה", "start": 35, "end": 45},
            {"column": "נטו", "start": 50, "end": 60}
        ]

        column_mapping = {
            "תאור": "description",
            "כמות": "quantity",
            "מחיר יחידה": "unit_price",
            "נטו": "line_net_total"
        }

        json_item = {
            "description": "קוטג 5% 250 גרם",
            "quantity": 1.0,
            "unit_price": 4.97,
            "line_total": 4.97
        }

        column_info = {
            "detected_columns": [
                {"hebrew_text": "תאור", "assigned_field": "description"},
                {"hebrew_text": "כמות", "assigned_field": "quantity"},
                {"hebrew_text": "מחיר יחידה", "assigned_field": "unit_price"},
                {"hebrew_text": "נטו", "assigned_field": "line_net_total"}
            ]
        }

        result = self.segmenter._process_item_with_columns(
            json_item, raw_lines, column_positions, column_mapping, column_info
        )

        self.assertIsNotNone(result)
        self.assertTrue(result.get("segmentation_success", False))
        self.assertEqual(result.get("row_index"), 1)
        self.assertIn("raw_row_text", result)
        self.assertIn("row_cells", result)
        self.assertIn("mapped_cells", result)

    def test_segment_with_columns_success(self):
        """Test main segmentation method with successful column detection."""
        result = self.segmenter.segment_with_columns(
            self.test_json_items,
            self.test_raw_text,
            self.test_column_info
        )

        self.assertEqual(len(result), 2)

        # Both items should be successfully segmented
        success_count = len([i for i in result if i.get("segmentation_success", False)])
        self.assertGreaterEqual(success_count, 1)

        # Check enhanced fields
        for item in result:
            if item.get("segmentation_success"):
                self.assertIn("row_cells", item)
                self.assertIn("raw_row_text", item)
                self.assertIn("column_positions", item)
                self.assertIn("row_index", item)

    def test_segment_with_columns_fallback(self):
        """Test fallback to fuzzy matching when column detection fails."""
        column_info = {
            "success": False,
            "detected_columns": [],
            "column_mapping": {},
            "lines_range": None,
            "detection_score": 0.0
        }

        result = self.segmenter.segment_with_columns(
            self.test_json_items,
            self.test_raw_text,
            column_info
        )

        self.assertEqual(len(result), 2)

        # Items should still be processed (with fallback)
        for item in result:
            self.assertIn("segmentation_success", item)

    def test_empty_inputs(self):
        """Test handling of empty inputs."""
        # Empty JSON items
        result = self.segmenter.segment_with_columns(
            [], self.test_raw_text, self.test_column_info
        )
        self.assertEqual(result, [])

        # Empty raw text
        result = self.segmenter.segment_with_columns(
            self.test_json_items, "", self.test_column_info
        )
        self.assertEqual(result, [])

        # Both empty
        result = self.segmenter.segment_with_columns([], "", self.test_column_info)
        self.assertEqual(result, [])

    def test_extract_numeric_values(self):
        """Test extraction of numeric values from cell text."""
        enhanced_item = {
            "description": "קוטג 5% 250 גרם",
            "quantity": 1.0
        }

        mapped_cells = {
            "quantity": "60",
            "unit_price": "4.97",
            "line_net_total": "298.20 ₪"
        }

        self.segmenter._extract_numeric_values(enhanced_item, mapped_cells)

        # Should extract numeric values
        self.assertEqual(enhanced_item.get("extracted_quantity"), 60.0)
        self.assertEqual(enhanced_item.get("extracted_unit_price"), 4.97)
        self.assertEqual(enhanced_item.get("extracted_line_net_total"), 298.20)

    def test_try_fuzzy_match(self):
        """Test fuzzy matching fallback."""
        raw_lines = [
            "תאור          כמות   מחיר יחידה   נטו",
            "קוטג 5% 250 גרם   60   4.97   298.20",
            "חלב 3% 1 ליטר     2    6.50   13.00"
        ]

        json_item = {
            "description": "קוטג 5% 250 גרם",
            "quantity": 1.0,
            "unit_price": 4.97,
            "line_total": 4.97
        }

        result = self.segmenter._try_fuzzy_match(json_item, raw_lines)

        self.assertIsNotNone(result)
        self.assertTrue(result.get("segmentation_success", False))
        self.assertIn("name_match_score", result)
        self.assertIn("matched_line", result)
        self.assertIn("row_index", result)
        self.assertEqual(result.get("fallback_method"), "fuzzy_matching")


if __name__ == "__main__":
    unittest.main()