from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional, Sequence
from stages.grouping.line_assembler import RawLine
from .regex_patterns import _DATE_PATTERNS, _AMOUNT_RE, parse_amount
from .models import ParsedStringField, ParsedAmountField, LineItem
from stages.post_process.fuzzy_corrector import snap_to_keyword

def _fuzzy_normalize(text: str) -> str:
    """Apply token-level keyword snapping before regex matching."""
    if not text:
        return text
    return " ".join(snap_to_keyword(tok) for tok in text.split())

def _parse_date_from_lines(lines: Sequence[RawLine]) -> ParsedStringField:
    candidates = []
    for i, line in enumerate(lines):
        text = _fuzzy_normalize(line.text_normalized or line.text_raw or "")
        if not text:
            continue
        is_date_kw = any(kw in text for kw in ("תאריך", "תאר", "הופק", "יום", "חאריך", "חאר", "חאריד"))
        for pat in _DATE_PATTERNS:
            for m in pat.finditer(text):
                day, month, year = m.group(1), m.group(2), m.group(3)
                if len(year) == 2: year = "20" + year
                iso_value = None
                try:
                    clean_date = f"{int(day):02d}.{int(month):02d}.{int(year):04d}"
                    dt = datetime.strptime(clean_date, "%d.%m.%Y")
                    iso_value = dt.date().isoformat()
                except ValueError:
                    continue
                if iso_value:
                    score = 0
                    if is_date_kw: score += 15
                    if i < 20: score += 10
                    if i > len(lines) - 15: score += 5
                    candidates.append((score, iso_value, line.confidence, i))
    if candidates:
        candidates.sort(key=lambda x: (-x[0], x[3]))
        best = candidates[0]
        return ParsedStringField(value=best[1], confidence=best[2], line_index=best[3])
    return ParsedStringField(value=None, confidence=None, line_index=None)

def _find_amount_field(lines: Sequence[RawLine], keywords: Sequence[str]) -> ParsedAmountField:
    expanded_keywords = list(keywords)
    if any(k in keywords for k in ("סה\"כ", "סהכ")):
        expanded_keywords.extend(["ה\"כ", "סח\"כ", "סה\"כז", "סהכז", "סיכום", "לתשלום"])
    if any(k in keywords for k in ("מע\"מ", "מעמ")):
        expanded_keywords.extend(["מ.ע.מ", "מע'מ", "ח\"יב"])
    
    candidates = []
    for line in lines:
        txt = _fuzzy_normalize((line.text_normalized or line.text_raw or "")).lower()
        if not txt: continue
        matched_kw = [kw for kw in expanded_keywords if kw in txt]
        if not matched_kw: continue
        txt_lower = txt.lower()
        is_before_vat = "לפני" in txt_lower and ("מ\"מ" in txt_lower or "מעמ" in txt_lower or "מע\"מ" in txt_lower)
        # Skip lines that look like they only contain catalog numbers or irrelevant info
        if any(w in txt_lower for w in ("גרם", "ק\"ג", "מל\"מל", "יח'")):
            # If the line contains "גרם" but also "סה\"כ", we have to be careful.
            # For now, let's just make sure we don't pick the '500' as the Total.
            pass

        amounts = []
        for m in _AMOUNT_RE.finditer(txt):
            amt_str = m.group(1)
            # Check context: if preceded by "500" and followed by "גרם", it's a weight.
            start, end = m.span()
            context = txt[max(0, start-10):min(len(txt), end+10)]
            if "גרם" in context or "גר'" in context or "ק\"ג" in context:
                continue
                
            amt = parse_amount(amt_str)
            if amt is not None and amt <= 1000000 and not (amt.is_integer() and len(str(int(amt))) >= 8):
                amounts.append(amt)
        is_total_search = any(k in keywords for k in ("סה\"כ", "לתשלום"))
        if amounts:
            best_amt = max(amounts) if is_total_search else amounts[-1]
            score = 10
            if any(k in matched_kw for k in keywords): score += 20
            if is_before_vat:
                if is_total_search: score -= 30 # Penalize for final total
                else: score += 15
            if line.index > len(lines) * 0.7: score += 5
            candidates.append((score, ParsedAmountField(value=best_amt, raw_text=line.text_raw, confidence=line.confidence, line_index=line.index)))
    if candidates:
        candidates.sort(key=lambda x: (-x[0], -x[1].line_index))
        return candidates[0][1]
    return ParsedAmountField(value=None, raw_text=None, confidence=None, line_index=None)

def _parse_invoice_no(lines: Sequence[RawLine]) -> ParsedStringField:
    invoice_kws = ("חשבונית", "מספר ח", "ח.מ", "מסרה", "מס '", "מס'", "ח-ן", "תעודת", "invoice")
    candidates = []
    for i, line in enumerate(lines):
        txt = (line.text_normalized or line.text_raw or "").lower()
        if not txt: continue
        if any(kw in txt for kw in invoice_kws) and not any(kw in txt for kw in ("מיקוד", "zip", "zipcode")):
            for j in range(max(0, i-2), min(len(lines), i+3)):
                nj_txt = (lines[j].text_normalized or lines[j].text_raw or "").lower()
                if j == i and any(kw in txt for kw in ("לקוח", "לכבוד")): continue
                for m in re.finditer(r"(\d{4,16})", nj_txt):
                    val = m.group(1)
                    if len(val) == 8 and (val.startswith("202") or val.startswith("05")): continue
                    score = 10
                    if j < len(lines) * 0.4: score += 15
                    if "חשבונית" in nj_txt: score += 10
                    if any(kw in nj_txt for kw in ("לקוח", "לכבוד")): score -= 20
                    candidates.append((score, ParsedStringField(value=val, confidence=lines[j].confidence, line_index=j)))
    if candidates:
        candidates.sort(key=lambda x: -x[0])
        return candidates[0][1]
    return ParsedStringField(value=None, confidence=None, line_index=None)

def _extract_items(lines: Sequence[RawLine], used_line_indices: Sequence[int]) -> List[LineItem]:
    used_set = set(used_line_indices)
    items = []
    for line in lines:
        if line.index in used_set: continue
        txt = line.text_normalized or line.text_raw
        if not txt: continue
        amounts = [m.group(1) for m in _AMOUNT_RE.finditer(txt)]
        if not amounts: continue
        line_total = None
        for amt_str in reversed(amounts):
            amt = parse_amount(amt_str)
            if amt is not None and amt <= 1000000 and not (amt.is_integer() and len(str(int(amt))) >= 8):
                line_total = amt
                break
        if line_total is None: continue
        quantity, unit_price = 1.0, line_total
        if len(amounts) >= 2:
            try:
                q_val = float(amounts[0].replace(" ", "").replace(",", ""))
                if 0 < q_val <= 10 and float(int(q_val)) == q_val:
                    quantity = q_val
                    unit_price = line_total / quantity if quantity > 0 else line_total
            except ValueError: pass
        desc = _AMOUNT_RE.sub("", txt).strip()
        if not desc: continue
        catalog_no = None
        for m in re.finditer(r"\b(\d{5,14})\b", txt):
            found_num = m.group(1)
            if float(found_num) not in (quantity, unit_price, line_total):
                catalog_no = found_num
                break
        items.append(LineItem(description=desc, quantity=quantity, unit_price=unit_price, line_total=line_total, confidence=line.confidence, line_index=line.index, catalog_no=catalog_no))
    return items
