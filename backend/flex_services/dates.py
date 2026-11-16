"""Date cells typed by hand in client workbooks (shared by the Flex adapters)."""
import re
from datetime import date

import pandas as pd

_DAY_FIRST = re.compile(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})')
_YEAR_FIRST = re.compile(r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})')
_TIME_SUFFIX = re.compile(r'[ T]\d{1,2}:\d{2}(:\d{2}(\.\d+)?)?$')
_MONTH_NAME = re.compile(r'[A-Za-z]{3}')


def is_blank_cell(value):
    """True for empty cells: None, NaN/NaT, or text that is only whitespace."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return bool(pd.isna(value))


def parse_date_cell(value):
    """Excel date or typed date text -> Timestamp; NaT when blank or not a real date.

    Text is read only in unambiguous shapes: dd/mm/yyyy (Singapore order, also with - or .),
    yyyy-mm-dd (also with / or .) and dates with a month name ('14 Nov 2026'). Anything
    else - two-digit years, typos such as '14/11/20256', bare numbers - returns NaT so the
    caller can flag it instead of guessing. Years outside 1900-2100 are treated as typos.
    """
    if is_blank_cell(value):
        return pd.NaT
    try:
        if isinstance(value, date):
            parsed = pd.Timestamp(value)
        elif isinstance(value, str):
            parsed = _parse_text(_TIME_SUFFIX.sub('', value.strip()))
        else:
            return pd.NaT
    except (ValueError, OverflowError):     # e.g. an Excel date in year 9999 on pandas 2.x
        return pd.NaT
    if pd.isna(parsed) or not 1900 <= parsed.year <= 2100:
        return pd.NaT
    return parsed.normalize()


def _parse_text(text):
    for pattern, order in ((_DAY_FIRST, (3, 2, 1)), (_YEAR_FIRST, (1, 2, 3))):
        match = pattern.fullmatch(text)
        if match:
            year, month, day = (int(match.group(i)) for i in order)
            try:
                return pd.Timestamp(year=year, month=month, day=day)
            except ValueError:
                return pd.NaT
    if _MONTH_NAME.search(text):
        return pd.to_datetime(text, dayfirst=True, errors='coerce')
    return pd.NaT
