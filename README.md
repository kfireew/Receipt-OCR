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

## Architecture

### Mindee Pipeline (2 Scans)

```
pipelines/
├── mindee_pipeline.py    # Main entry point (~130 lines)
└── _mindee/
    ├── client.py          # Mindee API calls
    ├── parser.py          # Response parsing
    └── formatter.py       # Output formatting
```

**Dual Scan Approach:**

1. **Scan 1: Receipt Model** - Gets structured fields (vendor, date, items, totals)
2. **Scan 2: Raw OCR** - Gets word positions for column detection (may fail on Starter tier)

**Heuristics:**
- `qty = total / unit_price` when Mindee's qty detection is wrong
- Allow ±2 ILS tolerance for rounding and discounts
- Trust line_total from Mindee as ground truth

### Tesseract (Sample Only)

Local OCR kept as reference for future 1-scan implementation:
- Currently not integrated into the pipeline
- Located at `stages/recognition/tesseract_client_SAMPLE.py`

## Future: 1 Scan Approach

Implement own box detection to use with Tesseract:

1. **OpenCV line detection** - Find table rows/columns
2. **Tesseract OCR** - Extract text from each cell
3. **Quantity detection** - Use positions to identify columns

**Pros:**
- 1 scan (Tesseract only)
- No API costs
- Full control over positions
- Works offline

**Cons:**
- Need to implement line/column detection
- Less accurate for descriptions
- Hebrew text handling

## Project Structure

```
Receipt OCR/
├── gui/                      # GUI application
├── pipelines/
│   ├── mindee_pipeline.py   # Main pipeline (130 lines)
│   └── _mindee/             # Pipeline modules
│       ├── client.py        # API client
│       ├── parser.py        # Response parser
│       └── formatter.py     # Output formatter
├── stages/
│   ├── recognition/         # OCR engines (samples only)
│   ├── parsing/             # Item extraction
│   └── preprocessing/       # Image preprocessing
├── utils/                   # Utilities
├── tests/                   # Tests (22 tests, all passing)
└── sample_images/           # Test receipts
```

## API Keys

Required for Mindee (Starter tier works):
- `MINDEE_API_KEY` - Mindee API key
- `MINDEE_MODEL_ID` - Mindee model ID

## Running Tests

```bash
python -m pytest tests/test_mindee_pipeline.py -v
```