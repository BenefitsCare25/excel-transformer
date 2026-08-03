# EL Project - Employee Listing & Excel Tools

## Project Overview

Internal tool for processing healthcare/insurance data with five main features:
- **Excel Transformer**: Transforms IHP clinic data into standardized template format (phone+remarks, operating hours consolidation, postal code extraction)
- **Clinic Matcher**: Compares clinic lists to identify panel coverage gaps
- **Mediacorp ADC**: Processes employee/dependant data to generate ADC reports
- **GP Panel Comparison**: Compares GP panel changes between files
- **Renewal Comparison**: Compares renewal listing Excel files between two policy years and generates an Adjustment Breakdown report (Cancel & Re-enroll method)
- **Flex Report**: Plugin-style monthly flexible benefits reimbursement factory — one adapter module per client company, each declaring its own upload slots and transformation rules (STM is live)

## Tech Stack

- **Backend**: Python Flask (app.py ~5600+ lines)
- **Frontend**: React with Tailwind CSS
- **Data**: Excel processing with pandas, openpyxl
- **APIs**: Google Maps for geocoding

## Project Structure

```
EL/
├── backend/
│   ├── app.py                 # Main Flask app (routes, all processing logic)
│   ├── cleanup_service.py     # Auto-cleanup for uploads
│   ├── mc_services/           # Mediacorp ADC processing
│   │   ├── el_processor.py    # Employee Listing processor
│   │   ├── dl_processor.py    # Dependant Listing processor
│   │   ├── ixchange_generator.py
│   │   ├── csv_processor.py   # Pipe-delimited CSV parser
│   │   ├── category_mapper.py # AIA/Flex category mapping (hardcoded)
│   │   └── validators.py
│   ├── gp_panel_services/     # GP Panel comparison
│   │   └── panel_processor.py
│   ├── renewal_services/      # Renewal comparison
│   │   └── renewal_processor.py
│   └── flex_services/         # Flex Report (per-company adapters)
│       ├── registry.py        # Company catalog: active adapters + pending slots
│       ├── run_store.py       # Ephemeral run folders, manifest, zip, 30-min reaper
│       └── companies/
│           └── stm.py         # STMicroelectronics adapter
├── frontend/
│   └── src/
│       ├── App.js
│       └── components/
│           ├── FileUpload.js          # Excel Transformer UI
│           ├── ProcessingStatus.js    # Job status display
│           ├── ClinicMatcher.js
│           ├── MediacorpProcessor.js
│           ├── GPPanelComparison.js
│           ├── RenewalComparison.js
│           ├── FlexReport.js          # Flex Report UI (company picker + upload slots)
│           └── FlexRunResult.js       # Flex Report run result panel
├── data/                      # Reference data (SG_postal.csv)
├── uploads/                   # Temporary upload storage
└── processed/                 # Output files
```

## Development Commands

```bash
# Backend
cd backend && python app.py              # Run Flask (port 5000)

# Frontend
cd frontend && npm start                 # Run React (port 3000)

# Full app
./start.bat                              # Windows: starts both
```

## Key Patterns

### Excel Processing
- Use `openpyxl` for Excel read/write
- Fill objects must be newly created, not copied (openpyxl limitation)
- Sheet names max 31 chars, no special characters: `[ ] : * ? / \ &`
- Always sanitize sheet names with `re.sub(r'[\\/*?:\[\]&]', '', name)[:31]` before `wb.create_sheet()`

### Data Validation
- Singapore postal codes: 6 digits extracted via regex
- Government hospitals/polyclinics filtered from clinic matching
- Phone numbers combined with remarks in format: `{phone} - {remarks}`

### Code Column Auto S/N
- If the mapped `Code` column contains zone names (NORTH, SOUTH, EAST, WEST, CENTRAL, etc.) instead of real clinic IDs, the transformer auto-replaces with sequential integers 1, 2, 3...
- Triggered when >50% of non-null values match known zone keywords
- Logic in `ExcelTransformer.transform_sheet()` around the `clinic_id` mapping block

### Duplicate Clinic Code Suffixing
- After the Code column is populated, duplicate codes are detected and suffixed with `-1`, `-2`, `-3` etc.
- All instances of a duplicate code get suffixed (e.g. `FHG123` appearing 3 times → `FHG123-1`, `FHG123-2`, `FHG123-3`)
- Unique codes remain unchanged
- Runs after zone-keyword detection, so sequential S/N values are unaffected
- Logic in `ExcelTransformer.transform_sheet()` immediately after the clinic_id mapping block (~line 1719)

