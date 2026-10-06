# Ceva Flex Report

Required inputs: employee claims export, built-in employee listing report, and
FSA utilisation summary report. Payment month is detected from `Paid Date`;
claims must be approved, converted to SGD, and paid in that month.
Text dates in `DD/MM/YYYY` or `DD-MM-YYYY` use day-first parsing, matching the
upload screen. Native Excel dates and ISO dates retain their original meaning.
Repeated nonblank column headings, including headings differing only in outer
whitespace, are rejected before pandas selects or renames any columns.

The adapter produces the two supplied layouts:

- Flexible Benefits: one row per entity, employee and claim type, summing
  `Payment Amt`, with the supplied EARN code and description.
- Utilisation: all uploaded FSA records, including leavers, with the export's
  entitlement, cumulative claims, pending claims and balance. `Date of Joined`
  uses the export's `Date of Hire`. Blank claims/pending amounts represent zero.

The 11 claim types and tax/CPF classifications come from Ceva's supplied tables.
The long Holiday Trips export label and `Holidays` map to `Holiday Trips`.
Tax differences and unknown claim types block generation. Uploaded CPF flags
are preserved; differences from the benefit table are review warnings.

Employee IDs, names and entities must match the employee listing. Recognised
entity spelling variants are matched consistently; payroll uses the canonical
entity and listing name, while utilisation preserves its source entity/name.
The listing's last day of service identifies leaver claims for review without
excluding them. Negative entitlement/balance and inconsistent balances are
also advisory and remain visible in the reports. A cumulative claims amount
below the monthly reimbursement flags a potentially outdated utilisation export.

The July output examples define the format, not the required month or employee
population. No source employee data or reference workbooks are stored in the adapter.
