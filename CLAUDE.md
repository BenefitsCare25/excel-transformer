# EL Project - Employee Listing & Excel Tools

## Project Overview

Internal tool for processing healthcare/insurance data with four main features:
- **Excel Transformer**: Transforms IHP clinic data into standardized template format (phone+remarks, operating hours consolidation, postal code extraction)
- **Clinic Matcher**: Compares clinic lists to identify panel coverage gaps
- **Mediacorp ADC**: Processes employee/dependant data to generate ADC reports
- **GP Panel Comparison**: Compares GP panel changes between files

## Tech Stack

- **Backend**: Python Flask (app.py ~2000+ lines)
- **Frontend**: React with Tailwind CSS
- **Data**: Excel processing with pandas, openpyxl
- **APIs**: Google Maps for geocoding

## Project Structure

```
EL/
├── backend/
│   ├── app.py                 # Main Flask app (routes, clinic matching)
│   ├── cleanup_service.py     # Auto-cleanup for uploads
│   ├── mc_services/           # Mediacorp ADC processing
│   │   ├── el_processor.py    # Employee Listing processor
│   │   ├── dl_processor.py    # Dependant Listing processor
│   │   ├── ixchange_generator.py
│   │   └── validators.py
│   └── gp_panel_services/     # GP Panel comparison
│       └── panel_processor.py
├── frontend/
│   └── src/
│       ├── App.js
│       └── components/
│           ├── FileUpload.js          # Excel Transformer UI
│           ├── ProcessingStatus.js    # Job status display
│           ├── ClinicMatcher.js
│           ├── MediacorpProcessor.js
│           └── GPPanelComparison.js
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
- Sheet names max 31 chars, no special characters: `[ ] : * ? / \`

### Data Validation
- Singapore postal codes: 6 digits extracted via regex
- Government hospitals/polyclinics filtered from clinic matching
- Phone numbers combined with remarks in format: `{phone} - {remarks}`

### File Handling
- Auto-cleanup after 15 minutes (cleanup_service.py)
- Job IDs via UUID for tracking uploads
- Processed files stored in `processed/` folder

## Common Issues

1. **openpyxl Fill Error**: Create new `PatternFill()` objects instead of copying
2. **Sheet Name Too Long**: Truncate to 31 chars, remove invalid chars
3. **Memory on Large Files**: Use chunked processing for >10MB files

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/upload` | POST | Excel Transformer upload |
| `/download/{job_id}` | GET | Download result |
| `/status/{job_id}` | GET | Check job status |
| `/clinic-matcher/upload` | POST | Clinic Matcher upload |
| `/mc/upload` | POST | Mediacorp ADC upload |
| `/gp-panel/compare` | POST | GP Panel comparison |

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