### File Handling
- Auto-cleanup after 15 minutes (cleanup_service.py)
- Job IDs via UUID for tracking uploads
- Processed files stored in `processed/` folder

## Mediacorp ADC — Key Design Notes

### CSV Support (Raw Sharepoint Files)
- Accepts both `.xlsx` and `.csv` files interchangeably for all 4 uploads (New/Old EL, New/Old DL)
- Raw CSV files from Sharepoint are **pipe-delimited** (`|`), parsed with `pd.read_csv(sep='|', dtype=str)`
- Auto-detects Excel Power Query artifact headers (`Column1, Column2, ...`) and shifts first data row to headers
- Encoding fallback: UTF-8 → latin-1
- File type auto-detection by extension in `excel_handler.py`

### Category Mapping (Hardcoded)
- 11-entry mapping table in `category_mapper.py` → `DEFAULT_CATEGORY_MAPPING`
- No 5th upload needed — falls back to hardcoded mapping when no `Category Mapping` sheet in XLSX
- **AIA Category**: VLOOKUP from employee Category (col 15) → mapping table
- **Flex Category**: Nested IF logic using LDS (col 14), Category (col 15), Overseas Assignment (col 8), Employment Type (col 9), and computed AIA Category

### Processing Pipeline
| Step | Name | Description |
|------|------|-------------|
| 0 | CSV Import | Auto-parse pipe-delimited CSV, detect headers, load data |
| 1 | Category Tagging | Assign AIA Category + Flex Category to new EL |
| 2 | DL Comparison | Compare new vs old Dependant Listings, generate ADC |
| 3 | EL Comparison | Compare new vs old Employee Listings, add ADC remarks |
| 4 | Output Generation | Combined Excel with 3 sheets (Processed EL, Processed DL, Employee) |

### Output Excel Files
**Main file**: `Mediacorp_ADC_Output_DDMMYY.xlsx` — 3 sheets:
| Sheet | Contents | Filtering |
|-------|----------|-----------|
| Processed EL | Full employee listing with categories and remarks | Only rows with non-empty ADC Remarks |
| Processed DL | Full dependant listing with comparison columns | All rows (unfiltered) |
| Employee | 13-column iXchange format | Only rows with non-empty ADC Remarks |

- ADC Remarks / Inspro ADC Remarks is always the **first column** in each sheet
- Sheet was previously named "iXchange ADC", renamed to "Employee"

**Standalone files** (date from uploaded filename, DDMMYYYY format):
| File | Contents | Source |
|------|----------|--------|
| `MediacorpEmployee_DDMMYYYY.xlsx` | Processed EL without ADC Remarks column | All rows |
| `MediacorpDependant_DDMMYYYY.xlsx` | Processed DL without Inspro ADC Remarks column | All rows |

### ADC Effective Date (`wef`)
- **EL Addition**: `wef` = employee's Date of Hire (col 12) — when coverage starts
- **EL Deletion**: `wef` = Last Day of Service (col 14) — when coverage ends
- **DL new dependant**: `wef` = date extracted from the **new DL filename** (e.g. `MediacorpDependant_16032026.csv` → `160326`)
  - Regex extracts 8-digit date from filename, converts `DDMMYYYY` → `DDMMYY`
  - Fallback: today's date if no date found in filename
  - Previously used DOB (incorrect) — fixed to use file date since it represents when the ADC was generated

### Backend Logging
- Comprehensive step-by-step logging with timing for Azure Log Stream monitoring
- Logs file types, row/column counts, category distributions, sample data, warnings, and full traceback on errors
- `file_info` dict (type, rows per file) included in API response for frontend display

### Frontend Summary & Details
- File type badges (CSV orange, XLSX green) on upload boxes
- File size display per upload
- Pre-submission validation summary grid showing all 4 files with type/size/missing status
- Error details array rendered as bulleted list (e.g. backend validation errors)
- Console logging with `[MC Processor]` prefix for debugging
- **Collapsible detail dropdowns** in results summary — click each category (EL additions/deletions/changes, DL new spouse/child/other/deletions/dropoffs) to expand a table showing Staff ID, Name, and Remark for each record
- Detail data extracted from processed DataFrames in `app.py` and returned via API response (`el_details`, `dl_details`)

