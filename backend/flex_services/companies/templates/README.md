# Saved payroll templates

Drop a company's payroll template here so the monthly run only needs its data files.

| Company | Filename | Contents |
|---------|----------|----------|
| STM | `stm_it15_template.xlsx` | IT15 workbook with sheet `SG1xPaymtTemplate`: header block (rows 1–19), the payroll-user formula columns (M/P), and row 20 carrying the cell formatting — **no employee data** |

Notes:

- Row 20 must exist with the fonts, borders and number formats you want on the data rows.
  Its values stay empty; the generator clones the formatting from it.
- Any employee data left in the template is cleared before new rows are written, so a
  prior-month IT15 file also works here — it is just larger than it needs to be.
- The file is read, never modified. Each run copies it and writes the copy.
- When no template is saved, the upload slot becomes required and the operator supplies
  the file with each run. Adding or removing a file here takes effect on app restart
  (a deploy counts), because the upload slot's required flag is read at import time.
- If payroll changes the format, either replace the file here or upload the new file once
  in the run — an uploaded file always overrides the saved template.
