"""
OBSOLETE TEST FILE - NOT USED BY MAIN PIPELINE
===============================================
COMPREHENSIVE INTEGRATION TEST: Smarter Phase 2 in Pipeline

This test runs the entire pipeline with the new smarter Phase 2 integration,
tracking input/output at each stage and identifying issues methodically.

We'll create a realistic test case that highlights the previous critical issues:
1. Column name mismatches (Hebrew variations)
2. Data flow breakage (Phase 2 → Phase 4)
3. Column detection false positives
4. extracted_numbers creation for Phase 4 compatibility
"""

import sys
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the Mindee API responses so we can test without actual API calls
class MockMindeeClient:
    """Mock Mindee client for testing."""

    def __init__(self, api_key=None, model_id=None):
        self.api_key = api_key
        self.model_id = model_id

    def scan_receipt_model(self, image_path):
        """Mock JSON scan response."""
        # Return mock JSON response matching Phase 1 expectations
        class MockResponse:
            class Inference:
                class Result:
                    class Fields:
                        pass
                    fields = Fields()
                result = Result()
            inference = Inference()

        return MockResponse()

    def raw_text(self, image_path):
        """Mock raw OCR text scan."""
        # Return realistic raw text with Hebrew columns
        return """תנובה
סניף מרכז
קופה: 5
תאריך: 2025-04-19

תאור פריט   כמות   מחיר יחידה   נטו
חלב 3% 1 ליטר   2   6.50   13.00
קוטג 5% 250 גרם   1   4.97   4.97
ביצים מזון 10   1   12.90   12.90

סה"כ: 30.87
מע"מ: 2.47
לתשלום: 30.87"""


class MockMindeeParser:
    """Mock parser for testing."""

    def parse_fields(self, fields):
        """Mock field parsing."""
        # Return fields matching what Phase 1 expects
        return {
            'vendor': {'value': 'תנובה', 'confidence': 0.9},
            'date': {'value': '2025-04-19', 'confidence': 0.8},
            'total': {'value': 30.87, 'confidence': 0.95}
        }

    def extract_header(self, fields):
        """Extract header info."""
        return {
            'vendor': 'תנובה',
            'date': '2025-04-19',
            'total': 30.87
        }

    def extract_items(self, fields):
        """Extract items (simulating JSON scan with WRONG quantities)."""
        return [
            {
                'description': 'חלב 3% 1 ליטר',
                'quantity': 1.0,  # WRONG: Should be 2.0
                'unit_price': 6.50,
                'line_total': 6.50  # WRONG: Should be 13.00
            },
            {
                'description': 'קוטג 5% 250 גרם',
                'quantity': 1.0,  # CORRECT
                'unit_price': 4.97,
                'line_total': 4.97  # CORRECT
            }
        ]


@dataclass
class TestStage:
    """Track a pipeline stage's status and issues."""
    stage_name: str
    status: str  # "PASS", "WARN", "FAIL"
    input_desc: str
    output_desc: str
    issues: List[str]
    data_snapshot: Optional[Dict] = None


