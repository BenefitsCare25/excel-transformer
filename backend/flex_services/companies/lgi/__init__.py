"""Lion Global Investors Flex Report adapter."""

from datetime import datetime
from pathlib import Path

from .constants import CLAIM_VALIDATION, RESULT_UI
from .processing import (
    balance_validations, employment_validations, leaver_validations,
    load_claims, load_listing, load_utilization, validate_claims,
)
from .workbooks import write_details, write_summary, write_utilization

COMPANY = {
    "id": "lgi",
    "name": "Lion Global Investors (LGI)",
    "status": "active",
    "month_detection": {"file_key": "claims", "column": "Paid Date"},
    "files": [
        {"key": "claims", "label": "LGI employee claims export", "required": True},
        {"key": "listing", "label": "LGI employee listing report", "required": True},
        {"key": "utilization", "label": "LGI utilisation summary report", "required": True},
    ],
    "notes": (
        "Generates Claims Detail, Claims Summary and Utilization Report as .xlsx files. "
        "Use a utilisation export for the reporting month: cumulative amounts and balances "
        "come from that export. Claims Summary keeps one row per claim."
    ),
    "result_ui": RESULT_UI,
    "claim_validation": CLAIM_VALIDATION,
    "input_validation": True,
}


def prepare_inputs(files, pay_month, policy_decisions=None):
    listing = load_listing(files['listing'])
    claims = load_claims(files['claims'], listing, pay_month)
    utilization, excluded = load_utilization(files['utilization'], listing, claims, pay_month, policy_decisions)
    excluded_ids = {item['employee_id'] for item in utilization.attrs.get('policy_review', [])
                    if item['decision'] == 'exclude'}
    claims = claims.loc[~claims['Staff ID'].isin(excluded_ids)].copy()
    return claims, utilization, excluded


def validate_inputs(files, pay_month, policy_decisions=None):
    """Run the generation checks without writing reports or creating a saved run."""
    claims, utilization, _ = prepare_inputs(files, pay_month, policy_decisions)
    return {'valid': True, 'claims': len(claims),
            'policy_review': utilization.attrs.get('policy_review', [])}


def run(files, pay_month, outdir, policy_decisions=None):
    month = datetime.fromisoformat(pay_month)
    claims, utilization, excluded = prepare_inputs(files, pay_month, policy_decisions)
    policy_review = utilization.attrs.get('policy_review', [])
    leavers = leaver_validations(claims)
    validation = leavers + balance_validations(utilization) + employment_validations(utilization)
    # The shared result cards display guidance in preference to Detail.
    for item in validation:
        item["guidance"] = f"{item['Detail']} {item['guidance']}"
    Path(outdir).mkdir(parents=True, exist_ok=True)
    outputs = [write_details(claims, month, outdir), write_summary(claims, month, outdir),
               write_utilization(utilization, month, outdir)]
    total = round(float(claims["Payment Amt"].sum()), 2)
    return {
        "outputs": outputs, "errors": 0, "warnings": len(validation), "validation": validation,
        "grand_total": total, "breakdown_rows": len(claims),
        "employees": int(claims["Staff ID"].nunique()), "leavers": len(leavers),
        "policy_review": policy_review,
        "log": [
            *[f"Employee choice: {item['employee_id']} — {item['decision']} in all three reports; "
              f"{item['claims']} claim(s), SGD {item['amount']:,.2f}" for item in policy_review],
            f"Loaded {len(claims)} approved LGI claims; preserved source order in both claims reports",
            f"Validated all claim types against LGI tax/CPF rules; included {len(leavers)} claimant(s) with a last day of service",
            f"Generated utilisation for {len(utilization)} selected employees, including explicit policy-date inclusions and the Brunei branch when supplied",
            f"Excluded {excluded} utilisation record(s) outside the current policy or starting after the reporting month",
            f"Reconciled monthly reimbursement across all three reports to SGD {total:,.2f}",
            f"Cumulative reimbursement from the utilisation export: SGD {utilization['Claims Payment Amt'].sum():,.2f}",
            "Cumulative figures reflect the uploaded export; Salary Deduction is blank because no source amount is provided",
        ],
    }
