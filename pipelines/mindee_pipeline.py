"""
Mindee Pipeline - Receipt extraction using Mindee API.

Usage:
    from pipelines.mindee_pipeline import process_receipt
    result = process_receipt("receipt.pdf")
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple, Any
import os
import sys

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

# Load .env for API keys
from dotenv import load_dotenv
load_dotenv()

# API Configuration

API_KEY = os.environ.get("MINDEE_API_KEY", "")
MODEL_ID = os.environ.get("MINDEE_MODEL_ID")
if not MODEL_ID:
    raise ValueError("MINDEE_MODEL_ID not found in .env file")


@dataclass
class MindeeItem:
    """Item extracted from receipt."""
    description: str
    quantity: float
    unit_price: float
    total: float


def process_receipt(
    image_path: str,
    api_key: str = None,
    model_id: str = None,
    save_to_output: bool = True,
    gui_callbacks: dict = None,
) -> dict:
    """
    Process receipt using Mindee 2-scan method with 8-phase pipeline.

    Args:
        image_path: Path to receipt file (PDF, PNG, JPG)
        api_key: Mindee API key
        model_id: Mindee model ID
        save_to_output: Save result to output/ folder
        gui_callbacks: Optional dict of GUI callback functions for user decisions

    Returns:
        GDocument dict with items
    """
    from pipelines._mindee import MindeeClient, MindeeParser, MindeeFormatter
    from utils.post_processor import process_items

    # Import phase implementations
    from phases.phase2_smart_column_segmentation import Phase2SmartColumnSegmentation
    from phases.phase3_column_detection import Phase3ColumnDetection
    from phases.phase4_quantity_pattern import Phase4QuantityPattern
    from phases.phase5_product_list import Phase5ProductList
    from phases.phase6_vendor_cache import Phase6VendorCache

    key = api_key or API_KEY
    mid = model_id or MODEL_ID

    print(f"\n{'='*80}")
    print(f"Processing receipt: {os.path.basename(image_path)}")
    print(f"{'='*80}")

    # Initialize components
    client = MindeeClient(key, mid)
    parser = MindeeParser()
    formatter = MindeeFormatter()

    # ========== PHASE 1: TWO SCANS ==========
    print("\nPHASE 1: Performing two scans...")

    # SCAN A: JSON scan
    print("  Scan A: JSON scan for structured data")
    json_response = client.scan_receipt_model(image_path)
    fields = parser.parse_fields(json_response.inference.result.fields)

    header = parser.extract_header(fields)
    items = parser.extract_items(fields)

    print(f"    Extracted {len(items)} items from JSON scan")

    # SCAN B: Raw OCR text scan
    print("  Scan B: Raw OCR text scan")
    raw_text = client.raw_text(image_path)

    if raw_text:
        print(f"    Extracted {len(raw_text)} characters of raw text")
        if len(raw_text) > 0:
            print(f"    Preview (first 300 chars): {raw_text[:300]}...")
    else:
        print("    WARNING: Raw OCR text scan failed or returned empty")
        # No fallback available - OCR model failed

    if not items:
        print("ERROR: No items extracted from receipt")
        return {"error": "No items extracted"}

    # ========== PHASE 6: EARLY VENDOR DETECTION (for cache) ==========
    print("\nPHASE 6: Early vendor detection for cache...")
    vendor_cache = Phase6VendorCache(gui_callbacks=gui_callbacks)
    vendor_info = {
        'name': header.get('vendor', ''),
        'slug': None,
        'cache_entry': None,
        'detected': False
    }

    # Detect vendor from raw text if available
    if raw_text and len(raw_text) > 0:
        vendor_detection = vendor_cache.detect_vendor_from_text(raw_text)

        if vendor_detection.get('success'):
            vendor_name = vendor_detection['vendor_name']
            vendor_english_key = vendor_detection.get('vendor_english_key')
            vendor_slug = vendor_english_key.lower() if vendor_english_key else vendor_cache._hebrew_to_english_key(vendor_name)
            cache_entry = vendor_cache.find_vendor(vendor_name, vendor_english_key)

            vendor_info = {
                'name': vendor_name,
                'english_key': vendor_english_key,
                'slug': vendor_slug,
                'cache_entry': cache_entry,
                'detected': True,
                'detection_result': vendor_detection
            }

            print(f"  Detected vendor: {vendor_name}")
            if cache_entry:
                confidence = vendor_cache._get_current_trust_score(cache_entry)
                print(f"  Cache entry found (trust_score: {confidence:.2f})")
        else:
            print(f"  No vendor detected in raw text")
    else:
        print(f"  SKIPPED: No raw text for vendor detection")

    # ========== PHASE 3: COLUMN DETECTION ==========
    print("\nPHASE 3: Column detection...")
    column_detector = Phase3ColumnDetection()
    column_info = None

    # Check if we have column info from cache
    cache_entry = vendor_info.get('cache_entry')
    if cache_entry and vendor_cache.should_skip_column_detection(cache_entry):
        # CACHE HIT: Use get_column_info_from_cache method
        column_info, success = vendor_cache.get_column_info_from_cache(cache_entry, raw_text)

        if success and column_info:
            print(f"  Using cached layout for {vendor_info.get('name')} with {len(column_info.get('detected_columns', []))} columns")
            lines_range = column_info.get('lines_range')
            if lines_range:
                print(f"  Found headers at lines {lines_range[0]+1}-{lines_range[1]}")
            else:
                print(f"  WARNING: Could not find header lines for cached columns")
        else:
            print(f"  WARNING: Failed to apply cached column assignments, falling back to detection")
            cache_entry = None  # Force fallback to detection
        # Add column info to items (similar to apply_column_mapping)
        if column_info and success:
            for item in items:
                item['column_info'] = {
                    'detected_columns': column_info.get('detected_columns', []),
                    'net_total_column': None,
                    'net_total_found': False,
                    'fallback_used': False,
                    'vendor_cache_used': True
                }
    elif raw_text and len(raw_text) > 0:
        # CACHE MISS or not trusted: Run column detection
        vendor_slug = vendor_info.get('slug')
        has_vendor_cache = vendor_info.get('cache_entry') is not None

        column_info = column_detector.detect_columns(
            raw_text,
            vendor_slug=vendor_slug,
            has_vendor_cache=has_vendor_cache
        )
        if column_info.get('success'):
            print(f"  Detected columns: {column_info.get('detected_columns', [])}")
            # Apply column mapping to items (adds column info metadata)
            items = column_detector.apply_column_mapping(items, column_info)
        else:
            print(f"  Column detection failed: {column_info.get('error', 'Unknown error')}")
    else:
        print("  SKIPPED: No raw text for column detection")

    # ========== PHASE 2: SMART COLUMN SEGMENTATION ==========
    print("\nPHASE 2: Smart column segmentation (three-layer intelligence)...")
    if raw_text and len(raw_text) > 0:
        # Use smarter Phase 2 that combines column-awareness with robust fallback
        segmenter = Phase2SmartColumnSegmentation()
        items = segmenter.segment_raw_text(items, raw_text, column_info)
        print(f"  Enhanced {len([i for i in items if i.get('segmentation_success', False)])}/{len(items)} items")

        # Debug: Check for extracted_numbers (critical for Phase 4)
        items_with_numbers = sum(1 for i in items if i.get('extracted_numbers', []))
        print(f"  Items with extracted_numbers: {items_with_numbers}/{len(items)} (Phase 4 compatibility)")
    else:
        print("  SKIPPED: No raw text available")

    # ========== PHASE 4: QUANTITY PATTERN DETECTION ==========
    print("\nPHASE 4: Quantity pattern detection...")
    quantity_detector = Phase4QuantityPattern()
    pattern_info = quantity_detector.detect_quantity_pattern(items)

    if pattern_info.get('success'):
        print(f"  Detected pattern: {pattern_info.get('pattern')}")

        # Apply pattern to extract quantities
        for i, item in enumerate(items):
            new_qty = quantity_detector.extract_quantity_from_block(item, pattern_info)
            if new_qty != item.get('quantity'):
                items[i]['quantity'] = new_qty
                items[i]['quantity_source'] = 'pattern_detection'
    else:
        print(f"  No pattern detected: {pattern_info.get('reason', 'Unknown')}")

    # ========== PHASE 5: PRODUCT LIST INTEGRATION ==========
    print("\nPHASE 5: Product list integration...")
    product_list = Phase5ProductList()

    # Use detected vendor name for filtering (prefer detected over header)
    vendor_name = vendor_info.get('name') or header.get('vendor', '')
    if vendor_name:
        try:
            print(f"  Using vendor for filtering: {vendor_name}")
        except UnicodeEncodeError:
            print(f"  Using vendor for filtering: [Hebrew vendor name]")

    items = product_list.enrich_items(items, vendor_name)

    # Count items with CatalogNo
    items_with_catalog = sum(1 for item in items if item.get('catalog_no'))
    print(f"  Found CatalogNo for {items_with_catalog}/{len(items)} items")

    # ========== PHASE 6: CACHE UPDATE (after successful parse) ==========
    print("\nPHASE 6: Cache update...")

    # Update cache if vendor was detected and column detection was successful
    if vendor_info.get('detected') and column_info and column_info.get('success'):
        vendor_name = vendor_info['name']

        # Get row format from Phase 2 segmentation if available
        row_format = 'unknown'
        if items and len(items) > 0:
            first_item = items[0]
            if first_item.get('block_pattern'):
                row_format = first_item.get('block_pattern')
            elif first_item.get('segmentation_success'):
                # Try to determine from item structure
                if 'item_block' in first_item and len(first_item['item_block']) > 3:
                    row_format = 'multiline'
                else:
                    row_format = 'single_line'

        # Collect validation metrics for trust score calculation
        def collect_validation_metrics(items, column_info, pattern_info, cache_entry):
            """Collect validation metrics for trust score calculation."""
            metrics = {
                'column_confidence': 0.5,
                'validation_rate': 0.5,
                'pattern_consistency': 0.5,
                'user_verification': 0.5
            }

            # 1. Column confidence from Phase 3
            if column_info and 'detection_score' in column_info:
                metrics['column_confidence'] = column_info.get('detection_score', 0.5)
            elif column_info and column_info.get('success'):
                # If success but no score, use 0.8 as default
                metrics['column_confidence'] = 0.8

            # 2. Validation rate: Check qty × price ≈ total for each item
            validated_count = 0
            total_items = 0

            if items and len(items) > 0:
                validated_count = 0
                total_items = len(items)

                for item in items:
                    quantity = item.get('quantity', 0)
                    unit_price = item.get('unit_price', 0)
                    total = item.get('line_total', 0)

                    # Calculate expected total
                    if quantity > 0 and unit_price > 0:
                        expected_total = quantity * unit_price
                        # Check if within 5% tolerance
                        if abs(expected_total - total) / max(expected_total, 1.0) <= 0.05:
                            validated_count += 1

                metrics['validation_rate'] = validated_count / total_items if total_items > 0 else 0.5

            # 3. Pattern consistency from Phase 4
            if pattern_info and pattern_info.get('success'):
                # Pattern detected successfully → high consistency
                metrics['pattern_consistency'] = 0.8
            elif pattern_info and pattern_info.get('pattern'):
                # Pattern exists but success=False → medium consistency
                metrics['pattern_consistency'] = 0.6
            else:
                # No pattern detected → low consistency
                metrics['pattern_consistency'] = 0.3

            # 4. User verification from existing cache entry
            if cache_entry:
                # Check for user verification in v2.0 structure
                if 'confidence' in cache_entry and isinstance(cache_entry['confidence'], dict):
                    if cache_entry['confidence'].get('user_verified', False):
                        metrics['user_verification'] = 1.0
                    else:
                        # Not verified by user yet
                        metrics['user_verification'] = 0.5
                # Check for legacy confirmed_by_user in legacy_fields (v2.0 backward compatibility)
                elif cache_entry.get('legacy_fields', {}).get('confirmed_by_user', False):
                    metrics['user_verification'] = 1.0
                else:
                    metrics['user_verification'] = 0.5
            # else: already set to 0.5 default

            print(f"Phase 6: Validation metrics collected:")
            print(f"  Column confidence: {metrics['column_confidence']:.2f}")
            print(f"  Validation rate: {metrics['validation_rate']:.2f} ({validated_count}/{len(items) if items else 0})")
            print(f"  Pattern consistency: {metrics['pattern_consistency']:.2f}")
            print(f"  User verification: {metrics['user_verification']:.2f}")

            return metrics

        validation_metrics = collect_validation_metrics(
            items, column_info, pattern_info, vendor_info.get('cache_entry')
        )

        # Update cache with successful parse results and validation metrics
        cache_entry = vendor_cache.add_or_update_vendor(
            vendor_name,
            column_info=column_info,
            quantity_pattern=pattern_info.get('pattern'),
            row_format=row_format,
            vendor_english_key=vendor_info.get('english_key'),
            validation_metrics=validation_metrics
        )
        if cache_entry:  # Only if cache was actually created/updated
            confidence = vendor_cache._get_current_trust_score(cache_entry)
            print(f"  Updated cache for {vendor_name} (trust_score: {confidence:.2f})")
        else:
            print(f"  No cache created for {vendor_name} (user declined or error)")
    else:
        print(f"  No cache update (vendor detection: {vendor_info.get('detected', False)}, column success: {column_info.get('success', False) if column_info else False})")

    # ========== PHASE 7: ABBYY JSON OUTPUT ==========
    print("\nPHASE 7: Formatting ABBYY JSON output...")

    # Convert items to format expected by formatter
    formatted_items = []
    for item in items:
        formatted_item = {
            'description': item.get('description', ''),
            'quantity': item.get('quantity', 1.0),
            'unit_price': item.get('unit_price', 0.0),
            'line_total': item.get('line_total', 0.0)
        }

        # Add CatalogNo if available
        if item.get('catalog_no'):
            formatted_item['catalog_no'] = item['catalog_no']

        formatted_items.append(formatted_item)

    # Apply post-processing
    try:
        fixed_items = process_items(formatted_items)
    except Exception as e:
        print(f"  Post-processing failed: {e}")
        fixed_items = formatted_items

    # Format output
    receipt_name = formatter.generate_receipt_name(
        header['vendor'], header['date'], image_path
    )

    print(f"  Creating ABBYY format for {len(fixed_items)} items")
    gdoc = formatter.format(fixed_items, header['vendor'], header['date'], receipt_name)

    if save_to_output:
        formatter.save_to_output(gdoc, receipt_name)
        print(f"  Saved to output/{receipt_name}.json")

    print(f"\n{'='*80}")
    print("Processing complete!")
    print(f"{'='*80}")

    # Build metadata result for GUI
    # Initialize variables with defaults to avoid NameError
    confidence_score = 0.5  # Default confidence
    cache_hit = False
    cache_entry_exists = False
    confidence_exists = False

    # Check if cache_entry variable exists and has a value
    try:
        if cache_entry:  # This will raise NameError if cache_entry doesn't exist
            cache_entry_exists = True
    except NameError:
        cache_entry_exists = False

    # Check if confidence variable exists
    try:
        confidence  # This will raise NameError if confidence doesn't exist
        confidence_exists = True
    except NameError:
        confidence_exists = False

    # Get confidence score
    if cache_entry_exists:
        confidence_score = vendor_cache._get_current_trust_score(cache_entry)
    elif confidence_exists:
        confidence_score = confidence

    # Determine if cache was hit
    cache_hit = vendor_info.get('detected', False) and vendor_info.get('cache_entry') is not None

    # Build result with metadata
    result = {
        'GDocument': gdoc,
        'vendor_info': {
            'vendor_slug': vendor_info.get('slug'),
            'vendor_name': vendor_info.get('name'),
            'trust_score': confidence_score,
            'match_score': vendor_info.get('detection_result', {}).get('match_score', 0.0) if vendor_info.get('detected') else 0.0
        },
        'column_info': column_info if 'column_info' in locals() else {},
        'quantity_pattern': pattern_info.get('pattern', 1) if 'pattern_info' in locals() else 1,
        'confidence_score': confidence_score,
        'cache_hit': cache_hit,
        'raw_text': raw_text if 'raw_text' in locals() else ""
    }

    return result


def _find_header_lines_for_cached_columns(raw_text: str, column_mapping: Dict[str, str]) -> Optional[Tuple[int, int]]:
    """
    Find header lines in raw text that contain cached column headers.

    Args:
        raw_text: Raw text from scan
        column_mapping: Dict mapping Hebrew column headers to field names

    Returns:
        Tuple of (start_line_idx, end_line_idx) or None if not found
    """
    if not raw_text or not column_mapping:
        return None

    lines = raw_text.splitlines()
    column_headers = list(column_mapping.keys())

    # Look for lines that contain multiple column headers
    best_start = None
    best_end = None
    best_score = 0

    # Search window of 1-3 lines (headers can span multiple lines)
    for start in range(min(20, len(lines))):  # Check first 20 lines
        for window_size in range(1, 4):  # 1 to 3 line window
            end = start + window_size
            if end > len(lines):
                break

            # Combine lines in window
            window_text = " ".join(lines[start:end])

            # Count how many column headers are found in this window
            found_headers = 0
            for header in column_headers:
                if header in window_text:
                    found_headers += 1

            # Score based on percentage of headers found
            score = found_headers / len(column_headers) if column_headers else 0

            if score > best_score and score >= 0.5:  # At least 50% of headers
                best_score = score
                best_start = start
                best_end = end

    if best_start is not None and best_end is not None:
        return (best_start, best_end)

    return None


def extract_items(image_path: str) -> List[MindeeItem]:
    """Extract just the items list from a receipt."""
    result = process_receipt(image_path)
    groups = result.get("GDocument", {}).get("groups", [])
    if groups and len(groups) > 0:
        table_items = groups[0].get("groups", [])
        return [
            MindeeItem(
                description=self._get_field_value(item, "description"),
                quantity=self._get_field_value(item, "quantity"),
                unit_price=self._get_field_value(item, "price"),
                total=self._get_field_value(item, "linetotal"),
            )
            for item in table_items
        ]
    return []

def _get_field_value(item: dict, field_name: str) -> float:
    """Get numeric value from item fields."""
    fields = item.get("fields", [])
    for f in fields:
        if f.get("name") == field_name:
            try:
                return float(f.get("value", 0))
            except ValueError:
                return 0
    return 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python mindee_pipeline.py <receipt_file>")
        sys.exit(1)

    result = process_receipt(sys.argv[1])
    print("Extracted successfully!")