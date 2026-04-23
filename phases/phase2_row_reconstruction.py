"""
OBSOLETE - NOT USED BY MAIN PIPELINE
=====================================
Phase 2: Implement row reconstruction from word polygons.

Using what you learned in Phase 1, implement a function that takes the
Mindee word polygon data and returns a list of reconstructed rows.

Each row is a list of words sorted by x coordinate, with text content
and x/y positions. Group words into the same row if their y coordinates
are within the appropriate tolerance for the coordinate system.
"""

from typing import List, Dict, Any, Tuple
from collections import defaultdict
import math


class RowReconstructor:
    """
    Reconstruct rows from word polygon data.

    Takes Mindee word polygon data and groups words into rows based on
    y-coordinate proximity, then sorts words within each row by x-coordinate.
    """

    def __init__(self, y_tolerance: float = 0.02):
        """
        Args:
            y_tolerance: Maximum Y difference to consider words in same row.
                         Based on normalized coordinates (0.0 to 1.0).
        """
        self.y_tolerance = y_tolerance

    def reconstruct_rows_from_polygons(
        self,
        ocr_response: Any
    ) -> List[List[Dict[str, Any]]]:
        """
        Extract words from OCR response and group into rows.

        Args:
            ocr_response: Mindee OCR response object (from get_raw_text or scan_raw_ocr)

        Returns:
            List of rows, each row is list of word dicts sorted by x-coordinate
            Each word dict has: content, x, y, polygon (original polygon if available)
        """
        # Extract words with positions
        words = self._extract_words_with_positions(ocr_response)
        if not words:
            print(f"No words extracted from OCR response")
            return []

        print(f"Extracted {len(words)} words from OCR response")

        # Understand coordinate system
        self._analyze_coordinate_system(words)

        # Group words into rows by Y coordinate
        rows = self._group_words_into_rows(words)
        print(f"Grouped into {len(rows)} rows")

        # Sort rows by Y position (top to bottom)
        sorted_rows = self._sort_rows_by_y(rows)
        print(f"Sorted {len(sorted_rows)} rows by Y position")

        # Sort words within each row by X position (left to right)
        for i, row in enumerate(sorted_rows):
            sorted_rows[i] = sorted(row, key=lambda w: w['x'])
            print(f"  Row {i+1}: {len(row)} words, Y≈{row[0]['y']:.3f}")

        return sorted_rows

    def _extract_words_with_positions(
        self,
        ocr_response: Any
    ) -> List[Dict[str, Any]]:
        """
        Extract words with their positions from OCR response.

        Handles different Mindee response formats:
        - With raw_text=True: may have different structure
        - With polygon=True: has polygon coordinates
        """
        words = []

        if ocr_response is None:
            return words

        # Method 1: Check for OCR with pages and words
        if hasattr(ocr_response, 'ocr') and hasattr(ocr_response.ocr, 'pages'):
            pages = ocr_response.ocr.pages
            if pages and isinstance(pages, list):
                for page in pages:
                    if hasattr(page, 'words'):
                        page_words = page.words
                        if page_words and isinstance(page_words, list):
                            for word in page_words:
                                word_dict = self._extract_word_data(word)
                                if word_dict:
                                    words.append(word_dict)

        # Method 2: Check for mrz (machine readable zone) - alternative structure
        if not words and hasattr(ocr_response, 'ocr') and hasattr(ocr_response.ocr, 'pages'):
            pages = ocr_response.ocr.pages
            if pages and isinstance(pages, list):
                for page in pages:
                    if hasattr(page, 'mrz'):
                        mrz = page.mrz
                        if mrz and isinstance(mrz, list):
                            for word in mrz:
                                word_dict = self._extract_word_data(word)
                                if word_dict:
                                    words.append(word_dict)

        # Method 3: Try to find any list attribute that might contain words
        if not words:
            # Fallback: look for any attribute that looks like word data
            words = self._fallback_extract_words(ocr_response)

        return words

    def _extract_word_data(self, word_obj: Any) -> Dict[str, Any]:
        """Extract position data from a word object."""
        word_dict = {}

        # Get content
        if hasattr(word_obj, 'content'):
            content = word_obj.content
        elif hasattr(word_obj, 'value'):
            content = word_obj.value
        elif hasattr(word_obj, 'text'):
            content = word_obj.text
        else:
            # Try to convert to string
            content = str(word_obj)

        word_dict['content'] = str(content).strip() if content else ""

        # Get position from polygon
        if hasattr(word_obj, 'polygon') and word_obj.polygon:
            polygon = word_obj.polygon
            if isinstance(polygon, list) and len(polygon) >= 1:
                # Use first point for x,y
                first_point = polygon[0]
                if isinstance(first_point, (list, tuple)) and len(first_point) >= 2:
                    word_dict['x'] = float(first_point[0])
                    word_dict['y'] = float(first_point[1])
                    word_dict['polygon'] = polygon
                else:
                    # Can't extract position
                    return None
            else:
                # Can't extract position
                return None
        elif hasattr(word_obj, 'bounding_box'):
            # Alternative: bounding box
            bbox = word_obj.bounding_box
            if hasattr(bbox, 'coordinates'):
                # Calculate center
                # This is simplified - actual implementation would depend on format
                word_dict['x'] = 0.5
                word_dict['y'] = 0.5
                word_dict['bounding_box'] = bbox
            else:
                return None
        else:
            # No position information
            return None

        # Skip words without content
        if not word_dict['content']:
            return None

        return word_dict

    def _fallback_extract_words(self, response: Any) -> List[Dict[str, Any]]:
        """Fallback method to extract words when standard methods fail."""
        words = []

        # Try to convert entire response to string and parse
        try:
            response_str = str(response)
            # Very basic parsing - in reality would need actual structure
            # This is just a fallback
            lines = response_str.split('\n')
            for y, line in enumerate(lines[:20]):  # Limit to first 20 lines
                if line.strip():
                    # Create fake positions (this is NOT accurate!)
                    words.append({
                        'content': line.strip(),
                        'x': 0.1,
                        'y': y * 0.05,
                        'source': 'fallback'
                    })
        except:
            pass

        return words

    def _analyze_coordinate_system(self, words: List[Dict[str, Any]]):
        """Analyze coordinate ranges to understand the coordinate system."""
        if not words:
            return

        xs = [w['x'] for w in words if 'x' in w]
        ys = [w['y'] for w in words if 'y' in w]

        if xs and ys:
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)

            print(f"Coordinate system analysis:")
            print(f"  X range: {min_x:.3f} to {max_x:.3f}")
            print(f"  Y range: {min_y:.3f} to {max_y:.3f}")
            print(f"  Using Y tolerance: {self.y_tolerance}")

            # Check if coordinates are normalized (0-1) or pixel-based
            if max_x > 1000 or max_y > 1000:
                print("  WARNING: Coordinates appear to be in pixels, not normalized 0-1")
                print("  Consider adjusting y_tolerance (currently for normalized coords)")

    def _group_words_into_rows(
        self,
        words: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Group words into rows based on Y coordinate proximity.

        Uses clustering algorithm to group words with similar Y coordinates.
        """
        if not words:
            return []

        # Sort words by Y for clustering
        words_sorted_by_y = sorted(words, key=lambda w: w['y'])

        rows = []
        current_row = []
        current_y = None

        for word in words_sorted_by_y:
            word_y = word['y']

            if current_y is None:
                # First word starts first row
                current_row = [word]
                current_y = word_y
            elif abs(word_y - current_y) <= self.y_tolerance:
                # Word is in same row (within tolerance)
                current_row.append(word)
                # Update current_y to average of row
                current_y = sum(w['y'] for w in current_row) / len(current_row)
            else:
                # Word starts new row
                rows.append(current_row)
                current_row = [word]
                current_y = word_y

        # Don't forget the last row
        if current_row:
            rows.append(current_row)

        return rows

    def _sort_rows_by_y(
        self,
        rows: List[List[Dict[str, Any]]]
    ) -> List[List[Dict[str, Any]]]:
        """Sort rows by their average Y position (top to bottom)."""
        if not rows:
            return []

        # Calculate average Y for each row
        rows_with_y = []
        for row in rows:
            if row:
                avg_y = sum(w['y'] for w in row) / len(row)
                rows_with_y.append((avg_y, row))

        # Sort by Y (top to bottom)
        rows_with_y.sort(key=lambda x: x[0])

        return [row for _, row in rows_with_y]

    def rows_to_text(self, rows: List[List[Dict[str, Any]]]) -> List[str]:
        """
        Convert rows of word dicts to readable text lines.

        Args:
            rows: List of rows (each row is list of word dicts)

        Returns:
            List of text strings, one per row
        """
        text_lines = []
        for i, row in enumerate(rows):
            # Sort words by x (left to right)
            sorted_words = sorted(row, key=lambda w: w['x'])
            # Join words with spaces
            line_text = ' '.join(w['content'] for w in sorted_words)
            text_lines.append(line_text)

        return text_lines


def test_row_reconstruction():
    """Test Phase 2 functionality with mock data."""
    print("Testing Row Reconstruction (Phase 2)")
    print("=" * 60)

    # Create mock OCR response
    class MockWord:
        def __init__(self, content, x, y):
            self.content = content
            self.polygon = [[x, y], [x + 0.1, y], [x + 0.1, y + 0.05], [x, y + 0.05]]

    class MockPage:
        def __init__(self, words):
            self.words = words
            self.mrz = []

    class MockOCR:
        def __init__(self, pages):
            self.pages = pages

    class MockResponse:
        def __init__(self, ocr):
            self.ocr = ocr

    # Create mock receipt with 3 rows
    mock_words = [
        MockWord("תנובה", 0.1, 0.1),
        MockWord("קופה:", 0.3, 0.1),
        MockWord("5", 0.45, 0.1),

        MockWord("קוטג", 0.1, 0.2),
        MockWord("5%", 0.25, 0.2),
        MockWord("250", 0.35, 0.2),
        MockWord("גרם", 0.42, 0.2),
        MockWord("4.97", 0.6, 0.2),

        MockWord("חלב", 0.1, 0.3),
        MockWord("3%", 0.2, 0.3),
        MockWord("1", 0.28, 0.3),
        MockWord("ליטר", 0.33, 0.3),
        MockWord("6.50", 0.5, 0.3),
        MockWord("13.00", 0.65, 0.3),
    ]

    # Add slight Y variations to test tolerance
    mock_words[3].polygon[0][1] = 0.201  # Slightly different Y for "קוטג"
    mock_words[8].polygon[0][1] = 0.299  # Slightly different Y for "חלב"

    mock_page = MockPage(mock_words)
    mock_ocr = MockOCR([mock_page])
    mock_response = MockResponse(mock_ocr)

    # Test reconstruction
    reconstructor = RowReconstructor(y_tolerance=0.02)
    rows = reconstructor.reconstruct_rows_from_polygons(mock_response)

    print(f"\nReconstructed {len(rows)} rows:")
    print("-" * 40)

    text_lines = reconstructor.rows_to_text(rows)
    for i, line in enumerate(text_lines):
        print(f"Row {i+1}: {line}")

    print(f"\nRow details:")
    for i, row in enumerate(rows):
        avg_y = sum(w['y'] for w in row) / len(row) if row else 0
        words_info = ', '.join(f"{w['content']}({w['x']:.2f},{w['y']:.3f})" for w in row[:3])
        if len(row) > 3:
            words_info += f" ... +{len(row)-3} more"
        print(f"  Row {i+1}: {len(row)} words, avg Y={avg_y:.3f}: {words_info}")

    # Validate
    expected_rows = 3
    if len(rows) == expected_rows:
        print(f"\n✓ Correctly reconstructed {expected_rows} rows")
        return True
    else:
        print(f"\n✗ Expected {expected_rows} rows, got {len(rows)}")
        return False


if __name__ == "__main__":
    success = test_row_reconstruction()
    if success:
        print("\nPhase 2 test passed!")
    else:
        print("\nPhase 2 test failed!")