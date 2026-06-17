"""Date formatting utilities for Mediacorp ADC Processor."""

import warnings
import pandas as pd
from datetime import datetime
from typing import Optional, Union

def format_date_ddmmyy(date_val: Union[str, datetime, pd.Timestamp, None]) -> str:
    """
    Format date as DDMMYY string.

    Args:
        date_val: Date value (can be string, datetime, Timestamp, or None)

    Returns:
        Formatted date string (e.g., '270325') or empty string if invalid
    """
    if date_val is None or pd.isna(date_val):
        return ''

    try:
        if isinstance(date_val, str):
            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y']:
                try:
                    date_val = datetime.strptime(date_val, fmt)
                    break
                except ValueError:
                    continue
            else:
                return str(date_val)

        if isinstance(date_val, (datetime, pd.Timestamp)):
            return date_val.strftime('%d%m%y')

        return str(date_val)
    except Exception:
        return str(date_val) if date_val else ''


def format_date_ddmmyyyy(date_val: Union[str, datetime, pd.Timestamp, None]) -> str:
    """
    Format date as DD/MM/YYYY string.

    Args:
        date_val: Date value

    Returns:
        Formatted date string (e.g., '27/03/2025') or empty string
    """
    if date_val is None or pd.isna(date_val):
        return ''

    try:
        if isinstance(date_val, str):
            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y']:
                try:
                    date_val = datetime.strptime(date_val, fmt)
                    break
                except ValueError:
                    continue
            else:
                return str(date_val)

        if isinstance(date_val, (datetime, pd.Timestamp)):
            return date_val.strftime('%d/%m/%Y')

        return str(date_val)
    except Exception:
        return str(date_val) if date_val else ''


def get_today_ddmmyy() -> str:
    """Get today's date as DDMMYY string."""
    return datetime.now().strftime('%d%m%y')


def is_blank(value) -> bool:
    """Check if a value is blank (None, NaN, or empty string)."""
    if value is None:
        return True
    if pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == '':
        return True
    return False


def is_not_blank(value) -> bool:
    """Check if a value is not blank."""
    return not is_blank(value)


def parse_lds(value):
    """Parse an LDS cell to a normalised midnight Timestamp, or None.

    Numeric values (Excel serial numbers) are NOT interpreted as dates to avoid
    producing bogus 1970-era results — they return None, falling back to string
    compare in lds_date_changed.
    """
    if is_blank(value):
        return None
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            ts = pd.to_datetime(value, dayfirst=True, errors='coerce')
    except Exception:
        return None
    if pd.isna(ts):
        return None
    return ts.normalize()


def lds_date_changed(new_lds, old_lds) -> bool:
    """True only when both LDS values are present and represent different dates.

    Both sides are parsed to normalised Timestamps before comparing, so equivalent
    values in different formats (Timestamp vs '31/01/2026', '31/1/2026' vs
    '31/01/2026') are not mis-flagged. Falls back to case-insensitive string
    compare when neither side parses. Returns False when only one side parses
    (avoids false positives from mixed xlsx/csv reads).
    """
    if is_blank(new_lds) or is_blank(old_lds):
        return False
    new_date = parse_lds(new_lds)
    old_date = parse_lds(old_lds)
    if new_date is not None and old_date is not None:
        return new_date != old_date
    if new_date is None and old_date is None:
        return str(new_lds).strip().lower() != str(old_lds).strip().lower()
    return False
