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

### Mindee API (Primary) - Works with Starter Tier

**Dual Scan Approach** (2 API calls per receipt):

1. **Scan 1: Receipt Model** - Gets structured items (description, qty, unit_price, total)
2. **Scan 2: Raw OCR** - Tries to get word positions (may fail on Starter tier)

**Heuristics:**
- `qty = total / unit_price` when Mindee's qty detection is wrong
- Allow ±2 ILS tolerance for rounding and discounts
- Trust line_total from Mindee as ground truth

### Google Cloud Vision (Optional)

Used for header extraction (vendor, date, invoice_no).
Can be removed if Mindee's header extraction is sufficient.

### Tesseract (Fallback)

Local OCR for:
- Header fallback when Google Cloud fails
- Box detection for custom processing
- Number OCR for quantity verification

## Run CLI

```cmd
cd "C:\Users\Kfir Ezer\Desktop\Receipt OCR" && python -c "from stages.recognition.tesseract_client import parse_receipt_combined; r=parse_receipt_combined('receipt.pdf'); print(r)"
```

## Test Results

| Receipt | Items | Accuracy | Multi-Qty |
|---------|-------|----------|-----------|
| Avikam 10.03.2025 | 14 | 85.7% | 13 |
| Hamefitz 27.12.2024 | 8 | 100.0% | 8 |
| Ida 20.03.2025 | 90 | 100.0% | 64 |
| Tnuva 19.08.2024 | 12 | 100.0% | 12 |
| Wisso 03.03.2025 | 27 | 88.9% | 27 |
| Shufersal 12.04.2026 | 23 | 100.0% | 1 |
| **TOTAL** | **174** | **95.4%** | **125** |

## Future: Own Box Detection (1 Scan Approach)

Instead of Mindee's dual scan, implement our own:

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
├── stages/
│   ├── recognition/          # OCR engines
│   │   ├── mindee_ocr.py    # Dual scan parser (primary)
│   │   ├── google_cloud_ocr.py  # Header extraction (optional)
│   │   └── tesseract_client.py  # Local OCR + box detection
│   ├── parsing/              # Item extraction
│   └── post_process/         # Post-processing
├── utils/                     # Utilities
└── sample_images/             # Test receipts
```

## Can We Remove Google Cloud Vision?

**Yes**, if we accept these limitations:
- Mindee provides: date, total
- Missing: vendor name (need simple heuristic or Tesseract)
- Missing: invoice_no

**Recommendation:** Keep Google Cloud for now. When implementing own box detection, we can remove it.

## API Keys (Optional)

For Mindee only (Starter tier works):
- `MINDEE_API_KEY` - Mindee API key
- `MINDEE_MODEL_ID` - Mindee model ID

For Google Cloud Vision (optional):
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to Google credentials JSON