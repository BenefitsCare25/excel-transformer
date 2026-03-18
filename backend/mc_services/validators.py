"""File and data validation utilities for Mediacorp ADC Processor."""

from typing import List
import pandas as pd

EL_MIN_COLUMNS = 21
DL_MIN_COLUMNS = 8

EL_EXPECTED_COLUMNS = [
    'Entity', 'Staff ID', 'Login ID', 'Employee Name', 'Identification No.',
    'Date of Birth', 'Gender', 'Marital Status', 'Overseas Assignment',
    'Employment Type', 'Foreigner Employment Pass', 'Nationality',
    'Date of Hire', 'Inactive Date', 'Last Day of Service', 'Category',
    'Designation', 'Email Address', 'Mobile Phone', 'Bank Code', 'Bank Account No.'
]

DL_EXPECTED_COLUMNS = [
    'Staff ID', 'Dependent ID', 'First Name', 'Last Name', 'Dependent ID Number',
    'Relationship', 'Gender', 'Date of Birth', 'Last Day of Service'
]


def validate_el_file(df: pd.DataFrame, file_label: str) -> List[str]:
    """Validate Employee Listing file structure."""
    errors = []

    if df is None:
        errors.append(f"{file_label}: DataFrame is None")
        return errors

    if df.empty:
        errors.append(f"{file_label}: File is empty")
        return errors

    if len(df.columns) < EL_MIN_COLUMNS:
        errors.append(
            f"{file_label}: Expected at least {EL_MIN_COLUMNS} columns, "
            f"found {len(df.columns)}"
        )

    critical_indices = [1, 3]
    for idx in critical_indices:
        if idx < len(df.columns):
            non_null_count = df.iloc[:, idx].notna().sum()
            if non_null_count == 0:
                errors.append(
                    f"{file_label}: Column {idx + 1} ({EL_EXPECTED_COLUMNS[idx]}) "
                    f"is entirely empty"
                )

    return errors


def validate_dl_file(df: pd.DataFrame, file_label: str) -> List[str]:
    """Validate Dependant Listing file structure."""
    errors = []

    if df is None:
        errors.append(f"{file_label}: DataFrame is None")
        return errors

    if df.empty:
        errors.append(f"{file_label}: File is empty")
        return errors

    if len(df.columns) < DL_MIN_COLUMNS:
        errors.append(
            f"{file_label}: Expected at least {DL_MIN_COLUMNS} columns, "
            f"found {len(df.columns)}"
        )

    critical_indices = [0, 1]
    for idx in critical_indices:
        if idx < len(df.columns):
            non_null_count = df.iloc[:, idx].notna().sum()
            if non_null_count == 0:
                errors.append(
                    f"{file_label}: Column {idx + 1} ({DL_EXPECTED_COLUMNS[idx]}) "
                    f"is entirely empty"
                )

    return errors


def validate_category_mapping(df: pd.DataFrame, file_label: str) -> List[str]:
    """Validate Category Mapping sheet structure."""
    errors = []

    if df is None or df.empty:
        errors.append(f"{file_label}: Category Mapping sheet is empty or missing")
        return errors

    if len(df.columns) < 2:
        errors.append(
            f"{file_label}: Category Mapping needs at least 2 columns "
            f"(Mediacorp Category, AIA Category)"
        )

    return errors


def allowed_file(filename: str) -> bool:
    """Check if file has allowed extension (.xlsx or .csv)."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ('xlsx', 'csv')
