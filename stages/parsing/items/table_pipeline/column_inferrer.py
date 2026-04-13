"""
Column Inference Service - Service 1 of 3

Analyzes X-positions across lines to detect column structure.
For RTL receipts: columns are [total, price, qty, desc] (right to left)

Usage:
    columns = infer_columns(raw_lines)
    # columns = {'desc': (x1, x2), 'qty': (x1, x2), ...}
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from stages.grouping.line_assembler import RawLine


@dataclass
class ColumnLayout:
    """Inferred column positions."""
    desc_x: Optional[Tuple[float, float]] = None  # Description column (rightmost)
    qty_x: Optional[Tuple[float, float]] = None   # Quantity column
    price_x: Optional[Tuple[float, float]] = None  # Unit price column
    total_x: Optional[Tuple[float, float]] = None  # Total column (leftmost)
    discount_x: Optional[Tuple[float, float]] = None  # Discount column (optional)
    confidence: float = 0.0

    @property
    def is_valid(self) -> bool:
        return self.total_x is not None  # At minimum need total column


def infer_columns(raw_lines: List[RawLine], num_lines: int = 20) -> ColumnLayout:
    """
    Infer column positions from the first N lines that look like table rows.

    Strategy:
    1. Find lines with numeric values (likely table rows)
    2. Cluster X-positions into groups
    3. Identify which cluster is which column based on position

    For RTL:
    - Rightmost cluster = description
    - Left of that = total (often just a number)
    - Left of that = price
    - Left of that = quantity
    """
    if not raw_lines:
        return ColumnLayout()

    # Find candidate lines (with amounts) - use more lines for better inference
    candidates = []
    for line in raw_lines:
        text = line.text_raw or ""
        # Count numeric values
        numeric_count = sum(1 for c in text if c.isdigit())
        if numeric_count >= 3:  # At least 3 digits = likely has amounts
            candidates.append(line)
        if len(candidates) >= num_lines:
            break

    if not candidates:
        return ColumnLayout()

    # Collect all box X-centers with their text info
    x_data: List[Tuple[float, int, str]] = []  # (x_center, line_idx, text)

    for line_idx, line in enumerate(candidates):
        if not line.boxes:
            continue
        for box in line.boxes:
            x_center = (box.box[0] + box.box[2]) / 2
            text = box.text_normalized or box.text_raw or ""
            # Only count boxes that look like numbers
            if text.replace(".", "").replace(",", "").isdigit():
                x_data.append((x_center, line_idx, text))

    if len(x_data) < 10:
        return ColumnLayout()

    # Cluster X positions into groups
    clusters = _cluster_x_positions(x_data)

    if len(clusters) < 2:
        return ColumnLayout()

    # Analyze each cluster to determine if it's numeric
    # and identify column types
    column_info = _identify_columns(clusters)

    if not column_info:
        return ColumnLayout()

    # Build layout
    layout = ColumnLayout()
    layout.confidence = _calculate_cluster_confidence(column_info, len(candidates))

    # Sort by X position (RTL: rightmost first)
    sorted_cols = sorted(column_info.items(), key=lambda x: x[0], reverse=True)

    # Assign columns based on position and type
    # RTL: cluster 0 = desc, then total, price, qty
    for i, (x_center, info) in enumerate(sorted_cols):
        x_range = (info['min_x'], info['max_x'])

        if i == 0:
            layout.desc_x = x_range  # Rightmost = description
        elif info['is_numeric']:
            # Determine if total, price, or qty based on position
            if i == 1:
                layout.total_x = x_range  # Second from right = total
            elif i == 2:
                layout.price_x = x_range
            elif i == 3:
                layout.qty_x = x_range
            else:
                layout.discount_x = x_range  # Extra columns could be discount

    return layout


def _cluster_x_positions(x_data: List[Tuple[float, int, str]], threshold: float = 40.0) -> Dict[float, Dict]:
    """
    Cluster X positions into groups.
    Returns: {cluster_center: {'min_x':, 'max_x':, 'texts': [], 'count': }}
    """
    if not x_data:
        return {}

    # Sort by X
    sorted_x = sorted(x_data, key=lambda x: x[0])

    clusters: Dict[float, Dict] = {}
    current_center = sorted_x[0][0]
    clusters[current_center] = {
        'min_x': current_center,
        'max_x': current_center,
        'texts': [sorted_x[0][2]],
        'count': 1
    }

    for x, line_idx, text in sorted_x[1:]:
        # If close to current cluster, add to it
        if abs(x - current_center) <= threshold:
            clusters[current_center]['min_x'] = min(clusters[current_center]['min_x'], x)
            clusters[current_center]['max_x'] = max(clusters[current_center]['max_x'], x)
            clusters[current_center]['texts'].append(text)
            clusters[current_center]['count'] += 1
        else:
            # Start new cluster
            current_center = x
            clusters[current_center] = {
                'min_x': x,
                'max_x': x,
                'texts': [text],
                'count': 1
            }

    # Merge very small clusters into nearest neighbor
    clusters = _merge_small_clusters(clusters, threshold)

    return clusters


def _merge_small_clusters(clusters: Dict[float, Dict], threshold: float) -> Dict[float, Dict]:
    """Merge clusters with very few points into nearest cluster."""
    if len(clusters) <= 4:
        return clusters

    # Find clusters with < 2 points
    small = {k: v for k, v in clusters.items() if v['count'] < 2}
    large = {k: v for k, v in clusters.items() if v['count'] >= 2}

    if not large:
        return clusters

    for small_center, small_info in small.items():
        # Find nearest large cluster
        nearest = min(large.keys(), key=lambda x: abs(x - small_center))
        large[nearest]['min_x'] = min(large[nearest]['min_x'], small_info['min_x'])
        large[nearest]['max_x'] = max(large[nearest]['max_x'], small_info['max_x'])
        large[nearest]['texts'].extend(small_info['texts'])
        large[nearest]['count'] += small_info['count']

    return large


def _identify_columns(clusters: Dict[float, Dict]) -> Dict[float, Dict]:
    """Identify what type of data each cluster contains (numeric or text)."""
    result = {}

    for x_center, info in clusters.items():
        texts = info['texts']

        # Check if cluster is numeric (mostly numbers)
        numeric_count = sum(1 for t in texts if _is_numeric(t))
        is_numeric = numeric_count / len(texts) > 0.5 if texts else False

        result[x_center] = {
            'min_x': info['min_x'],
            'max_x': info['max_x'],
            'is_numeric': is_numeric,
            'count': info['count']
        }

    return result


def _is_numeric(text: str) -> bool:
    """Check if text is primarily numeric."""
    if not text:
        return False
    cleaned = text.replace(".", "").replace(",", "").replace("'", "")
    return cleaned.replace("-", "").isdigit()


def _calculate_cluster_confidence(column_info: Dict[float, Dict], num_lines: int) -> float:
    """Calculate confidence based on cluster consistency."""
    if not column_info:
        return 0.0

    # More clusters = higher confidence (table has structure)
    cluster_score = min(len(column_info) / 4.0, 1.0) * 50

    # Consistency: how many items per cluster
    total_points = sum(v['count'] for v in column_info.values())
    avg_per_line = total_points / max(num_lines, 1)
    consistency_score = min(avg_per_line / 3.0, 1.0) * 50

    return cluster_score + consistency_score
