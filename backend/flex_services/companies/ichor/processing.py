"""Load and validate Ichor sources, then prepare report-ready claim data."""

import re
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from flex_services.errors import FlexInputError

from .constants import (
    CLAIMS_REQUIRED_COLUMNS,
    ICHOR_ENTITY,
    LISTING_REQUIRED_COLUMNS,
    SUMMARY_COLUMNS,
    TYPE_ALIASES,
)


@dataclass(frozen=True)
class PreparedIchorData:
    claims: pd.DataFrame
    validations: list
    leaver_count: int


def _require_columns(frame, required, label):
    missing = [column for column in required if column not in frame.columns]
    if missing:
        found = ", ".join(str(column) for column in frame.columns[:20])
        raise FlexInputError(
            f"{label}: missing required column(s): {', '.join(missing)}. Found: {found}",
            title=f'Check the {label}', summary=f"This file is missing these columns: {', '.join(missing)}.",
            guidance='Upload the complete export with its original column headings.'
        )


def _normalize_id(value):
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if re.fullmatch(r"\d+(?:\.0+)?", text):
        text = str(int(float(text)))
    return text.zfill(6)


def _normalize_space(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _parse_claim_type(value):
    normalized = _normalize_space(value)
    parts = re.split(r"\s*::\s*", normalized, maxsplit=1)
    if len(parts) != 2:
        return None, None
    claim_type = TYPE_ALIASES.get(parts[0], parts[0])
    relation = parts[1]
    if (claim_type, relation) not in SUMMARY_COLUMNS:
        return None, None
    return claim_type, relation


def _load_claims(path, pay_month):
    claims = pd.read_excel(path)
    claims.columns = [str(column).strip() for column in claims.columns]
    _require_columns(claims, CLAIMS_REQUIRED_COLUMNS, "Ichor employee claims export")
    if claims.empty:
        raise FlexInputError("Ichor employee claims export contains no claim rows",
                             guidance='Export the approved claims for the reporting month and upload the file again.')

    claims = claims.copy()
    claims["StaffID6"] = claims["Staff ID"].map(_normalize_id)
    claims["EmployeeName"] = claims["Employee Name"].map(_normalize_space)
    claims["ReferenceNo"] = claims["Reference No."].map(_normalize_space)
    claims["IncurredDate"] = pd.to_datetime(claims["Incurred Date"], errors="coerce")
    claims["PaidDate"] = pd.to_datetime(claims["Paid Date"], errors="coerce")
    claims["IncurredAmount"] = pd.to_numeric(
        claims["Converted Incurred Amt"], errors="coerce"
    ).round(2)
    claims["PaymentAmount"] = pd.to_numeric(claims["Payment Amt"], errors="coerce").round(2)

    _validate_claims(claims, pay_month)
    parsed = claims["Claim Type"].map(_parse_claim_type)
    claims["SummaryType"] = parsed.map(lambda item: item[0])
    claims["SummaryRelation"] = parsed.map(lambda item: item[1])
    unknown = claims[claims["SummaryType"].isna()]["ReferenceNo"].tolist()
    if unknown:
        raise FlexInputError(
            "Ichor employee claims export contains unsupported Claim Type values for reference(s): "
            + ", ".join(unknown[:10]),
            summary=f"The claim types for these claim references are not recognised: {', '.join(unknown)}.",
            guidance='Check Claim Type in the Ichor export. It must identify both the benefit and the claimant relationship, separated by ::.'
        )
    return claims


def _validate_claims(claims, pay_month):
    blank_keys = claims[
        (claims["StaffID6"] == "")
        | (claims["EmployeeName"] == "")
        | (claims["ReferenceNo"] == "")
    ]
    if not blank_keys.empty:
        raise FlexInputError("Ichor employee claims export has blank Staff ID, employee or reference values",
                             summary='Some claims are missing an employee ID, employee name or claim reference.',
                             guidance='Fill in Staff ID, Employee Name and Reference No. for each claim, then upload the corrected claims export.')
    duplicates = claims[claims["ReferenceNo"].duplicated(keep=False)]["ReferenceNo"].unique()
    if len(duplicates):
        raise FlexInputError("Duplicate Ichor claim reference(s): " + ", ".join(duplicates[:10]),
                             summary=f"These claim references appear more than once: {', '.join(duplicates)}.",
                             guidance='Review the repeated claims and keep one correct row per Reference No., then upload the file again.')
    if claims[["IncurredDate", "PaidDate", "IncurredAmount", "PaymentAmount"]].isna().any().any():
        raise FlexInputError("Ichor employee claims export has invalid dates or claim amounts",
                             guidance='Check Incurred Date and Paid Date for valid Excel dates, and Converted Incurred Amt and Payment Amt for numeric amounts. Fill in any missing values.')
    if (claims[["IncurredAmount", "PaymentAmount"]] < 0).any().any():
        raise FlexInputError("Ichor employee claims export contains negative claim amounts",
                             summary='Some claim amounts are below zero.',
                             guidance='Check Converted Incurred Amt and Payment Amt against the source records. This report requires amounts of zero or more.')

    invalid_status = claims[claims["Status"].map(_normalize_space).str.casefold() != "approved"]
    if not invalid_status.empty:
        raise FlexInputError("Ichor employee claims export must contain Approved claims only",
                             summary='Some claims do not have Approved status.',
                             guidance='Export only approved claims. Confirm approval in the source system before changing a claim status.')
    invalid_entity = claims[claims["Entity"].map(_normalize_space) != ICHOR_ENTITY]
    if not invalid_entity.empty:
        raise FlexInputError(f"Ichor employee claims export contains an entity other than {ICHOR_ENTITY}",
                             summary='Some claims are listed under a company other than Ichor.',
                             guidance=f'Check the Entity column and upload only claims for {ICHOR_ENTITY}.')
    invalid_currency = claims[
        claims["Converted Currency"].map(_normalize_space).str.upper() != "SGD"
    ]
    if not invalid_currency.empty:
        raise FlexInputError("Ichor converted claim amounts must be in SGD",
                             summary='Some claim amounts are not marked as Singapore dollars (SGD).',
                             guidance='Export the amounts converted to SGD and check Converted Currency before uploading again.')

    selected_period = pd.Period(datetime.fromisoformat(pay_month), freq="M")
    off_period = claims[claims["PaidDate"].dt.to_period("M") != selected_period]
    if not off_period.empty:
        refs = ", ".join(off_period["ReferenceNo"].tolist()[:10])
        raise FlexInputError(f"Ichor claims paid outside {selected_period}: {refs}",
                             summary=f'Some claims were paid outside {selected_period}. Claim references: {refs}.',
                             guidance='Check Paid Date and select the matching payment month, or upload the claims for the selected month.')


def _load_listing(path):
    listing = pd.read_excel(path)
    listing.columns = [str(column).strip() for column in listing.columns]
    _require_columns(listing, LISTING_REQUIRED_COLUMNS, "Ichor employee listing report")
    listing = listing.copy()
    listing["StaffID6"] = listing["User ID"].map(_normalize_id)
    listing["ListingName"] = listing["Employee Name"].map(_normalize_space)
    listing["LastDay"] = pd.to_datetime(listing["Last Day of Service"], errors="coerce")
    supplied_last_day = listing["Last Day of Service"].notna() & (
        listing["Last Day of Service"].astype(str).str.strip() != ""
    )
    if (supplied_last_day & listing["LastDay"].isna()).any():
        raise FlexInputError("Ichor employee listing contains an invalid Last Day of Service",
                             guidance='Check Last Day of Service in the employee listing. Use Excel dates, or leave the cell empty for employees with no last day of service.')
    listing = listing[listing["StaffID6"] != ""]
    duplicates = listing[listing["StaffID6"].duplicated(keep=False)]["StaffID6"].unique()
    if len(duplicates):
        raise FlexInputError("Duplicate employee ID(s) in Ichor listing: " + ", ".join(duplicates[:10]),
                             summary='These employee IDs appear more than once in the employee listing.', employee_ids=duplicates,
                             guidance='Review the repeated User ID records and keep one correct record per employee, then upload the listing again.')
    return listing[["StaffID6", "ListingName", "LastDay"]]


def _match_listing(claims, listing):
    matched = claims.merge(listing, on="StaffID6", how="left", validate="many_to_one")
    missing = matched[matched["ListingName"].isna()]["StaffID6"].unique()
    if len(missing):
        raise FlexInputError("Claim employee(s) missing from Ichor listing: " + ", ".join(missing[:10]),
                             summary='These employees have claims, but their IDs could not be found in the employee listing.', employee_ids=missing,
                             guidance='Compare Staff ID in the claims export with User ID in the employee listing. Check for missing employees or different IDs and upload the corrected file.')
    name_mismatch = matched[
        matched["EmployeeName"].str.casefold() != matched["ListingName"].str.casefold()
    ]
    if not name_mismatch.empty:
        row = name_mismatch.iloc[0]
        raise FlexInputError(
            f"Employee name mismatch for {row['StaffID6']}: claims '{row['EmployeeName']}', "
            f"listing '{row['ListingName']}'",
            summary=f"Employee {row['StaffID6']} has different names in the two files: {row['EmployeeName']} in claims and {row['ListingName']} in the listing.",
            guidance='Confirm the correct employee name and ID, then upload the corrected file.'
        )
    return matched


def _leaver_validations(claims):
    validations = []
    leavers = claims[claims["LastDay"].notna()]
    for (staff_id, name, last_day), rows in leavers.groupby(
        ["StaffID6", "EmployeeName", "LastDay"], sort=True
    ):
        references = ", ".join(rows["ReferenceNo"].tolist())
        amount = round(float(rows["PaymentAmount"].sum()), 2)
        detail = (
            f"Last day {last_day:%d/%m/%Y}; {len(rows)} claim(s) included: {references}. "
            f"Total SGD {amount:,.2f}."
        )
        validations.append(
            {
                "Sev": "WARNING",
                "Check": "LEAVER CLAIMS INCLUDED",
                "EEID": staff_id,
                "Name": name,
                "Detail": detail,
                "amount": amount,
                "disposition": "warn",
                "action": "Take note",
                "guidance": (
                    "Claims remain included in both Ichor Claims Details and Claims Summary. "
                    "Confirm the employee's handling with Ichor HR."
                ),
            }
        )
    return validations


def prepare(files, pay_month):
    claims = _load_claims(files["claims"], pay_month)
    listing = _load_listing(files["listing"])
    claims = _match_listing(claims, listing)
    validations = _leaver_validations(claims)
    return PreparedIchorData(claims=claims, validations=validations, leaver_count=len(validations))
