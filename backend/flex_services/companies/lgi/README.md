# Lion Global Investors Flex Report

Select **Lion Global Investors (LGI)** in Flex Report and upload:

- Employee claims export (`claims`). The payment month is detected from `Paid Date`.
- Built-in employee listing (`listing`).
- Utilisation summary export (`utilization`).

The profile produces three ordinary, unencrypted `.xlsx` files. Reference workbooks
and their opening password are not stored in the adapter or required for a run.

## Claims Detail and Claims Summary

Both files retain the claims export's row order and one row per claim, including
claims for employees with a last day of service. Claims Summary is not aggregated
by employee; this matches LGI's reference.

Claims must be approved, paid within the detected month, denominated in SGD after
conversion, and matched to the employee listing by staff ID. Duplicate references,
unknown claim types, invalid amounts, missing employees and name/entity mismatches
stop generation before output files are written.

The latest LGI checklist supplies the category rules in `constants.py`.
**Holiday travel insurance, admission fees to local attraction etc is taxable and
CPF-payable.** The profile also recognizes the shortened checklist labels for
Fertility Treatment, Lasik Surgery and Self-Improvement Course Fees while preserving
the uploaded wording in the reports. Tax/CPF conflicts stop generation.

| Output field | Input or calculation |
| --- | --- |
| ROC NO. | Reference No. |
| Receipt Date | Incurred Date |
| Employee ID | Staff ID; matched to Employee ID No. in the listing |
| Category, Cost Center, Department | Listing Designation, Cost Centre, Department |
| Taxable / Non Taxable | Payment Amt allocated according to the category rule |
| Receipt Amount | Converted Incurred Amt |
| Reimburse Amount | Payment Amt |
| Status | Paid, after validating Approved and the Paid Date |
| Inspro Remarks | Admin Remark |
| System Remarks | Blank; no corresponding input field |

## Utilization Report

The uploaded data is authoritative. The historical output is a layout reference,
not a source of employee balances or an employee inclusion list. Cumulative amounts
reflect the supplied utilisation export: the three inputs cannot reconstruct a
historical snapshot from a later export. Use a month-end export for historical reporting.

The policy year runs from 1 October to 30 September. Include source FSA records with
a Benefit Start Date in that policy year and on or before the reporting month-end,
and a hire date on or before that month-end. Retain current-policy leavers and zero
allocations. Exclude previous-policy records and future starters, and log the count.
Include both the Singapore entity and its Brunei branch when supplied. Every monthly
claimant must have an included utilisation record.

| Output field | Input or calculation |
| --- | --- |
| Flex$ Allocation | Total Allocation Amt |
| Flex$ Utilised | Buy Leave Amt − Sell Leave Amt + Selection Amt + Deals Amt |
| Flex$ Bal trf to FSA | Allocation − Flex$ Utilised |
| Total Amount Utilized in Month | Sum of this month's Payment Amt per employee |
| Year to Date Reimbursement | Claims Payment Amt from the utilisation export |
| Salary Deduction | Blank; no supplied deduction amount or deduction rule |
| Balance Flex Point | Balance Available Allocation Amt, including negative values |
| Termination Date | Employee listing Last Day of Service |

Pending claims are not added to reimbursement or deducted from the reported balance.
Check both source equations: total utilised equals Flex$ Utilised plus cumulative
claims paid; balance equals allocation minus total utilised. Cumulative claims paid
must cover this month's claims, and monthly reimbursement must agree across all
three outputs. Amounts are rounded to cents; reconciliation allows one cent of source
rounding difference.

Claimant last days of service, negative balances and termination-date differences
between the two inputs produce review notes. Employee
listing dates take precedence for Termination Date; no deduction or exclusion is
inferred from those warnings. Missing/invalid values, duplicate staff IDs, unsupported
wallets, hire-date conflicts and financial reconciliation errors block generation.

Run the synthetic-data checks from `backend` with:

```text
python -m unittest tests.test_lgi -v
```
