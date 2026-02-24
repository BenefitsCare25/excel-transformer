"""
Auto-detects header rows in Excel sheets by finding the densest non-numeric row.
"""
from typing import Any, List, Optional


def _is_text(val: Any) -> bool:
    if val is None:
        return False
    if isinstance(val, str) and val.strip():
        return True
    return False


def _row_text_density(row: List[Any]) -> float:
    """Fraction of non-null cells that are text."""
    non_null = [v for v in row if v is not None and v != '']
    if not non_null:
        return 0.0
    text_cells = sum(1 for v in non_null if _is_text(v))
    return text_cells / len(non_null)


def _row_non_null_count(row: List[Any]) -> int:
    return sum(1 for v in row if v is not None and v != '')


def detect_header_row(values_grid: List[List[Any]], max_scan_rows: int = 30) -> int:
    """
    Find the most likely header row index in a 2D grid.

    Strategy:
    1. Scan first `max_scan_rows` rows
    2. Find the row with highest text density AND reasonable fill rate
    3. Among ties, prefer the earliest row

    Returns: 0-based row index of detected header.
    """
    scan_limit = min(max_scan_rows, len(values_grid))
    if scan_limit == 0:
        return 0

    best_row = 0
    best_score = -1.0

    for i in range(scan_limit):
        row = values_grid[i]
        density = _row_text_density(row)
        fill = _row_non_null_count(row) / max(len(row), 1)

        # Score: high text density + reasonable fill rate
        score = density * 0.7 + fill * 0.3

        if score > best_score:
            best_score = score
            best_row = i

        # If we already found a very likely header (>80% text density) in first 5 rows, stop early
        if density > 0.8 and fill > 0.5 and i < 5:
            return i

    return best_row


def extract_header_names(values_grid: List[List[Any]], header_row: int) -> List[str]:
    """Return header cell values as strings for the detected header row."""
    if header_row >= len(values_grid):
        return []
    row = values_grid[header_row]
    return [str(v).strip() if v is not None else f'Col_{i}' for i, v in enumerate(row)]
