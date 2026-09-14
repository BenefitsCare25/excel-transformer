"""Validate LGI source data before creating any output workbooks."""

from datetime import datetime
import re

import numpy as np
import pandas as pd

from flex_services.errors import FlexInputError
from .constants import (
    BRUNEI_ENTITY, CLAIM_COLUMNS, CLAIM_RULES, CLAIM_TYPE_ALIASES, ENTITY,
    LISTING_COLUMNS, UTILIZATION_COLUMNS,
)


def text(value):
    return "" if pd.isna(value) else re.sub(r"\s+", " ", str(value)).strip()


def claim_rule(value):
    """Find a claim rule despite harmless case, spacing or documented label variants."""
    label = text(value)
    aliases = {text(key).casefold(): target for key, target in CLAIM_TYPE_ALIASES.items()}
    rules = {text(key).casefold(): rule for key, rule in CLAIM_RULES.items()}
    canonical = aliases.get(label.casefold(), label)
    return rules.get(text(canonical).casefold())


def read_source(path, columns, label):
    try:
        frame = pd.read_excel(path, dtype=object, usecols=lambda col: str(col).strip() in columns)
    except (ValueError, OSError) as exc:
        raise FlexInputError(f"{label}: unable to read the Excel workbook: {exc}") from exc
    frame.columns = [str(col).strip() for col in frame.columns]
    missing = [col for col in columns if col not in frame.columns]
    if missing:
        raise FlexInputError(f"{label}: missing required column(s): {', '.join(missing)}")
    if frame.empty:
        raise FlexInputError(f"{label}: contains no data rows")
    return frame.copy()


def require_keys(frame, columns, label, unique=None):
    for col in columns:
        frame[col] = frame[col].map(text)
        if frame[col].eq("").any():
            raise FlexInputError(f"{label}: blank {col}")
    if unique:
        require_unique(frame, unique, label)


def require_unique(frame, column, label):
    duplicate = frame.loc[frame[column].duplicated(keep=False), column].unique()
    if len(duplicate):
        raise FlexInputError(f"{label}: duplicate {column}: {', '.join(duplicate[:10])}")


def dates(frame, column, label, required=False):
    supplied = frame[column].map(text).ne("")
    parsed = pd.to_datetime(frame[column], errors="coerce")
    if (supplied & parsed.isna()).any() or (required and parsed.isna().any()):
        raise FlexInputError(f"{label}: invalid or missing {column}")
    frame[column] = parsed


def amounts(frame, columns, label, blank_zero=False, nonnegative=False):
    for col in columns:
        values = frame[col]
        if blank_zero:
            values = values.where(values.map(text).ne(""), 0)
        parsed = pd.to_numeric(values, errors="coerce")
        if not np.isfinite(parsed).all():
            raise FlexInputError(f"{label}: invalid or missing {col}")
        if nonnegative and parsed.lt(-0.005).any():
            raise FlexInputError(f"{label}: negative {col}")
        frame[col] = parsed.round(2)


def load_listing(path):
    label = "LGI employee listing"
    frame = read_source(path, LISTING_COLUMNS, label)
    require_keys(frame, ["Employee ID No.", "Employee Name", "Entity"], label, "Employee ID No.")
    if not frame["Entity"].isin([ENTITY, BRUNEI_ENTITY]).all():
        raise FlexInputError(f"{label}: contains an unrelated company")
    dates(frame, "Last Day of Service", label)
    dates(frame, "Date of Hire", label, required=True)
    for col in ["Designation", "Cost Centre", "Department"]:
        frame[col] = frame[col].map(text)
    return frame


def match_listing(frame, listing, label):
    metadata = listing.rename(columns={
        "Employee ID No.": "Staff ID", "Employee Name": "ListingName",
        "Entity": "ListingEntity", "Date of Hire": "HireDate",
        "Last Day of Service": "LastDay",
    })
    matched = frame.merge(metadata, on="Staff ID", how="left", sort=False, validate="many_to_one")
    missing = matched.loc[matched["ListingName"].isna(), "Staff ID"].unique()
    if len(missing):
        raise FlexInputError(f"{label}: employee(s) missing from listing: {', '.join(missing[:10])}")
    mismatch = matched["Employee Name"].map(text).str.casefold().ne(matched["ListingName"].str.casefold())
    mismatch |= matched["Entity"].map(text).ne(matched["ListingEntity"])
    if mismatch.any():
        ids = matched.loc[mismatch, "Staff ID"].unique()
        raise FlexInputError(f"{label}: employee name or entity mismatch for: {', '.join(ids[:10])}")
    return matched


