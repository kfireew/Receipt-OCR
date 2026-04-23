"""OBSOLETE TEST FILE - NOT USED BY MAIN PIPELINE
===============================================
Simple test of smarter Phase 2."""

from phase2_smart_column_segmentation import Phase2SmartColumnSegmentation

# Test basic functionality
segmenter = Phase2SmartColumnSegmentation()

json_items = [
    {
        "description": "קוטג 5% 250 גרם",
        "quantity": 1.0,
        "unit_price": 4.97,
        "line_total": 4.97
    }
]

raw_text = """4.97
קוטג 5% 250 גרם"""

print("Testing basic segmentation...")
result = segmenter.segment_raw_text(json_items, raw_text, None)

if result and len(result) > 0:
    item = result[0]
    print(f"Success: {item.get('segmentation_success', False)}")
    print(f"Method: {item.get('segmentation_method', 'unknown')}")
    print(f"Numbers: {item.get('extracted_numbers', [])}")
    if 'extracted_numbers' in item and item['extracted_numbers']:
        print("✓ extracted_numbers created (Phase 4 compatibility)")
    else:
        print("✗ NO extracted_numbers (BUG!)")
else:
    print("No result returned")