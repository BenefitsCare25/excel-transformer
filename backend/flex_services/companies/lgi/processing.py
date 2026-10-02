"""Validate LGI source data before creating any output workbooks."""

from datetime import datetime
import re

import numpy as np
import pandas as pd

from flex_services.errors import FlexInputError
from .constants import (
    BRUNEI_ENTITY, CLAIM_COLUMNS, CLAIM_ELIGIBILITY, CLAIM_RULES, CLAIM_TYPE_ALIASES, ENTITY,
    LISTING_COLUMNS, UTILIZATION_COLUMNS,
)


def input_error(label, detail, summary, guidance, *, employee_ids=None, files=None):
    """Keep diagnostic details separate from the operator's explanation."""
    file_key = {'LGI employee listing': 'listing', 'LGI employee claims': 'claims',
                'LGI utilisation summary': 'utilization'}[label]
    return FlexInputError(
        f'{label}: {detail}', title=f'Check the {label.removeprefix("LGI ")}',
        summary=summary, guidance=guidance, files=files or [file_key],
        employee_ids=employee_ids,
    )


def text(value):
    return "" if pd.isna(value) else re.sub(r"\s+", " ", str(value)).strip()


def claim_type_key(value):
    """Normalize export typography for lookup without changing report labels."""
    label = text(value).replace("\u2019", "'")
    return re.sub(r"\s*/\s*", "/", label).casefold()


def canonical_claim_type(value):
    label = claim_type_key(value)
    aliases = {claim_type_key(key): target for key, target in CLAIM_TYPE_ALIASES.items()}
    labels = {claim_type_key(key): key for key in CLAIM_RULES}
    return labels.get(claim_type_key(aliases.get(label, label)))


def claim_rule(value):
    """Find a claim rule despite harmless typography or documented label variants."""
    return CLAIM_RULES.get(canonical_claim_type(value))


def classification_issues(frame):
    """Collect every checklist mismatch so operators can correct one upload once."""
    issues = []
    for excel_row, (_, row) in enumerate(frame.iterrows(), start=2):
        label = text(row['Claim Type'])
        canonical = canonical_claim_type(label)

        def add(field, expected, message):
            issues.append({
                'row': excel_row, 'reference': text(row['Reference No.']),
                'claim_type': label, 'field': field, 'actual': text(row[field]),
                'expected': expected, 'message': message,
            })

        if canonical is None:
            message = 'This claim type is not in the LGI benefit list. Check the benefit claimed and select the matching Claim Type in the claims export.'
            add('Claim Type', 'A specific LGI benefit item', message)
            continue

        for flag, expected in zip(['TAX', 'CPF'], CLAIM_RULES[canonical]):
            if text(row[flag]).casefold() != expected.casefold():
                meaning = 'taxable' if flag == 'TAX' else 'subject to CPF'
                description = meaning if expected == 'Yes' else f'not {meaning}'
                add(flag, expected, f'This benefit is {description} under the LGI rules. Set {flag} to {expected} in the claims export.')
        allowed = CLAIM_ELIGIBILITY[canonical]
        if allowed is not None and text(row['Relation']).casefold() not in [relation.casefold() for relation in allowed]:
            add('Relation', ', '.join(allowed),
                'The listed relationship is not covered for this benefit under the LGI rules. '
                'Check who the claim is for and whether the benefit category is correct before updating the claims export.')
    return issues


def validate_claims(path):
    """Preflight used by the upload UI; generation repeats the same checklist checks."""
    frame = read_source(path, CLAIM_COLUMNS, 'LGI employee claims')
    issues = classification_issues(frame)
    return {'valid': not issues, 'claims': len(frame), 'validation': issues}


