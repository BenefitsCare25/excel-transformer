"""Read and validate Ceva exports without guessing missing values."""

import re
from zipfile import BadZipFile

import numpy as np
import pandas as pd
from openpyxl.utils.exceptions import InvalidFileException

from flex_services.errors import FlexInputError
from .constants import CLAIM_COLUMNS, LISTING_COLUMNS, UTILIZATION_COLUMNS, ENTITY_ALIASES


def lookup_key(value):
    return re.sub(r"[^\w]", "", str(value)).casefold()


ENTITIES = {lookup_key(alias): canonical for canonical, aliases in ENTITY_ALIASES.items()
            for alias in aliases}


def input_error(key, summary, guidance, employee_ids=None, validation=None):
    label = {"claims": "claims", "listing": "employee listing", "utilization": "utilisation"}[key]
    return FlexInputError(
        summary, title=f"Check the Ceva {label} export",
        summary=summary, guidance=guidance, files=[key], employee_ids=employee_ids,
        validation=validation,
    )


def _read_frame(path, key, columns):
    try:
        with pd.ExcelFile(path, engine="openpyxl") as workbook:
            raw_headers = workbook.parse(sheet_name=0, header=None, nrows=1, dtype=object)
            if not raw_headers.empty:
                headers = raw_headers.iloc[0].dropna().map(lambda value: str(value).strip())
                headers = headers.loc[headers.ne("")]
                duplicates = headers.loc[headers.duplicated(keep=False)].unique()
                if len(duplicates):
                    raise input_error(key, f"Repeated column headings: {', '.join(duplicates)}.",
                                      "Keep one correct column per heading and upload the corrected export.")
            return workbook.parse(sheet_name=0, dtype=object,
                                  usecols=lambda column: str(column).strip() in columns)
    except FlexInputError:
        raise
    except (ValueError, OSError, BadZipFile, InvalidFileException) as exc:
        raise input_error(key, "We could not read this Excel workbook.",
                          "Open it in Excel, remove any password, save as .xlsx and upload again.") from exc


def _parse_date(value):
    if isinstance(value, str):
        value = value.strip()
        if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", value):
            return pd.to_datetime(value.replace("-", "/"), format="%d/%m/%Y", errors="coerce")
    return pd.to_datetime(value, errors="coerce")


def _read(path, key, columns, keys, date_columns, money_columns, blank_zero=(), allow_negative=()):
    frame = _read_frame(path, key, columns)
    frame.columns = [str(column).strip() for column in frame.columns]
    missing = [column for column in columns if column not in frame.columns]
    if missing or frame.empty:
        detail = (f"Missing columns: {', '.join(missing)}." if missing else
                  "The export has no records.")
        raise input_error(key, detail, "Upload the complete Ceva export with its original headings.")
    frame = frame.loc[:, list(columns)].copy()
    frame["ExcelRow"] = np.arange(2, len(frame) + 2)
    for column in keys:
        values = frame[column].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
        if column in ("Staff ID", "User ID"):
            values = values.str.replace(r"^(\d+)\.0+$", r"\1", regex=True)
        if values.eq("").any():
            raise input_error(key, f"Some records have an empty {column}.",
                              f"Fill in {column} for every record and upload the corrected export.")
        frame[column] = values
    frame["EntityKey"] = frame["Entity"].map(lookup_key).map(ENTITIES)
    if frame["EntityKey"].isna().any():
        raise input_error(key, "This export includes an unrecognised company.",
                          "Upload Ceva entities and Pyramid Lines Singapore only. Check Entity spellings.")
    for column, required in date_columns.items():
        supplied = frame[column].fillna("").astype(str).str.strip().ne("")
        parsed = pd.to_datetime(frame[column].map(_parse_date), errors="coerce")
        if (supplied & parsed.isna()).any() or (required and parsed.isna().any()):
            raise input_error(key, f"Some {column} values are missing or are not valid dates.",
                              f"Use Excel dates in {column} and upload the corrected export.")
        frame[column] = parsed
    for column in money_columns:
        values = frame[column]
        if column in blank_zero:
            values = values.where(values.fillna("").astype(str).str.strip().ne(""), 0)
        parsed = pd.to_numeric(values, errors="coerce")
        if not np.isfinite(parsed).all() or (column not in allow_negative and parsed.round(2).lt(0).any()):
            raise input_error(key, f"Some {column} values are missing, negative or not valid numbers.",
                              f"Enter numeric amounts of zero or more in {column} and upload again.")
        frame[column] = parsed.round(2)
    return frame


def read_claims(path):
    return _read(path, "claims", CLAIM_COLUMNS,
                 ("Entity", "Staff ID", "Employee Name", "Reference No.", "Claim Type"),
                 {"Incurred Date": True, "Paid Date": True},
                 ("Converted Incurred Amt", "Payment Amt"))


def read_utilization(path):
    return _read(path, "utilization", UTILIZATION_COLUMNS,
                 ("Entity", "Staff ID", "Employee Name", "Wallet"),
                 {"Date of Hire": True, "Last Day of Service": False,
                  "Benefit Start Date": True, "Benefit End Date": False},
                 ("Total Allocation Amt", "Claims Payment Amt", "Total Utilized Amt (L-M+N+O+P)",
                  "Pending Claims Payment Amt", "Balance Available Allocation Amt"),
                 blank_zero=("Claims Payment Amt", "Pending Claims Payment Amt"),
                 allow_negative=("Total Allocation Amt", "Balance Available Allocation Amt"))


def read_listing(path):
    frame = _read(path, "listing", LISTING_COLUMNS, ("Entity", "User ID", "Employee Name"),
                  {"Date of Hire": True, "Last Day of Service": False}, ())
    return frame.rename(columns={"User ID": "Staff ID"})