def load_claims(path, listing, pay_month):
    label = "LGI employee claims"
    frame = read_source(path, CLAIM_COLUMNS, label)
    require_keys(frame, ["Staff ID", "Employee Name", "Reference No.", "Claimant Name", "Relation"],
                 label, "Reference No.")
    if not frame["Entity"].map(text).eq(ENTITY).all():
        raise FlexInputError(f"{label}: claims must belong to {ENTITY}")
    if not frame["Status"].map(text).str.casefold().eq("approved").all():
        raise FlexInputError(f"{label}: upload Approved claims only")
    if not frame["Converted Currency"].map(text).str.upper().eq("SGD").all():
        raise FlexInputError(f"{label}: converted claim amounts must be in SGD")
    for col in ["Incurred Date", "Paid Date"]:
        dates(frame, col, label, required=True)
    period = pd.Period(datetime.fromisoformat(pay_month), freq="M")
    if not frame["Paid Date"].dt.to_period("M").eq(period).all():
        raise FlexInputError(f"{label}: claims have Paid Date outside {period}")
    amounts(frame, ["Converted Incurred Amt", "Payment Amt"], label, nonnegative=True)
    if frame["Payment Amt"].gt(frame["Converted Incurred Amt"] + 0.005).any():
        raise FlexInputError(f"{label}: Payment Amt exceeds Converted Incurred Amt")
    frame["Claim Type"] = frame["Claim Type"].map(text)
    frame["ClaimRule"] = frame["Claim Type"].map(claim_rule)
    unknown = frame.loc[frame["ClaimRule"].isna(), "Claim Type"].unique()
    if len(unknown):
        raise FlexInputError(f"{label}: unsupported Claim Type: {'; '.join(unknown[:5])}")
    for index, flag in enumerate(["TAX", "CPF"]):
        expected = frame["ClaimRule"].map(lambda rule: rule[index])
        mismatch = frame[flag].map(text).str.casefold().ne(expected.str.casefold())
        if mismatch.any():
            refs = frame.loc[mismatch, "Reference No."].tolist()
            raise FlexInputError(f"{label}: {flag} conflicts with LGI classification for: {', '.join(refs[:10])}")
        frame[flag] = expected
    frame["Taxable"] = frame["Payment Amt"].where(frame["TAX"].eq("Yes"), 0)
    frame["Non Taxable"] = frame["Payment Amt"].where(frame["TAX"].eq("No"), 0)
    return match_listing(frame, listing, label)


def leaver_validations(claims):
    rows = []
    for staff_id, group in claims[claims["LastDay"].notna()].groupby("Staff ID", sort=True):
        first = group.iloc[0]
        rows.append({
            "Sev": "WARNING", "Check": "LEAVER CLAIMS INCLUDED", "EEID": staff_id,
            "Name": first["Employee Name"], "disposition": "warn", "action": "Take note",
            "Detail": f"Last day {first['LastDay']:%d/%m/%Y}; {len(group)} claim(s) remain included.",
            "amount": round(float(group["Payment Amt"].sum()), 2),
            "guidance": "Review the employee's last day of service before using the reports.",
        })
    return rows


def policy_period(pay_month):
    month = pd.Timestamp(datetime.fromisoformat(pay_month))
    year = month.year if month.month >= 10 else month.year - 1
    return pd.Timestamp(year, 10, 1), pd.Timestamp(year + 1, 9, 30)