## Renewal Comparison — Key Design Notes

### Required Sheet Name
Each uploaded Excel file **must** contain a sheet named `"Employee Listing YYYY"` where YYYY is the 4-digit policy year — e.g. `"Employee Listing 2025"` and `"Employee Listing 2026"`.
- The year is extracted **directly from the sheet name** (not from cell values)
- A sheet named just `"Employee Listing"` (without year) is rejected with a clear error
- Detection logic: `_find_employee_listing_sheet()` in `renewal_processor.py`

### Supported Products
| Abbr | Full Name | Type |
|------|-----------|------|
| GTL  | Group Term Life | Type 1 — Sum Insured based |
| GDD  | Group Dread Disease | Type 1 — Sum Insured based |
| GPA  | Group Personal Accident | Type 1 — Sum Insured based |
| GDI  | Group Disability Income Benefit | Type 1 — Sum Insured based |
| GHS  | Group Hospital & Surgical | Type 2 — Annual Premium + GST |
| GMM  | Group Major Medical | Type 2 — Annual Premium + GST |
| GP   | Group Clinical General Practitioner | Type 2 — Annual Premium + GST |
| SP   | Group Clinical Specialist Insurance | Type 2 — Annual Premium + GST |
| GD   | Group Dental Insurance | Type 2 — Annual Premium + GST |

### Dynamic Row Detection (`_detect_header_rows`)
Excel layouts vary by client — row numbers are **never hardcoded**. The processor auto-detects:
- **product_header_row**: row with merged cells containing product keywords (GTL, GHS, hospital, etc.)
- **subheader_row**: product_header_row + 1
- **data_start_row**: product_header_row + 2

This means files with headers at row 8 (e.g. Technetics format) and row 13 (standard format) both work without any changes.

### Year Detection (`_find_employee_listing_sheet`)
- Year is read from the sheet tab name: `"Employee Listing 2025"` → year `2025`
- The lower year becomes previous year, the higher year becomes current year
- No cell scanning for year — eliminates false matches from date ranges in metadata rows

### Employee Matching (`EmployeeRecord.unique_key`)
Employees are matched across years using this priority:
1. **NRIC** (primary) — column header containing `nric`, `ic no`, `id no`, `passport`, `fin`, `nric/fin`, `nric/passport`
2. **Email** (fallback) — column header containing `email`, `e-mail`, `e mail`
3. **Name + DOB** (last resort) — name normalised (uppercased, collapsed whitespace); DOB normalised to `dd/mm/yyyy` across all common formats

Key format examples: `NRIC|S1234567A`, `EMAIL|john@example.com`, `NAME|JOHN TAN|01/01/1980`

### Entity Column (Optional)
- If either uploaded file has a column header `Entity` (exact match, case-insensitive), the value is extracted per employee and included in the output product sheets
- Entity column appears between Department and Category in the output (col G), shifting all product columns right by 1
- If neither file has an Entity column, the output layout is unchanged (no Entity column, no shift)
- Useful for multi-entity clients (e.g. "Poh Heng Jewellery (Private) Limited") where employees belong to different subsidiary entities

### Product Detection (`_detect_products`)
- Reads merged cells on product_header_row for section names
- Supports **multi-row merged cells** — a merged range is detected as long as `product_header_row` falls within `min_row..max_row` (not just exact single-row match). Some files (e.g. SYNESYS) have product headers like GMM merged across R1-R13.
- Each section's `col_end` is **extended** to just before the next section's `col_start` — this captures premium/value columns that fall outside the merged range (common in some client formats)
- `admin_type_col` assigned as the nearest `'Type of Administration'` column to the LEFT of each section
- Type 1 (Sum Insured): detected when subheader contains `'sum insured'` or `'eligible sum insured'`
- Type 2 (Premium): detected when subheader contains `'premium'` (excluding GST and `w/` columns)
- Fallback: `PRODUCT_TYPE_HINTS` dict maps known product name patterns to their type when column headers are ambiguous

### Premium Column Detection & Output Logic

**All column detection is keyword-based (case-insensitive substring match) — column names vary by client file.**

| Output Column | Source | Detection Keyword |
|---|---|---|
| Sum Insured (Col J base) | `'eligible sum insured'` → first match wins | `eligible sum insured` or `sum insured` |
| Annual Premium (Type 1, Col K) | Per-row premium column in source file | `premium` in header, not `gst`, not `w/` |
| Annual Premium (Type 2, Col J) | Per-row premium column in source file | `premium` in header, not `gst`, not `w/` |

