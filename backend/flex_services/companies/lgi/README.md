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
the uploaded wording in the reports. **Children's Education/ Tuition Fees is taxable
and CPF-payable**, including the export label with a curly apostrophe. Matching
accepts straight/curly apostrophes and spacing around slashes, and retains support
for the older Children's Education Tuition Fees label.

The supplied LGI checklist is authoritative for tax, CPF and claimant eligibility.
EE maps to Self, SP to Spouse, CH to Child and Parents to Parent. Claim types with
restricted eligibility include childcare and children's education (Child only),
parents' medical/dental expenses (Parent only), self-improvement courses (Self only),
and fertility, maternity, fitness memberships, spa and utility bills (Self/Spouse).
Original claimant and category values are preserved; mismatches stop generation.

**Other Benefit is taxable and CPF-payable**, as confirmed in the setup update.
Both Other Benefit and Other Benefits are accepted, preserving the uploaded label.
No claimant eligibility rule was supplied for this category, so its eligibility
is shown as Not specified and no category-specific relation check is applied.

Uploading LGI claims triggers `POST /api/flex/validate/lgi` with the `claims` file.
The page lists every checklist issue with its Excel row, claim reference, uploaded
value, expected value and correction guidance. Generation stays disabled while
checks are pending, unavailable or failing. Re-uploading, resetting or switching
companies invalidates stale responses. The rules table comes from the company
catalog; both upload checks and generation use the same backend validator.
Once all files are uploaded, `POST /api/flex/validate-inputs/lgi` checks approval
status, dates, amounts, employee matching and totals without creating output files.
Generation stays disabled until this check passes and repeats the same checks.
Errors identify the file, explain the problem and give the next step. Employees
absent from the listing are distinguished from those present in the utilisation
summary but excluded by the policy date filter; the latter show the source dates
and the cutoff. Changing files or company, or resetting, invalidates old results.

For a claimant whose only utilisation record starts before the policy year, the
page requires an explicit **Include in reports** or **Exclude from reports**
choice. Include uses that record with its original balances; all other matching
and amount checks still apply. Exclude removes that employee's claims and
utilisation record from all three reports and their totals. No choice is selected
automatically. Choices reset when uploads, company or payment month change.
Both preflight and generation receive `policy_decisions` as a JSON object keyed
by employee ID. The server rejects stale IDs and unsupported values. Missing,
ambiguous or future utilisation records still require correction. The result,
run log and retained run manifest record the choices and affected claim amounts.
Excluding all claimants produces reports with no claim rows and a zero claim total.

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
