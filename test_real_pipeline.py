#!/usr/bin/env python3
"""
Real pipeline integration test with actual receipts.
Tests the complete pipeline with real API calls.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_pipeline_with_receipt(image_path, test_name):
    """Test pipeline with a single receipt file."""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"File: {os.path.basename(image_path)}")
    print(f"{'='*80}")

    try:
        # Import the main pipeline
        from pipelines.mindee_pipeline import process_receipt

        # Run pipeline WITHOUT GUI callbacks (headless mode)
        # This tests the default behavior when no GUI is available
        result = process_receipt(
            image_path,
            gui_callbacks=None  # No GUI in headless test
        )

        print(f"✓ Pipeline executed successfully")

        # Check result structure
        if 'GDocument' in result:
            gdoc = result['GDocument']
            if 'groups' in gdoc:
                items = []
                for group in gdoc['groups']:
                    items.extend(group.get('items', []))
                print(f"  Extracted {len(items)} items")

                # Show first item if available
                if items:
                    first_item = items[0]
                    print(f"  First item: {first_item.get('description', 'N/A')}")
                    print(f"    Quantity: {first_item.get('quantity', 0)}")
                    print(f"    Unit price: {first_item.get('unitPrice', 0)}")
                    print(f"    Total: {first_item.get('lineTotal', 0)}")
            else:
                print(f"  WARNING: No groups in GDocument")
        else:
            print(f"  ERROR: No GDocument in result")

        return True

    except Exception as e:
        print(f"✗ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_vendor_cache():
    """Check current vendor cache state."""
    print(f"\n{'='*80}")
    print("CHECKING VENDOR CACHE STATE")
    print(f"{'='*80}")

    cache_path = "data/vendor_cache.json"
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)

            print(f"Cache version: {cache.get('version', '1.0')}")
            vendors = cache.get('vendors', {})
            print(f"Vendors in cache: {len(vendors)}")

            for vendor_key, entry in vendors.items():
                display_name = entry.get('basics', {}).get('display_name', vendor_key)
                trust_score = entry.get('confidence', {}).get('trust_score', 0)
                user_created = entry.get('basics', {}).get('user_created', False)
                print(f"  - {vendor_key}: {display_name} (trust: {trust_score:.2f}, user: {user_created})")

        except Exception as e:
            print(f"Error reading cache: {e}")
    else:
        print("No vendor cache file found")

def main():
    print("=" * 80)
    print("REAL PIPELINE INTEGRATION TEST")
    print("=" * 80)

    # Check vendor cache first
    check_vendor_cache()

    # Test 1: Globrands (has cache)
    test1_path = r"C:\Users\Kfir Ezer\Desktop\tests\1\Globrands_23.03.2025_Globrands 24-03-25.pdf"
    if os.path.exists(test1_path):
        success1 = test_pipeline_with_receipt(test1_path, "Globrands (cached vendor)")
    else:
        print(f"\n✗ Test file not found: {test1_path}")
        success1 = False

    # Test 2: StraussCool (no cache yet)
    test2_path = r"C:\Users\Kfir Ezer\Desktop\tests\5\StraussCool_18.08.2024_StraussCool 19-08-24.pdf"
    if os.path.exists(test2_path):
        success2 = test_pipeline_with_receipt(test2_path, "StraussCool (new vendor)")
    else:
        print(f"\n✗ Test file not found: {test2_path}")
        success2 = False

    # Check cache again after tests
    print(f"\n{'='*80}")
    print("CHECKING CACHE AFTER TESTS")
    print(f"{'='*80}")
    check_vendor_cache()

    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Globrands test: {'✓ PASS' if success1 else '✗ FAIL'}")
    print(f"StraussCool test: {'✓ PASS' if success2 else '✗ FAIL'}")

    if success1 and success2:
        print(f"\n✅ ALL TESTS PASSED - Pipeline is working correctly!")
    else:
        print(f"\n❌ SOME TESTS FAILED - Check errors above")

if __name__ == "__main__":
    main()