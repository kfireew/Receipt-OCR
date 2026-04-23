"""
PHASE 3: COLUMN DETECTION - LOOP-INSIDE-LOOP

Implements Phase 3 from AGENT_GUIDE.md:

STRATEGY: Try different header regions, parse each, pick best
1. OUTER LOOP: Try line ranges 1-3, 1-4, 1-5, 1-6, 1-7, 1-8
2. INNER LOOP: Parse each candidate region for Hebrew column headers
3. FALLBACK: Try single lines 1, 2, 3, 4, 5

HEBREW COLUMN KEYWORDS - EXACT MAPPING:
תאור, פריט, מוצר → "description" (product description)
ברקוד, קוד → "product_code" (product code/barcode)
תומכ, יחיד, כמות, יחידות → "quantity" (quantity)
יחיד ריחמ, ריחמ, מחיר יחידה, מחיר ליחידה → "unit_price" (unit price)
ברוטו, ברוטו שורה, סכום ברוטו → "line_gross_total" (gross total)
נטו, נטו שורה, שורה נטו, סכום, שורה → "line_net_total" (NET TOTAL - MOST IMPORTANT)
החנה, הנחה, תחנה → "discount" (discount amount)
אחוז הנחה → "discount_percent" (discount percentage)
משקל, גרם → "weight" (weight for weight-based items)

CRITICAL: MUST identify which column is NET LINE TOTAL (נטו) - goes to LineTotal
"""

import re
from typing import List, Dict, Any, Tuple, Optional