class IntegrationTestRunner:
    """Run comprehensive pipeline integration test."""

    def __init__(self):
        self.stages = []
        self.current_items = []
        self.raw_text = ""
        self.column_info = None
        self.pattern_info = None
        self.vendor_info = None

    def add_stage(self, stage: TestStage):
        """Add a stage result."""
        self.stages.append(stage)
        print(f"\n{'='*80}")
        print(f"STAGE: {stage.stage_name}")
        print(f"Status: {stage.status}")
        print(f"Input: {stage.input_desc}")
        print(f"Output: {stage.output_desc}")
        if stage.issues:
            print(f"Issues ({len(stage.issues)}):")
            for issue in stage.issues:
                print(f"  - {issue}")
        if stage.data_snapshot:
            print(f"Data snapshot keys: {list(stage.data_snapshot.keys())}")

    def run_phase1_two_scans(self):
        """Test Phase 1: Two scans."""
        print("\n" + "="*80)
        print("PHASE 1: TWO SCANS")
        print("="*80)

        # Mock the two scans
        client = MockMindeeClient()
        parser = MockMindeeParser()

        # Scan A: JSON scan
        json_response = client.scan_receipt_model("test.jpg")
        fields = parser.parse_fields(json_response.inference.result.fields)
        header = parser.extract_header(fields)
        items = parser.extract_items(fields)

        # Scan B: Raw OCR text scan
        raw_text = client.raw_text("test.jpg")

        self.current_items = items
        self.raw_text = raw_text

        issues = []
        if not items:
            issues.append("No items extracted from JSON scan")
        if not raw_text:
            issues.append("No raw text from OCR scan")
        if len(items) != 2:
            issues.append(f"Expected 2 items, got {len(items)}")

        status = "PASS" if not issues else "FAIL"

        self.add_stage(TestStage(
            stage_name="Phase 1: Two Scans",
            status=status,
            input_desc="Mock receipt image",
            output_desc=f"{len(items)} JSON items, {len(raw_text)} chars raw text",
            issues=issues,
            data_snapshot={
                'item_count': len(items),
                'has_raw_text': bool(raw_text),
                'items_sample': items[0] if items else {}
            }
        ))

        return items, raw_text, header

    def run_phase3_column_detection(self, raw_text):
        """Test Phase 3: Column detection."""
        print("\n" + "="*80)
        print("PHASE 3: COLUMN DETECTION")
        print("="*80)

        from phases.phase3_column_detection import Phase3ColumnDetection

        detector = Phase3ColumnDetection()
        column_info = detector.detect_columns(raw_text)

        self.column_info = column_info

        issues = []

        # Check for known issues
        if not column_info.get('success'):
            issues.append(f"Column detection failed: {column_info.get('error', 'Unknown')}")

        detected_columns = column_info.get('detected_columns', [])
        if not detected_columns:
            issues.append("No columns detected")
        else:
            # Check for false positives (keyword in data, not headers)
            # This was a known issue from previous analysis
            column_texts = [col.get('hebrew_text', '') for col in detected_columns]
            print(f"Detected columns: {column_texts}")

            # Check if description column is detected
            has_description = any(col.get('assigned_field') == 'description' for col in detected_columns)
            if not has_description:
                issues.append("No description column detected (critical for Phase 2)")

        # Check column mapping
        column_mapping = column_info.get('column_mapping', {})
        if not column_mapping:
            issues.append("Empty column mapping")

        status = "PASS" if not issues else "WARN" if column_info.get('success') else "FAIL"

        self.add_stage(TestStage(
            stage_name="Phase 3: Column Detection",
            status=status,
            input_desc=f"{len(raw_text.splitlines())} lines of raw text",
            output_desc=f"Success: {column_info.get('success')}, Columns: {len(detected_columns)}",
            issues=issues,
            data_snapshot={
                'success': column_info.get('success'),
                'detected_columns_count': len(detected_columns),
                'has_description_column': has_description if detected_columns else False,
                'column_mapping': column_mapping
            }
        ))

        return column_info

    def run_phase2_smart_segmentation(self, items, raw_text, column_info):
        """Test Phase 2: Smart column segmentation."""
        print("\n" + "="*80)
        print("PHASE 2: SMART COLUMN SEGMENTATION")
        print("="*80)

        from phases.phase2_smart_column_segmentation import Phase2SmartColumnSegmentation

        segmenter = Phase2SmartColumnSegmentation()
        segmented_items = segmenter.segment_raw_text(items, raw_text, column_info)

        self.current_items = segmented_items

        issues = []
        critical_issues = []

        if not segmented_items:
            critical_issues.append("No items returned from segmentation")
        else:
            success_count = sum(1 for item in segmented_items if item.get('segmentation_success', False))

            if success_count != len(segmented_items):
                issues.append(f"Only {success_count}/{len(segmented_items)} items successfully segmented")

            # CRITICAL: Check for extracted_numbers (Phase 4 compatibility)
            missing_numbers = []
            has_row_cells = []

            for i, item in enumerate(segmented_items):
                if 'extracted_numbers' not in item or not item.get('extracted_numbers'):
                    missing_numbers.append(i)

                if 'row_cells' in item and item['row_cells']:
                    has_row_cells.append(i)

            if missing_numbers:
                critical_issues.append(f"Items {missing_numbers} missing extracted_numbers (breaks Phase 4)")

            # Check data completeness
            print(f"\nItem 1 data completeness check:")
            if segmented_items:
                item1 = segmented_items[0]
                print(f"  - segmentation_success: {item1.get('segmentation_success')}")
                print(f"  - extracted_numbers: {len(item1.get('extracted_numbers', []))} numbers")
                print(f"  - row_cells: {len(item1.get('row_cells', {}))} columns")
                print(f"  - item_block: {len(item1.get('item_block', []))} lines")
                print(f"  - segmentation_method: {item1.get('segmentation_method')}")

            # Check column boundary fix (was: '13   6.50' :'הדיחי ריחמ.')
            for i, item in enumerate(segmented_items):
                row_cells = item.get('row_cells', {})
                for col_name, cell_value in row_cells.items():
                    # Check for multiple numbers in a single cell (bug indicator)
                    import re
                    numbers = re.findall(r'\d+\.?\d*', cell_value)
                    if len(numbers) > 1 and ('מחיר' in col_name or 'ריחמ' in col_name):
                        issues.append(f"Item {i}: Multiple numbers in {col_name} cell: '{cell_value}'")

        status = "FAIL" if critical_issues else ("WARN" if issues else "PASS")
        all_issues = critical_issues + issues

        self.add_stage(TestStage(
            stage_name="Phase 2: Smart Column Segmentation",
            status=status,
            input_desc=f"{len(items)} JSON items, column_info: {column_info.get('success') if column_info else 'None'}",
            output_desc=f"{len([i for i in segmented_items if i.get('segmentation_success', False)])}/{len(segmented_items)} items segmented",
            issues=all_issues,
            data_snapshot={
                'segmented_count': len(segmented_items),
                'success_count': success_count if segmented_items else 0,
                'has_extracted_numbers': all(i.get('extracted_numbers', []) for i in segmented_items) if segmented_items else False,
                'sample_item_keys': list(segmented_items[0].keys()) if segmented_items else []
            }
        ))

        return segmented_items

    def run_phase4_quantity_pattern(self, items):
        """Test Phase 4: Quantity pattern detection."""
        print("\n" + "="*80)
        print("PHASE 4: QUANTITY PATTERN DETECTION")
        print("="*80)

        from phases.phase4_quantity_pattern import Phase4QuantityPattern

        detector = Phase4QuantityPattern()
        pattern_info = detector.detect_quantity_pattern(items)

        self.pattern_info = pattern_info

        issues = []
        critical_issues = []

        # Check if Phase 4 can work with the data
        if not items:
            critical_issues.append("No items to analyze")
        else:
            # CRITICAL: Check if items have extracted_numbers
            items_without_numbers = []
            for i, item in enumerate(items):
                extracted = item.get('extracted_numbers', [])
                if not extracted:
                    items_without_numbers.append(i)

            if items_without_numbers:
                critical_issues.append(f"Items {items_without_numbers} have no extracted_numbers (Phase 4 needs this)")

            # Check pattern detection result
            success = pattern_info.get('success', False)
            if not success:
                issues.append(f"Pattern detection failed: {pattern_info.get('reason', 'Unknown')}")
            else:
                pattern = pattern_info.get('pattern')
                print(f"Detected pattern: {pattern}")

                # Try to extract quantities
                for i, item in enumerate(items):
                    new_qty = detector.extract_quantity_from_block(item, pattern_info)
                    old_qty = item.get('quantity', 0)

                    if new_qty != old_qty:
                        print(f"Item {i}: Quantity updated {old_qty} → {new_qty}")

        status = "FAIL" if critical_issues else ("WARN" if issues else "PASS")
        all_issues = critical_issues + issues

        self.add_stage(TestStage(
            stage_name="Phase 4: Quantity Pattern Detection",
            status=status,
            input_desc=f"{len(items)} segmented items",
            output_desc=f"Success: {pattern_info.get('success')}, Pattern: {pattern_info.get('pattern', 'None')}",
            issues=all_issues,
            data_snapshot={
                'success': pattern_info.get('success'),
                'pattern': pattern_info.get('pattern'),
                'reason': pattern_info.get('reason'),
                'items_have_extracted_numbers': not any(not i.get('extracted_numbers', []) for i in items) if items else False
            }
        ))

        return pattern_info

    def run_phase5_product_list(self, items):
        """Test Phase 5: Product list integration."""
        print("\n" + "="*80)
        print("PHASE 5: PRODUCT LIST INTEGRATION")
        print("="*80)

        # Note: This test will be limited since we can't access the Excel file
        # But we can test the interface and check for known issues

        issues = []

        # Known issue from previous analysis: Hebrew column name mismatches
        # Specification: 'תאור פריט', 'קוד פריט'
        # Code expects: 'טירפ רואת', 'טירפ דוק'
        # Excel actual: 'טירפ רואת', ' טירפ דוק ' (with trailing spaces!)

        issues.append("CANNOT TEST FULLY: Requires Excel file 'prices_rimon_03-02-25.xlsx'")
        issues.append("KNOWN ISSUE: Hebrew column name mismatches between spec/code/Excel")

        # Mock what Phase 5 should do
        print("Product list integration would:")
        print("1. Look up product codes in item blocks")
        print("2. Fuzzy match names against canonical Hebrew names")
        print("3. Assign CatalogNo from matching products")

        status = "WARN"  # Can't fully test

        self.add_stage(TestStage(
            stage_name="Phase 5: Product List Integration",
            status=status,
            input_desc=f"{len(items)} items with raw text context",
            output_desc="CatalogNo assignment (simulated)",
            issues=issues
        ))

        return items  # Return items unchanged for now

    def run_full_test(self):
        """Run the complete integration test."""
        print("\n" + "="*80)
        print("COMPREHENSIVE PIPELINE INTEGRATION TEST")
        print("="*80)
        print("Testing with smarter Phase 2 implementation")
        print("Tracking all stages methodically")
        print("="*80)

        try:
            # Phase 1: Two scans
            items, raw_text, header = self.run_phase1_two_scans()

            # Phase 3: Column detection (comes before Phase 2 in pipeline)
            column_info = self.run_phase3_column_detection(raw_text)

            # Phase 2: Smart column segmentation
            segmented_items = self.run_phase2_smart_segmentation(items, raw_text, column_info)

            # Phase 4: Quantity pattern detection
            pattern_info = self.run_phase4_quantity_pattern(segmented_items)

            # Phase 5: Product list integration
            self.run_phase5_product_list(segmented_items)

            # Generate summary report
            self.generate_summary()

        except Exception as e:
            print(f"\n[FAIL] TEST FAILED WITH EXCEPTION: {e}")
            import traceback
            traceback.print_exc()

    def generate_summary(self):
        """Generate comprehensive test summary."""
        print("\n" + "="*80)
        print("INTEGRATION TEST SUMMARY")
        print("="*80)

        # Count statuses
        status_counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
        for stage in self.stages:
            status_counts[stage.status] = status_counts.get(stage.status, 0) + 1

        print(f"\nStage Results: PASS {status_counts['PASS']} | WARN {status_counts['WARN']} | FAIL {status_counts['FAIL']}")

        print("\n" + "-"*80)
        print("DETAILED STAGE ANALYSIS")
        print("-"*80)

        for stage in self.stages:
            print(f"\n{stage.stage_name}: {stage.status}")
            if stage.issues:
                print(f"  Issues: {len(stage.issues)}")
                for issue in stage.issues[:3]:  # Show first 3 issues
                    print(f"    - {issue}")
                if len(stage.issues) > 3:
                    print(f"    ... and {len(stage.issues) - 3} more")

        print("\n" + "-"*80)
        print("CRITICAL FINDINGS")
        print("-"*80)

        # Check for critical data flow issues
        critical_issue_found = False

        # Phase 2 → Phase 4 data flow
        phase2_stage = next((s for s in self.stages if "Phase 2" in s.stage_name), None)
        phase4_stage = next((s for s in self.stages if "Phase 4" in s.stage_name), None)

        if phase2_stage and phase4_stage:
            # Check if extracted_numbers is being created
            if any("missing extracted_numbers" in issue.lower() for issue in phase2_stage.issues):
                print("[FAIL] CRITICAL: Phase 2 not creating extracted_numbers (breaks Phase 4)")
                critical_issue_found = True
            elif any("no extracted_numbers" in issue.lower() for issue in phase4_stage.issues):
                print("[FAIL] CRITICAL: Phase 4 receiving items without extracted_numbers")
                critical_issue_found = True
            else:
                print("[PASS] Phase 2 → Phase 4 data flow: extracted_numbers is being passed")

        # Column detection issues
        phase3_stage = next((s for s in self.stages if "Phase 3" in s.stage_name), None)
        if phase3_stage:
            if phase3_stage.status in ["WARN", "FAIL"]:
                print(f"[WARN] Phase 3 column detection has issues: {len(phase3_stage.issues)}")
                if any("false positive" in issue.lower() for issue in phase3_stage.issues):
                    print("  - Includes false positive detection (keyword in data, not headers)")

        # Overall assessment
        print("\n" + "-"*80)
        print("OVERALL ASSESSMENT")
        print("-"*80)

        if status_counts["FAIL"] > 0:
            print("[FAIL] PIPELINE HAS CRITICAL FAILURES")
            print("   Address FAIL stages before proceeding")
        elif status_counts["WARN"] > 0:
            print("[WARN] PIPELINE HAS WARNINGS BUT MAY WORK")
            print("   Review WARN stages for potential issues")
        else:
            print("[PASS] PIPELINE LOOKS GOOD!")
            print("   All stages passed successfully")

        if critical_issue_found:
            print("\n[ALERT] CRITICAL DATA FLOW ISSUE DETECTED")
            print("   Phase 4 needs extracted_numbers from Phase 2")
            print("   This was the main bug the smarter Phase 2 was meant to fix")


def main():
    """Main entry point."""
    runner = IntegrationTestRunner()
    runner.run_full_test()


if __name__ == "__main__":
    main()