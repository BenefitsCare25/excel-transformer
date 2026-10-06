"""Prepare Ceva's monthly payroll and cumulative utilisation records."""

from datetime import datetime

import pandas as pd

from .sources import input_error, read_claims, read_listing, read_utilization
from .validation import classify_claims


def _unique(frame, columns, key):
    duplicate = frame.loc[frame.duplicated(columns, keep=False)]
    if not duplicate.empty:
        raise input_error(key, f"Repeated records found for {', '.join(columns)}.",
                          "Keep one correct record per key and upload the corrected export.",
                          employee_ids=duplicate["Staff ID"].unique())


def _claim_checks(claims, pay_month):
    _unique(claims, ["Reference No."], "claims")
    for column, expected in (("Status", "approved"), ("Converted Currency", "sgd")):
        if not claims[column].fillna("").astype(str).str.strip().str.casefold().eq(expected).all():
            raise input_error("claims", f"All claims must have {column} = {expected.upper()}.",
                              "Export approved Ceva claims with amounts converted to SGD.")
    period = pd.Period(datetime.fromisoformat(pay_month), freq="M")
    if not claims["Paid Date"].dt.to_period("M").eq(period).all():
        raise input_error("claims", f"Some claims were paid outside {period}.",
                          "Select the month shown in Paid Date or upload the claims for the selected month.")
    if claims["Payment Amt"].gt(claims["Converted Incurred Amt"] + 0.005).any():
        raise input_error("claims", "Some reimbursements exceed the incurred amount in SGD.",
                          "Check Payment Amt against Converted Incurred Amt and correct the source amounts.")
    issues, warnings = classify_claims(claims)
    if issues:
        raise input_error("claims", "Some claim types or tax/CPF values need correcting.",
                          "Review the claim rows and upload the corrected export.", validation=issues)
    return warnings


def _utilization_checks(utilization):
    _unique(utilization, ["Staff ID", "Wallet"], "utilization")
    if not utilization["Wallet"].str.casefold().eq("fsa").all():
        raise input_error("utilization", "The utilisation export includes a wallet other than FSA.",
                          "Upload Ceva's FSA utilisation export.")
    invalid_dates = utilization["Benefit End Date"].lt(utilization["Benefit Start Date"])
    if invalid_dates.any():
        raise input_error("utilization", "Some benefit end dates precede their start dates.",
                          "Correct the date ranges in the utilisation export.",
                          employee_ids=utilization.loc[invalid_dates, "Staff ID"].unique())


def _match_listing(frame, listing, key):
    metadata = listing[["Staff ID", "Employee Name", "EntityKey", "Date of Hire", "Last Day of Service"]]
    metadata = metadata.rename(columns={column: f"Listing{column}" for column in metadata
                                        if column != "Staff ID"})
    matched = frame.merge(metadata, on="Staff ID", how="left",
                           sort=False, validate="many_to_one")
    mismatch = (matched["ListingEntityKey"].isna()
                | matched["EntityKey"].ne(matched["ListingEntityKey"])
                | matched["Employee Name"].str.casefold().ne(
                    matched["ListingEmployee Name"].str.casefold()))
    if mismatch.any():
        error = input_error(key, "Some employees are missing or have different details in the employee listing.",
                            "Compare Staff ID with User ID, plus Employee Name and Entity across the exports.",
                            employee_ids=matched.loc[mismatch, "Staff ID"].unique())
        error.feedback["files"] = [key, "listing"]
        raise error
    return matched


def _warning(staff_id, name, check, guidance, amount=None):
    return {"Sev": "WARNING", "Check": check, "EEID": staff_id, "Name": name,
            "disposition": "warn", "action": "Review", "guidance": guidance,
            "amount": amount}


def report_warnings(claims, utilization, cpf_warnings):
    warnings = [_warning(item["employee_id"], item["employee_name"], "CPF FLAG DIFFERS",
                         f"Row {item['row']} / {item['reference']} ({item['claim_type']}): {item['message']}")
                for item in cpf_warnings]
    for _, row in utilization.loc[utilization["ListingLast Day of Service"].notna()
                                 & utilization["Staff ID"].isin(claims["Staff ID"])].iterrows():
        amount = round(float(claims.loc[claims["Staff ID"].eq(row["Staff ID"]), "Payment Amt"].sum()), 2)
        warnings.append(_warning(row["Staff ID"], row["Employee Name"], "LEAVER CLAIMS INCLUDED",
                                 f"Last day of service: {row['ListingLast Day of Service']:%d/%m/%Y}. "
                                 "Approved reimbursements remain included; confirm final-pay handling.", amount))
    discrepancy = (utilization["Total Allocation Amt"]
                   - utilization["Total Utilized Amt (L-M+N+O+P)"]
                   - utilization["Balance Available Allocation Amt"])
    monthly = claims.groupby("Staff ID")["Payment Amt"].sum()
    for _, row in utilization.iterrows():
        if row["Balance Available Allocation Amt"] < -0.005 or row["Total Allocation Amt"] < -0.005:
            warnings.append(_warning(row["Staff ID"], row["Employee Name"], "NEGATIVE ENTITLEMENT OR BALANCE",
                                     f"Entitlement SGD {row['Total Allocation Amt']:,.2f}; "
                                     f"balance SGD {row['Balance Available Allocation Amt']:,.2f}. "
                                     "Uploaded amounts are preserved. Review proration and any recovery required."))
        if abs(discrepancy.loc[row.name]) > 0.01:
            warnings.append(_warning(row["Staff ID"], row["Employee Name"], "BALANCE CHECK",
                                     "Entitlement less total utilised does not equal the uploaded balance. "
                                     "The export's amounts are preserved; confirm the source figures."))
        if monthly.get(row["Staff ID"], 0) > row["Claims Payment Amt"] + 0.01:
            warnings.append(_warning(row["Staff ID"], row["Employee Name"], "UTILISATION EXPORT MAY BE OLDER",
                                     "Monthly reimbursement exceeds cumulative Claims Payment Amt. "
                                     "Upload the latest utilisation export to show updated cumulative figures."))
    return warnings


def prepare_inputs(files, pay_month):
    claims = read_claims(files["claims"])
    utilization = read_utilization(files["utilization"])
    listing = read_listing(files["listing"])
    _unique(listing, ["Staff ID"], "listing")
    cpf_warnings = _claim_checks(claims, pay_month)
    _utilization_checks(utilization)
    claims = _match_listing(claims, listing, "claims")
    utilization = _match_listing(utilization, listing, "utilization")
    missing = set(claims["Staff ID"]) - set(utilization["Staff ID"])
    if missing:
        raise input_error("utilization", "Some claimants have no FSA utilisation record.",
                          "Upload the complete utilisation export for the reporting month.", employee_ids=sorted(missing))
    claims["Entity"] = claims["EntityKey"]
    claims["Employee Name"] = claims["ListingEmployee Name"]
    return claims, utilization, report_warnings(claims, utilization, cpf_warnings)
