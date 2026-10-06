"""Headerless, 13-column PE uploads for RHB's two payroll entities."""

import csv
from decimal import Decimal
from pathlib import Path

from .constants import ENTITIES


def payroll_groups(claims):
    return claims.groupby(["Entity", "PayrollCode", "Staff ID"], sort=True)["PaymentCents"].sum()


def write_payroll(claims, month, outdir):
    grouped = payroll_groups(claims)
    date = f"1/{month.month}/{month.year}"
    outputs = []
    for entity, (company_code, filename_label) in ENTITIES.items():
        path = Path(outdir) / f"PE Upload - Flexi Claims_{month:%B %Y} ({filename_label}).csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            for (group_entity, payroll_code, staff_id), cents in grouped.items():
                if group_entity != entity:
                    continue
                amount = format(Decimal(int(cents)) / 100, "f")
                writer.writerow([company_code, staff_id, "0", "ER0", payroll_code, "O", "SGD",
                                 "", "", amount, date, date, f"FLEX{month:%Y%m}"])
        outputs.append(str(path))
    return outputs
