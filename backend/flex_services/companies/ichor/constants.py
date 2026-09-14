"""Ichor-specific workbook schema, category rules and result presentation."""

ICHOR_ENTITY = "ICHOR SYSTEMS SINGAPORE PTE. LTD."

CLAIMS_REQUIRED_COLUMNS = (
    "Entity",
    "Staff ID",
    "Employee Name",
    "Reference No.",
    "Claim Type",
    "Incurred Date",
    "Service Provider",
    "Converted Currency",
    "Converted Incurred Amt",
    "Payment Amt",
    "Status",
    "Paid Date",
    "Admin Remark",
)

LISTING_REQUIRED_COLUMNS = (
    "User ID",
    "Employee Name",
    "Last Day of Service",
)

DETAIL_HEADERS = (
    "Staff ID",
    "Employee",
    "Reference No.",
    "Claim Type",
    "Incurred Date",
    "Service Provider",
    "Incurred Amt",
    "Reimbursement Amt",
    "Admin Remark",
)

MEDICAL = "Medical Expenses beyond or not covered Hospital & Surgical or Outpatient Plan Limits"
TCM = "TCM, Acupuncture, Podiatry, Homeopathy only treatment & consultation"
APPLIANCES = (
    "Medical and Dental Appliances (e.g. splints, insoles, guards, braces, "
    "retainers & tooth veneers)"
)
WELLNESS = "Wellness Benefits (Gym membership & Entrance Fee / Fitness Classes)"

# Group membership and column order are the business rules. The source TAX/CPF flags do not
# determine where a claim appears in the summary.
SUMMARY_GROUPS = (
    (
        "Non-Taxable \n& Non CPF Payable",
        "non_tax_non_cpf",
        (
            ("A&E", "Employee"),
            ("Polyclinic", "Employee"),
            ("Polyclinic", "Dependent"),
            ("Panel Fullerton GP", "Employee"),
            (MEDICAL, "Employee"),
            (MEDICAL, "Dependent"),
            ("Dental", "Employee"),
            ("Dental", "Dependent"),
            (TCM, "Employee"),
            (TCM, "Dependent"),
        ),
    ),
    (
        "Non-Taxable \n& CPF Payable",
        "non_tax_cpf",
        (
            ("Health Screening", "Employee"),
            ("Health Screening", "Dependent"),
            ("Vaccination", "Employee"),
            ("Vaccination", "Dependent"),
        ),
    ),
    (
        "Taxable \n& CPF Payable",
        "taxable_cpf",
        (
            (APPLIANCES, "Employee"),
            (APPLIANCES, "Dependent"),
            ("Vision", "Employee"),
            ("Vision", "Dependent"),
            (WELLNESS, "Employee"),
        ),
    ),
)

SUMMARY_COLUMNS = tuple(
    column
    for _, _, group_columns in SUMMARY_GROUPS
    for column in group_columns
)

TYPE_ALIASES = {
    "Panel Fullerton GP only": "Panel Fullerton GP",
}

RESULT_UI = {
    "show_submission_breakdown": False,
    "validation_title": "Ichor checks",
    "warning_badge_verb": "to note",
    "status_notes": {
        "success": "Both Ichor reports include every claim. No leavers were found in this run.",
        "warning": (
            "Both Ichor reports include every claim. Review the leavers listed below before using "
            "the files."
        ),
        "error": "Some Ichor claims could not be processed. Correct the source files and run again.",
    },
    "groups": {
        "warn": {
            "title": "Leavers to note - claims remain included",
            "intro": (
                "These employees have a Last Day of Service in the listing. Their claims remain "
                "in both Claims Details and Claims Summary."
            ),
        },
    },
    "stat_tiles": [
        {"key": "grand_total", "label": "Claims Total (SGD)", "money": True},
        {"key": "breakdown_rows", "label": "Claims"},
        {"key": "employees", "label": "Employees"},
        {"key": "leavers", "label": "Leavers to Note"},
    ],
}
