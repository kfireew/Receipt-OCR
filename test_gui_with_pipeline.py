#!/usr/bin/env python3
"""
Test GUI with actual pipeline integration.
This test will:
1. Launch GUI
2. Load a test receipt (Globrands - has user-made cache)
3. Test that pipeline integration works
"""

import os
import sys
import tkinter as tk
from pathlib import Path
import threading
import time

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 80)
print("GUI WITH PIPELINE INTEGRATION TEST")
print("=" * 80)

def test_gui_pipeline_integration():
    """Test actual GUI with pipeline."""

    print("This test will launch the GUI window for interactive testing.")
    print("\nTEST OBJECTIVES:")
    print("1. Launch GUI window")
    print("2. Click 'Browse' button")
    print("3. Select test file: tests/1/Globrands_23.03.2025_Globrands 24-03-25.pdf")
    print("4. Verify pipeline runs with GUI callbacks")
    print("5. Since Globrands is user-made cache, NO dialog should appear")
    print("\nMANUAL TEST STEPS (you must perform these):")
    print("1. GUI will launch")
    print("2. Click the 'Browse' button (cloud upload icon)")
    print("3. Navigate to: C:\\Users\\Kfir Ezer\\Desktop\\tests\\1")
    print("4. Select: Globrands_23.03.2025_Globrands 24-03-25.pdf")
    print("5. Observe console output for pipeline messages")
    print("6. Look for: 'User-made schema for globrands - always using existing schema'")
    print("\nEXPECTED RESULT:")
    print("- Pipeline should run")
    print("- Should use cached schema (trust_score: 0.95)")
    print("- NO 'Better Schema Detected' dialog should appear (user-made schema)")
    print("- Items should be extracted successfully")

    input("\nPress Enter to launch GUI...")

    try:
        # Launch actual GUI
        import subprocess
        import time

        print("\nLaunching GUI app...")

        # Run the GUI in a separate process
        gui_process = subprocess.Popen(
            [sys.executable, "gui/app.py"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print(f"GUI launched with PID: {gui_process.pid}")
        print("\nGUI should now be visible.")
        print("Perform the manual test steps above.")
        print("\nCheck console for pipeline output messages.")

        # Let GUI run for a bit
        time.sleep(2)

        print("\nWaiting for GUI to complete (will timeout after 60 seconds)...")

        try:
            # Wait for GUI to close (with timeout)
            stdout, stderr = gui_process.communicate(timeout=60)
            print("\nGUI closed.")
            if stdout:
                print("STDOUT:", stdout[-1000:])  # Last 1000 chars
            if stderr:
                print("STDERR:", stderr[-1000:])
        except subprocess.TimeoutExpired:
            print("\nGUI still running after 60 seconds.")
            print("This is normal - GUI stays open until user closes it.")
            gui_process.terminate()
            gui_process.wait()
            print("GUI terminated.")

        return True

    except Exception as e:
        print(f"✗ GUI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_phase6_callback_logic():
    """Test Phase6 callback logic programmatically."""

    print("\n" + "="*80)
    print("PROGRAMMATIC TEST: Phase6 Callback Logic")
    print("="*80)

    try:
        from phases.phase6_vendor_cache import Phase6VendorCache

        print("\n1. Testing callback triggering logic...")

        # Track callback invocations
        callback_invocations = []

        def mock_ask_replace(vendor_name, current_score, new_score):
            callback_invocations.append({
                'type': 'ask_replace_schema',
                'vendor_name': vendor_name,
                'current_score': current_score,
                'new_score': new_score
            })
            print(f"  ✓ Mock GUI: ask_replace_schema triggered")
            print(f"    Vendor: {vendor_name}")
            print(f"    Scores: {current_score:.2f} → {new_score:.2f}")
            return True

        gui_callbacks = {'ask_replace_schema': mock_ask_replace}
        vendor_cache = Phase6VendorCache(gui_callbacks=gui_callbacks)

        print("\n2. Testing _trigger_gui_callback...")

        # Direct callback trigger
        result = vendor_cache._trigger_gui_callback('ask_replace_schema', 'TestVendor', 0.5, 0.8)
        print(f"  Result: {result}")

        if len(callback_invocations) == 1:
            print(f"✓ Callback triggered successfully")
            inv = callback_invocations[0]
            if inv['vendor_name'] == 'TestVendor' and inv['current_score'] == 0.5 and inv['new_score'] == 0.8:
                print(f"✓ Correct parameters passed")
            else:
                print(f"✗ Incorrect parameters: {inv}")
        else:
            print(f"✗ Callback not triggered")

        print("\n3. Testing fallback (no GUI) behavior...")

        vendor_cache_no_gui = Phase6VendorCache(gui_callbacks=None)

        # This should print TODO message and return True (auto-update)
        result = vendor_cache_no_gui._trigger_gui_callback('ask_replace_schema', 'TestVendor', 0.5, 0.8)
        print(f"  Fallback result: {result}")
        print(f"  (Should be True for auto-update when no GUI)")

        print("\n4. Checking cache entry user-made detection...")

        # Test user-made vs auto-made detection
        user_made_entry = {
            'basics': {'user_created': True},
            'confidence': {'trust_score': 0.95, 'user_verified': True}
        }

        auto_made_entry = {
            'basics': {'user_created': False},
            'confidence': {'trust_score': 0.33, 'user_verified': False}
        }

        # Test v1.0 entry (backward compatibility)
        v1_user_entry = {'confirmed_by_user': True, 'confidence': 0.85}
        v1_auto_entry = {'confirmed_by_user': False, 'confidence': 0.33}

        test_cases = [
            ("v2.0 user-made", user_made_entry, True),
            ("v2.0 auto-made", auto_made_entry, False),
            ("v1.0 user-made", v1_user_entry, True),
            ("v1.0 auto-made", v1_auto_entry, False)
        ]

        for name, entry, expected in test_cases:
            result = vendor_cache._is_user_made_schema(entry)
            status = "✓" if result == expected else "✗"
            print(f"  {status} {name}: {result} (expected: {expected})")

        return True

    except Exception as e:
        print(f"✗ Phase6 test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\nTEST MENU:")
    print("1. Launch GUI for manual testing")
    print("2. Run programmatic Phase6 callback tests")
    print("3. Run both")
    print("4. Exit")

    choice = input("\nSelect option (1-4): ").strip()

    if choice == "1":
        test_gui_pipeline_integration()
    elif choice == "2":
        test_phase6_callback_logic()
    elif choice == "3":
        test_phase6_callback_logic()
        print("\n" + "="*80)
        test_gui_pipeline_integration()
    else:
        print("Exiting.")

if __name__ == "__main__":
    main()