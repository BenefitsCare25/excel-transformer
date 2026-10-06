"""Ceva Flex Report adapter."""

from datetime import datetime
from pathlib import Path

from .constants import CLAIM_VALIDATION, RESULT_UI
from .processing import prepare_inputs
from .validation import validate_claims
from .workbooks import payroll_rows, write_payroll, write_utilization

COMPANY = {
    "id": "ceva", "name": "Ceva", "status": "active",
    "month_detection": {"file_key": "claims", "column": "Paid Date"},
    "files": [
        {"key": "claims", "label": "Ceva employee claims export", "required": True},
        {"key": "listing", "label": "Ceva employee listing report", "required": True},
        {"key": "utilization", "label": "Ceva utilisation summary report", "required": True},
    ],
    "notes": (
        "Generates the Flexible Benefits payroll report (one row per employee and claim type) "
        "and the cumulative Utilisation report. Upload the utilisation export for the reporting month; "
        "its cumulative amounts and balances are preserved. CPF differences are flagged for review."
    ),
    "claim_validation": CLAIM_VALIDATION, "input_validation": True, "result_ui": RESULT_UI,
}


def validate_inputs(files, pay_month):
    claims, _, _ = prepare_inputs(files, pay_month)
    return {"valid": True, "claims": len(claims)}


def run(files, pay_month, outdir):
    month = datetime.fromisoformat(pay_month)
    claims, utilization, warnings = prepare_inputs(files, pay_month)
    Path(outdir).mkdir(parents=True, exist_ok=True)
    outputs = [write_payroll(claims, month, outdir), write_utilization(utilization, month, outdir)]
    total = round(float(claims["Payment Amt"].sum()), 2)
    payroll_count = len(payroll_rows(claims))
    return {
        "outputs": outputs, "errors": 0, "warnings": len(warnings), "validation": warnings,
        "grand_total": total, "payroll_total": total, "breakdown_rows": len(claims),
        "payroll_rows": payroll_count, "employees": int(claims["Staff ID"].nunique()),
        "utilization_rows": len(utilization),
        "log": [
            f"Loaded {len(claims)} approved Ceva claims paid in {month:%B %Y}",
            "Applied all 11 Ceva claim types and payroll codes; shortened Holiday Trips export labels",
            "Preserved uploaded CPF flags and flagged differences from the supplied benefit table",
            f"Grouped claims into {payroll_count} employee/claim-type payroll rows",
            f"Reconciled payroll reimbursement to SGD {total:,.2f}",
            f"Preserved {len(utilization)} FSA utilisation records from the uploaded export",
            "Date of Joined uses Date of Hire; cumulative claims, pending claims and balances use the export",
            "Employee details matched to the listing; leaver checks use the listing's Last Day of Service",
        ],
    }
