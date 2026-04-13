"""
Unified Pipeline Interface.

Usage:
    from pipelines import process_receipt

    # Mindee (default, best accuracy)
    result = process_receipt("receipt.pdf", method="mindee")

    # Tesseract (free, local)
    result = process_receipt("receipt.pdf", method="tesseract")

    # Google Cloud
    result = process_receipt("receipt.pdf", method="google", credentials_path="...")
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
        method: OCR method - "mindee", "tesseract", or "google"
        **kwargs: Additional args:
            - credentials_path: For Google Cloud
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

    elif method == "google":
        from pipelines.google_pipeline import process_receipt as google_process
        return google_process(
            image_path,
            credentials_path=kwargs.get("credentials_path"),
            config=kwargs.get("config"),
        )

    else:
        raise ValueError(f"Unknown method: {method}. Use: mindee, tesseract, google")