**Type 1 premium output (GTL, GDD, GPA, GDI):**
- The source file already has a calculated annual premium per employee (e.g. `"Premium GPA"`, `"GPA Annual Premium"` — any column containing `premium`).
- Different employee categories carry different rates (e.g. Director $800k vs Staff $150k), so the premium is **read directly from each row** — no rate calculation is done by the system.
- `DetectedProduct.annual_premium_col` stores the column index; `product_data['annual_premium']` stores the per-row value.
- Output sign convention:
  - **Cancel rows** (prev year block): Column K = `−annual_premium` (negative)
  - **New employee rows** (curr year block): Column K = `+annual_premium` (positive)
  - **Renewal rows** (curr year block): Column K = `+prev_annual_premium` → net with cancel row = 0
- Fallback: if no annual premium column detected, falls back to `=J*rate` using the fixed product-level rate from the rate row.

**Type 2 premium output (GHS, GMM, GP, SP, GD):**
- Annual premium read directly from source; GST calculated as 9% in output Column K.
- **Curr year block always uses previous year premium** for adjustment — even for new employees not in the previous year file. A category→premium lookup is built from prev year employees; new employees get the prev year rate for their category. Falls back to curr year premium only if no category match found.
- Adjustment column (L) = `J / divisor` (pro-rated by divisor entered by user).
- Each Type 2 product sheet includes 3 summary rows (Col L) below the data:
  - **Adjustment Premium** = `SUM(L data rows)`
  - **GST** = `Adjustment Premium × 9%`
  - **Adjustment Premium with GST** = `Adjustment Premium + GST`
- Type 1 product sheets have only one summary row: **Adjustment Breakdown** = `SUM(L data rows)` (no GST rows).

**Type 1 renewal SI changes:**
- For renewal employees (in both years), the current year Sum Insured is always used in Col I. If SI is unchanged, J = I − H = 0 → cancel and re-enroll nets to zero. If SI changed, J captures the difference and Col K reflects the updated annual premium automatically.

### Named vs Headcount
- Employees with `Type of Administration = Named` are excluded from the Headcount adjustment
- Classification changes (HC ↔ Named between years) are flagged in the Summary sheet output

### Employee Overview (Summary Sheet)
| Label | Meaning |
|-------|---------|
| Previous year employees | Total unique employees in the previous year file |
| Current year employees | Total unique employees in the current year file |
| Common (matched) | Employees found in **both** years (same NRIC/email/name+DOB) |
| New employees | In current year but **not** in previous — re-enrolled as NEW in adjustment |
| Left employees | In previous year but **not** in current — cancelled in adjustment |

Formula: `New = Current − Common`, `Left = Previous − Common`

## Flex Report — Key Design Notes

### Plugin Architecture (one module per client company)
Each company is a self-contained adapter in `backend/flex_services/companies/<id>.py` exposing:

```python
COMPANY = {"id", "name", "status": "active", "files": [{"key", "label", "required"}], "notes"}

def run(files: dict, pay_month: str, outdir: str) -> dict   # -> outputs, log, errors, warnings, validation, stats
```

Onboarding a company: add the module, add its name to `ACTIVE_MODULES` in `flex_services/registry.py`,
and reduce `PLACEHOLDER_COUNT` by 1. **No platform or frontend changes are needed** — the UI renders each
company's upload slots, labels and required/optional flags from its own `COMPANY["files"]` spec, and the
result panel renders whichever stat keys the adapter returns.

Companies without logic appear as greyed-out "pending setup" slots (`PLACEHOLDER_COUNT`, default 17).

### Run Storage & Retention
- Outputs live in `processed/flex_runs/<run_id>/out/` with a `manifest.json` listing ordered filenames
- Downloads resolve through the manifest (not in-memory state), so they survive a worker restart
- Uploaded source files are deleted immediately after generation succeeds
- Run folders are purged 30 minutes after the run by `FlexRunReaper`; orphans are swept at startup
- `CleanupService` skips directories, so it never interferes with flex run folders

