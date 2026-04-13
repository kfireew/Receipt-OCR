"""Header amounts extractor service.

Extracts Subtotal, VAT, and Total amounts from raw OCR lines.
Uses keyword matching + amount regex patterns.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from stages.grouping.line_assembler import RawLine
from stages.post_process.fuzzy_corrector import snap_to_keyword
from stages.parsing.shared import _AMOUNT_RE, parse_amount, ParsedAmountField


def _fuzzy_normalize(text: str) -> str:
    """Apply token-level keyword snapping before regex matching."""
    if not text:
        return text
    return " ".join(snap_to_keyword(tok) for tok in text.split())


def _find_amount_field(
    lines: Sequence[RawLine],
    keywords: Sequence[str],
) -> ParsedAmountField:
    """Find the best amount matching the given keywords.

    Scans all lines for keyword matches, then extracts the highest-scoring
    amount value. Scoring considers:
    - Exact keyword match (+20)
    - Position near bottom (+5 if > 70% of line count)
    - Pre-VAT context bonus for subtotal
    - Pre-VAT penalty for final total search
    """
    expanded_keywords = list(keywords)
    if any(k in keywords for k in ("סה\"כ", "סהכ")):
        expanded_keywords.extend(["ה\"כ", "סח\"כ", "סה\"כז", "סהכז", "סיכום", "לתשלום"])
    if any(k in keywords for k in ("מע\"מ", "מעמ")):
        expanded_keywords.extend(["מ.ע.מ", "מע'מ", "ח\"יב"])

    candidates = []
    for line in lines:
        txt = _fuzzy_normalize((line.text_normalized or line.text_raw or "")).lower()
        if not txt:
            continue
        matched_kw = [kw for kw in expanded_keywords if kw in txt]
        if not matched_kw:
            continue
        txt_lower = txt.lower()
        is_before_vat = "לפני" in txt_lower and ("מ\"מ" in txt_lower or "מעמ" in txt_lower or "מע\"מ" in txt_lower)

        amounts = []
        for m in _AMOUNT_RE.finditer(txt):
            amt_str = m.group(1)
            # Skip weight-like numbers (גרם, ק"ג)
            start, end = m.span()
            context = txt[max(0, start - 10):min(len(txt), end + 10)]
            if "גרם" in context or "גר'" in context or "ק\"ג" in context:
                continue

            amt = parse_amount(amt_str)
            if amt is not None and amt <= 1000000 and not (amt.is_integer() and len(str(int(amt))) >= 8):
                amounts.append(amt)

        is_total_search = any(k in keywords for k in ("סה\"כ", "לתשלום"))
        if amounts:
            best_amt = max(amounts) if is_total_search else amounts[-1]
            score = 10
            if any(k in matched_kw for k in keywords):
                score += 20
            if is_before_vat:
                if is_total_search:
                    score -= 30
                else:
                    score += 15
            if line.index > len(lines) * 0.7:
                score += 5
            candidates.append((
                score,
                ParsedAmountField(
                    value=best_amt,
                    raw_text=line.text_raw,
                    confidence=line.confidence,
                    line_index=line.index,
                ),
            ))
    if candidates:
        candidates.sort(key=lambda x: (-x[0], -x[1].line_index))
        return candidates[0][1]
    return ParsedAmountField(
        value=None, raw_text=None, confidence=None, line_index=None,
    )
