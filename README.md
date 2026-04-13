# Receipt OCR

Extract line items from Israeli supermarket receipts (Hebrew).

## Quick Start

```bash
pip install -r requirements.txt
python -m gui.app
```

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
