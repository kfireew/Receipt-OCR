"""
Adaptive Receipt Post-Processor

Analyzes each receipt and adjusts extraction parameters based on:
- Vendor type detection
- Amount distribution analysis
- Receipt total (if available)
- Known patterns per vendor

This allows the system to adapt to different receipt formats.
"""
from __future__ import annotations

import os
import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from collections import Counter

from .line_extractor import ExtractedLineItem
from .auto_corrector import auto_correct_items, CorrectedItem


# Known vendor patterns - catalog number ranges and typical item counts
VENDOR_PROFILES = {
    # Vendor: (catalog_number_prefixes, expected_item_count_range, typical_total_range)
    "StraussCool": {
        "catalog_prefixes": ["729000", "729001"],  # Long barcode prefixes
        "expected_items_range": (15, 35),
        "typical_total_range": (500, 5000),
        "has_discounts": True,
    },
    "Tnuva": {
        "catalog_prefixes": ["057", "729"],  # Short + long barcodes
        "expected_items_range": (8, 40),
        "typical_total_range": (300, 4000),
        "has_discounts": True,
    },
    "Wisso": {
        "catalog_prefixes": ["557", "558"],  # Wisso catalog system
        "expected_items_range": (20, 40),
        "typical_total_range": (1000, 8000),
        "has_discounts": False,
    },
    "Ida": {
        "catalog_prefixes": [],  # Various
        "expected_items_range": (30, 80),
        "typical_total_range": (500, 5000),
        "has_discounts": True,
    },
    "Avikam": {
        "catalog_prefixes": ["729"],  # Standard barcodes
        "expected_items_range": (8, 20),
        "typical_total_range": (200, 3000),
        "has_discounts": False,
    },
    "Globrands": {
        "catalog_prefixes": ["729"],
        "expected_items_range": (8, 25),
        "typical_total_range": (200, 5000),
        "has_discounts": False,
    },
    "Hamefitz": {
        "catalog_prefixes": [],
        "expected_items_range": (5, 15),
        "typical_total_range": (100, 2000),
        "has_discounts": False,
    },
    "Tayari": {
        "catalog_prefixes": [],
        "expected_items_range": (20, 60),
        "typical_total_range": (500, 8000),
        "has_discounts": True,
    },
}


@dataclass
class ReceiptProfile:
    """Profile for a specific receipt."""
    vendor: str
    item_count_range: Tuple[int, int]
    total_range: Tuple[float, float]
    amount_percentiles: Dict[str, float]  # 25th, 50th, 75th, 90th percentiles
    has_discounts: bool


def detect_vendor(ocr_text: str) -> str:
    """Detect vendor from OCR text."""
    ocr_lower = ocr_lower = ocr_text.lower() if ocr_text else ""

    vendors = {
        "StraussCool": ["שטראוס", "שטראום", "strauss"],
        "Tnuva": ["תנובה", "tnuva"],
        "Wisso": ["ויסוצקי", "wisso"],
        "Ida": ["עידה", "ידי", "יבוא"],
        "Avikam": ["אביקם", "זינגר", "avikam"],
        "Globrands": ["גלוב", "globrands"],
        "Hamefitz": ["המפיץ"],
        "Tayari": ["טיירי"],
    }

    for vendor, keywords in vendors.items():
        for kw in keywords:
            if kw in ocr_lower:
                return vendor

    return "Unknown"


def analyze_amount_distribution(items: List[ExtractedLineItem]) -> Dict[str, float]:
    """Analyze the distribution of line totals."""
    if not items:
        return {"p25": 0, "p50": 0, "p75": 0, "p90": 0, "max": 0}

    totals = sorted([i.line_total for i in items])

    def percentile(data, p):
        if not data:
            return 0
        idx = int(len(data) * p / 100)
        idx = min(idx, len(data) - 1)
        return data[idx]

    return {
        "p25": percentile(totals, 25),
        "p50": percentile(totals, 50),
        "p75": percentile(totals, 75),
        "p90": percentile(totals, 90),
        "max": max(totals) if totals else 0,
    }


