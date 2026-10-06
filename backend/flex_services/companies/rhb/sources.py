"""Read RHB exports while retaining identifiers, empty entitlements and source flags."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from zipfile import BadZipFile

import pandas as pd
from openpyxl.utils.exceptions import InvalidFileException

from flex_services.errors import FlexInputError
from .constants import CLAIM_COLUMNS, ENTITIES, LISTING_COLUMNS, UTILIZATION_COLUMNS


def lookup_key(value):
    return re.sub(r"\s+", "", str(value)).casefold()


def input_error(key, message, guidance, employee_ids=None, validation=None):
    return FlexInputError(message, title="Check the RHB export", guidance=guidance,
                          files=[key], employee_ids=employee_ids, validation=validation)


def _read(path, key, columns, required_text):
    try:
        with pd.ExcelFile(path, engine="openpyxl") as workbook:
            header = workbook.parse(header=None, nrows=1, dtype=object)
            headings = header.iloc[0].dropna().astype(str).str.strip() if len(header) else pd.Series(dtype=str)
            if headings.duplicated().any():
                raise input_error(key, "The export has repeated column headings.",
                                  "Keep one column per heading and upload again.")
            frame = workbook.parse(dtype=object)
    except (OSError, ValueError, BadZipFile, InvalidFileException) as exc:
        if isinstance(exc, FlexInputError):
            raise
        raise input_error(key, "We could not read this Excel workbook.",
                          "Open it in Excel, remove any password, save as .xlsx and upload again.") from exc
    frame.columns = [str(column).strip() for column in frame.columns]
    missing = set(columns) - set(frame.columns)
    if missing or frame.empty:
        message = f"Missing columns: {', '.join(sorted(missing))}." if missing else "The export has no records."
        raise input_error(key, message, "Upload the complete RHB export with its original headings.")
    frame = frame.loc[:, list(columns)].dropna(how="all").copy()
    if frame.empty:
        raise input_error(key, "The export has no records.", "Upload a populated RHB export.")
    frame["ExcelRow"] = frame.index + 2
    for column in required_text:
        frame[column] = frame[column].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
        if frame[column].eq("").any():
            raise input_error(key, f"Some records have an empty {column}.",
                              f"Fill in {column} for every record and upload again.")
    id_column = "User ID" if key == "listing" else "Staff ID"
    identifiers = frame[id_column].str.replace(r"^(\d+)\.0+$", r"\1", regex=True)
    if not identifiers.str.fullmatch(r"[0-9]{1,32}").all():
        raise input_error(key, f"Some {id_column} values are not numeric employee IDs.",
                          "Use RHB's employee ID, preserving any leading zeros.")
    frame[id_column] = identifiers
    entities = {lookup_key(entity): entity for entity in ENTITIES}
    frame["Entity"] = frame["Entity"].map(lookup_key).map(entities)
    if frame["Entity"].isna().any():
        raise input_error(key, "The export contains an unrecognised RHB entity.",
                          "Use RHB Bank Berhad or RHB Asset Management Pte Ltd.")
    return frame


def _date(value):
    if pd.isna(value) or str(value).strip() == "":
        return pd.NaT
    if isinstance(value, (date, datetime)):
        return pd.Timestamp(value)
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", text):
            return pd.to_datetime(text.replace("-", "/"), format="%d/%m/%Y", errors="coerce")
        return pd.to_datetime(text, errors="coerce")
    return pd.NaT


def _dates(frame, key, columns):
    for column, required in columns.items():
        supplied = frame[column].fillna("").astype(str).str.strip().ne("")
        parsed = pd.to_datetime(frame[column].map(_date), errors="coerce")
        if (supplied & parsed.isna()).any() or (required and parsed.isna().any()):
            raise input_error(key, f"Some {column} values are missing or invalid.",
                              f"Use Excel dates or DD/MM/YYYY in {column} and upload again.")
        frame[column] = parsed


def _amount(value, blank=None):
    if pd.isna(value) or str(value).strip() == "":
        return blank
    try:
        amount = Decimal(str(value))
        if amount.is_finite() and abs(amount) < Decimal("1000000000000"):
            return float(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError):
        pass
    raise ValueError("Invalid amount")


def _money(frame, key, columns, blank_zero=(), nullable=(), negative=()):
    for column in columns:
        try:
            values = frame[column].map(lambda value: _amount(value, 0 if column in blank_zero else None))
        except ValueError as exc:
            raise input_error(key, f"Some {column} values are invalid.",
                              "Use finite numeric amounts in the export.") from exc
        invalid = values.isna() if column not in nullable else pd.Series(False, index=frame.index)
        if column not in negative:
            invalid |= values.fillna(0).lt(0)
        if invalid.any():
            raise input_error(key, f"Some {column} values are missing or negative.",
                              f"Check the amounts in {column} and upload the corrected export.")
        frame[column] = values


def read_claims(path):
    frame = _read(path, "claims", CLAIM_COLUMNS,
                  ("Entity", "Staff ID", "Employee Name", "Claimant Name", "Reference No.", "Claim Type"))
    _dates(frame, "claims", {"Incurred Date": True, "Paid Date": True})
    _money(frame, "claims", ("Incurred Amt", "Converted Incurred Amt", "Payment Amt"))
    frame["PaymentCents"] = frame["Payment Amt"].map(lambda amount: int(round(amount * 100)))
    return frame


def read_listing(path):
    frame = _read(path, "listing", LISTING_COLUMNS, ("Entity", "User ID", "Employee Name"))
    _dates(frame, "listing", {"Date of Hire": True, "Last Day of Service": False})
    return frame.rename(columns={"User ID": "Staff ID"})


def read_utilization(path):
    frame = _read(path, "utilization", UTILIZATION_COLUMNS,
                  ("Entity", "Staff ID", "Employee Name", "Category"))
    excluded = frame["Category"].str.contains(r"\bwo\s+flex\b", case=False, regex=True)
    count = int(excluded.sum())
    frame = frame.loc[~excluded].copy()
    _dates(frame, "utilization", {"Date of Hire": True, "Last Day of Service": False,
                                   "Benefit Start Date": True, "Benefit End Date": False})
    _money(frame, "utilization", ("Total Allocation Amt", "Claims Payment Amt",
                                   "Total Utilized Amt (L-M+N+O+P)", "Pending Claims Payment Amt",
                                   "Balance Available Allocation Amt"),
           blank_zero=("Claims Payment Amt", "Pending Claims Payment Amt"),
           nullable=("Total Allocation Amt",),
           negative=("Total Allocation Amt", "Balance Available Allocation Amt"))
    return frame, count
