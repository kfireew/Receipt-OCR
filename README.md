# Receipt OCR

Extract line items from Israeli supermarket receipts (Hebrew).

## Quick Start

```bash
pip install -r requirements.txt
```

## Run GUI

```cmd
cd "C:\Users\Kfir Ezer\Desktop\Receipt OCR" && python -m gui.app
```

## Run CLI (Google Vision + Mindee)

```cmd
cd "C:\Users\Kfir Ezer\Desktop\Receipt OCR" && python -c "from stages.parsing import parse_receipt_combined; import json; r=parse_receipt_combined(r'path\to\receipt.pdf', header_ocr='google'); print(json.dumps(r.to_dict(), ensure_ascii=False, indent=2))"
```

## OCR Architecture

- **Header (vendor + date)**: Google Cloud Vision API
- **Items + total**: Mindee API

## Project Structure

```
receipt-ocr/
├── gui/                 # GUI application
├── pipelines/           # OCR pipelines (mindee, tesseract, google)
├── stages/             # Processing stages
│   ├── preprocess/    # Image preprocessing
│   ├── recognition/  # OCR providers
│   ├── parsing/      # Item extraction
│   └── post_process/ # Post-processing
├── utils/             # Utilities
├── sample_images/     # Training data (PDF + JSON)
└── tests/            # Tests
```

## Usage

### Code
```python
from pipelines import process_receipt

# Mindee (99% accuracy)
result = process_receipt("receipt.pdf", method="mindee")

# Tesseract (free, local)
result = process_receipt("receipt.pdf", method="tesseract")
```

### GUI
```bash
python -m gui.app
```

Select OCR method: `mindee`, `tesseract`, or `google`

## Accuracy

| Method | Coverage |
|--------|----------|
| Mindee | 99.1% |
| Tesseract | ~60% |

## Configuration

API keys in `pipelines/mindee_pipeline.py` and `pipelines/google_pipeline.py`

## Training Data

New receipts processed with Mindee are automatically saved to `sample_images/` for training.
