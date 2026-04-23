# EL Project - Employee Listing & Excel Tools

## Project Overview

Internal tool for processing healthcare/insurance data with five main features:
- **Excel Transformer**: Transforms IHP clinic data into standardized template format (phone+remarks, operating hours consolidation, postal code extraction)
- **Clinic Matcher**: Compares clinic lists to identify panel coverage gaps
- **Mediacorp ADC**: Processes employee/dependant data to generate ADC reports
- **GP Panel Comparison**: Compares GP panel changes between files
- **Renewal Comparison**: Compares renewal listing Excel files between two policy years and generates an Adjustment Breakdown report (Cancel & Re-enroll method)

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
│   └── renewal_services/      # Renewal comparison
│       └── renewal_processor.py
├── frontend/
│   └── src/
│       ├── App.js
│       └── components/
│           ├── FileUpload.js          # Excel Transformer UI
│           ├── ProcessingStatus.js    # Job status display
│           ├── ClinicMatcher.js
│           ├── MediacorpProcessor.js
│           ├── GPPanelComparison.js
│           └── RenewalComparison.js
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
