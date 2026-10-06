"""Reconcile the three RHB uploads before producing any payroll files."""

from datetime import datetime

import pandas as pd

from .sources import input_error, lookup_key, read_claims, read_listing, read_utilization
from .validation import classify_claims


def _unique(frame, columns, key):
    repeated = frame.loc[frame.duplicated(columns, keep=False)]
    if not repeated.empty:
        raise input_error(key, f"Repeated records found for {', '.join(columns)}.",
                          "Keep one correct record per key and upload again.",
                          employee_ids=repeated["Staff ID"].unique())


def _check_claims(claims, pay_month):
    _unique(claims, ["Reference No."], "claims")
    for column, expected in (("Status", "approved"), ("Converted Currency", "sgd")):
        if not claims[column].fillna("").astype(str).str.strip().str.casefold().eq(expected).all():
            raise input_error("claims", f"All claims must have {column} = {expected.upper()}.",
                              "Export approved RHB claims with amounts converted to SGD.")
    month = pd.Period(datetime.fromisoformat(pay_month), freq="M")
    if not claims["Paid Date"].dt.to_period("M").eq(month).all():
        raise input_error("claims", f"Some claims were paid outside {month}.",
                          "Upload claims for one payment month, using Paid Date.")
    if claims["Payment Amt"].gt(claims["Converted Incurred Amt"]).any():
        raise input_error("claims", "Some reimbursements exceed the incurred amount in SGD.",
                          "Check Payment Amt against Converted Incurred Amt.")
    if claims["Incurred Date"].gt(claims["Paid Date"]).any():
        raise input_error("claims", "Some claims were paid before their incurred date.",
                          "Correct Incurred Date or Paid Date in the claims export.")
    issues, warnings = classify_claims(claims)
    if issues:
        raise input_error("claims", "Some claim types or tax/CPF values need correcting.",
                          "Review the claim checklist and upload the corrected export.", validation=issues)
    return warnings


def _match_listing(frame, listing, key):
    columns = {column: f"Listing{column}" for column in listing if column != "Staff ID"}
    matched = frame.merge(listing.rename(columns=columns), on="Staff ID", how="left",
                          sort=False, validate="many_to_one")
    mismatch = (matched["ListingEntity"].isna() | matched["Entity"].ne(matched["ListingEntity"])
                | matched["Employee Name"].map(lookup_key).ne(matched["ListingEmployee Name"].map(lookup_key)))
    if mismatch.any():
        error = input_error(key, "Some employees are missing or have different details in the listing.",
                            "Compare Staff ID with User ID, plus Employee Name and Entity across the exports.",
                            employee_ids=matched.loc[mismatch, "Staff ID"].unique())
        error.feedback["files"] = [key, "listing"]
        raise error
    return matched


def _warning(staff_id, name, check, detail, amount=None):
    return {"Sev": "WARNING", "Check": check, "EEID": staff_id, "Name": name,
            "disposition": "warn", "action": "Review", "guidance": detail, "amount": amount}


def _report_warnings(claims, utilization, cpf_warnings):
    warnings = [_warning(item["employee_id"], item["employee_name"], "CPF FLAG DIFFERS",
                         f"Row {item['row']} / {item['reference']}: {item['message']}")
                for item in cpf_warnings]
    for (_, staff_id), employee in claims.groupby(["Entity", "Staff ID"], sort=False):
        row = employee.iloc[0]
        if pd.notna(row["ListingLast Day of Service"]):
            warnings.append(_warning(staff_id, row["Employee Name"], "LEAVER CLAIMS INCLUDED",
                                     f"Last day of service: {row['ListingLast Day of Service']:%d/%m/%Y}. "
                                     "Approved reimbursements remain included; confirm final-pay handling.",
                                     int(employee["PaymentCents"].sum()) / 100))
    monthly = claims.groupby("Staff ID")["PaymentCents"].sum() / 100
    cumulative = utilization.groupby("Staff ID")["Claims Payment Amt"].sum()
    for staff_id, amount in monthly.items():
        if amount > cumulative.get(staff_id, 0) + 0.01:
            name = claims.loc[claims["Staff ID"].eq(staff_id), "Employee Name"].iloc[0]
            warnings.append(_warning(staff_id, name, "UTILISATION EXPORT MAY BE OLDER",
                                     "Monthly reimbursement exceeds cumulative Claims Payment Amt. "
                                     "The uploaded utilisation figures are preserved; check the export date."))
    for _, row in utilization.iterrows():
        allocation, balance = row["Total Allocation Amt"], row["Balance Available Allocation Amt"]
        if balance < 0 or (pd.notna(allocation) and allocation < 0):
            warnings.append(_warning(row["Staff ID"], row["Employee Name"], "NEGATIVE ENTITLEMENT OR BALANCE",
                                     "Uploaded negative amounts are preserved. Review proration or recovery."))
        if pd.notna(allocation) and abs(allocation - row["Total Utilized Amt (L-M+N+O+P)"] - balance) > 0.011:
            warnings.append(_warning(row["Staff ID"], row["Employee Name"], "BALANCE CHECK",
                                     "Entitlement less total utilised differs from the uploaded balance. "
                                     "Check the source figures; uploaded amounts are preserved."))
        source_end, listing_end = row["Last Day of Service"], row["ListingLast Day of Service"]
        if (pd.isna(source_end) != pd.isna(listing_end)
                or (pd.notna(source_end) and pd.notna(listing_end) and source_end != listing_end)):
            warnings.append(_warning(row["Staff ID"], row["Employee Name"], "TERMINATION DATE DIFFERS",
                                     "The listing and utilisation export have different last days of service. "
                                     "The utilisation report retains its uploaded termination date."))
    return warnings


def prepare_inputs(files, pay_month):
    claims = read_claims(files["claims"])
    listing = read_listing(files["listing"])
    utilization, excluded = read_utilization(files["utilization"])
    _unique(listing, ["Staff ID"], "listing")
    cpf_warnings = _check_claims(claims, pay_month)
    _unique(utilization, ["Staff ID", "Wallet", "Benefit Start Date"], "utilization")
    if utilization["Benefit End Date"].lt(utilization["Benefit Start Date"]).any():
        raise input_error("utilization", "Some benefit end dates precede their start dates.",
                          "Correct the benefit dates in the utilisation export.")
    claims = _match_listing(claims, listing, "claims")
    utilization = _match_listing(utilization, listing, "utilization")
    missing = set(claims["Staff ID"]) - set(utilization["Staff ID"])
    if missing:
        raise input_error("utilization", "Some claimants have no flex utilisation record.",
                          "Upload the full utilisation export and check each claimant's category.",
                          employee_ids=sorted(missing))
    warnings = _report_warnings(claims, utilization, cpf_warnings)
    return claims, utilization, warnings, excluded
