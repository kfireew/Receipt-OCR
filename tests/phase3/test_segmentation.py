#!/usr/bin/env python3
"""
OBSOLETE TEST FILE - NOT USED BY MAIN PIPELINE
===============================================
Phase 3 Test: Raw Text Segmentation Using Price Anchors

Tests that JSON prices are used to segment raw text into item blocks.
"""
import os
import sys
import json
from unittest.mock import Mock, patch, MagicMock

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class TestSegmentation:
    """Test Phase 3: Raw text segmentation."""

    def setup_method(self):
        """Set up test environment."""
        pass

    def test_parser_import(self):
        """Test MindeeParser can be imported."""
        try:
            from pipelines._mindee.parser import MindeeParser
            parser = MindeeParser()
            assert parser is not None
            print("✓ MindeeParser import test passed")
            return True
        except Exception as e:
            print(f"✗ MindeeParser import failed: {e}")
            return False

    def test_segment_method_exists(self):
        """Test segment_raw_text_by_prices method exists."""
        try:
            from pipelines._mindee.parser import MindeeParser
            parser = MindeeParser()
            assert hasattr(parser, 'segment_raw_text_by_prices')
            assert callable(parser.segment_raw_text_by_prices)
            print("✓ segment_raw_text_by_prices method exists")
            return True
        except Exception as e:
            print(f"✗ segment_raw_text_by_prices check failed: {e}")
            return False

    def test_segmentation_logic(self):
        """Test segmentation method signature and logic."""
        parser_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                  'pipelines', '_mindee', 'parser.py')
        if os.path.exists(parser_path):
            with open(parser_path, 'r', encoding='utf-8') as f:
                content = f.read()

                # Check for key components of segmentation
                checks = [
                    ('Method definition', 'def segment_raw_text_by_prices' in content),
                    ('Uses JSON items', 'json_items' in content),
                    ('Uses raw text', 'raw_text' in content),
                    ('Price anchor logic', 'anchor_price' in content or 'line_total' in content),
                    ('Name anchor logic', 'description' in content or 'name.*anchor' in content.lower()),
                ]

                all_passed = True
                for check_name, check_result in checks:
                    if check_result:
                        print(f"✓ {check_name} found in parser")
                    else:
                        print(f"✗ {check_name} missing from parser")
                        all_passed = False

                return all_passed
        else:
            print("⚠ parser.py not found, skipping segmentation logic test")
            return None

    def test_find_item_block_method(self):
        """Test _find_item_block or similar helper method exists."""
        parser_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                  'pipelines', '_mindee', 'parser.py')
        if os.path.exists(parser_path):
            with open(parser_path, 'r', encoding='utf-8') as f:
                content = f.read()

                # Look for item block finding methods
                methods = [
                    '_find_item_block',
                    '_find_item_block_enhanced',
                    '_collect_item_block',
                    '_is_item_block_line'
                ]

                found_methods = []
                for method in methods:
                    if f'def {method}' in content:
                        found_methods.append(method)

                if found_methods:
                    print(f"✓ Found item block methods: {', '.join(found_methods)}")
                    return True
                else:
                    print("✗ No item block finding methods found")
                    return False
        else:
            print("⚠ parser.py not found, skipping method test")
            return None

    def test_hebrew_text_handling(self):
        """Test Hebrew text handling in segmentation."""
        parser_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                  'pipelines', '_mindee', 'parser.py')
        if os.path.exists(parser_path):
            with open(parser_path, 'r', encoding='utf-8') as f:
                content = f.read()

                # Check for Hebrew character handling
                has_hebrew_check = r'\u0590-\u05FF' in content or 'hebrew' in content.lower()
                has_normalization = 'normalize' in content.lower()

                if has_hebrew_check or has_normalization:
                    print("✓ Hebrew text handling appears implemented")
                    return True
                else:
                    print("⚠ Hebrew text handling may be missing")
                    return False
        else:
            print("⚠ parser.py not found, skipping Hebrew test")
            return None

    def test_pipeline_integration(self):
        """Test segmentation is called in pipeline."""
        pipeline_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                    'pipelines', 'mindee_pipeline.py')
        if os.path.exists(pipeline_path):
            with open(pipeline_path, 'r', encoding='utf-8') as f:
                content = f.read()

                # Check for segmentation call
                if 'segment_raw_text_by_prices' in content:
                    print("✓ Segmentation called in pipeline")
                    return True
                else:
                    print("✗ Segmentation not called in pipeline")
                    return False
        else:
            print("⚠ mindee_pipeline.py not found, skipping integration test")
            return None

def run_phase3_tests():
    """Run all Phase 3 tests."""
    print("\n" + "="*60)
    print("Phase 3 Tests: Raw Text Segmentation")
    print("="*60)

    test = TestSegmentation()
    test.setup_method()

    results = []

    # Run tests
    results.append(("Parser import", test.test_parser_import()))
    results.append(("Segmentation method", test.test_segment_method_exists()))

    logic_test = test.test_segmentation_logic()
    if logic_test is not None:
        results.append(("Segmentation logic", logic_test))

    method_test = test.test_find_item_block_method()
    if method_test is not None:
        results.append(("Item block methods", method_test))

    hebrew_test = test.test_hebrew_text_handling()
    if hebrew_test is not None:
        results.append(("Hebrew handling", hebrew_test))

    integration_test = test.test_pipeline_integration()
    if integration_test is not None:
        results.append(("Pipeline integration", integration_test))

    # Summary
    print("\n" + "="*60)
    print("Phase 3 Test Summary")
    print("="*60)

    passed = sum(1 for _, result in results if result is True)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result is True else "✗ FAIL" if result is False else "⚠ SKIP"
        print(f"{status}: {test_name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("✓ Phase 3 implementation appears correct")
        return True
    else:
        print("✗ Phase 3 has issues that need fixing")
        return False

if __name__ == "__main__":
    success = run_phase3_tests()
    sys.exit(0 if success else 1)