### STM Adapter Rules (verified against May 2026 manual outputs)
| Rule | Behaviour |
|------|-----------|
| Cost Centre | employee listing → leavers file → mapping master (fallback use raises a warning); none at all = hard error |
| Legal Entity Code | G0005086 → 2800; G0005088 / G0005089 → 0800 |
| Wage code | Optical → `Optical(T)`; Childcare / Health Screening → `HealthS/ChildC(NT)`; other medical → `N-Medi/Dental(NT)`. Unrecognised types are held with an error, never silently defaulted |
| Amount | `Payment Amt` rounded to 2dp per claim, summed per employee × wage code for the IT15 |
| Leavers | flagged Inactive; excluded from the IT15 only when the leavers file shows their claims are settled via final pay (exact subset match, earliest-incurred first) |
| SEA | Bangkok / Hanoi / Jakarta employees split into per-country reports (7900TH / 0800VN / 2800INDON) |

**Outputs**: Summary Reimbursement Report, IT15 payroll upload (written into the uploaded prior-month file so
formatting is preserved), refreshed `STM_Mapping_Master.xlsx`, SEA reports when applicable, plus a Validation
Exceptions Report when any check fires.

**Errors vs warnings**: errors hold the affected claim rows OUT of both output files (they go to the exception
report with a held-out total); warnings leave rows in the outputs but flag them on screen.

### IT15 Payroll Template (STM)
The template is used for **formatting only** — the generator clears any employee data in it before
writing the new rows, clones cell styling from row 20, sets the month of request in L3, and leaves the
payroll-user formula columns (M/P) intact.

- Save a **blank** template (header block, formulas, row-20 formatting, no employee data) at
  `backend/flex_services/companies/templates/stm_it15_template.xlsx` → the monthly run then needs only
  the **three data files**, and the template slot becomes optional
- Uploading a file always overrides the saved template (use when payroll changes the format)
- The required/optional flag is read at **import time**, so adding the saved template takes effect on restart
- Prior-month rows are cleared by scanning to `ws.max_row`, not to the first blank cell — a gap in the old
  data would otherwise leave last month's payments in the file submitted to payroll
- **Only rows whose EEID cell is numeric count as data.** The real template ends with a `Grand Total` row
  (row 1176, `=SUM(J20:J1174)`) that must survive — clearing to the last non-empty column-B cell would wipe it
- **Capacity is 1,155 payroll rows** (rows 20–1174). If a run produces more, it raises `FlexInputError` naming
  the footer row rather than overwriting the total. May 2026 used 1,154 — one row under the ceiling
- Helper columns P/Q/R (`=$B20`, `=$D20`, `=VLOOKUP(H20,'wt_notes (ref)'!…)`) are extended via openpyxl's
  `Translator` only for rows the template does not already pre-fill; existing cells are never touched
- The saved template is ~12 MB and carries ~950k validation formulas (incl. 93k array formulas out to column
  XFD in rows 1077–1173). A run takes ~30s, almost all of it the openpyxl round-trip. Verified that formulas,
  array formulas, all 5 sheets and the 9 data validations survive into the generated file

### Input File Expectations (STM)
- **Claims export**: `Staff ID`, `Employee Name`, `Reference No.`, `Entity`, `Claim Type`, `Payment Amt`, `Status`, `Incurred Date`
- **Employee listing**: `User ID`, `Cost Centre`, `Location Description`, `Last Day of Service`
- **Leavers file**: header on **row 2**, first 12 columns positional (EmpID, Name, LastDay, CostCentre, Company, HealthS, NMedi, Optical, Total, LastClaimMonth, Clawback, EmailDate)
- **IT15 template**: must contain sheet `SG1xPaymtTemplate`; data rows start at row 20, cols A–L are rewritten, cols M/P formulas are left intact
- Missing columns raise `FlexInputError` → HTTP 400 with the message shown verbatim; every other exception is a 500 with a logged traceback

### Data Integrity Rules (learned the hard way)
- **ID columns**: normalise with `_normalise_eeid()`, never `astype(str).str.zfill(6)`. One blank cell makes pandas type the column as float64, so plain zfill yields `'1001.0'` for every row and nothing matches
- **Payroll groupby uses `dropna=False`**: a NaN grouping key (e.g. blank Cost Centre) would otherwise silently drop the claim from the IT15 while it still counts in the summary report — the two outputs would not tie and the employee would not be paid
- **Rows are held out by source-row index**, not by Claim Reference — a claim with a blank reference must still be held
- **Blank Cost Centre in the listing counts as missing**, not as present
- **Leaver amounts that match no claim in their category** attempt the cross-category rescue first, then block that leaver's remaining claims from payroll (a wrong-category entry would otherwise be paid twice)

