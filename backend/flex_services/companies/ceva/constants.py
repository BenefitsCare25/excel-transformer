"""Ceva's supplied benefit rules, payroll codes and report layouts."""

CLAIM_RULES = {
    "Outpatient Medical": ("No", "No", "EARN56"),
    "Inpatient Medical": ("No", "No", "EARN57"),
    "Dental": ("No", "No", "EARN58"),
    "Vaccination": ("No", "No", "EARN59"),
    "Optical": ("Yes", "Yes", "EARN60"),
    "TCM": ("No", "No", "EARN61"),
    "Health Screening": ("No", "Yes", "EARN62"),
    "Health & Wellness": ("Yes", "Yes", "EARN63"),
    "Health & Wellness (Social)": ("Yes", "Yes", "EARN64"),
    "Personal Development": ("Yes", "Yes", "EARN65"),
    "Holiday Trips": ("Yes", "Yes", "EARN76"),
}
HOLIDAY_EXPORT_LABEL = (
    "Holiday Trips (For Employee ONLY) - Please submit this only after you return "
    "from the trip, and attach your boarding pass"
)
CLAIM_ALIASES = {HOLIDAY_EXPORT_LABEL: "Holiday Trips", "Holidays": "Holiday Trips"}
CODE_DESCRIPTIONS = {
    claim_type: ("Holiday Reimbursement" if claim_type == "Holiday Trips"
                 else f"Flexible Benefit - {claim_type}")
    for claim_type in CLAIM_RULES
}
ENTITY_ALIASES = {
    "CEVA Asia Pacific Holdings Company Pte Ltd": (
        "CEVA Asia Pacific Holdings Company Pte Ltd", "CEVA Asia Pacific Holdings",
        "Ceva Asia-Pacific Holdings Company Pte. Ltd",
    ),
    "CEVA LOGISTICS SOLUTIONS SINGAPORE PTE LTD": (
        "CEVA LOGISTICS SOLUTIONS SINGAPORE PTE LTD",
    ),
    "CEVA LOGISTICS SERVICES ASIA-PACIFIC PTE. LTD": (
        "CEVA LOGISTICS SERVICES ASIA-PACIFIC PTE. LTD",
    ),
    "CEVA MANAGEMENT ASIA-PACIFIC PTE. LTD": ("CEVA MANAGEMENT ASIA-PACIFIC PTE. LTD",),
    "Pyramid Lines Singapore Pte. Ltd.": ("Pyramid Lines Singapore Pte. Ltd.",),
}
CLAIM_COLUMNS = (
    "Entity", "Staff ID", "Employee Name", "Reference No.", "Claim Type", "TAX", "CPF",
    "Incurred Date", "Converted Currency", "Converted Incurred Amt", "Payment Amt",
    "Status", "Paid Date",
)
LISTING_COLUMNS = ("Entity", "User ID", "Employee Name", "Date of Hire", "Last Day of Service")
UTILIZATION_COLUMNS = (
    "Entity", "Staff ID", "Employee Name", "Date of Hire", "Last Day of Service",
    "Benefit Start Date", "Benefit End Date", "Wallet", "Total Allocation Amt",
    "Claims Payment Amt", "Total Utilized Amt (L-M+N+O+P)", "Pending Claims Payment Amt",
    "Balance Available Allocation Amt",
)
PAYROLL_HEADERS = (
    "Entity", "Staff ID", "Employee Name", "Claim Type", "Payment Amt", "Code",
    "Code Description",
)
PAYROLL_WIDTHS = (47.44, 10, 49, 24, 13, 8.89, 36.78)
UTILIZATION_HEADERS = (
    "Entity", "Employee ID", "Name", "Date of Joined", "Claim Type", "Entitlement",
    "Total Claimed Amount", "Pending Claims", "Balance",
)
UTILIZATION_WIDTHS = (47.78, 14.66, 63.22, 14.33, 10.66, 11.44, 20.89, 15.11, 13.78)
FILE_COMPANY_LABEL = "Ceva Logistics Singapore Pte Ltd"
PALETTE = {"header": "FFFF00", "grid": "000000"}

CLAIM_VALIDATION = {
    "file_key": "claims", "label": "Ceva", "check_relations": False,
    "notes": ("Tax and CPF rules follow Ceva's supplied benefit table. Uploaded CPF flags are "
              "preserved; differences are flagged for review. Claimant eligibility was not supplied."),
    "rules": [{"claim_type": label, "taxable": tax, "cpf": cpf,
               "code": code, "description": CODE_DESCRIPTIONS[label]}
              for label, (tax, cpf, code) in CLAIM_RULES.items()],
}
RESULT_UI = {
    "show_submission_breakdown": False,
    "validation_title": "Ceva report checks",
    "status_notes": {
        "success": "Both Ceva reports are ready to download.",
        "warning": "Both Ceva reports are complete. Review the noted records before submitting.",
    },
    "groups": {"warn": {
        "title": "Records to review",
        "intro": "These records are included in the generated reports. Review the details below.",
    }},
    "stat_tiles": [
        {"key": "grand_total", "label": "Reimbursement (SGD)", "money": True},
        {"key": "breakdown_rows", "label": "Claims"},
        {"key": "payroll_rows", "label": "Payroll Rows"},
        {"key": "employees", "label": "Claiming Employees"},
        {"key": "utilization_rows", "label": "Utilisation Employees"},
    ],
}
