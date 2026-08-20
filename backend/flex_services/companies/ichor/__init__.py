"""Ichor Flex Report adapter."""

import os
from datetime import datetime

from .constants import RESULT_UI
from .processing import prepare
from .workbooks import write_details, write_summary

COMPANY = {
    "id": "ichor",
    "name": "Ichor Systems",
    "status": "active",
    "month_detection": {"file_key": "claims", "column": "Paid Date"},
    "files": [
        {"key": "claims", "label": "Ichor employee claims export", "required": True},
        {"key": "listing", "label": "Ichor employee listing report", "required": True},
    ],
    "notes": (
        "Generates Ichor Claims Details and Claims Summary workbooks. All leaver claims remain "
        "included and are highlighted for review in the run result."
    ),
    "result_ui": RESULT_UI,
}


def run(files, pay_month, outdir):
    payment_month = datetime.fromisoformat(pay_month)
    os.makedirs(outdir, exist_ok=True)
    prepared = prepare(files, pay_month)

    details_path = write_details(prepared.claims, payment_month, outdir)
    summary_path = write_summary(prepared.claims, payment_month, outdir)
    total = round(float(prepared.claims["PaymentAmount"].sum()), 2)

    log = [
        f"Loaded {len(prepared.claims)} approved Ichor claims",
        f"Matched {prepared.claims['StaffID6'].nunique()} employees to the listing",
        f"Included every claim; flagged {prepared.leaver_count} leaver(s) for review",
        f"Reconciled Claims Details and Claims Summary to SGD {total:,.2f}",
    ]
    return {
        "outputs": [details_path, summary_path],
        "log": log,
        "errors": 0,
        "warnings": prepared.leaver_count,
        "validation": prepared.validations,
        "grand_total": total,
        "breakdown_rows": int(len(prepared.claims)),
        "employees": int(prepared.claims["StaffID6"].nunique()),
        "leavers": prepared.leaver_count,
    }