def read_source(path, columns, label):
    try:
        frame = pd.read_excel(path, dtype=object, usecols=lambda col: str(col).strip() in columns)
    except (ValueError, OSError) as exc:
        raise input_error(label, f'unable to read the Excel workbook: {exc}',
                          'We could not read this Excel file.',
                          'Open it in Excel, remove any password, save it as .xlsx and upload it again.') from exc
    frame.columns = [str(col).strip() for col in frame.columns]
    missing = [col for col in columns if col not in frame.columns]
    if missing:
        raise input_error(label, f"missing required column(s): {', '.join(missing)}",
                          f"This file is missing these columns: {', '.join(missing)}.",
                          'Check that you selected the correct export. Keep the original column headings and upload the complete file.')
    if frame.empty:
        raise input_error(label, 'contains no data rows', 'This file has column headings but no records.',
                          'Export the records for the reporting month and upload the file again.')
    return frame.copy()


def require_keys(frame, columns, label, unique=None):
    for col in columns:
        frame[col] = frame[col].map(text)
        if frame[col].eq("").any():
            raise input_error(label, f'blank {col}', f'Some records have an empty {col} cell.',
                              f'Fill in the missing {col} values, then upload the corrected file.')
    if unique:
        require_unique(frame, unique, label)


def require_unique(frame, column, label):
    duplicate = frame.loc[frame[column].duplicated(keep=False), column].unique()
    if len(duplicate):
        raise input_error(label, f"duplicate {column}: {', '.join(duplicate[:10])}",
                          f"The same {column} appears more than once: {', '.join(duplicate)}.",
                          'Review the repeated records and keep one correct record for each value, then upload the file again.')


def dates(frame, column, label, required=False):
    supplied = frame[column].map(text).ne("")
    parsed = pd.to_datetime(frame[column], errors="coerce")
    if (supplied & parsed.isna()).any() or (required and parsed.isna().any()):
        raise input_error(label, f'invalid or missing {column}', f'Some {column} cells are missing or are not valid dates.',
                          f'Check the {column} column and use Excel dates, then upload the corrected file.')
    frame[column] = parsed


def amounts(frame, columns, label, blank_zero=False, nonnegative=False):
    for col in columns:
        values = frame[col]
        if blank_zero:
            values = values.where(values.map(text).ne(""), 0)
        parsed = pd.to_numeric(values, errors="coerce")
        if not np.isfinite(parsed).all():
            raise input_error(label, f'invalid or missing {col}', f'Some {col} cells are missing or are not valid numbers.',
                              f'Check the {col} column and enter numeric amounts, then upload the corrected file.')
        if nonnegative and parsed.lt(-0.005).any():
            raise input_error(label, f'negative {col}', f'Some {col} amounts are below zero.',
                              'Check these amounts against the source records. This report requires amounts of zero or more.')
        frame[col] = parsed.round(2)


def load_listing(path):
    label = "LGI employee listing"
    frame = read_source(path, LISTING_COLUMNS, label)
    require_keys(frame, ["Employee ID No.", "Employee Name", "Entity"], label, "Employee ID No.")
    if not frame["Entity"].isin([ENTITY, BRUNEI_ENTITY]).all():
        raise input_error(label, 'contains an unrelated company', 'This file includes employees from a company other than LGI or its Brunei branch.',
                          'Upload the LGI employee listing, including its Brunei branch only where applicable.')
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
        raise input_error(label, f"employee(s) missing from listing: {', '.join(missing[:10])}",
                          'These employee IDs could not be found in the uploaded employee listing.',
                          'Compare Staff ID in this file with Employee ID No. in the employee listing. Check for missing employees or different IDs, then upload the corrected file.',
                          employee_ids=missing, files=['claims' if label == 'LGI employee claims' else 'utilization', 'listing'])
    mismatch = matched["Employee Name"].map(text).str.casefold().ne(matched["ListingName"].str.casefold())
    mismatch |= matched["Entity"].map(text).ne(matched["ListingEntity"])
    if mismatch.any():
        ids = matched.loc[mismatch, "Staff ID"].unique()
        raise input_error(label, f"employee name or entity mismatch for: {', '.join(ids[:10])}",
                          'These employee IDs were found, but their names or companies do not match the employee listing.',
                          'Compare Employee Name and Entity in both files for these IDs. Confirm the correct details and upload the corrected file.',
                          employee_ids=ids, files=['claims' if label == 'LGI employee claims' else 'utilization', 'listing'])
    return matched


