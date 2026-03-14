# Stage 5: Post-Processing Layer

This directory contains logic that runs *after* the OCR and basic parsing to refine and validate the extracted data using linguistic and mathematical heuristics.

## Modules

### 1. `fuzzy_corrector.py`
- **Purpose**: Corrects minor OCR spelling errors in Hebrew keywords.
- **Logic**: Uses the `difflib` library (Levenshtein distance) to match "broken" OCR words like `מערמ` against the known dictionary `מע"מ`.
- **Impact**: Stabilizes field detection by ensuring keywords like "Total" or "Invoice" are recognized even if characters are slightly garbled.

### 2. `math_validator.py`
- **Purpose**: Enforces logical consistency on the numeric results.
- **Logic**: 
    - Verifies `Subtotal + VAT == Total`.
    - Auto-calculates missing VAT if the `(Total - Subtotal)` matches a realistic tax amount.
    - Swaps fields if they were logically reversed (a common error when Price and Subtotal columns are near each other).
- **Impact**: Prevents "impossible" receipts from being returned to the user, acting as an automated Quality Assurance (QA) step.

## Usage
These modules are integrated into `stages/grouping/line_assembler.py` (Fuzzy) and `stages/parsing/receipt_parser.py` (Math).
