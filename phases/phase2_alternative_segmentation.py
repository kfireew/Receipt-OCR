"""
OBSOLETE - NOT USED BY MAIN PIPELINE
=====================================
Phase 3: Implement raw text segmentation.

Using the reconstructed rows from Phase 2, build the segmentation
needed for the pipeline. Keep it simple and direct.

Segmentation involves:
1. Identifying item blocks in the raw text
2. Separating headers from item rows
3. Grouping related lines together
4. Preparing data for Phase 4 (JSON anchor reconstruction)
"""

from typing import List, Dict, Any, Tuple
import re


class RawTextSegmenter:
    """
    Segment raw text into meaningful blocks for receipt processing.

    Takes the raw text from Scan B and segments it into:
    - Header block (store info, date, etc.)
    - Item blocks (product rows)
    - Footer block (totals, taxes, etc.)
    """

    def __init__(self):
        # Hebrew keywords for different sections
        self.header_keywords = [
            'תאריך', 'תאיר', 'תירך',  # Date (common OCR errors)
            'קופה', 'קפה',  # Cashier/register
            'חשבונית', 'תעודת', 'משלוח',  # Invoice/delivery note
            'סניף', 'שנף',  # Branch
            'מזהה', 'מזה',  # Identifier
        ]

        self.item_indicator_keywords = [
            'פריט', 'פרט',  # Item
            'תיאור', 'תאור',  # Description
            'ברקוד', 'ברקוד',  # Barcode
            'מחיר', 'מחיר',  # Price
            'כמות', 'כמת',  # Quantity
        ]

        self.footer_keywords = [
            'סה"כ', 'סהיכ', 'סהי',  # Total
            'סכום', 'סכום',  # Sum
            'מע"מ', 'מע"מ',  # VAT
            'הנחה', 'החנה', 'תחנה',  # Discount
            'לתשלום', 'לתשלום',  # To pay
        ]

        self.skip_keywords = [
            'תדפיס', 'תופיס',  # Print/receipt
            'לקוח', 'לקח',  # Customer
            'תשלום', 'תשלמ',  # Payment
            'אשראי', 'אשראי',  # Credit
        ]

    def segment_raw_text(
        self,
        raw_text: str,
        reconstructed_rows: List[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Segment raw text into sections.

        Args:
            raw_text: Full text from raw text scan
            reconstructed_rows: Optional rows from Phase 2 for validation

        Returns:
            Dictionary with segmented sections
        """
        if not raw_text:
            return {"error": "No raw text provided"}

        # Split into lines
        lines = raw_text.splitlines()
        print(f"Segmenting {len(lines)} lines of raw text")

        # Basic segmentation
        segmented = self._segment_by_position(lines)

        # Enhanced segmentation using keyword analysis
        enhanced = self._enhance_with_keyword_analysis(segmented, lines)

        # If we have reconstructed rows from Phase 2, use them for validation
        if reconstructed_rows:
            enhanced = self._validate_with_reconstructed_rows(enhanced, reconstructed_rows)

        print(f"\nSegmentation results:")
        print(f"  Header lines: {len(enhanced.get('header_lines', []))}")
        print(f"  Item blocks: {len(enhanced.get('item_blocks', []))}")
        print(f"  Footer lines: {len(enhanced.get('footer_lines', []))}")

        return enhanced

    def _segment_by_position(self, lines: List[str]) -> Dict[str, Any]:
        """
        Simple segmentation based on line position.

        Heuristic: Receipts typically have:
        - Header: First 5-10 lines
        - Items: Middle section
        - Footer: Last 5-10 lines
        """
        if not lines:
            return {}

        total_lines = len(lines)

        # Define boundaries (adjustable)
        header_end = min(8, total_lines // 3)  # First 8 lines or first third
        footer_start = max(total_lines - 8, total_lines * 2 // 3)  # Last 8 lines or last third

        # Ensure footer starts after header
        if footer_start <= header_end:
            footer_start = min(total_lines, header_end + 5)

        segmented = {
            "header_lines": lines[:header_end],
            "middle_lines": lines[header_end:footer_start],
            "footer_lines": lines[footer_start:],
            "total_lines": total_lines,
            "header_end": header_end,
            "footer_start": footer_start
        }

        # Further process middle lines into item blocks
        item_blocks = self._extract_item_blocks(segmented["middle_lines"])
        segmented["item_blocks"] = item_blocks

        return segmented

    def _extract_item_blocks(self, middle_lines: List[str]) -> List[List[str]]:
        """
        Extract individual item blocks from middle section.

        An item block is a group of lines that belong to one product item.
        """
        if not middle_lines:
            return []

        item_blocks = []
        current_block = []

        for i, line in enumerate(middle_lines):
            line_stripped = line.strip()

            if not line_stripped:
                # Empty line - potential block separator
                if current_block:
                    item_blocks.append(current_block)
                    current_block = []
                continue

            # Check if line looks like an item line
            is_item_line = self._is_item_line(line_stripped)

            if is_item_line:
                current_block.append(line_stripped)
            else:
                # Non-item line might separate blocks
                if current_block:
                    item_blocks.append(current_block)
                    current_block = []

        # Don't forget the last block
        if current_block:
            item_blocks.append(current_block)

        # Filter out blocks that are too small (likely not items)
        filtered_blocks = []
        for block in item_blocks:
            if len(block) >= 1 and self._is_likely_item_block(block):
                filtered_blocks.append(block)

        print(f"  Extracted {len(item_blocks)} blocks, filtered to {len(filtered_blocks)} likely item blocks")
        return filtered_blocks

    def _is_item_line(self, line: str) -> bool:
        """
        Determine if a line looks like an item line.

        Item lines typically:
        - Contain Hebrew text
        - May contain numbers (prices, quantities)
        - Don't contain header/footer keywords
        """
        line_lower = line.lower()

        # Skip if contains header/footer/skip keywords
        for keyword_list in [self.header_keywords, self.footer_keywords, self.skip_keywords]:
            for keyword in keyword_list:
                if keyword in line_lower:
                    return False

        # Check for Hebrew letters
        has_hebrew = bool(re.search(r'[\u0590-\u05FF]', line))

        # Check for numbers (prices, quantities)
        has_numbers = bool(re.search(r'\d', line))

        # Check for barcode-like sequences
        has_barcode = bool(re.search(r'\b\d{12,13}\b', line))

        # Item lines often have Hebrew or numbers (or both)
        return has_hebrew or has_numbers or has_barcode

    def _is_likely_item_block(self, block: List[str]) -> bool:
        """
        Determine if a block of lines is likely an item block.

        Criteria:
        - At least one line has Hebrew
        - At least one line has a number (price/quantity)
        - Not all lines are just numbers (could be price list)
        """
        if not block:
            return False

        has_hebrew = False
        has_number = False
        all_numbers = True

        for line in block:
            if re.search(r'[\u0590-\u05FF]', line):
                has_hebrew = True
            if re.search(r'\d', line):
                has_number = True
            if not re.search(r'^\s*[\d,\.\s]+\s*$', line):  # Not just numbers and punctuation
                all_numbers = False

        # An item block should have either Hebrew or not be all numbers
        # and should typically have numbers (prices)
        return (has_hebrew or not all_numbers) and has_number

    def _enhance_with_keyword_analysis(
        self,
        segmented: Dict[str, Any],
        all_lines: List[str]
    ) -> Dict[str, Any]:
        """
        Enhance segmentation using keyword analysis.

        Looks for specific keywords to better identify sections.
        """
        enhanced = segmented.copy()

        # Analyze header section more precisely
        header_lines = segmented.get("header_lines", [])
        if header_lines:
            header_analysis = self._analyze_section(header_lines, "header")
            enhanced["header_analysis"] = header_analysis

        # Analyze footer section
        footer_lines = segmented.get("footer_lines", [])
        if footer_lines:
            footer_analysis = self._analyze_section(footer_lines, "footer")
            enhanced["footer_analysis"] = footer_analysis

        # Identify column headers in middle section
        middle_lines = segmented.get("middle_lines", [])
        if middle_lines:
            # Look for column header lines (typically near top of middle section)
            column_headers = self._find_column_headers(middle_lines[:10])  # First 10 lines of middle
            enhanced["column_headers"] = column_headers

        # Try to detect table structure
        table_structure = self._detect_table_structure(all_lines)
        enhanced["table_structure"] = table_structure

        return enhanced

    def _analyze_section(self, lines: List[str], section_type: str) -> Dict[str, Any]:
        """Analyze a section (header/footer) for specific information."""
        analysis = {
            "type": section_type,
            "line_count": len(lines),
            "keywords_found": [],
            "has_date": False,
            "has_total": False,
            "has_vat": False
        }

        all_text = ' '.join(lines).lower()

        # Check for keywords
        if section_type == "header":
            keyword_list = self.header_keywords
        else:  # footer
            keyword_list = self.footer_keywords

        for keyword in keyword_list:
            if keyword in all_text:
                analysis["keywords_found"].append(keyword)

        # Check for specific patterns
        if section_type == "header":
            # Date patterns
            date_patterns = [
                r'\d{1,2}[/\.\-]\d{1,2}[/\.\-]\d{2,4}',  # DD/MM/YYYY
                r'\d{1,2}:\d{2}',  # Time HH:MM
            ]
            for pattern in date_patterns:
                if re.search(pattern, all_text):
                    analysis["has_date"] = True
                    break

        if section_type == "footer":
            # Total patterns
            total_patterns = [r'סה"כ', r'סכום', r'לתשלום']
            for pattern in total_patterns:
                if re.search(pattern, all_text):
                    analysis["has_total"] = True
                    break

            # VAT patterns
            vat_patterns = [r'מע"מ', r'ערך מוסף']
            for pattern in vat_patterns:
                if re.search(pattern, all_text):
                    analysis["has_vat"] = True
                    break

        return analysis

    def _find_column_headers(self, lines: List[str]) -> List[str]:
        """Find lines that look like column headers."""
        headers = []

        for line in lines:
            line_lower = line.lower()

            # Check for header keywords
            has_header_keyword = any(
                keyword in line_lower
                for keyword in self.item_indicator_keywords
            )

            # Check for common header patterns (multiple Hebrew words in a row)
            hebrew_words = re.findall(r'[\u0590-\u05FF]+', line)
            if len(hebrew_words) >= 2 and has_header_keyword:
                headers.append(line)

            # Also look for lines with spaced-out words (like a header row)
            if '  ' in line and len(line.split()) >= 3:  # Multiple words with spacing
                headers.append(line)

        return headers

    def _detect_table_structure(self, lines: List[str]) -> Dict[str, Any]:
        """Detect if text appears to be in a table structure."""
        analysis = {
            "is_table_like": False,
            "consistent_columns": False,
            "max_columns": 0,
            "column_alignment": None
        }

        if len(lines) < 3:
            return analysis

        # Check if lines have consistent column-like structure
        # Look for lines with similar number of "fields" (groups of non-space chars)
        field_counts = []
        for line in lines[:20]:  # Check first 20 lines
            # Split by multiple spaces (column-like separation)
            fields = [f for f in line.split('  ') if f.strip()]
            field_counts.append(len(fields))

        # Count occurrences of each field count
        from collections import Counter
        count_freq = Counter(field_counts)
        most_common = count_freq.most_common(1)

        if most_common and most_common[0][0] > 1:  # At least 2 columns
            analysis["is_table_like"] = True
            analysis["max_columns"] = most_common[0][0]
            analysis["column_alignment"] = "spaces"  # Assuming space-separated columns

            # Check consistency
            if most_common[0][1] >= len(field_counts) * 0.5:  # At least 50% consistent
                analysis["consistent_columns"] = True

        return analysis

    def _validate_with_reconstructed_rows(
        self,
        segmented: Dict[str, Any],
        reconstructed_rows: List[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Validate segmentation against reconstructed rows from Phase 2.

        This helps ensure consistency between polygon-based reconstruction
        and text-based segmentation.
        """
        if not reconstructed_rows:
            return segmented

        # Convert reconstructed rows to text
        from phases.phase2_row_reconstruction import RowReconstructor
        temp_reconstructor = RowReconstructor()
        row_texts = temp_reconstructor.rows_to_text(reconstructed_rows)

        segmented["reconstructed_row_count"] = len(reconstructed_rows)
        segmented["reconstructed_row_texts"] = row_texts

        # Compare with our segmented item blocks
        item_blocks = segmented.get("item_blocks", [])
        if item_blocks:
            # Simple comparison: count similarity
            block_texts = [' '.join(block) for block in item_blocks]

            print(f"  Validation: {len(row_texts)} reconstructed rows vs {len(block_texts)} segmented blocks")

            # TODO: More sophisticated matching could be added here

        return segmented


def test_raw_text_segmentation():
    """Test Phase 3 functionality with sample data."""
    print("Testing Raw Text Segmentation (Phase 3)")
    print("=" * 60)

    # Sample raw text from a receipt
    sample_raw_text = """תנובה
    סניף: מרכז
    קופה: 5
    תאריך: 23.03.2025 14:30

    פריט תיאור כמות מחיר סה"כ
    1. קוטג 5% 250 גרם 4.97 4.97
    2. חלב 3% 1 ליטר 6.50 13.00
    3. לחם מחיטה מלאה 8.90 8.90

    סה"כ לפני מע"מ: 26.87
    מע"מ: 4.30
    סה"כ לתשלום: 31.17

    תודה ולהתראות!"""

    print("Sample raw text:")
    print("-" * 40)
    print(sample_raw_text)
    print("-" * 40)

    # Create segmenter
    segmenter = RawTextSegmenter()

    # Segment the text
    segmented = segmenter.segment_raw_text(sample_raw_text)

    print("\nSegmentation details:")

    # Print header
    header = segmented.get("header_lines", [])
    if header:
        print(f"\nHeader ({len(header)} lines):")
        for i, line in enumerate(header):
            print(f"  {i+1}: {line}")

    # Print item blocks
    item_blocks = segmented.get("item_blocks", [])
    if item_blocks:
        print(f"\nItem blocks ({len(item_blocks)}):")
        for i, block in enumerate(item_blocks):
            print(f"  Block {i+1} ({len(block)} lines):")
            for j, line in enumerate(block):
                print(f"    {j+1}: {line}")

    # Print footer
    footer = segmented.get("footer_lines", [])
    if footer:
        print(f"\nFooter ({len(footer)} lines):")
        for i, line in enumerate(footer):
            print(f"  {i+1}: {line}")

    # Print analysis
    header_analysis = segmented.get("header_analysis", {})
    if header_analysis:
        print(f"\nHeader analysis: {header_analysis}")

    footer_analysis = segmented.get("footer_analysis", {})
    if footer_analysis:
        print(f"Footer analysis: {footer_analysis}")

    column_headers = segmented.get("column_headers", [])
    if column_headers:
        print(f"\nColumn headers found:")
        for header in column_headers:
            print(f"  - {header}")

    table_structure = segmented.get("table_structure", {})
    if table_structure:
        print(f"\nTable structure: {table_structure}")

    # Validation
    expected_blocks = 3  # Should find 3 item blocks
    if len(item_blocks) == expected_blocks:
        print(f"\n✓ Correctly segmented {expected_blocks} item blocks")
        return True
    else:
        print(f"\n✗ Expected {expected_blocks} item blocks, got {len(item_blocks)}")
        return False


if __name__ == "__main__":
    success = test_raw_text_segmentation()
    if success:
        print("\nPhase 3 test passed!")
    else:
        print("\nPhase 3 test failed!")