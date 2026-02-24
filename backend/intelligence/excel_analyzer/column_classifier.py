"""
Infers column types (text/numeric/date/formula) from raw cell values.
"""
import re
from datetime import datetime, date
from typing import Any, Dict, List, Optional


DATE_PATTERNS = [
    r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$',
    r'^\d{4}[/-]\d{2}[/-]\d{2}$',
    r'^\d{1,2}\s+\w+\s+\d{4}$',
]


def _is_date_value(val: Any) -> bool:
    if isinstance(val, (datetime, date)):
        return True
    if isinstance(val, str):
        for pattern in DATE_PATTERNS:
            if re.match(pattern, val.strip()):
                return True
    return False


def _is_numeric_value(val: Any) -> bool:
    if isinstance(val, (int, float)):
        return True
    if isinstance(val, str):
        try:
            float(val.replace(',', '').replace('%', '').strip())
            return True
        except ValueError:
            pass
    return False


def classify_column(values: List[Any], formula_count: int = 0, total_cells: int = 0) -> str:
    """
    Classify a column's type based on its non-null values.

    Returns: 'text' | 'numeric' | 'date' | 'formula' | 'mixed' | 'empty'
    """
    non_null = [v for v in values if v is not None and v != '']
    if not non_null:
        return 'empty'

    # If more than 30% of cells have formulas, classify as formula
    if total_cells > 0 and formula_count / max(total_cells, 1) > 0.3:
        return 'formula'

    date_count = sum(1 for v in non_null if _is_date_value(v))
    numeric_count = sum(1 for v in non_null if _is_numeric_value(v))
    text_count = len(non_null) - date_count - numeric_count

    total = len(non_null)
    if date_count / total > 0.6:
        return 'date'
    if numeric_count / total > 0.6:
        return 'numeric'
    if text_count / total > 0.6:
        return 'text'
    return 'mixed'


def analyze_columns(values_grid: List[List[Any]], formula_grid: List[List[Optional[str]]],
                    header_row: int = 0) -> List[Dict]:
    """
    Analyze all columns from a 2D values grid.

    Returns list of ColumnAnalysis dicts.
    """
    if not values_grid:
        return []

    # Skip header row(s) for type classification
    data_rows = values_grid[header_row + 1:]
    formula_data_rows = formula_grid[header_row + 1:] if formula_grid else []

    if not data_rows:
        return []

    num_cols = max(len(row) for row in data_rows)
    results = []

    for col_idx in range(num_cols):
        col_values = [row[col_idx] if col_idx < len(row) else None for row in data_rows]
        col_formulas = [row[col_idx] if col_idx < len(row) else None for row in formula_data_rows]

        formula_count = sum(1 for f in col_formulas if f is not None)
        total_cells = len([v for v in col_values if v is not None])

        # Sample formula for display
        sample_formula = next((f for f in col_formulas if f is not None), None)

        null_count = sum(1 for v in col_values if v is None or v == '')
        null_rate = null_count / len(col_values) if col_values else 0.0

        col_type = classify_column(col_values, formula_count, len(col_values))

        # Get header name
        header_name = None
        if header_row < len(values_grid):
            header_row_data = values_grid[header_row]
            if col_idx < len(header_row_data):
                header_name = str(header_row_data[col_idx]).strip() if header_row_data[col_idx] is not None else f'Column_{col_idx}'

        results.append({
            'index': col_idx,
            'name': header_name or f'Column_{col_idx}',
            'detected_type': col_type,
            'null_rate': round(null_rate, 3),
            'formula_count': formula_count,
            'sample_values': [str(v) for v in col_values[:3] if v is not None],
            'formula_info': {
                'formula_type': None,  # filled by formula_classifier
                'sample_expression': sample_formula,
                'formula_count': formula_count,
            } if col_type == 'formula' or formula_count > 0 else None,
        })

    return results
