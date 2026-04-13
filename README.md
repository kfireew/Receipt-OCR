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

## How to Use GUI

1. Run the GUI command above
2. Drag and drop a receipt PDF onto the window
3. Select OCR method (mindee - uses Google Vision + Mindee)
4. Click Process
5. Click "Save Folder" to save results

### Output Format

When saving, creates a folder named: `Vendor_Date`

Example: `Haperesal_2026-04-13`

Files created:
- `Haperesal_2026-04-13_Haperesal 13-04-26.pdf` (renamed receipt)
- `Haperesal_2026-04-13_Haperesal 13-04-26.JSON` (results in GDocument format)

## OCR Architecture

- **Header (vendor + date)**: Google Cloud Vision API
- **Items + total**: Mindee API

## Run CLI

```cmd
cd "C:\Users\Kfir Ezer\Desktop\Receipt OCR" && python -c "from stages.parsing import parse_receipt_combined; import json; r=parse_receipt_combined('receipt.pdf'); print(json.dumps(r.to_gdocument_dict(), ensure_ascii=False, indent=2))"
```

## Project Structure

```
Receipt OCR/
├── gui/                    # GUI application
├── stages/                 # Processing stages
│   ├── preprocess/        # Image preprocessing
│   ├── recognition/       # OCR (Google Vision, Mindee, Tesseract)
│   ├── parsing/           # Item extraction
│   ├── grouping/         # Line assembly
│   └── post_process/     # Post-processing
├── pipelines/            # OCR pipelines
├── utils/                 # Utilities
├── sample_images/          # Sample receipts
└── mindee/               # Mindee client
```

## API Keys

Required in `.env` file:
- `MINDEE_API_KEY` - Mindee API key
- `MINDEE_MODEL_ID` - Mindee model ID