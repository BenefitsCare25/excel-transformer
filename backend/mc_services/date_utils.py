"""Date formatting utilities for Mediacorp ADC Processor."""

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
