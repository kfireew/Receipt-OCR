"""
Unified Pipeline Interface.

Usage:
    from pipelines import process_receipt

    # Mindee (default, best accuracy)
    result = process_receipt("receipt.pdf", method="mindee")

    # Tesseract (free, local)
    result = process_receipt("receipt.pdf", method="tesseract")
"""
from typing import Optional


def process_receipt(
    image_path: str,
    method: str = "mindee",
    **kwargs
) -> dict:
    """
    Process receipt using specified OCR method.

    Args:
        image_path: Path to receipt file
        method: OCR method - "mindee" or "tesseract"
        **kwargs: Additional args:
            - config: For Tesseract

    Returns:
        GDocument dict with items
    """
    if method == "mindee":
        from pipelines.mindee_pipeline import process_receipt as mindee_process
        return mindee_process(image_path)

    elif method == "tesseract":
        from pipelines.tesseract_pipeline import process_receipt as tesseract_process
        return tesseract_process(image_path, kwargs.get("config"))

    else:
        raise ValueError(f"Unknown method: {method}. Use: mindee or tesseract")