def load_claims(path, listing, pay_month):
    label = "LGI employee claims"
    frame = read_source(path, CLAIM_COLUMNS, label)
    require_keys(frame, ["Staff ID", "Employee Name", "Reference No.", "Claimant Name", "Relation"],
                 label, "Reference No.")
    if not frame["Entity"].map(text).eq(ENTITY).all():
        raise input_error(label, f'claims must belong to {ENTITY}', 'Some claims are listed under a company other than LGI Singapore.',
                          f'Check the Entity column and upload only claims for {ENTITY}.')
    if not frame["Status"].map(text).str.casefold().eq("approved").all():
        raise input_error(label, 'upload Approved claims only', 'Some claims do not have Approved status.',
                          'Export only approved claims and upload that file. Confirm approval in the source system before changing a claim status.')
    if not frame["Converted Currency"].map(text).str.upper().eq("SGD").all():
        raise input_error(label, 'converted claim amounts must be in SGD', 'Some claim amounts are not marked as Singapore dollars (SGD).',
                          'Export the amounts converted to SGD and check Converted Currency before uploading again.')
    for col in ["Incurred Date", "Paid Date"]:
        dates(frame, col, label, required=True)
    period = pd.Period(datetime.fromisoformat(pay_month), freq="M")
    if not frame["Paid Date"].dt.to_period("M").eq(period).all():
        raise input_error(label, f'claims have Paid Date outside {period}', f'Some claims were paid outside the reporting month, {period}.',
                          'Check Paid Date and upload claims paid within one reporting month.')
    amounts(frame, ["Converted Incurred Amt", "Payment Amt"], label, nonnegative=True)
    if frame["Payment Amt"].gt(frame["Converted Incurred Amt"] + 0.005).any():
        raise input_error(label, 'Payment Amt exceeds Converted Incurred Amt', 'Some reimbursements are higher than the original claim amount in SGD.',
                          'Compare Payment Amt with Converted Incurred Amt and correct the source amounts before uploading again.')
    frame["Claim Type"] = frame["Claim Type"].map(text)
    issues = classification_issues(frame)
    if issues:
        raise FlexInputError(
            f"{label}: {len(issues)} checklist issue(s). {issues[0]['message']}",
            validation=issues,
            title='Some claims need correcting',
            summary='Some tax, CPF or claimant details do not match the LGI benefit rules.',
            guidance='Review the claim rows below and upload the corrected claims export.', files=['claims'],
        )
    frame["ClaimRule"] = frame["Claim Type"].map(claim_rule)
    for index, flag in enumerate(["TAX", "CPF"]):
        frame[flag] = frame["ClaimRule"].map(lambda rule: rule[index])
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


