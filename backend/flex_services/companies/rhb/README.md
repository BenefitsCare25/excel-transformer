# RHB Flex Report

Upload the employee claims, employee listing and utilisation summary exports. The payment month is detected from Paid Date. No prior-month output or template is required.

The adapter generates three `.xlsx` reports and two headerless PE payroll CSVs. The supplied legacy `.xls` summary is generated as `.xlsx`, retaining all 14 claim-type columns, three code totals, receipt counts and a source-claims sheet.

## Rules

- Claim types follow the two supplied RHB screenshots dated 6 October 2026. Whitespace and case differences are accepted; unknown types are rejected.
- RE0235: alternative treatment, dental, outpatient medical and medical expenses beyond insurance.
- RE0238: health screening / preventive checks / vaccination.
- RE0237: the remaining nine taxable claim types.
- CPF differences are warnings. The user confirmed that the screenshot's code must still be used. Invalid Yes/No flags and tax mismatches block generation.
- Claims must be approved, have unique references, use SGD converted amounts, and belong to one payment month. Amounts are rounded per claim to cents before aggregation.
- Payroll groups by entity, employee and code. RHB Bank Berhad uses RHBBSG; RHB Asset Management Pte Ltd uses RHBROAM. Both CSVs are always produced, with an empty file when an entity has no claims.
- Payroll dates are the first of the payment month; the reference is FLEXYYYYMM. CSVs have the reference's 13 columns and no header or BOM.
- Details retain one row per claim with employee subtotals and a grand total. The incurred amount uses Converted Incurred Amt in SGD.
- Utilisation excludes categories containing `wo flex`. It retains separate wallet rows, historic leavers, blank entitlements and the uploaded dates and cumulative amounts. It does not add monthly claims again or infer an as-of date from the workbook filename.
- Employee IDs, names and entities must match the listing. Last Day of Service from the listing flags claiming leavers without removing payments. Conflicting termination dates and stale cumulative totals produce warnings.
- After a successful match, reports use the employee listing's name. Accepted case or whitespace variations cannot split an employee's summary or detail subtotal; claimant names are preserved.

The July reference summary contains its original 96 claims on Sheet3, allowing summary and payroll outputs to be reconciled to the supplied July files. The separate input claims workbook is for September 2026.
