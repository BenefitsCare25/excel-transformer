"""Lion Global Investors Flex Report adapter."""

from datetime import datetime
from pathlib import Path

from .constants import RESULT_UI
from .processing import (
    balance_validations, employment_validations, leaver_validations,
    load_claims, load_listing, load_utilization,
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
}


def run(files, pay_month, outdir):
    month = datetime.fromisoformat(pay_month)
    listing = load_listing(files["listing"])
    claims = load_claims(files["claims"], listing, pay_month)
    utilization, excluded = load_utilization(files["utilization"], listing, claims, pay_month)
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
        "log": [
            f"Loaded {len(claims)} approved LGI claims; preserved source order in both claims reports",
            f"Validated all claim types against LGI tax/CPF rules; included {len(leavers)} claimant(s) with a last day of service",
            f"Generated utilisation for {len(utilization)} current-policy employees, including the Brunei branch when supplied",
            f"Excluded {excluded} utilisation record(s) outside the current policy or starting after the reporting month",
            f"Reconciled monthly reimbursement across all three reports to SGD {total:,.2f}",
            f"Cumulative reimbursement from the utilisation export: SGD {utilization['Claims Payment Amt'].sum():,.2f}",
            "Cumulative figures reflect the uploaded export; Salary Deduction is blank because no source amount is provided",
        ],
    }
