"""RHB claim checklist, including reviewable employee-specific CPF differences."""

import pandas as pd

from .constants import CLAIM_RULES
from .sources import lookup_key, read_claims

CLAIM_TYPES = {lookup_key(label): label for label in CLAIM_RULES}


def classify_claims(claims):
    claims["ReportType"] = claims["Claim Type"].map(lookup_key).map(CLAIM_TYPES)
    claims["PayrollCode"] = claims["ReportType"].map(
        {label: rule[2] for label, rule in CLAIM_RULES.items()})
    issues, warnings = [], []
    for _, row in claims.iterrows():
        def issue(field, expected, message):
            return {"row": int(row["ExcelRow"]), "reference": row["Reference No."],
                    "claim_type": row["Claim Type"], "field": field,
                    "actual": "" if pd.isna(row[field]) else str(row[field]).strip(),
                    "expected": expected, "message": message,
                    "employee_id": row["Staff ID"], "employee_name": row["Employee Name"]}

        label = row["ReportType"]
        if not isinstance(label, str):
            issues.append(issue("Claim Type", "One of RHB's 14 listed claim types",
                                "Select the matching claim type from the RHB checklist."))
            continue
        tax, cpf, code = CLAIM_RULES[label]
        for field, expected in (("TAX", tax), ("CPF", cpf)):
            actual = str(row[field]).strip().casefold()
            if actual not in ("yes", "no"):
                issues.append(issue(field, "Yes or No", f"Set {field} to Yes or No."))
            elif actual != expected.casefold():
                if field == "TAX":
                    issues.append(issue(field, expected, f"RHB's table requires TAX = {expected}."))
                else:
                    warnings.append(issue(field, expected,
                                          f"Uploaded CPF flag preserved; payroll remains {code} "
                                          "under RHB's claim-type table. Confirm the employee's CPF treatment."))
    return issues, warnings


def validate_claims(path):
    claims = read_claims(path)
    issues, warnings = classify_claims(claims)
    return {"valid": not issues, "claims": len(claims), "validation": issues, "warnings": warnings}