def missing_policy_error(source, missing, start, month_end):
    """Explain whether a claimant is absent or present but excluded by dates."""
    records = []
    for staff_id in missing:
        rows = source.loc[source['Staff ID'].eq(staff_id)]
        if rows.empty:
            records.append({'employee_id': staff_id, 'benefit_start': 'No record',
                            'hire_date': 'No record', 'reason': 'Employee ID not found in the utilisation summary.'})
        for _, row in rows.iterrows():
            reasons = []
            if row['Benefit Start Date'] < start:
                reasons.append(f'Benefit start date is before the {start:%d %b %Y} policy cutoff.')
            if row['Benefit Start Date'] > month_end:
                reasons.append('Benefits start after the reporting month.')
            if row['Date of Hire'] > month_end:
                reasons.append('Hire date is after the reporting month.')
            records.append({'employee_id': staff_id, 'benefit_start': row['Benefit Start Date'].strftime('%d %b %Y'),
                            'hire_date': row['Date of Hire'].strftime('%d %b %Y'), 'reason': ' '.join(reasons)})
    all_present = set(missing).issubset(set(source['Staff ID']))
    error = input_error(
        'LGI utilisation summary', f"claim employee(s) missing from current policy: {', '.join(missing[:10])}",
        ('These employees are in both the employee listing and utilisation summary, but their utilisation records were excluded by the policy date check.'
         if all_present else 'These employees are in the employee listing, but the utilisation summary has no matching record that passes the policy date check.'),
        f'The app currently accepts Benefit Start Dates from {start:%d %b %Y} to {month_end:%d %b %Y}, with a Date of Hire on or before {month_end:%d %b %Y}. Check the dates below. If the source dates are correct, confirm the policy rule with your administrator before changing any employee dates.',
        employee_ids=missing,
    )
    error.feedback['title'] = 'Employee policy dates need review' if all_present else 'Check employee records in the utilisation summary'
    error.feedback['records'] = records
    return error


