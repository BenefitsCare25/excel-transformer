# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Excel Template Transformer is a full-stack web application that transforms IHP clinic Excel files into standardized template format. The application consists of a Flask backend API and React frontend with drag-and-drop file upload.

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
The application performs specific data transformations for IHP clinic data:

1. **Phone & Remarks Combination**: `TEL NO. + " - " + REMARKS → PhoneNumber`
2. **Operating Hours Consolidation**: `AM/PM/NIGHT → "AM/PM/NIGHT"` format
3. **Postal Code Extraction**: Extract 6-digit codes from Singapore addresses
4. **Field Mapping**: IHP CLINIC ID → Code, CLINIC NAME → Name, etc.
5. **Geocoding**: Postal code lookup with Google Maps API fallback

### Data Flow
1. Frontend uploads Excel file via `/upload` endpoint
2. Backend detects header row automatically (handles various layouts)
3. ExcelTransformer processes data with geocoding
4. Transformed file saved to processed/ directory
5. Frontend downloads result via `/download/{job_id}` endpoint

## API Endpoints

- `GET /health` - Backend health check with geocoding service status
- `POST /upload` - Upload and transform Excel file
- `GET /download/{job_id}` - Download transformed file
- `GET /status/{job_id}` - Check processing status
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
```
REACT_APP_API_URL=http://localhost:5000
REACT_APP_UPLOAD_TIMEOUT=300000
```

## Testing

- **Backend**: Run `python test_backend.py` to test all endpoints with sample data
- **Frontend**: Uses react-scripts test runner
- **Integration**: Backend test creates sample Excel file and tests full upload/download flow

## Key Dependencies

### Backend
- Flask 3.0.0 (web framework)
- pandas 2.3.2 (Excel processing)
- openpyxl 3.1.5 (Excel file I/O)
- googlemaps 4.10.0 (geocoding API)
- geopy 2.4.1 (geocoding services)

### Frontend
- React 18.2.0
- react-dropzone 14.2.3 (file upload)
- axios 1.6.0 (API calls)
- Tailwind CSS 3.3.0 (styling)

## Development Notes

- Backend runs on port 5000, frontend on port 3000
- CORS enabled for cross-origin development
- Automatic header detection handles various Excel layouts
- Geocoding uses postal code lookup first, Google Maps API as fallback
- Files are automatically cleaned up after processing
- Real-time health monitoring shows backend status in frontend