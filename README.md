# Receipt OCR & Parsing for Hebrew

A powerful, native end-to-end OCR and parsing pipeline built heavily initialized for Hebrew receipts outputting matching data fields into an ABBYY GDocument JSON structure format.

## System Flow
The processing pipeline implements four clean stages:
1. **Preprocess:** deskews bounding boxes, applies `cv2.adaptiveThreshold` for binarization, and crops image edges for maximum text isolation.
2. **Detect & Recognize:** utilizes Tesseract's highly capable native detection mapped over all available pages of a Document to output detected bounding boxes and normalized bounding texts.
3. **Line Grouping:** combines individual disjointed word boxes that fall into the same Y-axis thresholds into coherent `RawLine` objects.
4. **Parse:** applies a sequence of heuristics and line-scanning REGEX patterns (`סה"כ`, `חשבונית מס`, Date formats) to scrape Merchant arrays, amounts, strings, and LineItem rows into a `ParsedReceipt` structure.

## Repository Structure
```text
Receipt OCR/
├── receipt_ocr/            # Core OCR & Parsing Library 
│   ├── utils/              # Config loaders, confidence math, string manipulation
│   ├── cli.py              # Main execution thread
│   ├── ocr_preprocess.py   # Image normalization & Box generation 
│   ├── parse_receipt.py    # Line grouping and Regex evaluation
│   └── recognize_tesseract.py
├── test_accuracy/          # Validation and Evaluation Module
├── scripts/                # Loose toolkit apps for cropping and visual testing
├── sample_images/          # PDF and Exact-JSON pairs for accuracy regression
├── debug/                  # Holds .JSON and .LOG dumps from Tesseract failure
├── gui.py                  # Drag & drop interactive desktop UI
├── config.yml              # Parameter and path loader config
└── requirements.txt
```

## Requirements

1. **Tesseract OCR (Required)**
You MUST download and install Tesseract natively on your system:
- **Windows:** Download from UB-Mannheim (https://github.com/UB-Mannheim/tesseract/wiki)
- Note: Tesseract is configured to run at `C:/Program Files/Tesseract-OCR/tesseract.exe`. If you install it elsewhere, update `executable_path` in `config.yml`.
- Make sure to check the option to include **Hebrew language packages** during installation!

2. **Python Dependencies**
Install standard libraries directly into your system with:
```bash
pip install -r requirements.txt
```

## Usage Menu

### 1) The Desktop GUI (Recommended)
We built a graphical interface for easy testing and evaluation. 

**To open the GUI:**
```bash
python gui.py
```

**Features:**
- **Browse:** Click "Browse Image/PDF" to select a receipt and see the parsed JSON output instantly.
- **Drag & Drop:** If you installed `tkinterdnd2`, you can literally drag a PDF or Image file from your desktop directly into the text area to process it!
- **Run Test Evaluation:** Click this button to run the complete accuracy test suite over the `sample_images` folder and see the success rate live.

### 2) The Production CLI
If you want to plug this pipeline into an existing structure naturally, you can output formatted `.JSON` to standard out seamlessly:
```bash
python -m receipt_ocr.cli --image "sample_images/receipt.pdf" --config config.yml
```
Optional Arguments:
- `--debug` displays images during line finding heuristics.
- `--output <path>` sends the output GDocument JSON to your choice filepath.

### 3) Accuracy Evaluation Testing
The evaluation suite runs through all PDF/JSON pairs in the `sample_images` directory, runs the OCR pipeline, and compares the parsed fields (Invoice, Date, Total, and Line Items) against the ground truth using fuzzy string matching and numeric decimal tolerance.

**To run the test suite:**
```bash
python -m test_accuracy.cli
```

**Optional Arguments:**
- `--images-dir <path>`: Specify a different folder containing PDFs and JSONs.
- `--pattern <glob>`: Only test specific files (e.g. `*.pdf`).
- `--dry-run`: Just print which files would be tested without running the heavy OCR.

## Recommendations for Improving Accuracy
To further push the accuracy score on Line Items and complex tables:
1. **Column Mapping (Grid Parsing)**: Current parsing uses horizontal row boundaries. Since quantities and prices shift horizontally, parsing values by their `X` pixel coordinate column under specific table headers (e.g. "Price", "Qty") is recommended.
2. **Numeric Whitelisting**: Tesseract occasionally misreads barcodes or prices as Hebrew characters. Passing an English-only, numeric-only config (`-c tessedit_char_whitelist=0123456789.`) specifically on the right half of the image will fix numeric drift.
3. **Vendor Templating**: Pre-defining layout grids for known vendors (like *Strauss*, *Tayari*, *Tnuva*) rather than using one generic heuristic parser will drastically improve pinpoint accuracy.
