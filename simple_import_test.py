#!/usr/bin/env python3
"""
Simple import test
"""

import sys
sys.path.insert(0, '.')

print("Testing basic imports...")

try:
    # Try importing Phase6VendorCache
    print("1. Importing Phase6VendorCache...")
    from phases.phase6_vendor_cache import Phase6VendorCache
    print("   ✓ Success")

    # Create instance
    vendor_cache = Phase6VendorCache(gui_callbacks=None)
    print("   ✓ Instance created")

    # Test methods
    print("   Testing _trigger_gui_callback...")
    result = vendor_cache._trigger_gui_callback('ask_replace_schema', 'Test', 0.5, 0.8)
    print(f"   ✓ Result: {result}")

except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Import test passed!")