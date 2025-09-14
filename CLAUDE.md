# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Excel Template Transformer is a full-stack web application that transforms various clinic Excel files (IHP, SP, TCM) into standardized template format. The application consists of a Flask backend API and React frontend with drag-and-drop file upload.

## Development Commands

### Backend (Flask)
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
cd backend
python app.py

# Test backend functionality
python test_backend.py
```

### Frontend (React)
```bash
# Install dependencies
cd frontend
npm install

# Run development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

### Quick Start (Windows)
```bash
# Start both servers simultaneously
start.bat
```

## Architecture

### Backend Structure (`backend/`)
- **app.py**: Main Flask application with API endpoints
- **ExcelTransformer**: Core class handling Excel file transformations
- **GeocodingService**: Handles postal code lookup and Google Maps API integration
- **uploads/**: Temporary storage for uploaded files
- **processed/**: Output directory for transformed files

### Frontend Structure (`frontend/src/`)
- **App.js**: Main React application with health monitoring
- **components/FileUpload.js**: Drag-and-drop file upload component
- **components/ProcessingStatus.js**: Status display and download handling
- **services/api.js**: API communication layer

### Key Transformations
The application performs specific data transformations for various clinic data formats:

1. **Phone & Remarks Combination**: `TEL NO. + " - " + REMARKS → PhoneNumber`
2. **Operating Hours Consolidation**:
   - Complex format: `AM/PM/NIGHT → "AM/PM/NIGHT"` (GP/TCM sheets)
   - Simple format: Clean hours without suffixes (SP clinic sheets)
3. **Postal Code Extraction**:
   - Extract 6-digit codes from Singapore addresses (handles "S" prefix)
   - SP format: Extract from Address4 column ("SINGAPORE 247909" → "247909")
4. **Field Mapping**: Dynamic mapping for different formats (IHP, SP, TCM)
5. **Address Construction**:
   - Standard: Single address field
   - SP clinic: Separate Address1/Address2/Address3 fields
   - TCM: Component-based address construction
6. **Geocoding**: Postal code lookup with Google Maps API fallback
7. **Multi-Sheet Support**: Processes GP, TCM, SP clinic, and specialty sheets
8. **Empty Row Filtering**: Automatically removes invalid/empty rows from processing
9. **SP Clinic Features**: Specialty field, doctor names, multi-part addresses

### Data Flow
1. Frontend uploads Excel file via `/upload` endpoint
2. Backend detects header row automatically (handles various layouts including TCM and SP clinic)
3. ExcelTransformer processes each sheet with automatic empty row filtering
4. Applies sheet-specific column mappings (GP vs TCM vs SP clinic vs specialty formats)
5. Geocoding applied with postal code lookup and API fallback
6. Transformed files saved to processed/ directory (one per sheet)
7. Frontend downloads individual files or ZIP archive via `/download/{job_id}` endpoints

## API Endpoints

- `GET /health` - Backend health check with geocoding service status
- `POST /upload` - Upload and transform Excel file (multi-sheet support)
- `GET /download/{job_id}` - Download all files as ZIP archive
- `GET /download/{job_id}/{filename}` - Download specific transformed file
- `GET /status/{job_id}` - Check processing status with per-file details
- `POST /geocode` - Standalone geocoding endpoint for testing

## Environment Configuration

### Backend (.env)
```
GOOGLE_MAPS_API_KEY=your_api_key_here
POSTAL_CODE_MASTER_FILE=path/to/postal_code_master.xlsx
UPLOAD_FOLDER=uploads
PROCESSED_FOLDER=processed
FLASK_ENV=production
PORT=5000
```

### Frontend
Development uses `.env.development`, production uses `.env.production`:
```
# Development
REACT_APP_API_URL=http://localhost:5000

# Production
REACT_APP_API_URL=https://excel-transformer-backend.onrender.com
```

## Testing

- **Backend**: Run `python test_backend.py` from project root to test all endpoints with sample data
- **Frontend**: Uses react-scripts test runner (`npm test` in frontend directory)
- **Integration**: Backend test creates sample Excel file and tests full upload/download flow

## Production Deployment

### Backend (Gunicorn)
```bash
cd backend
gunicorn --config gunicorn.conf.py app:app
```
- Configured for port 10000 in production (configurable via PORT env var)
- Uses single worker process with 300s timeout for large file processing
- Process name: 'excel-transformer'

### Docker/Container Setup
The gunicorn configuration supports containerized deployment with environment-based port configuration.

## Key Dependencies

### Backend
- Flask 3.0.0 (web framework)
- pandas 2.3.2 (Excel processing)
- openpyxl 3.1.5 (Excel file I/O)
- googlemaps 4.10.0 (geocoding API)
- geopy 2.4.1 (geocoding services)
- flask-cors 4.0.0 (cross-origin requests)
- gunicorn 21.2.0 (production WSGI server)
- python-dotenv 1.0.0 (environment variable loading)

### Frontend
- React 18.2.0
- react-dropzone 14.2.3 (file upload)
- axios 1.6.0 (API calls)
- Tailwind CSS 3.3.0 (styling)
- react-scripts 5.0.1 (build tooling)

## Development Notes

- Backend runs on port 5000 (dev) / 10000 (prod), frontend on port 3000
- CORS enabled for cross-origin development
- Automatic header detection handles various Excel layouts (GP, TCM, SP clinic, specialty formats)
- Enhanced column mapping with fuzzy matching and format-specific patterns
- Empty row filtering ensures accurate record counts by removing null/empty rows
- Geocoding uses postal code lookup first, Google Maps API as fallback
- Handles Singapore postal codes with "S" prefix (e.g., "S238869" → "238869")
- Address construction from separate components for TCM sheets
- Multi-sheet processing with individual file outputs
- Files are automatically cleaned up after processing
- Real-time health monitoring shows backend status in frontend
- Environment variables loaded from `.env` files in respective directories
- Production deployment uses Render.com backend URL (configured in `.env.production`)

## Sheet Format Support

### GP/Standard Clinic Sheets
- Column headers: CLINIC CODE, CLINIC, REGION, AREA, ADDRESS, etc.
- Single address field with postal code extraction
- Standard operating hours format (AM/PM/NIGHT structure)

### TCM Sheets
- Column headers: MASTER CODE, PHYSICIAN - IN - CHARGE, CLINIC, BLK & ROAD NAME, etc.
- Separate address components (BLK & ROAD NAME + UNIT & BUILDING NAME)
- Physician/doctor name extraction
- Enhanced postal code handling
- Automatic empty row filtering for clean data processing

### SP Clinic Sheets (AIA Parkway Shenton Panel)
- Column headers: S/N, SPECIALTY, SP CODE, DOCTOR, CLINIC NAME, ADDRESS1-4, TEL NO, MON-FRI, SAT, SUN, PH, etc.
- **Header Detection**: Headers located at row 6 (after metadata rows 0-5)
- **Multi-Part Addresses**:
  - Address1: Street address ("19 TANGLIN ROAD")
  - Address2: Unit number ("#05-45")
  - Address3: Building name ("TANGLIN SHOPPING CENTRE")
  - Address4: Postal code format ("SINGAPORE 247909")
- **Simple Operating Hours**: Clean format without /CLOSED/CLOSED suffixes
- **Specialty Field**: Medical specialty classification
- **Doctor Names**: Individual practitioner identification
- **Processing**: All 1,500+ records with 100% postal code extraction success