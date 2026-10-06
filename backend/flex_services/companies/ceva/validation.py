"""Ceva's claim checklist: CPF differences remain reviewable source values."""

import pandas as pd

from .constants import CLAIM_ALIASES, CLAIM_RULES
from .sources import lookup_key, read_claims

CLAIM_TYPES = {lookup_key(label): label for label in CLAIM_RULES}
CLAIM_TYPES.update({lookup_key(alias): label for alias, label in CLAIM_ALIASES.items()})


def classify_claims(claims):
    claims["ReportType"] = claims["Claim Type"].map(lookup_key).map(CLAIM_TYPES)
    issues, warnings = [], []
    for _, row in claims.iterrows():
        label = row["ReportType"]

        def issue(field, expected, message):
            actual = "" if pd.isna(row[field]) else str(row[field]).strip()
            return {"row": int(row["ExcelRow"]), "reference": row["Reference No."],
                    "claim_type": row["Claim Type"], "field": field, "actual": actual,
                    "expected": expected, "message": message,
                    "employee_id": row["Staff ID"], "employee_name": row["Employee Name"]}

        if not isinstance(label, str):
            issues.append(issue("Claim Type", "A listed Ceva benefit",
                                "Select the matching Ceva claim type from the supplied benefit table."))
            continue
        tax, cpf, _ = CLAIM_RULES[label]
        for field, expected in (("TAX", tax), ("CPF", cpf)):
            actual = str(row[field]).strip().casefold()
            if actual not in ("yes", "no"):
                issues.append(issue(field, "Yes or No", f"Set {field} to Yes or No in the claims export."))
            elif actual != expected.casefold():
                if field == "TAX":
                    issues.append(issue(field, expected,
                                        f"Ceva's benefit table requires TAX = {expected} for this claim type."))
                else:
                    warnings.append(issue(field, expected,
                                          f"Uploaded CPF = {row[field]}; Ceva's table says {expected}. "
                                          "The uploaded flag is preserved. Confirm any employee-specific exemption."))
    return issues, warnings


def validate_claims(path):
    claims = read_claims(path)
    issues, warnings = classify_claims(claims)
    return {"valid": not issues, "claims": len(claims), "validation": issues, "warnings": warnings}
