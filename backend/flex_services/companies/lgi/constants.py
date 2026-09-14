"""LGI's supplied claim classification and reference workbook columns."""

ENTITY = "Lion Global Investors Limited"
BRUNEI_ENTITY = "Lion Global Investors Ltd, Brunei Branch"

# (Taxable, CPF payable), transcribed from LGI's latest classification checklist.
TRAVEL_INSURANCE = "Holiday travel insurance, admission fees to local attraction etc"
CLAIM_RULES = {
    "Alternative Treatment (part of medical treatment)": ("No", "No"),
    "Dental": ("No", "No"),
    "Family Holidays (hotel, chalets, holiday bungalows, tour package, air tickets)": ("Yes", "No"),
    "Fertility Treatment (CPF Payable)": ("No", "Yes"),
    "Health Screening (part of medical treatment)": ("No", "No"),
    "Infant and Childcare Expenses at ECDA Registered Childcare Centres": ("No", "Yes"),
    "Lasik Surgery (CPF Payable)": ("No", "Yes"),
    "Maternity": ("No", "Yes"),
    "Medical Expenses (incurred for general well-being)": ("No", "Yes"),
    "Medical Expenses beyond Hospital & Surgical or Outpatient Plan (Cash payment)": ("No", "No"),
    "Medical Expenses not covered by Hospital & Surgical or Outpatient Plan (Cash payment)": ("No", "No"),
    "Other Benefits": ("Yes", "Yes"),
    "Outpatient GP": ("No", "No"),
    "Outpatient Specialist (without referral letter)": ("No", "No"),
    "Self-Improvement Course Fees (Non CPF Payable)": ("Yes", "No"),
    "Vaccinations and Immunizations": ("No", "Yes"),
    "Medical and Dental Expenses for Parents": ("Yes", "Yes"),
    "Purchase of Fitness Equipment": ("Yes", "Yes"),
    "Utility/Broadband/Telephone Bills": ("Yes", "Yes"),
    "Entertainment & Concert Tickets": ("Yes", "Yes"),
    "Personal Insurance Premium": ("Yes", "Yes"),
    "Children's Education Tuition Fees": ("Yes", "Yes"),
    "Spa/Wellness Services": ("Yes", "Yes"),
    "Medical Appliances": ("Yes", "Yes"),
    "Optical Expenses": ("Yes", "Yes"),
    "Fitness Club Memberships and entrance fees": ("Yes", "Yes"),
    "Purchase of Handphone/PDAs/Laptop and computer accessories": ("Yes", "Yes"),
    TRAVEL_INSURANCE: ("Yes", "Yes"),
}

# Source exports and reference material sometimes use shortened labels. Resolve
# those labels to one rule without changing the original claim text in the output.
CLAIM_TYPE_ALIASES = {
    "Fertility Treatment": "Fertility Treatment (CPF Payable)",
    "Lasik Surgery": "Lasik Surgery (CPF Payable)",
    "Self-Improvement Course Fees": "Self-Improvement Course Fees (Non CPF Payable)",
}

CLAIM_COLUMNS = (
    "Entity", "Staff ID", "Employee Name", "Claimant Name", "Relation",
    "Reference No.", "Claim Type", "TAX", "CPF", "Incurred Date",
    "Service Provider", "Converted Currency", "Converted Incurred Amt",
    "Payment Amt", "Status", "Paid Date", "Admin Remark",
)
LISTING_COLUMNS = (
    "Entity", "Employee ID No.", "Employee Name", "Designation", "Cost Centre",
    "Department", "Date of Hire", "Last Day of Service",
)
UTILIZATION_COLUMNS = (
    "Entity", "Staff ID", "Employee Name", "Date of Hire", "Last Day of Service",
    "Benefit Start Date", "Benefit End Date", "Wallet", "Total Allocation Amt",
    "Buy Leave Amt", "Sell Leave Amt", "Selection Amt", "Deals Amt",
    "Claims Payment Amt", "Total Utilized Amt (L-M+N+O+P)",
    "Pending Claims Payment Amt", "Balance Available Allocation Amt",
)

DETAIL_HEADERS = (
    "ROC NO.", "Receipt Date", "Employee ID", "Employee Name", "Claimant Name",
    "Relation", "Claim Type", "Taxable", "Non Taxable", "CPF Payable",
    "Receipt Amount", "Reimburse Amount", "Service Provider", "Status",
    "Inspro Remarks", "System Remarks",
)
SUMMARY_HEADERS = (
    "Employee ID", "Employee Name", "Category", "Cost Center", "Department",
    "Taxable", "Non Taxable", "CPF Payable",
)
UTILIZATION_HEADERS = (
    "Policy Period", "Employee ID", "Employee Name", "Category", "Cost Centre",
    "Department", "Flex$ Allocation", "Flex$ Utilised", "Flex$ Bal trf to FSA",
    "Total Amount Utilized in Month", "Year to Date Reimbursement",
    "Salary Deduction", "Balance Flex Point", "Termination Date",
)

DETAIL_WIDTHS = (13, 16.78, 16.33, 34.55, 29.78, 12.22, 80.22, 18.22, 13.89,
                 16.11, 19.33, 18.22, 38.66, 6.44, 14.55, 15.55)
SUMMARY_WIDTHS = (16.33, 34.55, 28.55, 18.66, 39, 18.22, 13.89, 16.11)
UTILIZATION_WIDTHS = (33.11, 17.44, 38.44, 16.55, 16.55, 37.89, 20, 17.66,
                      22.33, 27.66, 20.44, 21.44, 22, 21.78)

RESULT_UI = {
    "show_submission_breakdown": False,
    "validation_title": "LGI checks",
    "warning_badge_verb": "to review",
    "status_notes": {
        "success": "LGI reports have been generated and reconciled.",
        "warning": "LGI reports have been generated. Review the notes below before using the files.",
        "error": "Correct the LGI source files and run again.",
    },
    "groups": {"warn": {"title": "Items to review", "intro": "Flagged claims remain included."}},
    "stat_tiles": [
        {"key": "grand_total", "label": "Claims Total (SGD)", "money": True},
        {"key": "breakdown_rows", "label": "Claims"},
        {"key": "employees", "label": "Claiming Employees"},
        {"key": "leavers", "label": "Leavers to Note"},
    ],
}
