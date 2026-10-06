"""RHB's supplied claim classifications and report layouts."""

# Order follows the columns in the supplied Claim Summary report.
CLAIM_RULES = {
    "Alternative Treatment, e.g. TCM (registered under MOH), etc.": ("No", "No", "RE0235"),
    "Dental": ("No", "No", "RE0235"),
    "Outpatient Medical": ("No", "No", "RE0235"),
    "Medical Expenses beyond or not covered under insurance plan": ("No", "No", "RE0235"),
    "Health Screening / Preventive Checks/ Vaccination": ("No", "Yes", "RE0238"),
    "Communication/ Technology/ Electronic Expenses (includes internet bill, IT services/repairs/ IT accessories)":
        ("Yes", "Yes", "RE0237"),
    "Fitness Memberships fee": ("Yes", "Yes", "RE0237"),
    "Holiday Subsidy": ("Yes", "Yes", "RE0237"),
    "Local Attraction Entrance Fees": ("Yes", "Yes", "RE0237"),
    "Medical Insurance premium": ("Yes", "Yes", "RE0237"),
    "Optical Expenses": ("Yes", "Yes", "RE0237"),
    "Self-Improvement Course Fees": ("Yes", "Yes", "RE0237"),
    "Utilities Bills": ("Yes", "Yes", "RE0237"),
    "Work From Home Furniture & Fittings": ("Yes", "Yes", "RE0237"),
}
CODE_DESCRIPTIONS = {
    "RE0235": "Non-Taxable & Non CPF Payable",
    "RE0238": "Non-Taxable & CPF Payable",
    "RE0237": "Taxable & CPF Payable",
}
ENTITIES = {
    "RHB Asset Management Pte Ltd": ("RHBROAM", "RHB Asset Mgmt PL"),
    "RHB Bank Berhad": ("RHBBSG", "RHB Bank Singapore"),
}
CLAIM_COLUMNS = (
    "Entity", "Staff ID", "Employee Name", "Category", "Claimant Name", "Relation",
    "Reference No.", "Claim Type", "Claim Sub-Type", "TAX", "CPF", "Incurred Date",
    "Service Provider", "Incurred Currency", "Incurred Amt", "Converted Currency",
    "Converted Incurred Amt", "Payment Amt", "Status", "Paid Date", "Admin Remark",
)
LISTING_COLUMNS = ("Entity", "User ID", "Employee Name", "Date of Hire", "Last Day of Service")
UTILIZATION_COLUMNS = (
    "Entity", "Staff ID", "Employee Name", "Date of Hire", "Last Day of Service",
    "Benefit Start Date", "Benefit End Date", "Category", "Wallet", "Total Allocation Amt",
    "Claims Payment Amt", "Total Utilized Amt (L-M+N+O+P)", "Pending Claims Payment Amt",
    "Balance Available Allocation Amt",
)
DETAIL_HEADERS = (
    "Staff ID", "Employee", "Claimant", "Relation", "Reference No.", "Claim Type",
    "Incurred Date", "Service Provider", "Incurred Amt", "Reimbursement Amt", "Admin Remark",
)
DETAIL_FIELDS = (
    "Staff ID", "Employee Name", "Claimant Name", "Relation", "Reference No.", "Claim Type",
    "Incurred Date", "Service Provider", "Converted Incurred Amt", "Payment Amt", "Admin Remark",
)
DETAIL_WIDTHS = (12, 46, 39, 12, 16, 50, 16, 42, 17, 22, 25)
SUMMARY_WIDTHS = (14, 51, 17, 13, 23, 16, 23, 26, 26, 32, 23, 21, 24, 24, 22, 24, 19, 26, 22, 25, 25, 25)
UTILIZATION_HEADERS = (
    "Employee ID", "Name", "Date of Joined", "Termination Date", "Entity",
    "Claim Benefit Group", "Entitlement", "Reimbursed", "Pending Reimbursement", "Balance",
)
UTILIZATION_FIELDS = (
    "Staff ID", "Employee Name", "Date of Hire", "Last Day of Service", "Entity", "Category",
    "Total Allocation Amt", "Claims Payment Amt", "Pending Claims Payment Amt",
    "Balance Available Allocation Amt",
)
UTILIZATION_WIDTHS = (16, 42, 19, 21, 31, 32, 17, 18, 27, 17)
PALETTE = {"heading": "CCCCFF", "benefit": "CCFFFF", "grid": "C0C0C0", "text": "000000"}

CLAIM_VALIDATION = {
    "file_key": "claims", "label": "RHB", "check_relations": False,
    "notes": (
        "Payroll codes follow RHB's claim-type table. Uploaded CPF flags are preserved; "
        "differences are flagged for review and do not change the payroll code."
    ),
    "rules": [{"claim_type": label, "taxable": tax, "cpf": cpf, "code": code,
               "description": CODE_DESCRIPTIONS[code]}
              for label, (tax, cpf, code) in CLAIM_RULES.items()],
}
RESULT_UI = {
    "show_submission_breakdown": False,
    "validation_title": "RHB report checks",
    "status_notes": {
        "success": "All five RHB reports are ready to download.",
        "warning": "All five RHB reports are complete. Review the noted records before submitting.",
    },
    "groups": {"warn": {"title": "Records to review",
                        "intro": "These records remain included in the reports."}},
    "stat_tiles": [
        {"key": "grand_total", "label": "Reimbursement (SGD)", "money": True},
        {"key": "breakdown_rows", "label": "Claims"},
        {"key": "employees", "label": "Claiming Employees"},
        {"key": "payroll_rows", "label": "Payroll Rows"},
        {"key": "utilization_rows", "label": "Utilisation Records"},
    ],
}
