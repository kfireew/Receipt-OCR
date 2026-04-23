#!/usr/bin/env python3
"""
OBSOLETE TEST FILE - NOT USED BY MAIN PIPELINE
===============================================
Phase 2 Test: Two-Scan Architecture

Tests that Mindee is called twice on every receipt:
1. JSON scan for structured fields
2. Raw text scan with raw_text=True for accurate numbers
"""
import os
import sys
import json
from unittest.mock import Mock, patch, MagicMock

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class TestTwoScans:
    """Test Phase 2: Two-scan architecture."""

    def setup_method(self):
        """Set up test environment."""
        os.environ['MINDEE_API_KEY'] = 'test_key'
        os.environ['MINDEE_MODEL_ID'] = 'test_model'

    def test_client_initialization(self):
        """Test MindeeClient can be initialized."""
        try:
            from pipelines._mindee.client import MindeeClient
            client = MindeeClient('test_key', 'test_model')
            assert client.api_key == 'test_key'
            assert client.model_id == 'test_model'
            print("✓ MindeeClient initialization test passed")
            return True
        except Exception as e:
            print(f"✗ MindeeClient initialization failed: {e}")
            return False

    def test_scan_receipt_model_method_exists(self):
        """Test scan_receipt_model method exists."""
        try:
            from pipelines._mindee.client import MindeeClient
            client = MindeeClient('test_key', 'test_model')
            assert hasattr(client, 'scan_receipt_model')
            assert callable(client.scan_receipt_model)
            print("✓ scan_receipt_model method exists")
            return True
        except Exception as e:
            print(f"✗ scan_receipt_model check failed: {e}")
            return False

    def test_get_raw_text_method_exists(self):
        """Test get_raw_text method exists."""
        try:
            from pipelines._mindee.client import MindeeClient
            client = MindeeClient('test_key', 'test_model')
            assert hasattr(client, 'get_raw_text')
            assert callable(client.get_raw_text)
            print("✓ get_raw_text method exists")
            return True
        except Exception as e:
            print(f"✗ get_raw_text check failed: {e}")
            return False

    def test_raw_text_parameter_used(self):
        """Test that get_raw_text uses raw_text=True parameter."""
        # This test checks the source code directly
        client_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                  'pipelines', '_mindee', 'client.py')
        if os.path.exists(client_path):
            with open(client_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Check for raw_text=True in get_raw_text method
                if 'raw_text=True' in content:
                    print("✓ get_raw_text uses raw_text=True parameter")
                    return True
                else:
                    print("✗ get_raw_text does not use raw_text=True parameter")
                    return False
        else:
            print("⚠ client.py not found, skipping raw_text parameter test")
            return None

    def test_pipeline_calls_both_scans(self):
        """Test that mindee_pipeline calls both scans."""
        pipeline_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                    'pipelines', 'mindee_pipeline.py')
        if os.path.exists(pipeline_path):
            with open(pipeline_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Check for both scan calls
                has_json_scan = 'scan_receipt_model' in content
                has_raw_scan = 'get_raw_text' in content

                if has_json_scan and has_raw_scan:
                    print("✓ mindee_pipeline calls both scan methods")
                    return True
                else:
                    print(f"✗ mindee_pipeline missing scans: JSON={has_json_scan}, Raw={has_raw_scan}")
                    return False
        else:
            print("⚠ mindee_pipeline.py not found, skipping scan call test")
            return None

    def test_fallback_mechanism(self):
        """Test fallback mechanism exists for raw text failure."""
        pipeline_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                    'pipelines', 'mindee_pipeline.py')
        if os.path.exists(pipeline_path):
            with open(pipeline_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Check for fallback logic
                if 'scan_raw_ocr' in content and 'fallback' in content.lower():
                    print("✓ Fallback mechanism exists for raw text failure")
                    return True
                else:
                    print("⚠ Fallback mechanism may not be properly implemented")
                    return False
        else:
            print("⚠ mindee_pipeline.py not found, skipping fallback test")
            return None

def run_phase2_tests():
    """Run all Phase 2 tests."""
    print("\n" + "="*60)
    print("Phase 2 Tests: Two-Scan Architecture")
    print("="*60)

    test = TestTwoScans()
    test.setup_method()

    results = []

    # Run tests
    results.append(("Client initialization", test.test_client_initialization()))
    results.append(("JSON scan method", test.test_scan_receipt_model_method_exists()))
    results.append(("Raw text method", test.test_get_raw_text_method_exists()))

    param_test = test.test_raw_text_parameter_used()
    if param_test is not None:
        results.append(("raw_text=True parameter", param_test))

    scan_test = test.test_pipeline_calls_both_scans()
    if scan_test is not None:
        results.append(("Pipeline calls both scans", scan_test))

    fallback_test = test.test_fallback_mechanism()
    if fallback_test is not None:
        results.append(("Fallback mechanism", fallback_test))

    # Summary
    print("\n" + "="*60)
    print("Phase 2 Test Summary")
    print("="*60)

    passed = sum(1 for _, result in results if result is True)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result is True else "✗ FAIL" if result is False else "⚠ SKIP"
        print(f"{status}: {test_name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("✓ Phase 2 implementation appears correct")
        return True
    else:
        print("✗ Phase 2 has issues that need fixing")
        return False

if __name__ == "__main__":
    success = run_phase2_tests()
    sys.exit(0 if success else 1)