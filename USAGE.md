# Excel Template Transformer - Usage Guide

## Quick Start

### 1. Start the Application

#### Option A: Using the Batch File (Windows)
```bash
# Double-click or run from command line
start.bat
```

#### Option B: Manual Startup
```bash
# Terminal 1: Start Backend
cd excel-transformer
pip install -r requirements.txt
cd backend
python app.py

# Terminal 2: Start Frontend
cd excel-transformer/frontend
npm install
npm start
```

### 2. Access the Application
- Open your browser to `http://localhost:3000`
- The backend API runs on `http://localhost:5000`

### 3. Transform Your Excel File
1. **Upload**: Drag and drop your Excel file (like "To be uploaded.xlsx")
2. **Wait**: Processing typically takes 5-30 seconds depending on file size
3. **Download**: Click the download button to get your transformed file

## File Requirements

### Hospital Bill OCR / Vision

Open **OCR / Vision** and choose up to five scanned hospital bill PDFs. Each file can
be up to 25 MB and 40 pages. The server blanks NRIC and FIN-like identifiers in
the page images before reading bill data. Review the extracted rows, edit any OCR
mistakes, then download one Excel workbook and each redacted PDF. The workbook
uses the eight columns in the supplied billing template; cash payable is an Excel
formula. Redacted PDFs are eligible for cleanup after 15 minutes. The original
upload is not saved.

Check every redacted page before sharing it. OCR can miss an identifier on an
unusual or low-quality scan, and patient names remain visible.

### LGI Flex Reports

In **Flex Report**, select **Lion Global Investors (LGI)** and upload the employee
claims export, built-in employee listing and utilisation summary. The claims' Paid
Date sets the payment month. Download the unencrypted `.xlsx` Claims Detail, Claims
Summary and Utilization Report, individually or as a ZIP.

Use a utilisation export for the reporting month: cumulative claims and balances
come from that export. Review the run's notes before using the files. LGI's field
mappings and validation rules are documented in
[the company profile guide](backend/flex_services/companies/lgi/README.md).

### Supported Input Formats
- Excel files (.xlsx, .xls)
- Files with header rows similar to the IHP clinic data structure
- Files containing clinic information with address details

### Automatic Regional Sheet Consolidation
- Workbooks with two or more compatible geographic tabs are combined automatically.
- Supported tab labels include North, North-East, Central, East, West, Singapore, and Malaysia, with common GP/panel/list suffixes.
- Each tab may place its header on a different row; the transformer locates and validates every header before merging.
- Regional rows are split into separate Singapore and Malaysia output workbooks; each workbook contains one worksheet named `List` and preserves the source workbook's sheet and row order.
- Possible duplicate clinic/address rows are retained and reported for review rather than silently removed.
- If any detected regional tab has incompatible or missing headers, processing stops with a specific validation error so no region is omitted.

### Expected Data Structure
Your input file should have columns similar to:
- S/N, IHP CLINIC ID, REGION, AREA, CLINIC NAME
- ADDRESS (with Singapore postal codes)
- TEL NO., REMARKS
- Operating hours columns (MON-FRI AM/PM/NIGHT, SAT AM/PM/NIGHT, etc.)

## Transformation Details

### What Gets Transformed

1. **Phone & Remarks Combination**
   - Input: `TEL NO.` = "12345678", `REMARKS` = "Call before visit"  
   - Output: `PhoneNumber` = "12345678 - Call before visit"

2. **Operating Hours Consolidation**
   - Input: `MON-FRI (AM)` = "0900-1200", `MON-FRI (PM)` = "1400-1700", `MON-FRI (NIGHT)` = "CLOSED"
   - Output: `MonToFri` = "0900-1200/1400-1700/CLOSED"

3. **Postal Code Extraction**
   - Input: `ADDRESS` = "BLK 123 SAMPLE STREET #01-01 SINGAPORE 123456"
   - Output: `PostalCode` = "123456"

4. **Field Mapping**
   ```
   IHP CLINIC ID → Code
   CLINIC NAME → Name
   REGION → Zone
   AREA → Area
   ADDRESS → Address1
   ```

### Output Format
The transformed file follows this standard template structure:
- Code, Name, Zone, Area, Specialty, Doctor
- Address1, Address2, Address3, PostalCode, Country
- PhoneNumber, MonToFri, Saturday, Sunday, PublicHoliday
- Latitude, Longitude, GoogleMapURL

## Troubleshooting

### Backend Issues
```bash
# Check if backend is running
curl http://localhost:5000/health

# Common issues:
# 1. Port 5000 already in use
# 2. Python dependencies missing: pip install -r requirements.txt
# 3. File path issues: Use absolute paths for uploads
```

### Frontend Issues
```bash
# Check if frontend is running
# Should open automatically at http://localhost:3000

# Common issues:
# 1. Node.js not installed
# 2. Port 3000 in use
# 3. Dependencies missing: npm install
```

### File Processing Issues
- **File not recognized**: Ensure Excel format (.xlsx/.xls)
- **Wrong headers detected**: File structure might be different from expected IHP format
- **Postal codes not extracted**: Addresses must contain "SINGAPORE" followed by 6 digits
- **Empty results**: Check that input file has actual data rows below headers

## Advanced Usage

### API Endpoints
```bash
# Health check
GET http://localhost:5000/health

# Upload file
POST http://localhost:5000/upload
Content-Type: multipart/form-data
Body: file=@your_file.xlsx

# Download result
GET http://localhost:5000/download/{job_id}

# Check status
GET http://localhost:5000/status/{job_id}
```

### Customization
To modify transformations, edit `backend/app.py`:
- Update field mappings in `transform_excel()` method
- Modify regex patterns in `extract_postal_code()` 
- Change operating hours format in `combine_operating_hours()`

## File Structure
```
excel-transformer/
├── backend/
│   ├── app.py              # Main Flask application
│   ├── uploads/            # Temporary input files
│   └── processed/          # Output files
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API communication
│   │   └── App.js         # Main React app
│   ├── package.json
│   └── public/
├── requirements.txt        # Python dependencies
├── start.bat              # Windows startup script
└── README.md
```

## Performance Notes
- **File Size**: Handles files up to 10MB efficiently
- **Processing Time**: ~1 second per 100 records
- **Memory Usage**: ~50MB for typical clinic datasets
- **Concurrent Users**: Supports multiple simultaneous uploads
