"""
Per-field difference detection with type-aware comparison.
"""
import re
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple


def _normalize(val: Any) -> str:
    """Normalize a value to a comparable string."""
    if val is None:
        return ''
    if isinstance(val, float) and val == int(val):
        return str(int(val))
    if isinstance(val, (datetime, date)):
        return val.strftime('%Y-%m-%d')
    return str(val).strip()


def _is_empty(val: Any) -> bool:
    return val is None or str(val).strip() == ''


def fields_changed(row_a: Dict, row_b: Dict, fields: List[str]) -> List[str]:
    """Return list of field names that differ between two rows."""
    changed = []
    for f in fields:
        val_a = row_a.get(f)
        val_b = row_b.get(f)
        if _normalize(val_a) != _normalize(val_b):
            changed.append(f)
    return changed


def evaluate_condition(row_a: Optional[Dict], row_b: Optional[Dict],
                       condition: Dict) -> bool:
    """
    Evaluate a single condition against matched row pair (row_a, row_b).
    For PRESENCE_RULE context, one of row_a/row_b may be None.
    """
    field = condition['field']
    operator = condition['operator']
    cond_value = condition.get('value')

    # Use row_b if available (newer state), else row_a
    current_row = row_b if row_b is not None else row_a
    prev_row = row_a

    current_val = current_row.get(field) if current_row else None
    prev_val = prev_row.get(field) if prev_row else None

    if operator == 'is_empty':
        return _is_empty(current_val)

    if operator == 'is_not_empty':
        return not _is_empty(current_val)

    if operator == 'equals':
        return _normalize(current_val) == _normalize(cond_value)

    if operator == 'not_equals':
        return _normalize(current_val) != _normalize(cond_value)

    if operator == 'contains':
        return str(cond_value).lower() in str(current_val or '').lower()

    if operator == 'starts_with':
        return str(current_val or '').lower().startswith(str(cond_value).lower())

    if operator == 'changed_from_empty':
        return _is_empty(prev_val) and not _is_empty(current_val)

    if operator == 'changed_to_empty':
        return not _is_empty(prev_val) and _is_empty(current_val)

    if operator == 'date_is_before':
        try:
            dt_current = _parse_date(current_val)
            dt_compare = _parse_date(cond_value)
            if dt_current and dt_compare:
                return dt_current < dt_compare
        except Exception:
            pass
        return False

    if operator == 'date_is_after':
        try:
            dt_current = _parse_date(current_val)
            dt_compare = _parse_date(cond_value)
            if dt_current and dt_compare:
                return dt_current > dt_compare
        except Exception:
            pass
        return False

    if operator == 'changed_from_pattern':
        return bool(re.search(str(cond_value), str(prev_val or ''), re.IGNORECASE))

    if operator == 'changed_to_pattern':
        return bool(re.search(str(cond_value), str(current_val or ''), re.IGNORECASE))

    return False


def evaluate_conditions(row_a: Optional[Dict], row_b: Optional[Dict],
                        conditions: List[Dict], join: str = 'AND') -> bool:
    """Evaluate a list of conditions with AND/OR joining."""
    results = [evaluate_condition(row_a, row_b, c) for c in conditions]
    if join == 'AND':
        return all(results)
    return any(results)


def _parse_date(val: Any) -> Optional[datetime]:
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day)
    if isinstance(val, str) and val.strip():
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d %b %Y'):
            try:
                return datetime.strptime(val.strip(), fmt)
            except ValueError:
                continue
    return None


def resolve_outcome_label(label_template: str, row: Dict) -> str:
    """Replace {field_name} placeholders in outcome labels with row values."""
    def replacer(match):
        field = match.group(1)
        val = row.get(field, '')
        return str(val) if val is not None else ''
    return re.sub(r'\{(\w[\w\s]*)\}', replacer, label_template)
