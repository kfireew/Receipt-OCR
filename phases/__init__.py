"""
Phase-based receipt OCR pipeline.
Each phase is implemented in its own file for clear separation.
"""

__all__ = [
    'phase1_mindee_structure',
    'phase2_row_reconstruction',
    'phase3_raw_text_segmentation',
    'phase4_json_anchor_reconstruction',
    'phase5_variant_detection',
    'phase6_quantity_extraction',
    'phase7_catalogno_extraction',
    'phase8_test_report',
]