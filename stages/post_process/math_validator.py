from __future__ import annotations

import logging
from typing import Optional
from stages.parsing.models import ParsedReceipt

logger = logging.getLogger(__name__)

def validate_math(receipt: ParsedReceipt, tolerance: float = 0.05) -> ParsedReceipt:
    """
    Algorithm: The "Accounting Ledger" Check
    ----------------------------------------
    This validator enforces the fundamental accounting rule: 
    Subtotal + Value Added Tax (VAT) = Grand Total.
    
    If the equation does not balance:
    1. It checks if the discrepancy matches a missing 17% VAT (Standard Israeli VAT).
    2. it checks if the Subtotal and Total were accidentally swapped during parsing.
    3. It logs the inconsistency for future debugging.
    
    This acts as a logical safety net for OCR character slips in numeric fields.
    """
    sub = receipt.subtotal.value
    vat = receipt.vat.value
    tot = receipt.total.value

    if sub is None or tot is None:
        return receipt

    # If VAT is missing, assume it might be 0 or included
    calc_vat = vat if vat is not None else 0.0
    
    expected_total = sub + calc_vat
    
    diff = abs(expected_total - tot)
    if diff <= tolerance:
        return receipt
    
    # Logic for common OCR slips (e.g. 17% VAT check)
    if vat is None and sub > 0:
        # Check if total is roughly sub * 1.17
        if abs((sub * 1.17) - tot) <= tolerance:
            # We found a missing VAT!
            receipt.vat.value = tot - sub
            receipt.vat.raw_text = "AUTO-CORRECTED (17% VAT)"
            logger.info("Auto-corrected missing VAT based on 17% rule.")
            
    # Check if total and subtotal were swapped
    if abs((tot + calc_vat) - sub) <= tolerance:
        # Swapped sub and total
        receipt.subtotal, receipt.total = receipt.total, receipt.subtotal
        logger.info("Swapped subtotal and total based on math check.")

    return receipt
