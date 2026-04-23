#!/usr/bin/env python3
"""
Test script to verify GUI imports work correctly.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print("Testing GUI module imports...")

# Test theme import
try:
    from gui.theme import theme
    print("✓ theme.py imports successfully")
except ImportError as e:
    print(f"✗ Failed to import theme: {e}")

# Test components import
try:
    from gui.components import DropZone, ProcessingSpinner, ResultDisplay, ConfidenceMeter, CacheStatusDisplay
    print("✓ components.py imports successfully")
except ImportError as e:
    print(f"✗ Failed to import components: {e}")

# Test main window import
try:
    from gui.main_window import MainWindow
    print("✓ main_window.py imports successfully")
except ImportError as e:
    print(f"✗ Failed to import main_window: {e}")

# Test cache manager import
try:
    from gui.cache_manager_window import CacheManagerWindow
    print("✓ cache_manager_window.py imports successfully")
except ImportError as e:
    print(f"✗ Failed to import cache_manager_window: {e}")

# Test schema editor import
try:
    from gui.schema_editor_window import SchemaEditorWindow
    print("✓ schema_editor_window.py imports successfully")
except ImportError as e:
    print(f"✗ Failed to import schema_editor_window: {e}")

# Test layout review import
try:
    from gui.layout_review_window import LayoutReviewWindow
    print("✓ layout_review_window.py imports successfully")
except ImportError as e:
    print(f"✗ Failed to import layout_review_window: {e}")

# Test vendor editor import
try:
    from gui.vendor_editor_window import VendorEditorWindow
    print("✓ vendor_editor_window.py imports successfully")
except ImportError as e:
    print(f"✗ Failed to import vendor_editor_window: {e}")

# Test pipeline imports
try:
    from pipelines.mindee_pipeline_with_metadata import process_receipt_with_metadata
    print("✓ mindee_pipeline_with_metadata.py imports successfully")
except ImportError as e:
    print(f"✗ Failed to import pipeline: {e}")

print("\nAll imports tested.")