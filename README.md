# Hebrew Receipt OCR MVP

This project provides a small, modular Python pipeline that takes a Hebrew receipt image (photo/PDF), runs OCR, and outputs structured JSON (merchant, date, items, totals, etc.).

## Features

- Image preprocessing (deskew, denoise, binarization, resize).
- Text detection using docTR.
- Text recognition using Tesseract with Hebrew language data.
- Rule-based parsing of dates, totals, VAT, currency, and line items.
- CLI entry point for easy use and scripting.

## Installation

1. Create and activate a virtual environment (recommended).
2. Install system dependencies:
   - Tesseract OCR with Hebrew language data.
   - libpng, libjpeg, and other standard image libraries (usually installed with Tesseract/OpenCV).
3. Install Python dependencies:

```bash
pip install -r requirements.txt
```

4. If Tesseract is not on your `PATH`, set its location in `config.yml` under `tesseract.executable_path`.

## Usage

Run the CLI on a receipt image:

```bash
python -m receipt_ocr.cli --image path/to/receipt.jpg --config config.yml --debug --output result.json
```

- **`--image`**: Path to a receipt image (or PDF). For PDFs, the first page is used.
- **`--config`**: Optional path to a YAML config (defaults to `config.yml` in project root).
- **`--debug`**: If provided, intermediate images/overlays are written to the configured debug directory.
- **`--output`**: Optional path to save the resulting JSON (otherwise printed to stdout).

## Project Layout

- `receipt_ocr/` — main Python package
  - `ocr_preprocess.py` — image loading + preprocessing.
  - `detect_doctr.py` — docTR-based text detection.
  - `recognize_tesseract.py` — Tesseract-based recognition.
  - `parse_receipt.py` — rule-based parsing and structuring.
  - `cli.py` — command-line interface.
  - `utils/` — bidi/normalization, confusion map, confidence utilities, I/O helpers.
- `tests/` — unit and end-to-end tests.
- `sample_images/` — placeholder images and JSON for local testing.
- `debug/` — generated at runtime, contains intermediate debug images/overlays.

## Docker

You can run the pipeline in a container for reproducibility. After building the image (see `Dockerfile`), run:

```bash
docker run --rm -v /absolute/path/to/receipts:/data receipts-ocr \
  python -m receipt_ocr.cli --image /data/your_receipt.jpg --config /app/config.yml --output /data/out.json
```

## Testing

Run the unit and smoke tests with:

```bash
pytest
```

## Limitations & Future Work

- Detection/recognition quality depends heavily on image quality and receipt layout.
- The rule-based parser is tuned for common Hebrew supermarket-style receipts and may need adjustment for other formats.
- docTR and Tesseract models are used with generic settings; custom fine-tuned models and better heuristics can significantly improve results.

