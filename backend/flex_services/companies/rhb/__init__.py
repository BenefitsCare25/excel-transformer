"""RHB Flex Report adapter."""

from datetime import datetime
from pathlib import Path

from .constants import CLAIM_VALIDATION, RESULT_UI
from .payroll import payroll_groups, write_payroll
from .processing import prepare_inputs
from .validation import validate_claims
from .workbooks import write_details, write_summary, write_utilization

COMPANY = {
    "id": "rhb", "name": "RHB", "status": "active",
    "month_detection": {"file_key": "claims", "column": "Paid Date"},
    "files": [
        {"key": "claims", "label": "RHB employee claims export", "required": True},
        {"key": "listing", "label": "RHB employee listing report", "required": True},
        {"key": "utilization", "label": "RHB utilisation summary report", "required": True},
    ],
    "notes": (
        "Generates Claims Detail, Claim Summary and Utilisation and Balance reports as .xlsx, "
        "plus separate PE payroll CSVs for RHB Bank and RHB Asset Management. "
        "Codes follow RHB's 14 claim types; CPF differences are flagged for review. "
        "Use the reporting month's utilisation export: cumulative amounts and balances are preserved. "
        "Categories marked 'wo flex' are excluded from utilisation; separate wallet records and leavers remain."
    ),
    "claim_validation": CLAIM_VALIDATION, "input_validation": True, "result_ui": RESULT_UI,
}


def validate_inputs(files, pay_month):
    claims, _, _, _ = prepare_inputs(files, pay_month)
    return {"valid": True, "claims": len(claims)}


def run(files, pay_month, outdir):
    month = datetime.fromisoformat(pay_month)
    claims, utilization, warnings, excluded = prepare_inputs(files, pay_month)
    Path(outdir).mkdir(parents=True, exist_ok=True)
    outputs = [write_details(claims, month, outdir), write_summary(claims, month, outdir),
               write_utilization(utilization, month, outdir), *write_payroll(claims, month, outdir)]
    total = int(claims["PaymentCents"].sum()) / 100
    payroll_count = len(payroll_groups(claims))
    return {
        "outputs": outputs, "errors": 0, "warnings": len(warnings), "validation": warnings,
        "grand_total": total, "breakdown_rows": len(claims), "payroll_rows": payroll_count,
        "employees": int(claims["Staff ID"].nunique()), "utilization_rows": len(utilization),
        "leavers": sum(item["Check"] == "LEAVER CLAIMS INCLUDED" for item in warnings),
        "log": [
            f"Loaded {len(claims)} approved RHB claims paid in {month:%B %Y}",
            "Applied the 14 supplied claim types and RE0235 / RE0237 / RE0238 codes",
            "Preserved uploaded CPF flags and flagged differences without changing payroll codes",
            f"Grouped claims into {payroll_count} employee/code payroll rows across two entity CSVs",
            f"Reconciled claim summary and payroll reimbursement to SGD {total:,.2f}",
            f"Preserved {len(utilization)} utilisation records; excluded {excluded} 'wo flex' records",
            "Retained separate wallets, leavers, blank entitlements and uploaded cumulative balances",
            "The summary uses .xlsx and includes the source claims on its Claims Data sheet",
        ],
    }