def adaptive_post_process(
    items: List[CorrectedItem],
    receipt_total: float = None,
    vendor: str = None,
    ocr_text: str = None
) -> List[CorrectedItem]:
    """
    Apply adaptive post-processing to filter noise and fix issues.

    This analyzes the receipt to determine appropriate thresholds.

    Args:
        items: Corrected items from pipeline
        receipt_total: Known receipt total
        vendor: Detected vendor type
        ocr_text: Full OCR text for vendor detection

    Returns:
        Filtered and cleaned items
    """
    if not items:
        return []

    # Auto-detect vendor if not provided
    if not vendor and ocr_text:
        vendor = detect_vendor(ocr_text)

    # Get vendor profile
    profile = VENDOR_PROFILES.get(vendor, VENDOR_PROFILES.get("Unknown", {}))

    # Analyze amount distribution
    dist = analyze_amount_distribution(items)

    # Calculate thresholds based on distribution
    thresholds = _calculate_thresholds(items, receipt_total, profile, dist)

    # Apply filters
    filtered = _apply_filters(items, thresholds, profile)

    # Remove duplicates based on total
    deduped = _deduplicate_items(filtered)

    # Re-validate math
    final = _revalidate_math(deduped, receipt_total)

    return final


def _calculate_thresholds(
    items: List[CorrectedItem],
    receipt_total: float,
    profile: Dict,
    dist: Dict
) -> Dict:
    """Calculate appropriate thresholds for this receipt."""

    # MORE LENIENT thresholds - don't filter aggressively
    min_total = 1.0  # Very low minimum (filter only obvious noise)
    max_total = 5000  # High maximum

    # Adjust based on distribution - but be lenient
    if dist.get("p90", 0) > 0:
        # Only cap at 2x the 90th percentile
        max_total = min(max_total, dist["p90"] * 2)

    # Adjust based on receipt total
    if receipt_total:
        # Items can be up to 60% of receipt total
        max_from_receipt = receipt_total * 0.6
        max_total = min(max_total, max_from_receipt)

    return {
        "min_total": min_total,
        "max_total": max_total,
    }


def _apply_filters(
    items: List[CorrectedItem],
    thresholds: Dict,
    profile: Dict
) -> List[CorrectedItem]:
    """Apply threshold-based filtering - BE LENIENT."""
    filtered = []

    for item in items:
        total = item.line_total

        # Filter: too small (noise) - but be very lenient
        if total < thresholds["min_total"]:
            continue

        # Filter: extremely large (likely catalog numbers > 10000)
        # But DON'T filter based on qty - bulk purchases are valid
        if total > 10000:
            continue

        filtered.append(item)

    return filtered


def _deduplicate_items(items: List[CorrectedItem]) -> List[CorrectedItem]:
    """Remove duplicate items (same total + similar description)."""
    if not items:
        return []

    # Group by line_total
    by_total = {}
    for item in items:
        key = round(item.line_total, 2)
        if key not in by_total:
            by_total[key] = []
        by_total[key].append(item)

    # For each group, keep the one with best confidence
    result = []
    for total, group in by_total.items():
        if len(group) == 1:
            result.append(group[0])
        else:
            # Keep the one with highest confidence
            best = max(group, key=lambda x: x.confidence)
            result.append(best)

    return result


def _revalidate_math(
    items: List[CorrectedItem],
    receipt_total: float
) -> List[CorrectedItem]:
    """Re-validate math and fix any remaining issues."""
    result = []

    for item in items:
        # Recalculate to ensure consistency
        expected = round(item.quantity * item.unit_price, 2)
        if abs(expected - item.line_total) > 0.01:
            # Fix the total to match qty * price
            item.line_total = expected

        result.append(item)

    return result