def load_utilization(path, listing, claims, pay_month, policy_decisions=None):
    label = "LGI utilisation summary"
    frame = read_source(path, UTILIZATION_COLUMNS, label)
    require_keys(frame, ["Staff ID", "Employee Name", "Entity"], label)
    if not frame["Entity"].isin([ENTITY, BRUNEI_ENTITY]).all():
        raise input_error(label, 'contains an unrelated company', 'This utilisation summary includes a company other than LGI or its Brunei branch.',
                          'Upload the LGI utilisation summary for the reporting month.')
    for col in ["Date of Hire", "Benefit Start Date", "Last Day of Service", "Benefit End Date"]:
        dates(frame, col, label, required=col in ["Date of Hire", "Benefit Start Date"])
    start, _ = policy_period(pay_month)
    month_end = pd.Timestamp(datetime.fromisoformat(pay_month)) + pd.offsets.MonthEnd(0)
    # Keep current-policy leavers, including zero allocations. Old-policy records and
    # employees whose benefit has not started by the reporting month are out of scope.
    eligible = frame["Benefit Start Date"].between(start, month_end)
    eligible &= frame["Date of Hire"].le(month_end)
    decisions = {} if policy_decisions is None else policy_decisions
    if not isinstance(decisions, dict) or any(
        not isinstance(key, str) or value not in ('include', 'exclude')
        for key, value in decisions.items()
    ):
        raise FlexInputError('Choose Include or Exclude for each employee.',
                             title='Review your employee choices')
    # Only offer an override for a claimant with one unambiguous earlier record.
    # A current-policy record takes precedence over any historical records.
    missing_ids = sorted(set(claims['Staff ID']) - set(frame.loc[eligible, 'Staff ID']))
    review = []
    for staff_id in missing_ids:
        rows = frame.loc[frame['Staff ID'].eq(staff_id)]
        if len(rows) != 1:
            continue
        row = rows.iloc[0]
        if row['Benefit Start Date'] >= start or row['Date of Hire'] > month_end:
            continue
        employee_claims = claims.loc[claims['Staff ID'].eq(staff_id)]
        review.append({
            'employee_id': staff_id, 'name': text(row['Employee Name']),
            'benefit_start': row['Benefit Start Date'].strftime('%d %b %Y'),
            'policy_start': start.strftime('%d %b %Y'),
            'claims': len(employee_claims),
            'amount': round(float(employee_claims['Payment Amt'].sum()), 2),
            'decision': decisions.get(staff_id),
        })
    review_ids = {item['employee_id'] for item in review}
    if set(decisions) - review_ids:
        raise FlexInputError('Some employee choices no longer match the uploaded files.',
                             title='Review your employee choices',
                             guidance='Upload the files again and choose Include or Exclude for the employees shown.')
    included_ids = {key for key, value in decisions.items() if value == 'include'}
    excluded_ids = {key for key, value in decisions.items() if value == 'exclude'}
    eligible |= frame['Staff ID'].isin(included_ids)
    claims = claims.loc[~claims['Staff ID'].isin(excluded_ids)].copy()
    excluded = int((~eligible).sum())
    source = frame
    frame = frame.loc[eligible].copy()
    missing = sorted(set(claims['Staff ID']) - set(frame['Staff ID']))
    if missing:
        error = missing_policy_error(source, missing, start, month_end)
        error.feedback['policy_review'] = review
        if set(missing).issubset(review_ids):
            error.feedback['policy_choice_required'] = True
            error.feedback['title'] = 'Choose which employees to include'
            error.feedback['message'] = 'These employees have benefit start dates before the selected policy period. Choose whether to include or exclude each employee from all three reports.'
            error.feedback['guidance'] = 'Review the employee choices below. Totals will update to match your selections.'
        raise error
    if frame.empty and not excluded_ids:
        raise input_error(label, f'no eligible records for the policy year containing {pay_month[:7]}',
                          f'No employee records in this utilisation summary qualify for {pay_month[:7]}.',
                          f'Check that Benefit Start Date is between {start:%d %b %Y} and {month_end:%d %b %Y}, and Date of Hire is on or before {month_end:%d %b %Y}. Upload the export for the correct policy period.')
    require_unique(frame, "Staff ID", label)
    if not frame["Wallet"].map(text).str.upper().eq("FSA").all():
        raise input_error(label, 'expected one FSA wallet per employee', 'Some records use a benefit wallet other than FSA.',
                          'Export the FSA wallet records, with one record per employee for the current policy period.')
    frame = match_listing(frame, listing, label)
    frame["LastDayMismatch"] = frame["Last Day of Service"].ne(frame["LastDay"]) & (
        frame["Last Day of Service"].notna() | frame["LastDay"].notna())
    hire_mismatch = frame["Date of Hire"].ne(frame["HireDate"])
    if hire_mismatch.any():
        ids = frame.loc[hire_mismatch, "Staff ID"].tolist()
        raise input_error(label, f"hire dates differ from listing for: {', '.join(ids[:10])}",
                          'The hire dates for these employees differ between the utilisation summary and employee listing.',
                          'Confirm the correct Date of Hire in the source records, then upload the corrected file.',
                          employee_ids=ids, files=['utilization', 'listing'])
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
            raise input_error(label, f"{column} does not reconcile for: {', '.join(ids[:10])}",
                              f'The {column} figures do not add up for these employees.',
                              'Check the allocation, leave purchases and sales, selections, deals and claims paid in the utilisation export. Total used must equal those net costs; available balance must equal allocation minus total used.',
                              employee_ids=ids)
    monthly = claims.groupby("Staff ID", sort=False)["Payment Amt"].sum().round(2)
    frame["MonthlyClaims"] = frame["Staff ID"].map(monthly).fillna(0).round(2)
    insufficient = frame["Claims Payment Amt"].add(0.011).lt(frame["MonthlyClaims"])
    if insufficient.any():
        ids = frame.loc[insufficient, "Staff ID"].tolist()
        raise input_error(label, f"cumulative claims paid is less than this month's claims for: {', '.join(ids[:10])}",
                          "The total claims paid to date in the utilisation summary is lower than this month's claims for these employees.",
                          'Check that the utilisation export includes payments for the reporting month. Compare Claims Payment Amt with the claims export and upload the updated file.',
                          employee_ids=ids, files=['utilization', 'claims'])
    if abs(frame["MonthlyClaims"].sum() - claims["Payment Amt"].sum()) > 0.011:
        raise input_error(label, 'monthly claims total does not reconcile', 'The monthly claim totals do not match between the uploaded files.',
                          'Check that the claims export and utilisation summary cover the same employees and reporting month, then upload the corrected files.',
                          files=['utilization', 'claims'])
    frame.attrs['policy_review'] = review
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