def load_utilization(path, listing, claims, pay_month):
    label = "LGI utilisation summary"
    frame = read_source(path, UTILIZATION_COLUMNS, label)
    require_keys(frame, ["Staff ID", "Employee Name", "Entity"], label)
    if not frame["Entity"].isin([ENTITY, BRUNEI_ENTITY]).all():
        raise FlexInputError(f"{label}: contains an unrelated company")
    for col in ["Date of Hire", "Benefit Start Date", "Last Day of Service", "Benefit End Date"]:
        dates(frame, col, label, required=col in ["Date of Hire", "Benefit Start Date"])
    start, _ = policy_period(pay_month)
    month_end = pd.Timestamp(datetime.fromisoformat(pay_month)) + pd.offsets.MonthEnd(0)
    # Keep current-policy leavers, including zero allocations. Old-policy records and
    # employees whose benefit has not started by the reporting month are out of scope.
    eligible = frame["Benefit Start Date"].between(start, month_end)
    eligible &= frame["Date of Hire"].le(month_end)
    excluded = int((~eligible).sum())
    frame = frame.loc[eligible].copy()
    if frame.empty:
        raise FlexInputError(f"{label}: no eligible records for the policy year containing {pay_month[:7]}")
    require_unique(frame, "Staff ID", label)
    if not frame["Wallet"].map(text).str.upper().eq("FSA").all():
        raise FlexInputError(f"{label}: expected one FSA wallet per employee")
    frame = match_listing(frame, listing, label)
    frame["LastDayMismatch"] = frame["Last Day of Service"].ne(frame["LastDay"]) & (
        frame["Last Day of Service"].notna() | frame["LastDay"].notna())
    hire_mismatch = frame["Date of Hire"].ne(frame["HireDate"])
    if hire_mismatch.any():
        ids = frame.loc[hire_mismatch, "Staff ID"].tolist()
        raise FlexInputError(f"{label}: hire dates differ from listing for: {', '.join(ids[:10])}")
    amounts(frame, ["Total Allocation Amt"], label)
    amounts(frame, [
        "Buy Leave Amt", "Sell Leave Amt", "Selection Amt", "Deals Amt",
        "Claims Payment Amt", "Total Utilized Amt (L-M+N+O+P)",
        "Pending Claims Payment Amt", "Balance Available Allocation Amt",
    ], label, blank_zero=True)
    frame["FlexUsed"] = (frame["Buy Leave Amt"] - frame["Sell Leave Amt"]
                         + frame["Selection Amt"] + frame["Deals Amt"]).round(2)
    frame["TransferredFSA"] = (frame["Total Allocation Amt"] - frame["FlexUsed"]).round(2)
    expected_used = frame["FlexUsed"] + frame["Claims Payment Amt"]
    expected_balance = frame["Total Allocation Amt"] - expected_used
    for column, expected in [
        ("Total Utilized Amt (L-M+N+O+P)", expected_used),
        ("Balance Available Allocation Amt", expected_balance),
    ]:
        mismatch = (frame[column] - expected).abs().gt(0.011)
        if mismatch.any():
            ids = frame.loc[mismatch, "Staff ID"].tolist()
            raise FlexInputError(f"{label}: {column} does not reconcile for: {', '.join(ids[:10])}")
    missing = sorted(set(claims["Staff ID"]) - set(frame["Staff ID"]))
    if missing:
        raise FlexInputError(f"{label}: claim employee(s) missing from current policy: {', '.join(missing[:10])}")
    monthly = claims.groupby("Staff ID", sort=False)["Payment Amt"].sum().round(2)
    frame["MonthlyClaims"] = frame["Staff ID"].map(monthly).fillna(0).round(2)
    insufficient = frame["Claims Payment Amt"].add(0.011).lt(frame["MonthlyClaims"])
    if insufficient.any():
        ids = frame.loc[insufficient, "Staff ID"].tolist()
        raise FlexInputError(f"{label}: cumulative claims paid is less than this month's claims for: {', '.join(ids[:10])}")
    if abs(frame["MonthlyClaims"].sum() - claims["Payment Amt"].sum()) > 0.011:
        raise FlexInputError(f"{label}: monthly claims total does not reconcile")
    return frame, excluded


def balance_validations(utilization):
    return [{
        "Sev": "WARNING", "Check": "NEGATIVE FLEX BALANCE", "EEID": row["Staff ID"],
        "Name": row["Employee Name"], "disposition": "warn", "action": "Review balance",
        "Detail": f"Source balance is SGD {row['Balance Available Allocation Amt']:,.2f}.",
        "guidance": "The source balance remains in the report. No salary deduction has been inferred.",
    } for _, row in utilization[utilization["Balance Available Allocation Amt"].lt(-0.005)].iterrows()]


def employment_validations(utilization):
    def date_label(value):
        return "blank" if pd.isna(value) else f"{value:%d/%m/%Y}"

    return [{
        "Sev": "WARNING", "Check": "LAST DAY DIFFERS BETWEEN INPUTS", "EEID": row["Staff ID"],
        "Name": row["Employee Name"], "disposition": "warn", "action": "Review employment date",
        "Detail": (f"Listing: {date_label(row['LastDay'])}; "
                   f"utilisation export: {date_label(row['Last Day of Service'])}."),
        "guidance": "Termination Date uses the employee listing. The employee's source balances remain included.",
    } for _, row in utilization[utilization["LastDayMismatch"]].iterrows()]
