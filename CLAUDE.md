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

## Renewal Comparison — Key Design Notes

### Required Sheet Name
The uploaded Excel files **must** contain a sheet named exactly `"Employee Listing"`.

### Supported Products
| Abbr | Full Name | Type |
|------|-----------|------|
| GTL  | Group Term Life | Type 1 — Sum Insured × Rate |
| GDD  | Group Dread Disease | Type 1 — Sum Insured × Rate |
| GPA  | Group Personal Accident | Type 1 — Sum Insured × Rate |
| GDI  | Group Disability Income Benefit | Type 1 — Sum Insured × Rate |
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

### Year Detection (`_detect_year`)
- Scans only rows **before** the product_header_row (metadata area)
- Only accepts years 2000–2100
- This prevents employee DOBs and hire dates (which live in data rows) from being mistaken for the policy year
- Typical sources: `'YEAR : 2025'` text cell, `'Period Of Insurance : 01/01/2025'`, or a date value in a legend row

### Product Detection (`_detect_products`)
- Reads merged cells on product_header_row for section names
- Each section's `col_end` is **extended** to just before the next section's `col_start` — this captures premium/value columns that fall outside the merged range (common in some client formats)
- `admin_type_col` assigned as the nearest `'Type of Administration'` column to the LEFT of each section
- Type 1 (Sum Insured): detected when subheader contains `'sum insured'` or `'eligible sum insured'`
- Type 2 (Premium): detected when subheader contains `'premium'` (excluding GST and `w/` columns)
- Fallback: `PRODUCT_TYPE_HINTS` dict maps known product name patterns to their type when column headers are ambiguous

### Named vs Headcount
- Employees with `Type of Administration = Named` are excluded from the Headcount adjustment
- Classification changes (HC ↔ Named between years) are flagged in the Summary sheet output

## Common Issues

1. **openpyxl Fill Error**: Create new `PatternFill()` objects instead of copying
2. **Sheet Name Invalid Chars**: Product names from merged cell headers may contain `&`, `:`, etc. (e.g. "Group Life & Medical"). Always strip with `re.sub(r'[\\/*?:\[\]&]', '', name)[:31]` — fixed in `renewal_processor.py:_generate_product_sheet`
3. **Memory on Large Files**: Use chunked processing for >10MB files
4. **Wrong Year Detected**: Year detection only scans rows before the product header — if the year is missing from the metadata rows, add it as text (e.g. `YEAR : 2025`) anywhere in rows 1 to product_header_row-1

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