class Phase3ColumnDetection:
    """
    Phase 3: Column detection using loop-inside-loop strategy.

    Detects receipt column structure by trying multiple header regions
    and selecting the best match.
    """

    def __init__(self):
        # Hebrew to English column mapping
        self.hebrew_keywords = {
            'description': [
                'תאור', 'תיאור', 'פריט', 'מוצר', 'מוצד', 'פריי',
                'תור', 'תיר', 'תאר', 'שם', 'שם מוצר',  # OCR variations
                'מוצר שם', 'שם הפריט', 'שם המוצר'  # Wine vendor variations
            ],
            'product_code': [
                'ברקוד', 'ברקד', 'קוד', 'ברוקוד', 'ברוד',
                'ברקז', 'ברקזד', 'קוד מוצר', 'קוד פריט',  # OCR variations
                'מק"ט', 'מספר', 'מספר פריט'  # Wine vendor codes
            ],
            'quantity': [
                'תומכ', 'תומך', 'יחיד', 'כמות', 'יחידות', 'כמת',
                'תמך', 'תמכ', 'תומק', 'מספר יחידות',  # OCR variations
                'מ"ר', 'יח', 'יחידות'  # Abbreviations
            ],
            'unit_price': [
                'יחיד ריחמ', 'ריחמ', 'מחיר יחידה', 'מחיר ליחידה',
                'יחריחמ', 'ריחם', 'מחיר', 'מחירון',  # OCR variations
                'מחיר ליח', 'מחיר ליחיד', 'מחיר יח',  # Wine vendor variations
                'עלות', 'מחיר קניה', 'מחיר מכירה'
            ],
            'line_gross_total': [
                'ברוטו', 'ברוטא', 'ברוטה', 'ברוט',
                'שורה ברוטו', 'סכום ברוטו', 'סה"כ ברוטו'
            ],
            'line_net_total': [
                'נטו', 'נטא', 'נטה', 'נתו',
                'שורה נטו', 'נטו שורה', 'סכום', 'שורה',
                'סה"כ', 'סיכום', 'סה"כ נטו', 'סה"כ שורה',  # Wine vendor totals
                'לתשלום', 'סך הכל', 'סך הכל נטו'
            ],
            'discount': [
                'החנה', 'הנחה', 'תחנה', 'חנה', 'נחה',
                'החנח', 'הנחח', 'הנחה %', 'אחוז הנחה'  # OCR variations
            ],
            'discount_percent': [
                'אחוז הנחה', 'אחוז חנה', 'אחוז תחנה',
                '% הנחה', 'הנחה באחוזים'
            ],
            'weight': [
                'משקל', 'גרם', 'משקל', 'גרם',
                'משק', 'גר', 'ק"ג', 'ליטר', 'מ"ל'  # OCR & volume variations
            ]
        }

        # Reverse mapping for debugging
        self.english_to_hebrew = {}
        for eng, heb_list in self.hebrew_keywords.items():
            for heb in heb_list:
                self.english_to_hebrew[heb] = eng

        # Additional vendor-specific keyword expansions
        self._expand_vendor_keywords()

    def _expand_vendor_keywords(self):
        """Expand Hebrew keywords with vendor-specific variations."""
        # Wine vendor specific expansions
        wine_variations = {
            'description': ['יין', 'בקבוק', 'בקבוקים', 'משקה', 'משקאות'],
            'product_code': ['מק"ט יין', 'קוד בקבוק', 'מספר יין'],
            'quantity': ['מספר בקבוקים', 'בקבוקים', 'יחידות בקבוק'],
            'unit_price': ['מחיר בקבוק', 'מחיר ליין', 'מחיר למשקה'],
            'line_net_total': ['סה"כ בקבוקים', 'סכום יין', 'סה"כ משקאות']
        }

        # Add wine variations to main keywords
        for eng_field, heb_variations in wine_variations.items():
            if eng_field in self.hebrew_keywords:
                self.hebrew_keywords[eng_field].extend(heb_variations)
                for heb in heb_variations:
                    self.english_to_hebrew[heb] = eng_field

    def _is_likely_data_cell(self, text: str) -> bool:
        """
        Check if a cell looks like data (not a header).
        Data cells often contain prices, quantities, product codes, etc.
        """
        if not text or not text.strip():
            return False

        cleaned = text.lower().strip()

        # Check for price patterns (numbers with decimal points)
        if re.search(r'\d+\.\d+', cleaned):  # e.g., "12.50"
            return True

        # Check for quantity patterns (numbers with operators)
        if re.search(r'\d+\s*[x×]\s*\d+', cleaned):  # e.g., "2 x 1" or "2×1"
            return True

        # Check for calculation patterns (with = sign)
        if '=' in cleaned and re.search(r'\d', cleaned):
            return True

        # Check for product codes (long numbers, barcodes)
        # Barcodes often start with 729 and are 13 digits
        if re.search(r'729\d{10}', cleaned):
            return True

        # Check for item descriptions with measurements
        # e.g., "250 גרם", "1 ליטר", "750 מ\"ל"
        measurement_patterns = [
            r'\d+\s*גרם',
            r'\d+\s*ליטר',
            r'\d+\s*מ"ל',
            r'\d+\s*ק"ג',
            r'\d+\s*משקל'
        ]
        for pattern in measurement_patterns:
            if re.search(pattern, cleaned):
                return True

        # Check for percentages in descriptions
        if re.search(r'\d+\s*%', cleaned):  # e.g., "5%"
            return True

        # Check for mixed content (numbers with Hebrew)
        # Headers are usually pure Hebrew or Hebrew + a few symbols
        # Data has numbers mixed with Hebrew
        hebrew_chars = len(re.findall(r'[\u0590-\u05FF]', cleaned))
        digit_chars = len(re.findall(r'\d', cleaned))
        total_chars = len(cleaned)

        if total_chars > 0 and digit_chars > 0 and hebrew_chars > 0:
            # Has both Hebrew and digits - likely data
            # But check ratio: if mostly Hebrew with one digit, might still be header
            if digit_chars / total_chars > 0.1:  # More than 10% digits
                return True

        # Check for measurement units that appear with other text
        # e.g., "250 גרם" (data) vs "גרם" (header)
        measurement_keywords = ['גרם', 'ליטר', 'ק"ג', 'מ"ל', 'משקל']
        for keyword in measurement_keywords:
            if keyword in cleaned:
                # If the text contains the keyword plus other content (not just the keyword)
                # e.g., "גרם" alone = header, "250 גרם" = data
                if cleaned != keyword and not cleaned.endswith(' ' + keyword):
                    # Check if there's a number before the keyword
                    if re.search(r'\d.*' + keyword, cleaned):
                        return True

        return False

    def _keyword_matches_part(self, keyword: str, part_lower: str) -> bool:
        """
        Check if a keyword matches a part (cell).
        Improved to avoid false positives like "גרם" matching "250 גרם".

        Returns True if:
        1. Keyword equals the entire part (exact match)
        2. Keyword is a whole word in the part
        3. Part starts or ends with the keyword (for OCR variations)
        """
        # Exact match
        if part_lower == keyword:
            return True

        # Check if keyword is a whole word in the part
        words = re.split(r'\s+', part_lower)
        if keyword in words:
            return True

        # Check if part starts or ends with keyword (for OCR variations)
        if part_lower.startswith(keyword) or part_lower.endswith(keyword):
            # But avoid matching if keyword is just a substring of a larger word
            # e.g., "תאור" should match "תאור" but not "תאורך"
            if part_lower.startswith(keyword):
                # Check next character if exists
                if len(part_lower) > len(keyword):
                    next_char = part_lower[len(keyword)]
                    if next_char.isalpha() or next_char.isdigit():
                        return False  # Part is longer word, not just keyword
            if part_lower.endswith(keyword):
                # Check previous character if exists
                if len(part_lower) > len(keyword):
                    prev_char = part_lower[-len(keyword) - 1]
                    if prev_char.isalpha() or prev_char.isdigit():
                        return False  # Part is longer word, not just keyword
            return True

        return False

    def detect_columns(self, raw_text: str, vendor_slug: str = None, has_vendor_cache: bool = False) -> Dict[str, Any]:
        """
        Main entry point: Detect columns using loop-inside-loop strategy.

        Enhanced with vendor cache integration and fallback strategies.

        Args:
            raw_text: Raw text from scan B
            vendor_slug: Normalized vendor slug (e.g., 'tnuva') for cache lookup
            has_vendor_cache: Whether vendor has cached column_assignments

        Returns:
            Dictionary with column detection results matching TODO.md spec:
            - success: True/False
            - detected_columns: List of dicts with hebrew_text and assigned_field
            - column_mapping: Dict mapping Hebrew keywords to column types
            - net_total_column: Hebrew text of net total column (נטו)
            - fallback_used: True if default mapping used
        """
        # Initialize result structure
        result = {
            'success': False,
            'column_mapping': {},
            'detected_columns': [],
            'net_total_column': None,
            'net_total_found': False,
            'fallback_used': False,
            'vendor_cache_used': False,
            'error': None,
            'detection_score': 0.0,
            'lines_range': None
        }

        lines = raw_text.splitlines()
        print(f"Phase 3: Detecting columns in {len(lines)} lines")

        # Check vendor cache if vendor_slug provided (should check BEFORE line count)
        if vendor_slug:
            cache_result = self._check_vendor_cache(vendor_slug)
            if cache_result['success']:
                print(f"  ✓ Using cached column mapping for vendor: {vendor_slug}")
                result.update(cache_result)
                result['vendor_cache_used'] = True
                result['success'] = True
                return result

        if len(lines) < 3:
            print("  Not enough lines for column detection")
            result['error'] = 'Not enough lines'

            # Return empty mapping per TODO.md
            default_mapping = self.get_default_mapping()
            result['column_mapping'] = default_mapping
            result['fallback_used'] = True

            # Build detected_columns from mapping (will be empty)
            detected_columns = []
            for heb, eng in default_mapping.items():
                detected_columns.append({
                    'hebrew_text': heb,
                    'assigned_field': eng
                })
            result['detected_columns'] = detected_columns

            return result

        # Already checked cache above, now proceed with detection if cache not found
        if vendor_slug and not result.get('vendor_cache_used', False):
            print(f"  No valid cache entry for vendor: {vendor_slug}, running detection")

        best_result = None
        best_score = -1

        # OUTER LOOP: Try different line ranges
        # Headers are typically in first 15 lines, limit search
        max_header_lines = min(15, len(lines))
        line_ranges = [
            (0, 3),   # lines 1-3
            (0, 4),   # lines 1-4
            (0, 5),   # lines 1-5
            (0, 6),   # lines 1-6
            (0, 7),   # lines 1-7
            (0, 8),   # lines 1-8
            (0, 9),   # lines 1-9
            (0, 10),  # lines 1-10
            (0, 12),  # lines 1-12
            (0, 15),  # lines 1-15
        ]

        print("  Outer loop: Trying different line ranges...")
        for start, end in line_ranges:
            if end > len(lines):
                continue

            region_lines = lines[start:end]
            region_text = '\n'.join(region_lines)

            # INNER LOOP: Parse candidate region
            region_result = self._parse_header_region(region_lines, start)

            if region_result['success']:
                score = self._score_mapping(region_result)
                print(f"    Lines {start+1}-{end}: Score {score:.2f}")

                if score > best_score:
                    best_score = score
                    best_result = region_result
                    best_result['lines_range'] = (start, end)

        # FALLBACK: Try single lines
        if not best_result or best_score < 0.5:
            print("  Fallback: Trying single lines...")
            for i in range(min(5, len(lines))):
                line = lines[i]
                line_result = self._parse_single_header([line], i)

                if line_result['success']:
                    score = self._score_mapping(line_result)
                    print(f"    Line {i+1}: Score {score:.2f}")

                    if score > best_score:
                        best_score = score
                        best_result = line_result
                        best_result['lines_range'] = (i, i+1)

        if best_result and best_score >= 0.5:  # Minimum threshold for success
            # Identify net total column
            self._identify_net_total_column(best_result)

            print(f"  ✓ Best result: Lines {best_result.get('lines_range', (0,0))[0]+1}-{best_result.get('lines_range', (0,0))[1]}, Score: {best_score:.2f}")
            print(f"  Net total column: {best_result.get('net_total_column', 'Not found')}")

            # Convert column_assignments to column_mapping format
            column_mapping = {}
            for heb_keyword, eng_column in best_result.get('column_assignments', {}).items():
                column_mapping[heb_keyword] = eng_column

            # Build detected_columns as list of dicts (per TODO.md spec)
            detected_columns = []
            for col in best_result.get('detected_columns', []):
                # Find Hebrew keyword for this column
                heb_text = None
                for heb, eng in column_mapping.items():
                    if eng == col:
                        heb_text = heb
                        break
                detected_columns.append({
                    'hebrew_text': heb_text or '',
                    'assigned_field': col
                })

            result.update({
                'success': True,
                'detected_columns': detected_columns,  # List of dicts
                'column_mapping': column_mapping,
                'net_total_column': best_result.get('net_total_column'),  # Hebrew text
                'net_total_found': best_result.get('net_total_found', False),
                'detection_score': best_score,
                'lines_range': best_result.get('lines_range'),
                'fallback_used': False
            })

            return result
        else:
            # No headers found, return empty mapping per TODO.md
            default_mapping = self.get_default_mapping()
            print(f"  ✗ No column headers detected, using empty mapping (per TODO.md)")

            # Build detected_columns as list of dicts (will be empty)
            detected_columns = []
            net_total_column = None
            net_total_found = False

            for heb, eng in default_mapping.items():
                detected_columns.append({
                    'hebrew_text': heb,
                    'assigned_field': eng
                })

                # Check if this is net total column
                if eng == 'line_net_total':
                    net_total_column = heb
                    net_total_found = True

            result.update({
                'success': False,
                'detected_columns': detected_columns,
                'column_mapping': default_mapping,
                'net_total_column': net_total_column,
                'net_total_found': net_total_found,
                'fallback_used': True,
                'vendor_cache_used': False,
                'detection_score': 0.0,
                'lines_range': None,
                'error': 'No column headers detected'
            })

            return result

    def _parse_header_region(
        self,
        region_lines: List[str],
        start_line_idx: int
    ) -> Dict[str, Any]:
        """
        Parse a candidate header region.

        Args:
            region_lines: Lines in the region
            start_line_idx: Starting line index in full text

        Returns:
            Dictionary with parsing results
        """
        if not region_lines:
            return {'success': False}

        # Try multiline header first
        if len(region_lines) >= 2:
            multiline_result = self._parse_multiline_header(region_lines, start_line_idx)
            if multiline_result['success']:
                return multiline_result

        # Try each line as single header
        best_line_result = None
        best_line_score = -1

        for i, line in enumerate(region_lines):
            line_result = self._parse_single_header([line], start_line_idx + i)
            if line_result['success']:
                score = self._score_mapping(line_result)
                if score > best_line_score:
                    best_line_score = score
                    best_line_result = line_result

        if best_line_result:
            return best_line_result

        return {'success': False}

    def _parse_multiline_header(
        self,
        lines: List[str],
        start_line_idx: int
    ) -> Dict[str, Any]:
        """
        Parse a multiline header (2+ lines).

        Args:
            lines: Header lines
            start_line_idx: Starting line index

        Returns:
            Dictionary with column assignments
        """
        result = {
            'success': False,
            'header_lines': lines,
            'start_line': start_line_idx,
            'column_assignments': {},
            'detected_columns': [],
            'line_assignments': {}
        }

        # Combine lines for analysis
        combined_text = ' '.join(lines).lower()

        # Look for Hebrew keywords in combined text
        detected_columns = []
        for column_type, keywords in self.hebrew_keywords.items():
            for keyword in keywords:
                # FIX: Check if keyword appears as a whole word
                # Use regex to match whole words
                if re.search(r'\b' + re.escape(keyword) + r'\b', combined_text):
                    if column_type not in detected_columns:
                        detected_columns.append(column_type)
                    break

        if not detected_columns:
            return result

        # Try to assign columns to specific lines
        # Common pattern: description on one line, prices on another
        # But first, check if lines look like header lines (not data lines)
        header_line_count = 0
        data_line_count = 0

        for i, line in enumerate(lines):
            line_lower = line.lower()
            line_columns = []

            # Check if line looks like a data line
            is_data_line = self._is_likely_data_cell(line)

            if is_data_line:
                data_line_count += 1
                # Skip data lines for column assignment
                continue
            else:
                header_line_count += 1

            for column_type, keywords in self.hebrew_keywords.items():
                for keyword in keywords:
                    # FIX: Check if keyword matches as a whole word
                    if self._keyword_matches_part(keyword, line_lower):
                        if column_type not in line_columns:
                            line_columns.append(column_type)
                        # Map this keyword to column type
                        result['column_assignments'][keyword] = column_type
                        break

            if line_columns:
                result['line_assignments'][start_line_idx + i] = line_columns

        # Only succeed if we have more header-like lines than data-like lines
        # and we found at least 2 columns total
        if result['column_assignments'] and header_line_count > data_line_count and len(detected_columns) >= 2:
            result['success'] = True
            result['detected_columns'] = detected_columns
            result['is_multiline'] = True
            result['header_line_count'] = header_line_count
            result['data_line_count'] = data_line_count

        return result

    def _parse_single_header(
        self,
        lines: List[str],
        line_idx: int
    ) -> Dict[str, Any]:
        """
        Parse a single header line.

        Args:
            lines: Header line(s) - typically just one
            line_idx: Line index in full text

        Returns:
            Dictionary with column assignments
        """
        if not lines:
            return {'success': False}

        # Use first line
        line = lines[0]
        line_lower = line.lower()

        result = {
            'success': False,
            'header_lines': [line],
            'start_line': line_idx,
            'column_assignments': {},
            'detected_columns': [],
            'line_assignments': {},
            'is_multiline': False
        }

        # Split line by spaces or tabs to get "columns"
        # In Hebrew receipts, columns are often separated by multiple spaces
        # First try with 2+ spaces (more reliable for column separation)
        parts = [p for p in re.split(r'\s{2,}', line) if p.strip()]

        if len(parts) < 2:
            # Try with single spaces as fallback
            # This is less reliable but might catch headers with single spaces
            parts = [p for p in re.split(r'\s+', line) if p.strip()]

        if len(parts) < 2:
            # Not enough parts for columns
            return result

        # Try to match each part to a column type
        column_matches = []
        for part in parts:
            part_lower = part.lower()
            matched_column = None

            # Check if this part looks like a data cell (not a header)
            # Data cells often contain: prices (numbers with .), quantities, product codes
            # Header cells should be mostly Hebrew keywords
            is_likely_data_cell = self._is_likely_data_cell(part)

            if is_likely_data_cell:
                # Skip matching for data-like cells to avoid false positives
                # e.g., "250 גרם" should not match "גרם" as weight column
                column_matches.append({
                    'text': part,
                    'column_type': None,
                    'part_index': len(column_matches),
                    'is_data_cell': True
                })
                continue

            for column_type, keywords in self.hebrew_keywords.items():
                for keyword in keywords:
                    # FIX: Check if keyword is a whole word in the part, not just contained
                    # This avoids matching "גרם" in "250 גרם" or "ליטר" in "1 ליטר"
                    if self._keyword_matches_part(keyword, part_lower):
                        matched_column = column_type
                        result['column_assignments'][keyword] = column_type
                        break
                if matched_column:
                    break

            column_matches.append({
                'text': part,
                'column_type': matched_column,
                'part_index': len(column_matches),
                'is_data_cell': False
            })

        # Count successful matches
        successful_matches = [m for m in column_matches if m['column_type']]
        detected_columns = list(set([m['column_type'] for m in successful_matches if m['column_type']]))

        if len(successful_matches) >= 2:  # Need at least 2 columns
            result['success'] = True
            result['detected_columns'] = detected_columns
            result['column_matches'] = column_matches
            result['parts'] = parts
            result['line_assignments'][line_idx] = detected_columns
        elif len(successful_matches) == 1:
            # Single column match - might be footer total, not header
            # Only accept if it's part of a multiline header
            result['success'] = False
            result['single_column_found'] = successful_matches[0]['column_type']

        return result

    def _score_mapping(self, result: Dict[str, Any]) -> float:
        """
        Score a column mapping result.

        Higher scores are better.
        """
        if not result.get('success'):
            return 0.0

        score = 0.0

        # Base score for having any mapping
        if result.get('column_assignments'):
            score += 0.3

        # More columns = better (but not too many)
        detected_columns = result.get('detected_columns', [])
        num_columns = len(detected_columns)

        if 2 <= num_columns <= 6:
            score += num_columns * 0.1

        # Bonus for critical columns
        critical_columns = ['line_net_total', 'quantity', 'unit_price']
        for col in critical_columns:
            if col in detected_columns:
                score += 0.15

        # Bonus for net total column (most important)
        if 'line_net_total' in detected_columns:
            score += 0.2

        # Penalty for too many columns
        if num_columns > 6:
            score -= (num_columns - 6) * 0.1

        return min(1.0, score)  # Cap at 1.0

    def _identify_net_total_column(self, result: Dict[str, Any]):
        """
        Identify which column is the net line total (נטו).

        CRITICAL for mapping to LineTotal in output.
        Returns Hebrew keyword (e.g., 'נטו') not English field name.
        """
        if not result.get('success'):
            return

        detected_columns = result.get('detected_columns', [])
        column_assignments = result.get('column_assignments', {})

        if 'line_net_total' in detected_columns:
            # Find the Hebrew keyword used for net total
            for heb_keyword, eng_column in column_assignments.items():
                if eng_column == 'line_net_total':
                    result['net_total_column'] = heb_keyword  # Hebrew text, not English
                    result['net_total_found'] = True
                    result['net_total_keyword'] = heb_keyword
                    break
        else:
            result['net_total_column'] = None
            result['net_total_found'] = False

            # Try to infer from other columns
            if 'line_gross_total' in detected_columns:
                # Find Hebrew keyword for line_gross_total
                for heb_keyword, eng_column in column_assignments.items():
                    if eng_column == 'line_gross_total':
                        result['net_total_column'] = heb_keyword  # Use gross total as fallback
                        result['net_total_inferred'] = True
                        break

    def _check_vendor_cache(self, vendor_slug: str) -> Dict[str, Any]:
        """
        Check vendor cache for column assignments.

        Args:
            vendor_slug: Normalized vendor slug (e.g., 'tnuva')

        Returns:
            Dictionary with cached column info if available and valid
        """
        # Import here to avoid circular imports
        try:
            from phases.phase6_vendor_cache import Phase6VendorCache
            cache = Phase6VendorCache()

            entry = cache.find_vendor(vendor_slug)
            if entry and cache._is_cache_entry_valid(entry):
                column_assignments = entry.get('column_assignments', {})

                # Build detected_columns as list of dicts (per TODO.md spec)
                detected_columns = []
                for heb, eng in column_assignments.items():
                    detected_columns.append({
                        'hebrew_text': heb,
                        'assigned_field': eng
                    })

                # Identify net total column from cached assignments
                net_total_column = None
                net_total_found = False
                for heb, eng in column_assignments.items():
                    if eng == 'line_net_total':
                        net_total_column = heb  # Hebrew text
                        net_total_found = True
                        break

                # Convert to required format
                result = {
                    'success': True,
                    'detected_columns': detected_columns,  # List of dicts
                    'column_mapping': column_assignments,
                    'net_total_column': net_total_column,  # Hebrew text or None
                    'net_total_found': net_total_found,
                    'vendor_cache_entry': entry,
                    'vendor_slug': vendor_slug,
                    'vendor_cache_used': True,
                    'fallback_used': False
                }

                return result
        except ImportError:
            print(f"  Warning: Phase6VendorCache not available for vendor cache check")
        except Exception as e:
            print(f"  Warning: Error checking vendor cache: {e}")

        return {'success': False}

    def get_default_mapping(self) -> Dict[str, str]:
        """
        Get default column mapping for fallback when detection fails.

        According to TODO.md: "Return empty dict when detection fails"
        """
        # TODO.md says: "return empty mapping"
        return {}

    def apply_column_mapping(
        self,
        items: List[Dict[str, Any]],
        column_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply column mapping to items (for demonstration).

        In a real implementation, this would use the column positions
        to extract data from aligned rows.
        """
        if not column_info.get('success') and not column_info.get('fallback_used'):
            return items

        # For now, just add column info to items
        enhanced_items = []
        for item in items:
            enhanced = item.copy()
            enhanced['column_info'] = {
                'detected_columns': column_info.get('detected_columns', []),
                'net_total_column': column_info.get('net_total_column'),
                'net_total_found': column_info.get('net_total_found', False),
                'fallback_used': column_info.get('fallback_used', False),
                'vendor_cache_used': column_info.get('vendor_cache_used', False)
            }
            enhanced_items.append(enhanced)

        return enhanced_items


# Test function
def test_phase3_column_detection():
    """Test Phase 3 column detection with new features."""
    print("Testing Phase 3: Column Detection with fixes")
    print("=" * 60)

    detector = Phase3ColumnDetection()

    # Test 1: Good receipt with Hebrew headers
    raw_text_good = """תנובה
סניף מרכז

תאור פריט   כמות   מחיר יחידה   נטו
קוטג 5% 250 גרם   1   4.97   4.97
חלב 3% 1 ליטר   2   6.50   13.00

סה"כ: 17.97"""

    print("\n1. Test with Hebrew headers (should succeed):")
    print("-" * 40)
    result = detector.detect_columns(raw_text_good)
    print(f"Success: {result.get('success')}")
    print(f"Detected columns: {result.get('detected_columns', [])}")
    print(f"Column mapping: {result.get('column_mapping', {})}")
    print(f"Net total column: {result.get('net_total_column', 'Not found')}")
    print(f"Fallback used: {result.get('fallback_used', False)}")
    print(f"Vendor cache used: {result.get('vendor_cache_used', False)}")

    # Test 2: Receipt without headers
    raw_text_bad = """תנובה
סניף מרכז

קוטג 5% 250 גרם   1   4.97   4.97
חלב 3% 1 ליטר   2   6.50   13.00

סה"כ: 17.97"""

    print("\n2. Test without headers (should use default mapping):")
    print("-" * 40)
    result2 = detector.detect_columns(raw_text_bad)
    print(f"Success: {result2.get('success')}")
    print(f"Error: {result2.get('error', 'None')}")
    print(f"Column mapping: {result2.get('column_mapping', {})}")
    print(f"Fallback used: {result2.get('fallback_used', False)}")
    print(f"Detected columns with text: {result2.get('detected_columns_with_text', [])}")

    # Test 3: Test with vendor slug (cache won't exist but shows integration)
    print("\n3. Test with vendor slug parameter:")
    print("-" * 40)
    result3 = detector.detect_columns(raw_text_good, vendor_slug="tnuva")
    print(f"Success: {result3.get('success')}")
    print(f"Vendor cache used: {result3.get('vendor_cache_used', False)}")

    # Test 4: Test default mapping method
    print("\n4. Test default mapping method:")
    print("-" * 40)
    default_mapping = detector.get_default_mapping()
    print(f"Default mapping: {default_mapping}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    return result


if __name__ == "__main__":
    test_phase3_column_detection()