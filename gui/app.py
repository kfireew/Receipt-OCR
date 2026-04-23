#!/usr/bin/env python3
"""
Receipt OCR GUI - Main Application

This is the main entry point for the Receipt OCR GUI.
It uses the modular GUI structure with cute theme and vendor cache integration.
"""

import os
import sys
from pathlib import Path
import tkinter as tk

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()


def check_dependencies():
    """Check required dependencies and warn if missing."""
    missing = []

    # Check for tkinterdnd2 (optional but recommended)
    try:
        from tkinterdnd2 import TkinterDnD
    except ImportError:
        missing.append("tkinterdnd2 (drag & drop will be disabled)")

    # Check for deep_translator (optional)
    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        missing.append("deep_translator (Hebrew translation will use fallback)")

    # Check for mindee package (required for pipeline)
    try:
        import mindee
    except ImportError:
        missing.append("mindee (required for OCR processing)")

    # Check for vendor cache pipeline
    try:
        from pipelines.mindee_pipeline_with_metadata import process_receipt_with_metadata
    except ImportError as e:
        missing.append(f"mindee_pipeline_with_metadata: {e}")

    # Check for basic pipeline
    try:
        from pipelines.mindee_pipeline import process_receipt
    except ImportError as e:
        missing.append(f"mindee_pipeline: {e}")

    return missing


def create_main_window():
    """Create and configure the main application window."""
    try:
        from gui.main_window import MainWindow
    except ImportError as e:
        print(f"Error importing GUI modules: {e}")
        print("Make sure all modular GUI files exist in the gui/ directory.")
        return None

    # Try to use TkinterDnD for drag & drop
    root = None
    has_dnd = False

    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
        print("Created TkinterDnD window (drag & drop enabled)")
        has_dnd = True
    except ImportError:
        # Fall back to regular Tk
        root = tk.Tk()
        print("Created tk.Tk() window (drag & drop disabled - install tkinterdnd2)")
        has_dnd = False
    except Exception as e:
        print(f"Error creating TkinterDnD window: {e}")
        root = tk.Tk()
        print("Fallback to tk.Tk() window")
        has_dnd = False

    # Create main application
    try:
        app = MainWindow(root)
        print("MainWindow created successfully")
        return app
    except Exception as e:
        print(f"Error creating MainWindow: {e}")
        import traceback
        traceback.print_exc()
        if root:
            root.destroy()
        return None


def run_simple_cache_editor():
    """Run the super simple cache editor as an alternative."""
    try:
        from gui.super_simple_cache_editor import main
        main()
    except ImportError as e:
        print(f"Error: {e}")
        print("Make sure super_simple_cache_editor.py exists in the gui/ directory.")


def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("Receipt OCR GUI with Vendor Cache")
    print("="*60)

    # Check dependencies
    missing = check_dependencies()
    if missing:
        print("\nWarning: Missing or problematic dependencies:")
        for dep in missing:
            print(f"  • {dep}")

        # Ask if user wants to continue
        response = input("\nContinue anyway? (y/n): ").lower()
        if response != 'y':
            print("Exiting.")
            return

    print("\nAvailable modes:")
    print("1. Main OCR GUI (recommended)")
    print("2. Simple Cache Editor")
    print("3. Exit")

    choice = input("\nSelect mode (1-3): ").strip()

    if choice == "1":
        # Run main GUI
        app = create_main_window()
        if app:
            print("\nStarting main GUI...")
            app.root.mainloop()
        else:
            print("Failed to create main window.")

    elif choice == "2":
        # Run simple cache editor
        print("\nStarting simple cache editor...")
        run_simple_cache_editor()

    elif choice == "3":
        print("Exiting.")
        return

    else:
        print("Invalid choice. Exiting.")


def run():
    """Run the application (for setup.py entry point)."""
    main()


if __name__ == "__main__":
    main()