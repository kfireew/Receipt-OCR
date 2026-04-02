from __future__ import annotations

from stages.grouping.line_assembler import RawLine, _boxes_to_lines
from stages.recognition.tesseract_client import RecognizedBox
from stages.recognition.box_refiner import deduplicate_boxes
from stages.post_process.math_validator import validate_math
from stages.parsing.models import (
    ParsedReceipt, ParsedStringField, ParsedAmountField, LineItem
)
import os
import json

def _match_merchant(combined_val: str) -> str:
    """Matches the merchant name using the merchants_mapping.json config file."""
    lower_val = combined_val.lower()
    
    # Load mapping from project root
    try:
        current_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(os.path.dirname(current_dir))
        mapping_path = os.path.join(project_root, "merchants_mapping.json")
        with open(mapping_path, "r", encoding="utf-8") as f:
            mapping = json.load(f)
    except Exception:
        mapping = {}
        
    for normalized_name, keywords in mapping.items():
        if any(kw in lower_val for kw in keywords):
            return normalized_name
            
    return combined_val

def parse_receipt(recognized_boxes: Iterable[RecognizedBox]) -> ParsedReceipt:
    from stages.parsing.field_extractors import (
        _parse_date_from_lines, _find_amount_field, _parse_invoice_no, _extract_items
    )
    
    boxes_list = deduplicate_boxes(list(recognized_boxes))
    raw_lines = _boxes_to_lines(boxes_list)

    date_field = _parse_date_from_lines(raw_lines)
    subtotal_field = _find_amount_field(raw_lines, keywords=("סך הכל", "סכום ביניים", "ביניים"))
    vat_field = _find_amount_field(raw_lines, keywords=("מע\"מ", "מעמ"))
    total_field = _find_amount_field(raw_lines, keywords=("סה\"כ", "סהכ", "לתשלום", "לשלם", "סך הכל"))
    
    # Simple currency detection (can be moved later)
    currency_field = ParsedStringField(value=None, confidence=None, line_index=None)
    for ln in raw_lines:
        txt = (ln.text_normalized or ln.text_raw or "").lower()
        if any(sym in txt for sym in ("₪", "nis", "ש\"ח", "שח", "ש״ח")):
            currency_field = ParsedStringField(value="ILS", confidence=ln.confidence, line_index=ln.index)
            break

    # Smarter merchant guessing: use the first 2-3 lines if they look like a header
    def _guess_merchant(lines: List[RawLine]) -> ParsedStringField:
        if not lines:
            return ParsedStringField(value=None, confidence=None, line_index=None)
            
        from stages.post_process.fuzzy_corrector import fuzzy_correct_line
        import re as _re

        # 1. Broad search: scan ALL lines for known merchant keywords
        for line in lines:
            txt = line.text_normalized or line.text_raw or ""
            if not txt or len(txt) < 3:
                continue
            
            # Apply fuzzy correction just for checking
            fuzzy_txt = fuzzy_correct_line(txt)
            fuzzy_txt = _re.sub(r'[\|\\/]+', ' ', fuzzy_txt)
            fuzzy_txt = _re.sub(r'\s+', ' ', fuzzy_txt).strip()
            
            mapped = _match_merchant(fuzzy_txt)
            # If the mapping returned something different than what was inputted, we found a known merchant!
            if mapped != fuzzy_txt:
                return ParsedStringField(value=mapped, confidence=line.confidence, line_index=line.index)
        
        # 2. Fallback: Candidate lines are the first few lines that are NOT mostly digits or known keywords
        candidates = []
        for i in range(min(5, len(lines))):
            txt = lines[i].text_normalized or lines[i].text_raw or ""
            # Stop if we hit a line that looks like an invoice header or date
            if any(kw in txt for kw in ("חשבונית", "תאריך", "מספר", "תעודת")):
                break
            if len(txt) > 3:
                candidates.append(txt)
        
        if not candidates:
            return ParsedStringField(value=lines[0].text_raw, confidence=lines[0].confidence, line_index=0)
            
        combined_val = " ".join(candidates)
        # Apply fuzzy correction to fix common OCR errors in merchant name
        combined_val = fuzzy_correct_line(combined_val)
        
        # Post-clean: remove noise like pipes and multiple spaces
        combined_val = _re.sub(r'[\|\\/]+', ' ', combined_val)
        combined_val = _re.sub(r'\s+', ' ', combined_val).strip()
        
        # Standardize for XAMPP Checksum script using config
        normalized_merchant = _match_merchant(combined_val)
        
        return ParsedStringField(value=normalized_merchant, confidence=lines[0].confidence, line_index=0)

    merchant_field = _guess_merchant(raw_lines)
    invoice_field = _parse_invoice_no(raw_lines)

    used_indices = [f.line_index for f in (subtotal_field, vat_field, total_field, invoice_field, date_field, merchant_field) if f.line_index is not None]
    items = _extract_items(raw_lines, used_indices)

    parsed = ParsedReceipt(
        merchant=merchant_field, date=date_field, subtotal=subtotal_field,
        vat=vat_field, total=total_field, currency=currency_field,
        items=items, raw_lines=raw_lines, invoice_no=invoice_field
    )
    
    return validate_math(parsed)