## Common Issues

1. **openpyxl Fill Error**: Create new `PatternFill()` objects instead of copying
2. **Sheet Name Invalid Chars**: Product names from merged cell headers may contain `&`, `:`, etc. (e.g. "Group Life & Medical"). Always strip with `re.sub(r'[\\/*?:\[\]&]', '', name)[:31]` — fixed in `renewal_processor.py:_generate_product_sheet`
3. **Memory on Large Files**: Use chunked processing for >10MB files
4. **Common = 0 (no matches)**: Check server logs for `Sample key:` lines to see which key strategy is being used. Most likely cause: NRIC/email column header not detected — check it matches one of the supported labels. Fallback is name+DOB which requires consistent formatting across both files.
5. **Wrong year assigned**: Ensure sheet tabs are named `"Employee Listing YYYY"` — the year comes from the sheet name, not cell content.
6. **NRIC wrongly mapped / DOB not detected (Berkshire-style files)**: Files using headers like `"EMPLOYEE STAFF ID NO."`, `"MEMBER NATIONAL ID NO."`, `"MEMBER DOB (DD-MM-YYYY)"` are handled by checking employee_id (`staff id`) **before** NRIC (`id no`) to prevent false substring matches, and matching DOB via `'dob' in header` rather than exact match. Hardcoded fallback column indices for employee_id/cost_centre/department were removed — fields are blank if their column is absent.

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/upload` | POST | Excel Transformer upload |
| `/upload/batch` | POST | Batch upload |
| `/download/<job_id>` | GET | Download result |
| `/status/<job_id>` | GET | Check job status |
| `/validate-clinic-file` | POST | Validate clinic file |
| `/match-clinics` | POST | Run clinic matching |
| `/download-match/<filename>` | GET | Download match result |
| `/api/mc/process` | POST | Mediacorp ADC process |
| `/api/mc/download/<filename>` | GET | Download ADC result |
| `/api/gp-panel/compare` | POST | GP Panel comparison |
| `/api/gp-panel/download/<filename>` | GET | Download GP Panel result |
| `/api/renewal/compare` | POST | Renewal comparison |
| `/api/renewal/download/<filename>` | GET | Download renewal result |
| `/api/flex/health` | GET | Flex Report health + adapter load errors |
| `/api/flex/companies` | GET | Company catalog with upload slot specs |
| `/api/flex/run/<company_id>` | POST | Run one company's monthly generation |
| `/api/flex/download/<run_id>/<index>` | GET | Download one output file of a run |
| `/api/flex/download-all/<run_id>` | GET | Download all outputs of a run as zip |

## Environment Variables

```
GOOGLE_MAPS_API_KEY=xxx        # For geocoding
UPLOAD_FOLDER=uploads
PROCESSED_FOLDER=processed
POSTAL_CODE_MASTER_FILE=path   # Optional override
```

## Testing

```bash
python test_backend.py         # Backend tests
```

## Deployment

- **Platform**: Azure Web App (`excel-transformer-rg`)
- **CI/CD**: GitHub Actions → `.github/workflows/main_excel-transformer-rg.yml`
- **Trigger**: Push to `main` branch or manual `workflow_dispatch`
- **Build**: Installs Python deps in venv, builds React frontend, copies static files to `backend/static/`, deploys `./backend` folder to Azure
- **Deploy action**: `azure/webapps-deploy@v3` with publish profile secret `AZUREAPPSERVICE_PUBLISHPROFILE_5B226EAFC9C04C9489E59C924562DD9E`
- **Live URL**: https://excel-transformer-rg.azurewebsites.net

### GitHub Actions Permissions Required
```yaml
permissions:
  contents: read
  id-token: write   # Required for azure/webapps-deploy@v3
```

### Deployment Troubleshooting
- **401 Unauthorized downloading action**: Usually transient GitHub issue — re-run the workflow. If persistent, check org action permissions at `GitHub Org → Settings → Actions → General`
- **Publish profile missing**: Ensure secret `AZUREAPPSERVICE_PUBLISHPROFILE_...` is set in repo secrets
- **Frontend not updating**: Confirm `REACT_APP_API_URL` env var points to the Azure URL, not localhost
