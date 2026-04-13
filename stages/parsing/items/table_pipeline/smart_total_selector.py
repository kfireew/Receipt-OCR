"""
Smart Total Selector Service

Uses receipt total to help identify which amount is the true item total
vs catalog numbers or other noise.
"""
from typing import List, Optional


def select_line_total(
    amounts: List[float],
    receipt_total: float = None
) -> Optional[float]:
    """
    Select the most likely line total from amounts.

    Strategy:
    1. Filter to realistic amounts (0.5 - 5000)
    2. Filter out catalog numbers (>1000) unless needed
    3. Use receipt_total to help validate if available
    4. Return the most likely total

    Args:
        amounts: All parsed amounts from the line
        receipt_total: Known receipt total (if available)

    Returns:
        The most likely line total, or None
    """
    if not amounts:
        return None

    # Step 1: Filter to realistic range
    valid = [a for a in amounts if 0.5 <= a <= 5000]
    if not valid:
        return None

    # Step 2: Filter out potential catalog numbers
    # Catalog numbers typically are > 1000 and appear early in the line
    non_catalog = [a for a in valid if a <= 1000]
    if not non_catalog:
        # All amounts are > 1000, might be a bulk item
        # Check if receipt_total helps
        if receipt_total and receipt_total > 0:
            # Find amount closest to receipt_total / expected item count
            # (This is rough heuristics)
            for a in valid:
                if a <= receipt_total * 0.5:
                    return a
        return max(valid)  # Fallback

    # Step 3: For non-catalog amounts, pick the right one
    if len(non_catalog) == 1:
        return non_catalog[0]

    # Multiple candidates - pick the one that makes most sense
    # Heuristic: largest is usually the total
    # But verify it's not much larger than the second largest
    sorted_amounts = sorted(non_catalog, reverse=True)
    largest = sorted_amounts[0]
    second = sorted_amounts[1]

    # If largest is more than 3x the second, it might be wrong
    if largest > second * 3:
        # Could be a catalog number that slipped through
        # Use second largest instead
        return second

    return largest
