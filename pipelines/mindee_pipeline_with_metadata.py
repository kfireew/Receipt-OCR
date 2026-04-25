#!/usr/bin/env python3
"""
Mindee Pipeline WITH METADATA for GUI integration

This version wraps the pipeline results with metadata needed by the GUI:
- vendor_info
- column_info
- quantity_pattern
- confidence_score
- cache_hit
"""

import os
import sys
from typing import Dict, Any

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

from dotenv import load_dotenv
load_dotenv()


def process_receipt_with_metadata(
    image_path: str,
    use_cache: bool = True,
    force_new_detection: bool = False,
    gui_callbacks: dict = None,
) -> Dict[str, Any]:
    """
    Process receipt with metadata for GUI integration.

    Returns a dict with:
    - GDocument: The main result
    - vendor_info: Vendor detection info
    - column_info: Column detection info
    - quantity_pattern: Detected quantity pattern
    - confidence_score: Overall confidence (0.0-1.0)
    - cache_hit: Whether vendor cache was used
    - raw_text: Raw OCR text (for layout review)
    """
    try:
        # Try to use cache-enabled pipeline first
        from pipelines.mindee_pipeline_with_cache import process_receipt_with_cache

        print(f"\n{'='*80}")
        print(f"PROCESSING WITH CACHE & METADATA: {os.path.basename(image_path)}")
        print(f"{'='*80}")

        # Get the base result
        gdoc_result = process_receipt_with_cache(
            image_path,
            use_cache=use_cache,
            force_new_detection=force_new_detection,
            gui_callbacks=gui_callbacks
        )

        # Extract vendor info from cache pipeline if possible
        # This would require the cache pipeline to expose this info
        # For now, we'll simulate it

        # Try to detect vendor from result
        vendor_info = _extract_vendor_info(gdoc_result)

        # Try to get column info (would need to be exposed by pipeline)
        column_info = _extract_column_info(gdoc_result)

        # Estimate confidence score based on various factors
        confidence_score = _estimate_confidence(gdoc_result, vendor_info, column_info)

        # Determine if cache was hit
        cache_hit = use_cache and vendor_info.get('vendor_slug') is not None

        # Get raw text (would need to be captured during processing)
        raw_text = _get_raw_text(image_path) if cache_hit else ""

        # Quantity pattern (default to 1)
        quantity_pattern = 1

        # Build final result with metadata
        result = {
            'GDocument': gdoc_result,
            'vendor_info': vendor_info,
            'column_info': column_info,
            'quantity_pattern': quantity_pattern,
            'confidence_score': confidence_score,
            'cache_hit': cache_hit,
            'raw_text': raw_text
        }

        return result

    except ImportError as e:
        print(f"Cache pipeline not available: {e}")
        print("Falling back to basic pipeline...")

        # Fall back to basic pipeline
        from pipelines.mindee_pipeline import process_receipt

        gdoc_result = process_receipt(image_path)

        # Basic metadata for fallback
        result = {
            'GDocument': gdoc_result,
            'vendor_info': {},
            'column_info': {},
            'quantity_pattern': 1,
            'confidence_score': 0.5,  # Medium confidence
            'cache_hit': False,
            'raw_text': ""
        }

        return result


def _extract_vendor_info(gdoc_result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract vendor info from GDocument result."""
    vendor_info = {
        'vendor_slug': None,
        'vendor_name': None,
        'trust_score': 0.0,
        'match_score': 0.0
    }

    # Try to extract vendor from GDocument fields
    gdoc = gdoc_result.get('GDocument', {})
    fields = gdoc.get('fields', [])

    # Check for VendorNameS (correct field name)
    vendor_name = ''
    for field in fields:
        if field.get('name') == 'VendorNameS':  # Correct field name
            vendor_name = field.get('value', '')
            break

    if vendor_name:
        vendor_info['vendor_name'] = vendor_name
        # Create simple slug from vendor name
        vendor_slug = vendor_name.lower().replace(' ', '_').replace('-', '_')
        vendor_info['vendor_slug'] = vendor_slug
        # Default trust score for known vendors
        vendor_info['trust_score'] = 0.7
        vendor_info['match_score'] = 0.8

    return vendor_info


def _extract_column_info(gdoc_result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract column info from GDocument result."""
    column_info = {
        'detected_columns': [],
        'headers': [],
        'confidence': 0.0,
        'column_mapping': {}
    }

    # Try to extract from GDocument structure
    gdoc = gdoc_result.get('GDocument', {})
    groups = gdoc.get('groups', [])

    if groups and len(groups) > 0:
        table_group = groups[0]
        # Check if table group has column info
        if 'column_definitions' in table_group:
            column_defs = table_group['column_definitions']
            column_info['detected_columns'] = column_defs

            # Extract headers
            headers = [col.get('header', '') for col in column_defs]
            column_info['headers'] = [h for h in headers if h]

            # Estimate confidence based on number of columns
            if len(column_defs) >= 3:
                column_info['confidence'] = 0.8
            elif len(column_defs) >= 2:
                column_info['confidence'] = 0.6
            else:
                column_info['confidence'] = 0.4

            # Create column mapping
            for col in column_defs:
                header = col.get('header', '')
                col_type = col.get('type', 'unknown')
                if header:
                    column_info['column_mapping'][header] = col_type

    return column_info


def _estimate_confidence(
    gdoc_result: Dict[str, Any],
    vendor_info: Dict[str, Any],
    column_info: Dict[str, Any]
) -> float:
    """Estimate overall confidence score (0.0-1.0)."""
    confidence = 0.5  # Base confidence

    # Factor 1: Vendor detection
    if vendor_info.get('vendor_slug'):
        confidence += 0.2
        # Higher trust score increases confidence
        trust_score = vendor_info.get('trust_score', 0.0)
        confidence += trust_score * 0.1

    # Factor 2: Column detection
    column_confidence = column_info.get('confidence', 0.0)
    confidence += column_confidence * 0.2

    # Factor 3: Number of items extracted
    gdoc = gdoc_result.get('GDocument', {})
    groups = gdoc.get('groups', [])
    if groups and len(groups) > 0:
        table_group = groups[0]
        items = table_group.get('groups', [])
        if len(items) >= 5:
            confidence += 0.1
        elif len(items) >= 2:
            confidence += 0.05

    # Cap at 1.0
    return min(confidence, 1.0)


def _get_raw_text(image_path: str) -> str:
    """Get raw OCR text for layout review."""
    try:
        # This would need to actually perform OCR
        # For now, return empty or simulate
        return f"Raw text for {os.path.basename(image_path)} would appear here..."
    except Exception:
        return ""


# Backward compatibility
def process_receipt(*args, **kwargs):
    """Alias for backward compatibility."""
    return process_receipt_with_metadata(*args, **kwargs)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python mindee_pipeline_with_metadata.py <receipt_file>")
        sys.exit(1)

    result = process_receipt_with_metadata(sys.argv[1])
    print(f"\nPipeline completed with metadata.")
    print(f"  GDocument present: {'GDocument' in result}")
    print(f"  Vendor info: {result.get('vendor_info', {})}")
    print(f"  Confidence score: {result.get('confidence_score', 0.0):.2f}")
    print(f"  Cache hit: {result.get('cache_hit', False)}")

    if 'GDocument' in result:
        gdoc = result['GDocument']
        items = gdoc.get('groups', [{}])[0].get('groups', [])
        print(f"  Items extracted: {len(items)}")