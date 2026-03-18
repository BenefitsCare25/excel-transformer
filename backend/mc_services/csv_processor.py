"""CSV processor for raw pipe-delimited Mediacorp data files."""

import pandas as pd
import io
import logging

logger = logging.getLogger(__name__)


def parse_pipe_delimited_csv(file_path_or_buffer, file_type='el'):
    """Parse a raw pipe-delimited CSV file into a clean DataFrame.

    Handles:
    - Pipe '|' delimiter
    - Auto-generated 'Column1, Column2...' header row (removes if detected)
    - Data type detection disabled (all read as strings initially)
    - Whitespace stripping on headers and values

    Args:
        file_path_or_buffer: File path string or file-like object
        file_type: 'el' for Employee Listing, 'dl' for Dependant Listing

    Returns:
        pd.DataFrame with clean columnar data
    """
    try:
        df = pd.read_csv(
            file_path_or_buffer,
            sep='|',
            dtype=str,
            keep_default_na=False,
            encoding='utf-8',
            on_bad_lines='skip'
        )
    except UnicodeDecodeError:
        if isinstance(file_path_or_buffer, str):
            df = pd.read_csv(
                file_path_or_buffer,
                sep='|',
                dtype=str,
                keep_default_na=False,
                encoding='latin-1',
                on_bad_lines='skip'
            )
        else:
            file_path_or_buffer.seek(0)
            df = pd.read_csv(
                file_path_or_buffer,
                sep='|',
                dtype=str,
                keep_default_na=False,
                encoding='latin-1',
                on_bad_lines='skip'
            )

    if df.empty:
        logger.warning("CSV file is empty after parsing")
        return df

    # Detect and remove auto-generated 'Column1, Column2...' header row
    # This happens when Excel Power Query imports the CSV
    headers_are_auto = all(
        col.strip().lower().startswith('column') and col.strip()[6:].isdigit()
        for col in df.columns
        if col.strip()
    )

    if headers_are_auto and len(df) > 0:
        logger.info("Detected auto-generated 'Column1...' headers, using first data row as headers")
        new_headers = df.iloc[0].values
        df = df.iloc[1:].reset_index(drop=True)
        df.columns = [str(h).strip() for h in new_headers]

    # Strip whitespace from column names
    df.columns = [str(col).strip() for col in df.columns]

    # Strip whitespace from all string values
    for col in df.columns:
        df[col] = df[col].apply(lambda x: str(x).strip() if x and str(x).strip() else '')

    # Replace empty strings with NaN for consistent handling with Excel-loaded data
    df = df.replace('', pd.NA)

    # Convert numeric-looking columns back to appropriate types
    # Staff ID should stay as-is (could have leading zeros)
    # Dates should stay as strings for now

    logger.info(f"CSV parsed: {len(df)} rows, {len(df.columns)} columns")
    logger.info(f"Columns: {list(df.columns)}")

    return df


def is_csv_file(filename):
    """Check if file has CSV extension."""
    if not filename:
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'


def is_supported_file(filename):
    """Check if file is CSV or XLSX."""
    if not filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in ('csv', 'xlsx')
