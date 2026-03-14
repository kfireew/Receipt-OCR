from __future__ import annotations

import difflib
from typing import List, Dict, Optional

# A dictionary of standard Hebrew receipt keywords and their expected "clean" versions.
RECEIPT_KEYWORDS = [
    "חשבונית", "מספר", "סך הכל", "סה\"כ", "סהכ", "מע\"מ", "מעמ",
    "תאריך", "הופק", "יום", "לתשלום", "לשום", "סכום", "ביניים",
    "מיקוד", "לקוח", "לכבוד", "מחיר", "כמות", "פריט", "תיאור",
    "סחר", "שיווק", "בע\"מ", "גורמה", "אביקם", "זינגר"
]

def snap_to_keyword(token: str, threshold: float = 0.7) -> str:
    """
    Algorithm: Token-Level Snapping
    -------------------------------
    This function takes a single word (token) from the OCR output and compares it 
    against a dictionary of known Hebrew receipt keywords. 
    
    If the token is 'close' enough (defined by the threshold), we assume the OCR 
    made a minor character error (e.g. 'ה' instead of 'ח') and we snap it back 
    to the correct dictionary word.
    
    Args:
        token: The raw word from OCR.
        threshold: 0 to 1 similarity score required to trigger a correction.
    """
    if not token or len(token) < 2:
        return token
    
    # We only care about tokens that look like they might be Hebrew keywords
    # Skip clearly numeric tokens
    if any(c.isdigit() for c in token) and not any(c.isalpha() for c in token):
        return token

    matches = difflib.get_close_matches(token, RECEIPT_KEYWORDS, n=1, cutoff=threshold)
    if matches:
        return matches[0]
    return token

def fuzzy_correct_line(text: str, threshold: float = 0.8) -> str:
    """
    Process a full line of text, attempting to fuzzy correct each word.
    """
    if not text:
        return text
    
    words = text.split()
    corrected_words = []
    
    for word in words:
        # Avoid correcting tokens with symbols like quotes or dots unless they are short
        if any(c in word for c in "\".-") and len(word) > 4:
            corrected_words.append(word)
            continue
            
        corrected = snap_to_keyword(word, threshold=threshold)
        corrected_words.append(corrected)
        
    return " ".join(corrected_words)
