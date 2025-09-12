# Excel Template Transformer

A web application that automatically transforms Excel files to match a desired template format. Built specifically for converting IHP clinic data files into a standardized template.

## Features

- **Drag & Drop File Upload**: Easy file upload interface with validation
- **Automatic Transformations**:
  - Combines telephone & remarks fields
  - Consolidates operating hours (AM/PM/Night → standardized format)  
  - Extracts postal codes from Singapore addresses
  - Maps clinic data to template format
- **Real-time Processing**: Live status updates during transformation
- **Error Handling**: Comprehensive error reporting and recovery
- **Download Results**: One-click download of transformed files

## Project Structure

```
excel-transformer/
├── backend/                 # Flask API server
│   ├── app.py              # Main Flask application
│   ├── uploads/            # Temporary uploaded files
│   └── processed/          # Transformed output files
├── frontend/               # React web interface
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API service layer
│   │   └── App.js         # Main application
│   └── package.json
└── requirements.txt        # Python dependencies
```

## Setup Instructions

### Backend Setup

1. **Install Python dependencies**:
   ```bash
   cd excel-transformer
   pip install -r requirements.txt
   ```

2. **Start the Flask server**:
   ```bash
   cd backend
   python app.py
   ```
   
   Server will run on `http://localhost:5000`

### Frontend Setup

1. **Install Node.js dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start the React development server**:
   ```bash
   npm start
   ```
   
   Application will open at `http://localhost:3000`

## Usage

1. **Upload File**: Drag and drop your Excel file or click to browse
2. **Processing**: The system automatically detects headers and transforms data
3. **Download**: Click the download button to get your transformed template file

## Data Transformations

### Source File Format (To be uploaded.xlsx)
- Header row detection (skips intro text)
- 23 columns including clinic details and split operating hours
- Individual fields: TEL NO., REMARKS, MON-FRI (AM), (PM), (NIGHT), etc.

### Target Template Format (Follow this template.xlsx) 
- 19 standardized columns
- Combined fields: PhoneNumber, MonToFri, Saturday, Sunday, PublicHoliday
- Extracted postal codes from addresses

### Specific Transformations

1. **Phone & Remarks**: `TEL NO. + " - " + REMARKS → PhoneNumber`
2. **Operating Hours**: `AM/PM/NIGHT → "AM/PM/NIGHT"` format
3. **Postal Code**: Extract 6-digit codes from `SINGAPORE ######` addresses
4. **Field Mapping**:
   - `IHP CLINIC ID → Code`
   - `CLINIC NAME → Name`
   - `REGION → Zone`
   - `AREA → Area`
   - `ADDRESS → Address1`

## API Endpoints

- `POST /upload` - Upload and transform Excel file
- `GET /download/{job_id}` - Download transformed file
- `GET /status/{job_id}` - Check processing status  
- `GET /health` - Backend health check

## Technology Stack

- **Backend**: Python, Flask, pandas, openpyxl
- **Frontend**: React, Tailwind CSS, react-dropzone, axios
- **File Processing**: pandas for Excel I/O and data transformation
- **UI/UX**: Modern responsive design with drag-and-drop interface

## Error Handling

- File format validation (Excel files only)
- Automatic header detection for various layouts
- Graceful error messages with technical details
- Backend health monitoring
- Processing status tracking

## Development Notes

- Files are temporarily stored and automatically cleaned up
- Large file support with progress indicators
- Cross-origin requests enabled for development
- Real-time status updates during processing