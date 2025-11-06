from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import os
import sys
import uuid
import re
from datetime import datetime
import traceback
import googlemaps
from geopy.geocoders import GoogleV3
from dotenv import load_dotenv
from functools import lru_cache
import logging
import threading
import time
try:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    CONCURRENT_SUPPORT = True
except ImportError:
    # Fallback for environments without concurrent.futures
    CONCURRENT_SUPPORT = False
    import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
PROCESSED_FOLDER = os.getenv('PROCESSED_FOLDER', 'processed')

# Postal code master file paths (in order of preference)
POSTAL_CODE_PATHS = [
    os.getenv('POSTAL_CODE_MASTER_FILE'),  # Environment variable (highest priority)
    os.path.join('..', 'data', 'postal_code_master.xlsx'),  # Project data folder
    os.getenv('POSTAL_CODE_FALLBACK_PATH'),  # Configurable fallback path
    'postal_code_master.xlsx',  # Current directory
]

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

class GeocodingService:
    def __init__(self, use_google_api=True):
        self.use_google_api = use_google_api
        self.google_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        self._initialize_google_maps_clients()
        self.postal_code_lookup = self._load_postal_code_lookup()
        self.geocode_stats = {'postal_matches': 0, 'api_calls': 0, 'failures': 0}
    
    def _initialize_google_maps_clients(self):
        """Initialize Google Maps API clients with status logging"""
        if not self.use_google_api:
            logger.info("Google Maps API: DISABLED BY USER - Using postal code lookup only")
            self.gmaps = None
            self.geolocator = None
            return

        if not self.google_api_key:
            logger.info("Google Maps API: NOT CONFIGURED - Using postal code lookup only")
            self.gmaps = None
            self.geolocator = None
            return

        try:
            self.gmaps = googlemaps.Client(key=self.google_api_key)
            self.geolocator = GoogleV3(api_key=self.google_api_key)
            logger.info("Google Maps API: CONFIGURED AND ENABLED")
        except Exception as e:
            logger.error(f"Google Maps API: FAILED - {e}")
            self.gmaps = None
            self.geolocator = None
    
    
    @lru_cache(maxsize=1)
    def _load_postal_code_lookup(self):
        """Load postal code lookup table from master file - deployment safe"""
        try:
            # Quick check - if we're in a deployment environment (no local files), skip immediately
            is_deployment = os.getenv('RENDER') or os.getenv('VERCEL') or os.getenv('HEROKU')
            if is_deployment:
                logger.info("Postal Code Lookup: DEPLOYMENT MODE - Using Google Maps API only")
                return {}

            # Try each path in order of preference with fast fail
            master_file_path = None
            for path in POSTAL_CODE_PATHS:
                if path and os.path.exists(path):
                    # Quick file size check to avoid loading huge files
                    try:
                        file_size = os.path.getsize(path)
                        if file_size > 50 * 1024 * 1024:  # Skip files > 50MB
                            logger.warning(f"Postal Code Lookup: File too large ({file_size/1024/1024:.1f}MB), skipping: {path}")
                            continue
                        master_file_path = path
                        break
                    except OSError:
                        continue

            if not master_file_path:
                logger.warning("Postal Code Lookup: NO SUITABLE FILE FOUND - Using Google Maps API only")
                return {}

            logger.info(f"Loading postal code lookup from: {master_file_path}")

            # Load with chunking for better memory management
            df = pd.read_excel(master_file_path, dtype={'PostalCode': str})

            # Create dictionary for fast lookup: {postal_code: (lat, lng)}
            lookup = {}
            row_count = 0
            for _, row in df.iterrows():
                row_count += 1
                if row_count % 1000 == 0:  # Progress indicator
                    logger.debug(f"Processing row {row_count}...")

                # Handle postal code formatting
                postal_code_raw = row.get('PostalCode')
                if pd.notna(postal_code_raw) and postal_code_raw:
                    try:
                        # Ensure 6-digit format
                        if isinstance(postal_code_raw, str):
                            postal_code = postal_code_raw.strip().zfill(6)
                        else:
                            postal_code = f"{int(float(postal_code_raw)):06d}"
                    except (ValueError, TypeError):
                        continue
                else:
                    continue

                lat = row.get('Latitude')
                lng = row.get('Longitude')
                if pd.notna(lat) and pd.notna(lng):
                    try:
                        lookup[postal_code] = (float(lat), float(lng))
                    except (ValueError, TypeError):
                        continue

            logger.info(f"Postal Code Lookup: {len(lookup)} Singapore postal codes loaded successfully")
            return lookup

        except Exception as e:
            logger.error(f"Postal Code Lookup: FAILED - {e}")
            logger.warning("Continuing without postal code lookup, using Google Maps API only")
            return {}
    
    def geocode_by_postal_code(self, postal_code):
        """Get coordinates by postal code lookup"""
        if not postal_code or str(postal_code).strip() in ('None', '', 'nan'):
            return None, None
        
        try:
            # Normalize postal code to 6-digit format with leading zeros
            postal_code_str = str(postal_code).strip()
            # Handle Singapore postal codes with 'S' prefix
            if postal_code_str.upper().startswith('S') and len(postal_code_str) > 1:
                postal_code_str = postal_code_str[1:]  # Remove 'S' prefix
            postal_code_normalized = f"{int(float(postal_code_str)):06d}"
            
            if postal_code_normalized in self.postal_code_lookup:
                self.geocode_stats['postal_matches'] += 1
                lat, lng = self.postal_code_lookup[postal_code_normalized]
                return lat, lng
        except (ValueError, TypeError, AttributeError) as e:
            # Log invalid postal code format for debugging
            logger.warning(f"Invalid postal code format: {postal_code} - {e}")
        
        return None, None
    
    def geocode_by_address(self, address):
        """Get coordinates by Google Maps API using full address"""
        if not address or str(address).strip() in ('', 'None', 'nan') or not self.geolocator:
            return None, None

        try:
            self.geocode_stats['api_calls'] += 1

            # Clean address and detect country
            address_str = str(address).strip()
            address_lower = address_str.lower()

            # Check if address already contains country information
            has_singapore = 'singapore' in address_lower
            has_malaysia = 'malaysia' in address_lower

            # If no country specified, try to detect from context
            if not has_singapore and not has_malaysia:
                # Check for Malaysian states/regions in address
                malaysian_indicators = ['johor', 'kuala lumpur', 'selangor', 'penang', 'perak', 'kedah', 'kelantan', 'terengganu', 'pahang', 'negeri sembilan', 'melaka', 'sabah', 'sarawak', 'perlis', 'putrajaya', 'labuan']
                if any(indicator in address_lower for indicator in malaysian_indicators):
                    address_str += ', Malaysia'
                else:
                    # Default to Singapore for addresses without clear country indicators
                    address_str += ', Singapore'

            location = self.geolocator.geocode(address_str, timeout=10)

            if location:
                return location.latitude, location.longitude
            else:
                self.geocode_stats['failures'] += 1
                return None, None

        except Exception as e:
            self.geocode_stats['failures'] += 1
            logger.warning(f"Address geocoding failed for '{address}': {e}")
            return None, None
    
    def geocode(self, postal_code, address):
        """Main geocoding method: try postal code first, then address (if enabled)"""
        # Try postal code lookup first
        lat, lng = self.geocode_by_postal_code(postal_code)
        if lat is not None and lng is not None:
            return lat, lng, 'postal_code'

        # Fallback to address geocoding only if use_google_api is enabled
        if self.use_google_api:
            lat, lng = self.geocode_by_address(address)
            if lat is not None and lng is not None:
                return lat, lng, 'address'

        return None, None, 'failed'
    
    def get_stats(self):
        """Get geocoding statistics"""
        return self.geocode_stats.copy()

class ExcelTransformer:
    @staticmethod
    def detect_alliance_tokio_format(ws):
        """
        Detect Alliance-Tokio Marine format by checking:
        1. Merged cell K1:N1 (operating hours disclaimer)
        2. Row 1 has 'POSTAL\\nCODE' or 'POSTAL CODE' header
        3. Row 2 has 'MON - FRI' sub-header
        4. ZONE and ESTATE columns present
        """
        try:
            # Check for merged cells pattern
            has_operating_hours_merge = False
            for merged_range in ws.merged_cells.ranges:
                range_str = str(merged_range)
                if 'K1:N1' in range_str or 'K1' in range_str:
                    has_operating_hours_merge = True
                    break

            # Check row 1 headers
            row1 = [cell.value for cell in ws[1]]
            has_postal_code = any(
                'POSTAL' in str(h).upper() for h in row1 if h
            )
            has_zone_estate = (
                any('ZONE' in str(h).upper() for h in row1 if h) and
                any('ESTATE' in str(h).upper() for h in row1 if h)
            )

            # Check row 2 sub-headers
            row2 = [cell.value for cell in ws[2]]
            has_mon_fri_subheader = any('MON - FRI' in str(h) for h in row2 if h)

            is_alliance_tokio = (
                has_operating_hours_merge and
                has_postal_code and
                has_zone_estate and
                has_mon_fri_subheader
            )

            if is_alliance_tokio:
                logger.info("Detected Alliance-Tokio Marine format (multi-level headers with merged cells)")

            return is_alliance_tokio

        except Exception as e:
            logger.debug(f"Alliance-Tokio format detection failed: {e}")
            return False

    @staticmethod
    def unmerge_and_fill_cells(ws):
        """
        Unmerge all cells and fill merged cell values into all cells in the range.
        This ensures row-by-row reading works correctly.
        """
        import openpyxl

        # Get all merged ranges (need to copy list as we'll modify it)
        merged_ranges = list(ws.merged_cells.ranges)

        logger.info(f"Unmerging {len(merged_ranges)} merged cell ranges")

        for merged_range in merged_ranges:
            # Get the value from top-left cell
            top_left = merged_range.start_cell
            merge_value = top_left.value

            # Unmerge the range
            ws.unmerge_cells(str(merged_range))

            # Fill the value into all cells that were part of the merge
            for row in range(merged_range.min_row, merged_range.max_row + 1):
                for col in range(merged_range.min_col, merged_range.max_col + 1):
                    ws.cell(row=row, column=col).value = merge_value

        return ws

    @staticmethod
    def get_alliance_tokio_headers(ws):
        """
        Reconstruct headers from unmerged rows 1-2.
        For most columns: use row 1 value
        For columns K-N: use row 2 values (MON-FRI, SAT, SUN, PUBLIC HOLIDAYS)
        """
        headers = []

        for col_idx in range(1, 16):  # Columns A-O (1-15)
            if col_idx <= 10 or col_idx == 15:  # Columns A-J and O
                # Use row 1 value, clean it
                value = ws.cell(row=1, column=col_idx).value
                if value:
                    value = str(value).replace('\n', ' ').replace('\r', ' ').strip()
                headers.append(value)
            else:  # Columns K-N (11-14)
                # Use row 2 sub-headers for operating hours
                value = ws.cell(row=2, column=col_idx).value
                if value:
                    value = str(value).strip()
                headers.append(value)

        logger.debug(f"Alliance-Tokio headers: {headers}")
        return headers

    @staticmethod
    def convert_alliance_hours_to_standard(mon_fri, sat, sun, ph):
        """
        Convert Alliance-Tokio operating hours format to standard AM/PM/NIGHT format.

        Alliance format: 4 columns with detailed hours or "Closed"
        Standard format: "AM hours/PM hours/NIGHT hours" or "CLOSED/CLOSED/CLOSED"

        Strategy: Extract time ranges and categorize into AM/PM/NIGHT slots
        """
        def parse_time_slots(hours_str):
            """Parse hours string into AM/PM/NIGHT slots"""
            if pd.isna(hours_str) or str(hours_str).strip().upper() in ('CLOSED', '', 'NAN'):
                return 'CLOSED', 'CLOSED', 'CLOSED'

            hours_str = str(hours_str).strip()

            # Extract all time ranges
            import re
            time_pattern = r'(\d{1,2}[:.]\d{2}\s*(?:am|pm))\s*-\s*(\d{1,2}[:.]\d{2}\s*(?:am|pm))'
            matches = re.findall(time_pattern, hours_str, re.IGNORECASE)

            if not matches:
                # No parseable times, return as-is for AM slot
                return hours_str, 'CLOSED', 'CLOSED'

            am_slots = []
            pm_slots = []
            night_slots = []

            for start, end in matches:
                # Parse start time
                start_clean = start.lower().replace('.', ':')

                # Categorize by start time
                if 'am' in start_clean or ('12:' in start_clean and 'pm' in start_clean):
                    # Morning slot (before noon)
                    am_slots.append(f"{start} - {end}")
                elif '6' in start_clean.split(':')[0] and 'pm' in start_clean:
                    # Evening/Night slot (6pm or later)
                    night_slots.append(f"{start} - {end}")
                else:
                    # Afternoon slot
                    pm_slots.append(f"{start} - {end}")

            # Combine slots
            am_result = ', '.join(am_slots) if am_slots else 'CLOSED'
            pm_result = ', '.join(pm_slots) if pm_slots else 'CLOSED'
            night_result = ', '.join(night_slots) if night_slots else 'CLOSED'

            return am_result, pm_result, night_result

        # Parse each day type
        mon_fri_am, mon_fri_pm, mon_fri_night = parse_time_slots(mon_fri)
        sat_am, sat_pm, sat_night = parse_time_slots(sat)
        sun_am, sun_pm, sun_night = parse_time_slots(sun)
        ph_am, ph_pm, ph_night = parse_time_slots(ph)

        # Build standard format strings
        weekday = f"{mon_fri_am}/{mon_fri_pm}/{mon_fri_night}"
        saturday = f"{sat_am}/{sat_pm}/{sat_night}"
        sunday = f"{sun_am}/{sun_pm}/{sun_night}"
        holiday = f"{ph_am}/{ph_pm}/{ph_night}"

        return weekday, saturday, sunday, holiday

    @staticmethod
    def safe_read_excel(file_path, sheet_name=None, **kwargs):
        """Safely read Excel file with fallback for corrupted XML metadata"""
        try:
            # First attempt: Normal read
            return pd.read_excel(file_path, sheet_name=sheet_name, **kwargs)
        except ValueError as e:
            if "could not assign names" in str(e) or "invalid XML" in str(e):
                # Openpyxl XML corruption - monkey patch the problematic function
                logger.warning(f"Excel file has corrupted metadata (print titles/names), using patched openpyxl")
                import openpyxl
                from openpyxl.reader.workbook import WorkbookParser

                # Save original method
                original_assign_names = WorkbookParser.assign_names

                def patched_assign_names(self):
                    """Patched version that skips invalid print titles"""
                    try:
                        original_assign_names(self)
                    except ValueError as ve:
                        if "not a valid print titles definition" in str(ve):
                            logger.warning(f"Skipping invalid print title: {ve}")
                            # Continue without assigning this name
                            pass
                        else:
                            raise

                # Apply patch
                WorkbookParser.assign_names = patched_assign_names

                try:
                    # Retry with patched openpyxl
                    result = pd.read_excel(file_path, sheet_name=sheet_name, **kwargs)
                    return result
                finally:
                    # Restore original method
                    WorkbookParser.assign_names = original_assign_names
            else:
                raise

    @staticmethod
    def find_header_row(file_path, sheet_name=None):
        """Find the actual header row by looking for clinic-related keywords"""
        df_raw = ExcelTransformer.safe_read_excel(file_path, sheet_name=sheet_name, header=None)

        for idx, row in df_raw.iterrows():
            row_values = [str(val) for val in row.values if pd.notna(val)]
            row_text = ' '.join(row_values).lower()

            # Enhanced header detection patterns
            header_patterns = [
                # Primary pattern: S/N with clinic ID
                ('s/n' in row_text and 'clinic' in row_text and 'id' in row_text),
                # SP Clinic specific patterns
                ('s/n' in row_text and 'specialty' in row_text and 'sp code' in row_text and 'doctor' in row_text),
                ('s/n' in row_text and 'sp code' in row_text and 'clinic name' in row_text and 'address1' in row_text),
                # MY GP List specific patterns
                ('s/n' in row_text and 'clinic code' in row_text and 'city' in row_text and 'state' in row_text),
                ('s/n' in row_text and 'clinic name' in row_text and 'address1' in row_text),
                ('s/n' in row_text and 'clinic' in row_text and 'tel' in row_text and 'operation' in row_text),
                # Alternative patterns for different sheet layouts
                ('s/n' in row_text and 'region' in row_text and 'area' in row_text),
                ('s/n' in row_text and 'clinic' in row_text and 'name' in row_text),
                ('no.' in row_text and 'clinic' in row_text and 'name' in row_text),
                # For termination sheets
                ('no.' in row_text and 'region' in row_text and 'area' in row_text),
                # TCM sheet specific patterns
                ('s/n' in row_text and 'clinic' in row_text and 'postal' in row_text),
                ('master code' in row_text and 'clinic' in row_text and 'postal' in row_text),
                ('master code' in row_text and 'physician' in row_text and 'charge' in row_text),
                ('master code' in row_text and 'tel' in row_text and len(row_values) >= 8),
                # General patterns that indicate header rows
                ('clinic' in row_text and 'postal' in row_text and 'tel' in row_text),
                ('code' in row_text and 'clinic' in row_text and 'address' in row_text),
                ('provider' in row_text and 'name' in row_text and len(row_values) >= 5),
                # Enhanced minimum viable header patterns
                ('region' in row_text and 'clinic' in row_text and len(row_values) >= 5),
                ('city' in row_text and 'clinic' in row_text and 'tel' in row_text),
                ('state' in row_text and 'clinic name' in row_text and len(row_values) >= 6)
            ]

            if any(pattern for pattern in header_patterns):
                return idx

        # If no clear header found, look for the first row with substantial data
        for idx, row in df_raw.iterrows():
            non_null_count = sum(1 for val in row.values if pd.notna(val) and str(val).strip())
            if non_null_count >= 5:  # At least 5 non-empty columns
                return idx

        # Final fallback
        return 4

    @staticmethod
    def classify_sheets(sheet_names):
        """Enhanced classification for various sheet types"""
        panel_sheets = []
        termination_sheets = []

        for sheet in sheet_names:
            sheet_lower = sheet.lower()
            # Identify termination sheets
            if any(term in sheet_lower for term in ['terminat', 'remov', 'cancel', 'delist']):
                termination_sheets.append(sheet)
            # Enhanced panel sheet identification
            elif any(panel in sheet_lower for panel in [
                'gp', 'tcm', 'dental', 'clinic', 'panel',  # Original patterns
                'sp list', 'sp clinic', 'specialist',      # Specialist patterns
                'sg', 'my', 'msia', 'malaysia', 'singapore', # Country patterns
                'blue', 'red', 'flexi', 'aia',            # Plan type patterns
                'medical', 'health', 'doctor',             # Healthcare patterns
                'alliance', 'tokio', 'marine', 'provider'  # Insurance/Provider patterns
            ]):
                panel_sheets.append(sheet)

        return panel_sheets, termination_sheets

    @staticmethod
    def extract_terminated_clinic_ids(file_path, termination_sheets):
        """Extract clinic IDs from termination sheets"""
        terminated_ids = set()

        for sheet in termination_sheets:
            try:
                # Find header row for termination sheet
                header_row = ExcelTransformer.find_header_row(file_path, sheet)
                df = ExcelTransformer.safe_read_excel(file_path, sheet_name=sheet, header=header_row)
                df.columns = df.columns.str.strip()

                # Look for clinic ID column (various possible names)
                id_columns = [col for col in df.columns if 'clinic' in col.lower() and 'id' in col.lower()]
                if not id_columns:
                    id_columns = [col for col in df.columns if 'provider' in col.lower() and ('code' in col.lower() or 'id' in col.lower())]
                if not id_columns:
                    id_columns = [col for col in df.columns if 'code' in col.lower()]

                if id_columns:
                    # Convert to string and handle any NaN/None values
                    clinic_ids = df[id_columns[0]].dropna()
                    clinic_ids = clinic_ids.astype(str).str.strip()
                    # Filter out any 'nan' strings that might have been created
                    clinic_ids = clinic_ids[clinic_ids.str.lower() != 'nan']
                    terminated_ids.update(clinic_ids)
                    logger.info(f"Extracted {len(clinic_ids)} terminated clinic IDs from sheet '{sheet}'")
                else:
                    logger.warning(f"Could not find clinic ID column in termination sheet '{sheet}'")

            except Exception as e:
                logger.error(f"Error processing termination sheet '{sheet}': {e}")

        logger.info(f"Total terminated clinic IDs: {len(terminated_ids)}")
        return terminated_ids

    @staticmethod
    def sanitize_filename(name):
        """Sanitize sheet name for use in filename"""
        # Remove invalid characters and replace spaces
        sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized.strip('_')

    @staticmethod
    def map_columns(df_columns):
        """Robust column mapping with fuzzy matching and multiple file format support"""
        import re
        from difflib import get_close_matches

        column_mapping = {}

        # Enhanced column mapping patterns with more variations
        mappings = {
            'clinic_id': [
                'ihp clinic id', 'provider code', 'clinic id', 'id', 'clinic code',
                'provider id', 'clinic identifier', 'code', 'clinic no', 'clinic number',
                'master code', 'master id',  # TCM sheet specific
                'sp code', 'sp id'  # SP clinic specific
            ],
            'clinic_name': [
                'clinic name', 'name', 'clinic', 'provider name', 'facility name',
                'medical center', 'medical centre', 'center name', 'centre name'
            ],
            'region': [
                'region', 'zone', 'district', 'sector', 'territory', 'location',
                'geographical region', 'geo region', 'state', 'province', 'city'  # Added city for MY sheets
            ],
            'area': [
                'area', 'estate', 'neighbourhood', 'neighborhood', 'locality',
                'precinct', 'town', 'suburb', 'community', 'district area', 'state'  # Added state for MY sheets
            ],
            'address': [
                'address', 'full address', 'complete address', 'location address',
                'physical address', 'street address', 'mailing address', 'address1'
            ],
            'telephone': [
                'tel no.', 'tel', 'phone', 'telephone', 'contact', 'contact no',
                'contact number', 'phone number', 'tel number', 'mobile', 'contact no.', 'tel no'
            ],
            'remarks': [
                'remarks', 'comment', 'note', 'remark', 'comments', 'notes',
                'additional info', 'special notes', 'observation', 'memo'
            ],
            'operating_hours': [
                'operating hours', 'hours', 'business hours', 'clinic hours',
                'opening hours', 'operation hours', 'working hours', 'service hours'
            ],
            'mon_fri_am': [
                'mon - fri (am)', 'monday - friday', 'weekday am', 'mon-fri am',
                'operating hours\nmon-fri', 'operating hours mon-fri', 'weekdays am',
                'operating hours \nmon - fri', 'operating hours mon - fri',  # TCM format
                'operation hours', 'mon to fri',  # MY GP List format
                'mon - fri',  # AIA SP format
                'weekdays'  # AIA dental format - direct weekdays column
            ],
            'mon_fri_pm': [
                'mon - fri (pm)', 'monday - friday (evening)', 'weekday pm', 'mon-fri pm', 'weekdays pm'
            ],
            'mon_fri_night': [
                'mon - fri (night)', 'weekday night', 'mon-fri night', 'weekdays night'
            ],
            'sat_am': ['sat (am)', 'saturday', 'sat am', 'saturday am'],
            'sat_pm': ['sat (pm)', 'sat pm', 'saturday pm'],
            'sat_night': ['sat (night)', 'sat night', 'saturday night'],
            'sat_simple': ['sat'],  # Simple Saturday column
            'sun_am': ['sun (am)', 'sunday', 'sun am', 'sunday am'],
            'sun_pm': ['sun (pm)', 'sun pm', 'sunday pm'],
            'sun_night': ['sun (night)', 'sun night', 'sunday night'],
            'sun_simple': ['sun'],  # Simple Sunday column
            'holiday_am': ['public holiday (am)', 'public holiday', 'holiday am', 'ph am', 'ph', 'publicday'],
            'holiday_pm': ['public holiday (pm)', 'holiday pm', 'ph pm'],
            'holiday_night': ['public holiday (night)', 'holiday night', 'ph night'],
            'holiday_simple': ['holiday', 'ph'],  # Simple Holiday column
            # Address components for composite address construction
            'address_blk': ['blk', 'block', 'building no', 'bldg no', 'unit block', 'blk & road name'],
            'address_road': ['road name', 'street name', 'street', 'road', 'avenue', 'ave', 'blk & road name'],
            'address_unit': ['unit no.', 'unit no', 'unit', '#', 'suite', 'level', 'unit & building name'],
            'address_building': ['building name', 'building', 'bldg name', 'complex name', 'unit & building name'],
            'postal_code': ['postal code', 'postcode', 'zip code', 'zip', 'postal'],
            # TCM-specific field for doctor information
            'doctor_name': ['physician - in - charge', 'physician in charge', 'doctor', 'physician', 'practitioner'],
            # SP clinic specific fields
            'specialty': ['specialty', 'speciality', 'medical specialty', 'specialization', 'department'],
            'address1': ['address1', 'address 1', 'primary address', 'street address'],
            'address2': ['address2', 'address 2', 'secondary address', 'unit number'],
            'address3': ['address3', 'address 3', 'building name', 'complex name'],
            'address4': ['address4', 'address 4', 'postal address', 'location detail']
        }

        # Convert all column names to lowercase and clean for comparison
        df_cols_lower = {}
        df_cols_cleaned = {}
        df_cols_original = {}  # Keep track of original column names

        for col in df_columns:
            if pd.notna(col) and isinstance(col, str):
                col_clean = col.lower().strip()
                # Remove extra whitespace and newlines
                col_clean = re.sub(r'\s+', ' ', col_clean)
                df_cols_lower[col_clean] = col
                df_cols_cleaned[col_clean] = col
                df_cols_original[col] = col_clean

        logger.debug(f"Available columns (cleaned): {list(df_cols_cleaned.keys())}")

        # Phase 1: Exact pattern matching
        for expected_col, patterns in mappings.items():
            for pattern in patterns:
                if pattern in df_cols_lower:
                    column_mapping[expected_col] = df_cols_lower[pattern]
                    logger.debug(f"Exact match: {expected_col} -> {pattern} -> {df_cols_lower[pattern]}")
                    break

        # Phase 2: Handle sequential operating hours columns (MY GP List format)
        # Look for operation hours followed by unnamed columns
        if 'mon_fri_am' in column_mapping:
            # Find the index of operation hours column
            operation_hours_col = column_mapping['mon_fri_am']
            col_list = list(df_columns)

            try:
                operation_hours_idx = col_list.index(operation_hours_col)
                logger.debug(f"Found operation hours at index {operation_hours_idx}: {operation_hours_col}")

                # Check for sequential unnamed columns
                if operation_hours_idx + 1 < len(col_list):
                    next_col = col_list[operation_hours_idx + 1]
                    if pd.notna(next_col) and ('unnamed' in str(next_col).lower() or str(next_col).lower().strip() == 'sat'):
                        column_mapping['sat_simple'] = next_col
                        logger.debug(f"Sequential match: sat_simple -> {next_col}")

                if operation_hours_idx + 2 < len(col_list):
                    next_col = col_list[operation_hours_idx + 2]
                    if pd.notna(next_col) and ('unnamed' in str(next_col).lower() or 'sun' in str(next_col).lower()):
                        column_mapping['sun_simple'] = next_col
                        logger.debug(f"Sequential match: sun_simple -> {next_col}")

                if operation_hours_idx + 3 < len(col_list):
                    next_col = col_list[operation_hours_idx + 3]
                    if pd.notna(next_col) and ('unnamed' in str(next_col).lower() or 'ph' in str(next_col).lower() or 'holiday' in str(next_col).lower()):
                        column_mapping['holiday_simple'] = next_col
                        logger.debug(f"Sequential match: holiday_simple -> {next_col}")

            except ValueError:
                pass  # Column not found in list

        # Phase 3: Fuzzy matching for unmapped essential columns
        essential_columns = ['clinic_name', 'telephone']
        # Only add region/area if we have good candidates (avoid false matches)
        has_region_candidate = any(pattern in col.lower() for col in df_cols_cleaned.keys() for pattern in ['region', 'zone', 'state', 'city'])
        has_area_candidate = any(pattern in col.lower() for col in df_cols_cleaned.keys() for pattern in ['area', 'district', 'state'])

        if has_region_candidate:
            essential_columns.append('region')
        if has_area_candidate:
            essential_columns.append('area')

        for expected_col in essential_columns:
            if expected_col not in column_mapping:
                # Get all patterns for this column
                all_patterns = mappings.get(expected_col, [])

                # Try fuzzy matching with higher threshold for region/area
                cutoff = 0.8 if expected_col in ['region', 'area'] else 0.6
                for pattern in all_patterns:
                    # Find close matches with similarity threshold
                    close_matches = get_close_matches(
                        pattern,
                        list(df_cols_cleaned.keys()),
                        n=1,
                        cutoff=cutoff
                    )
                    if close_matches:
                        matched_col = df_cols_cleaned[close_matches[0]]
                        column_mapping[expected_col] = matched_col
                        logger.debug(f"Fuzzy match: {expected_col} -> {pattern} ~= {close_matches[0]} -> {matched_col}")
                        break

        # Phase 4: Keyword-based matching for remaining columns (with better specificity)
        remaining_mappings = {
            'clinic_id': ['clinic code', 'clinic id', 'provider id', 'provider code'],  # More specific patterns
            'address': ['address1', 'address', 'location'],
            'remarks': ['remark', 'comment', 'note'],
        }

        for expected_col, keywords in remaining_mappings.items():
            if expected_col not in column_mapping:
                for col_name in df_cols_cleaned.keys():
                    # Use more specific matching - keyword must be substantial part of column name
                    for keyword in keywords:
                        if keyword in col_name and len(keyword) / len(col_name) > 0.4:  # At least 40% match
                            column_mapping[expected_col] = df_cols_cleaned[col_name]
                            logger.debug(f"Keyword match: {expected_col} -> {keyword} in {col_name} -> {df_cols_cleaned[col_name]}")
                            break
                    if expected_col in column_mapping:
                        break

        return column_mapping

    @staticmethod
    def infer_columns_from_data(df):
        """Infer column structure when headers are not clear"""
        inferred_mapping = {}

        # Check if we need to infer columns (either few meaningful names OR column names look like data)
        meaningful_cols = [col for col in df.columns if pd.notna(col) and isinstance(col, str) and len(str(col).strip()) > 0]

        # Detect if column names look like data rather than headers
        data_like_columns = 0
        for col in meaningful_cols[:6]:  # Check first 6 columns
            col_str = str(col).upper()
            if any(indicator in col_str for indicator in ['SINGAPORE', 'CLINIC', 'MEDICAL', 'CENTRE', 'AVENUE', 'ROAD', 'STREET', 'AM', 'PM']):
                data_like_columns += 1

        should_infer = len(meaningful_cols) < 3 or data_like_columns >= 2

        if should_infer:
            # Assume standard clinic data structure based on position
            cols = list(df.columns)

            if len(cols) >= 5:
                # Standard pattern: [S/N, Region, Area, Clinic_ID, Clinic_Name, Address, ...]
                inferred_mapping = {
                    'region': cols[1] if len(cols) > 1 else None,
                    'area': cols[2] if len(cols) > 2 else None,
                    'clinic_id': cols[3] if len(cols) > 3 else None,
                    'clinic_name': cols[4] if len(cols) > 4 else None,
                    'address': cols[5] if len(cols) > 5 else None,
                    'telephone': cols[6] if len(cols) > 6 else None,
                    'mon_fri_am': cols[7] if len(cols) > 7 else None,
                    'sat_am': cols[9] if len(cols) > 9 else None,
                    'sun_am': cols[10] if len(cols) > 10 else None,
                    'holiday_am': cols[11] if len(cols) > 11 else None
                }

                # Filter out None values
                inferred_mapping = {k: v for k, v in inferred_mapping.items() if v is not None}

                logger.debug(f"Inferred column mapping based on position: {inferred_mapping}")

        return inferred_mapping
    
    @staticmethod
    def extract_postal_code(address, country=None):
        """Extract postal code from address based on country format"""
        if pd.isna(address):
            return None

        address_str = str(address).strip()

        # Detect country from address if not provided
        if country is None:
            address_lower = address_str.lower()
            malaysian_indicators = [
                'malaysia', 'johor', 'kuala lumpur', 'selangor', 'penang', 'perak',
                'kedah', 'kelantan', 'terengganu', 'pahang', 'negeri sembilan',
                'melaka', 'sabah', 'sarawak', 'perlis', 'putrajaya', 'labuan',
                # Additional Malaysian cities and areas
                'kulai', 'skudai', 'pasir gudang', 'ulu tiram', 'masai', 'gelang patah',
                'johor bahru', 'kl', 'shah alam', 'petaling jaya', 'bandar', 'taman'
            ]
            # Also check for Malaysian postal code patterns (5 digits vs Singapore's 6)
            has_5_digit = bool(re.search(r'\b\d{5}\b', address_str))
            has_6_digit = bool(re.search(r'\b\d{6}\b', address_str))

            is_malaysian = any(indicator in address_lower for indicator in malaysian_indicators)
            # If we find 5-digit codes but no 6-digit codes, likely Malaysian
            if has_5_digit and not has_6_digit:
                is_malaysian = True

            country = 'MALAYSIA' if is_malaysian else 'SINGAPORE'

        if country == 'SINGAPORE':
            # Singapore: Look for SINGAPORE followed by 6 digits
            match = re.search(r'SINGAPORE\s+(\d{6})', address_str, re.IGNORECASE)
            if match:
                return match.group(1)
            # Fallback: Look for 6-digit patterns in Singapore addresses
            matches = re.findall(r'\b(\d{6})\b', address_str)
            return matches[-1] if matches else None  # Return last 6-digit number found

        elif country == 'MALAYSIA':
            # Malaysia: Look for 5-digit postal codes in various formats
            # Use multiple patterns to catch different formats
            patterns = [
                # Pattern 1: Standalone 5-digit codes (81300 SKUDAI, JOHOR)
                r'\b(\d{5})\b',
                # Pattern 2: City followed by postal code (KULAI 81000)
                r'\b[A-Za-z\s]+\s+(\d{5})',
                # Pattern 3: Postal code at end (TAMAN PERLING, 81200)
                r',\s*(\d{5})\s*$',
                # Pattern 4: Postal code before end tokens
                r'(\d{5})(?=\s*(?:$|,|\s+(?:JOHOR|SELANGOR|MALAYSIA)))',
                # Pattern 5: Any 5-digit sequence (most permissive)
                r'(\d{5})'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, address_str, re.IGNORECASE)
                if matches:
                    # Return the first match found
                    return matches[0]

        return None
    
    @staticmethod
    def combine_phone_remarks(phone, remarks):
        """Combine telephone number with remarks"""
        phone_str = str(phone) if pd.notna(phone) else ""
        remarks_str = str(remarks) if pd.notna(remarks) else ""
        
        if remarks_str and remarks_str.lower() != 'nan':
            return f"{phone_str} - {remarks_str}"
        return phone_str
    

    @staticmethod
    def combine_operating_hours_flexible(df_source, col_map, day_type):
        """Smart operating hours combination supporting both complex (AM/PM/NIGHT) and simple formats"""

        # Define potential column keys for each day type
        if day_type == 'weekday':
            complex_keys = ('mon_fri_am', 'mon_fri_pm', 'mon_fri_night')
            simple_key = 'mon_fri_am'  # Sometimes Mon-Fri is in a single column
        elif day_type == 'saturday':
            complex_keys = ('sat_am', 'sat_pm', 'sat_night')
            simple_key = 'sat_simple'
        elif day_type == 'sunday':
            complex_keys = ('sun_am', 'sun_pm', 'sun_night')
            simple_key = 'sun_simple'
        elif day_type == 'public_holiday':
            complex_keys = ('holiday_am', 'holiday_pm', 'holiday_night')
            simple_key = 'holiday_simple'
        else:
            return ['CLOSED/CLOSED/CLOSED'] * len(df_source)

        result = []
        for _, row in df_source.iterrows():
            # Strategy 1: Try complex format (AM/PM/NIGHT columns)
            am_key, pm_key, night_key = complex_keys
            # Only use complex format if we have multiple time periods (AM/PM/Night)
            complex_keys_found = [key for key in complex_keys if key in col_map]
            has_complex = len(complex_keys_found) > 1

            if has_complex:
                # Use complex format
                am = row.get(col_map.get(am_key, ''), 'CLOSED') if am_key in col_map else 'CLOSED'
                pm = row.get(col_map.get(pm_key, ''), 'CLOSED') if pm_key in col_map else 'CLOSED'
                night = row.get(col_map.get(night_key, ''), 'CLOSED') if night_key in col_map else 'CLOSED'

                # Handle NaN values
                am = 'CLOSED' if pd.isna(am) else str(am)
                pm = 'CLOSED' if pd.isna(pm) else str(pm)
                night = 'CLOSED' if pd.isna(night) else str(night)

                result.append(f"{am}/{pm}/{night}")

            else:
                # Strategy 2: Use simple format - check any available key
                hours_str = 'CLOSED'
                found_key = False
                for key_to_check in [simple_key] + list(complex_keys):
                    if key_to_check in col_map:
                        hours_value = row.get(col_map[key_to_check], 'CLOSED')
                        hours_str = 'CLOSED' if pd.isna(hours_value) else str(hours_value)
                        found_key = True
                        break

                if found_key:
                    # For SP clinic format, use clean hours without /CLOSED/CLOSED suffix
                    result.append(hours_str)
                else:
                    # Strategy 3: No mapping found, default to CLOSED
                    result.append('CLOSED')

        return result

    @staticmethod
    def construct_address(df_source, col_map):
        """Smart address construction from multiple columns"""
        addresses = []

        # Define address component priorities
        address_components = [
            ('address_blk', 'Blk'),     # Block number
            ('address_unit', '#'),       # Unit number
            ('address_road', ''),        # Road name
            ('address_building', ''),    # Building name
        ]

        for _, row in df_source.iterrows():
            address_parts = []

            # Check if we have a complete address column first
            if 'address' in col_map and pd.notna(row.get(col_map['address'], '')):
                address_str = str(row[col_map['address']]).strip()
                if address_str and address_str.lower() not in ['nan', '', 'none']:
                    addresses.append(address_str)
                    continue

            # SP Clinic format: Use only Address1 for primary address (Address2/Address3 handled separately)
            if 'address1' in col_map:
                value = row.get(col_map['address1'], '')
                if pd.notna(value) and str(value).strip() and str(value).lower() not in ['nan', '', 'none']:
                    addresses.append(str(value).strip())
                    continue

            # Construct address from components (avoid duplicates)
            used_columns = set()
            for comp_key, prefix in address_components:
                if comp_key in col_map and col_map[comp_key] not in used_columns:
                    used_columns.add(col_map[comp_key])
                    value = row.get(col_map[comp_key], '')
                    if pd.notna(value) and str(value).strip() and str(value).lower() not in ['nan', '', 'none']:
                        value_str = str(value).strip()
                        # For TCM sheets, don't add prefix if the value already contains structural info
                        if comp_key == 'address_blk' and ('blk' in value_str.lower() or 'block' in value_str.lower()):
                            address_parts.append(value_str)
                        elif comp_key == 'address_unit' and ('#' in value_str or 'unit' in value_str.lower()):
                            address_parts.append(value_str)
                        elif prefix and not value_str.startswith(prefix):
                            address_parts.append(f"{prefix} {value_str}")
                        else:
                            address_parts.append(value_str)

            # Combine parts
            if address_parts:
                addresses.append(' '.join(address_parts))
            else:
                addresses.append('')

        return addresses

    @staticmethod
    def smart_column_fallback(df_source, col_map, field_type):
        """Intelligent fallback for missing critical fields"""
        if field_type == 'clinic_id':
            # Try to generate ID from clinic name or use row index
            if 'clinic_name' in col_map:
                return [f"AUTO_{i+1:04d}_{str(name).replace(' ', '_').upper()[:10]}"
                       for i, name in enumerate(df_source[col_map['clinic_name']])]
            else:
                return [f"AUTO_{i+1:04d}" for i in range(len(df_source))]

        elif field_type == 'region':
            # For TCM sheets without region, use 'TCM' as default
            if 'area' in col_map:
                return df_source[col_map['area']].fillna('TCM')
            else:
                return ['TCM'] * len(df_source)

        elif field_type == 'area':
            # For TCM sheets without area, use clinic location or 'SINGAPORE'
            if 'region' in col_map:
                return df_source[col_map['region']].fillna('SINGAPORE')
            else:
                return ['SINGAPORE'] * len(df_source)

        return [''] * len(df_source)

    @staticmethod
    def transform_sheet(input_path, sheet_name, terminated_ids=None, use_google_api=True):
        """Transform a single sheet to target template format with geocoding"""
        try:
            # Initialize geocoding service with user preference
            geocoding_service = GeocodingService(use_google_api=use_google_api)

            # Check if this is Alliance-Tokio Marine format
            import openpyxl
            wb = openpyxl.load_workbook(input_path)
            ws = wb[sheet_name]

            is_alliance_tokio = ExcelTransformer.detect_alliance_tokio_format(ws)

            if is_alliance_tokio:
                logger.info(f"Processing Alliance-Tokio Marine format for sheet: {sheet_name}")

                # Unmerge cells and fill values
                ws = ExcelTransformer.unmerge_and_fill_cells(ws)

                # Save to temporary file
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
                wb.save(temp_file.name)
                temp_file.close()

                # Read with pandas (data starts at row 3, after headers at rows 1-2)
                df_source = pd.read_excel(temp_file.name, sheet_name=sheet_name, header=None, skiprows=2)

                # Set column names from reconstructed headers
                headers = ExcelTransformer.get_alliance_tokio_headers(ws)
                df_source.columns = headers[:len(df_source.columns)]

                # Clean up temp file
                import os
                os.unlink(temp_file.name)

                header_row = None  # Already handled
            else:
                # Standard format - find the correct header row
                header_row = ExcelTransformer.find_header_row(input_path, sheet_name)

                # Read the source sheet
                df_source = ExcelTransformer.safe_read_excel(input_path, sheet_name=sheet_name, header=header_row)
                df_source.columns = df_source.columns.str.strip()
            
            # Create transformed dataframe
            df_transformed = pd.DataFrame()
            
            # Map columns flexibly
            col_map = ExcelTransformer.map_columns(df_source.columns)
            logger.debug(f"Column mapping for sheet '{sheet_name}': {col_map}")

            # If column mapping failed, try to infer from data structure
            if 'clinic_name' not in col_map:
                logger.info(f"Standard column mapping failed for '{sheet_name}', attempting inference...")
                inferred_map = ExcelTransformer.infer_columns_from_data(df_source)
                if 'clinic_name' in inferred_map:
                    col_map.update(inferred_map)
                    logger.info(f"Successfully inferred columns for sheet '{sheet_name}'")
                else:
                    raise ValueError(f"Sheet '{sheet_name}' missing required 'clinic name' column after inference attempt")

            # Filter out metadata rows for Alliance-Tokio format
            if is_alliance_tokio:
                initial_count = len(df_source)
                # Filter out rows where ZONE contains metadata keywords
                metadata_keywords = ['Legend:', 'Remarks', '24 Hours', 'Newly joined', 'JB Clinics', 'clinic']
                zone_col = 'ZONE'
                if zone_col in df_source.columns:
                    metadata_mask = df_source[zone_col].astype(str).str.contains('|'.join(metadata_keywords), case=False, na=False)
                    df_source = df_source[~metadata_mask]
                    filtered_metadata = initial_count - len(df_source)
                    if filtered_metadata > 0:
                        logger.info(f"Filtered out {filtered_metadata} metadata rows from Alliance-Tokio sheet")

            # Filter out terminated clinics if provided
            terminated_count = 0
            if terminated_ids and 'clinic_id' in col_map:
                initial_count = len(df_source)
                df_source = df_source[~df_source[col_map['clinic_id']].astype(str).str.strip().isin(terminated_ids)]
                filtered_count = len(df_source)
                terminated_count = initial_count - filtered_count
                logger.info(f"Filtered out {terminated_count} terminated clinics from sheet '{sheet_name}'")

            # Filter out empty/invalid rows - keep only rows with valid clinic data
            initial_count = len(df_source)
            if 'clinic_id' in col_map and 'clinic_name' in col_map:
                # For sheets with both clinic_id and clinic_name, filter by both
                valid_id_mask = df_source[col_map['clinic_id']].notna() & (df_source[col_map['clinic_id']].astype(str).str.strip() != '')
                valid_name_mask = df_source[col_map['clinic_name']].notna() & (df_source[col_map['clinic_name']].astype(str).str.strip() != '')
                valid_mask = valid_id_mask & valid_name_mask
            elif 'clinic_name' in col_map:
                # Fallback: filter by clinic_name only
                valid_mask = df_source[col_map['clinic_name']].notna() & (df_source[col_map['clinic_name']].astype(str).str.strip() != '')
            else:
                # Should not happen, but keep all rows if no clinic identifier found
                valid_mask = pd.Series([True] * len(df_source))

            df_source = df_source[valid_mask]
            filtered_count = len(df_source)
            if initial_count != filtered_count:
                logger.info(f"Filtered out {initial_count - filtered_count} empty/invalid rows from sheet '{sheet_name}', keeping {filtered_count} valid records")

            # Robust field mapping with fallbacks
            # Clinic ID with smart fallback
            if 'clinic_id' in col_map:
                df_transformed['Code'] = df_source[col_map['clinic_id']]
            else:
                df_transformed['Code'] = ExcelTransformer.smart_column_fallback(df_source, col_map, 'clinic_id')
                logger.info(f"Generated auto clinic IDs for {len(df_source)} records")

            # Clinic Name (required field)
            df_transformed['Name'] = df_source[col_map['clinic_name']]

            # Region with smart fallback
            if 'region' in col_map:
                df_transformed['Zone'] = df_source[col_map['region']]
            else:
                df_transformed['Zone'] = ExcelTransformer.smart_column_fallback(df_source, col_map, 'region')

            # Area with smart fallback
            if 'area' in col_map:
                df_transformed['Area'] = df_source[col_map['area']]
            else:
                df_transformed['Area'] = ExcelTransformer.smart_column_fallback(df_source, col_map, 'area')

            # Specialty field (available in SP clinic sheets)
            if 'specialty' in col_map:
                df_transformed['Specialty'] = df_source[col_map['specialty']]
            else:
                df_transformed['Specialty'] = None

            # Doctor field (available in TCM and SP clinic sheets)
            if 'doctor_name' in col_map:
                df_transformed['Doctor'] = df_source[col_map['doctor_name']]
            else:
                df_transformed['Doctor'] = None

            # Smart address construction
            df_transformed['Address1'] = ExcelTransformer.construct_address(df_source, col_map)

            # Extract Address2 and Address3 from source data if available
            if 'address2' in col_map:
                df_transformed['Address2'] = df_source[col_map['address2']].fillna('')
            else:
                df_transformed['Address2'] = None

            if 'address3' in col_map:
                df_transformed['Address3'] = df_source[col_map['address3']].fillna('')
            else:
                df_transformed['Address3'] = None

            # Extract postal codes from addresses (supports both Singapore and Malaysia)

            # Enhanced postal code extraction
            postal_codes = []
            for index, address in enumerate(df_transformed['Address1']):
                postal_code = None

                # Try dedicated postal code column first (if it has valid data)
                if 'postal_code' in col_map:
                    postal_col_value = df_source.iloc[index][col_map['postal_code']]
                    if pd.notna(postal_col_value) and str(postal_col_value).strip() not in ('', 'nan', 'None'):
                        postal_code = str(postal_col_value).strip()

                # If no valid postal code from dedicated column, extract from address
                if not postal_code:
                    # For SP clinic format, check Address4 first (contains "SINGAPORE 247909")
                    if 'address4' in col_map:
                        address4_value = df_source.iloc[index].get(col_map['address4'], '')
                        if pd.notna(address4_value) and str(address4_value).strip():
                            postal_code = ExcelTransformer.extract_postal_code(str(address4_value))

                    # Fallback to extracting from combined address
                    if not postal_code and pd.notna(address) and str(address).strip():
                        postal_code = ExcelTransformer.extract_postal_code(address)

                postal_codes.append(postal_code)

            df_transformed['PostalCode'] = postal_codes

            # Detect country from address information
            def detect_country(address):
                if pd.isna(address) or str(address).strip() == '':
                    return 'SINGAPORE'  # Default

                address_lower = str(address).lower()

                # Check for Malaysian indicators
                malaysian_indicators = [
                    'malaysia', 'johor', 'kuala lumpur', 'selangor', 'penang', 'perak',
                    'kedah', 'kelantan', 'terengganu', 'pahang', 'negeri sembilan',
                    'melaka', 'sabah', 'sarawak', 'perlis', 'putrajaya', 'labuan',
                    'johor bahru', 'kl', 'shah alam', 'petaling jaya'
                ]

                if any(indicator in address_lower for indicator in malaysian_indicators):
                    return 'MALAYSIA'
                else:
                    return 'SINGAPORE'

            df_transformed['Country'] = df_transformed['Address1'].apply(detect_country)

            # Combine phone and remarks (if available)
            if 'telephone' in col_map and col_map['telephone'] is not None and pd.notna(col_map['telephone']):
                if 'remarks' in col_map and col_map['remarks'] is not None:
                    df_transformed['PhoneNumber'] = df_source.apply(
                        lambda row: ExcelTransformer.combine_phone_remarks(
                            row[col_map['telephone']], row[col_map['remarks']]
                        ), axis=1
                    )
                else:
                    df_transformed['PhoneNumber'] = df_source[col_map['telephone']].astype(str)
            else:
                df_transformed['PhoneNumber'] = ''

            # Operating hours handling
            if is_alliance_tokio:
                # Alliance-Tokio format: Convert 4-column format to AM/PM/NIGHT
                logger.info("Converting Alliance-Tokio operating hours to standard AM/PM/NIGHT format")

                weekdays = []
                saturdays = []
                sundays = []
                holidays = []

                for _, row in df_source.iterrows():
                    mon_fri = row.get('MON - FRI', '')
                    sat = row.get('SAT', '')
                    sun = row.get('SUN', '')
                    ph = row.get('PUBLIC HOLIDAYS', '')

                    wd, sat_result, sun_result, hol_result = ExcelTransformer.convert_alliance_hours_to_standard(
                        mon_fri, sat, sun, ph
                    )

                    weekdays.append(wd)
                    saturdays.append(sat_result)
                    sundays.append(sun_result)
                    holidays.append(hol_result)

                df_transformed['MonToFri'] = weekdays
                df_transformed['Saturday'] = saturdays
                df_transformed['Sunday'] = sundays
                df_transformed['PublicHoliday'] = holidays
            else:
                # Standard format: flexible mapping
                df_transformed['MonToFri'] = ExcelTransformer.combine_operating_hours_flexible(df_source, col_map, 'weekday')
                df_transformed['Saturday'] = ExcelTransformer.combine_operating_hours_flexible(df_source, col_map, 'saturday')
                df_transformed['Sunday'] = ExcelTransformer.combine_operating_hours_flexible(df_source, col_map, 'sunday')
                df_transformed['PublicHoliday'] = ExcelTransformer.combine_operating_hours_flexible(df_source, col_map, 'public_holiday')
            
            # Geocoding: Populate Latitude and Longitude
            latitudes = []
            longitudes = []
            geocoding_methods = []
            
            for index, row in df_transformed.iterrows():
                postal_code = row['PostalCode']
                address = row['Address1']
                
                lat, lng, method = geocoding_service.geocode(postal_code, address)
                latitudes.append(lat)
                longitudes.append(lng)
                geocoding_methods.append(method)
            
            df_transformed['Latitude'] = latitudes
            df_transformed['Longitude'] = longitudes
            
            # Generate Google Maps URLs for successfully geocoded locations
            def generate_google_maps_url(lat, lng):
                if lat is not None and lng is not None:
                    return f"https://maps.google.com/?q={lat},{lng}"
                return None
            
            df_transformed['GoogleMapURL'] = df_transformed.apply(
                lambda row: generate_google_maps_url(row['Latitude'], row['Longitude']), axis=1
            )
            
            # Return the transformed dataframe instead of saving
            # Saving will be handled by the multi-sheet processor
            
            # Get geocoding statistics
            stats = geocoding_service.get_stats()
            successful_geocodes = sum(1 for lat in latitudes if lat is not None)
            postal_matches = len([m for m in geocoding_methods if m == 'postal_code'])
            address_matches = len([m for m in geocoding_methods if m == 'address'])
            
            return {
                'success': True,
                'dataframe': df_transformed,
                'message': f'Successfully transformed {len(df_transformed)} records',
                'records_processed': len(df_transformed),
                'terminated_clinics_filtered': terminated_count,
                'geocoding_stats': {
                    'total_records': len(df_transformed),
                    'successful_geocodes': successful_geocodes,
                    'postal_code_matches': postal_matches,
                    'address_geocodes': address_matches,
                    'failed_geocodes': len(df_transformed) - successful_geocodes,
                    'success_rate': f"{(successful_geocodes/len(df_transformed)*100):.1f}%"
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error transforming sheet {sheet_name}: {str(e)}',
                'error_details': traceback.format_exc()
            }

    @staticmethod
    def transform_excel_multi_sheet(input_path, output_dir, job_id, use_google_api=True):
        """Transform Excel file with multiple sheets to multiple output files"""
        try:
            # Get all sheet names (with fallback for corrupted XML)
            try:
                xl_file = pd.ExcelFile(input_path)
                sheet_names = xl_file.sheet_names
            except ValueError as e:
                if "could not assign names" in str(e) or "invalid XML" in str(e):
                    logger.warning(f"Excel file has corrupted metadata, using patched openpyxl to read sheet names")
                    import openpyxl
                    from openpyxl.reader.workbook import WorkbookParser

                    # Save original method
                    original_assign_names = WorkbookParser.assign_names

                    def patched_assign_names(self):
                        """Patched version that skips invalid print titles"""
                        try:
                            original_assign_names(self)
                        except ValueError as ve:
                            if "not a valid print titles definition" in str(ve):
                                logger.warning(f"Skipping invalid print title: {ve}")
                                pass
                            else:
                                raise

                    # Apply patch
                    WorkbookParser.assign_names = patched_assign_names

                    try:
                        xl_file = pd.ExcelFile(input_path)
                        sheet_names = xl_file.sheet_names
                    finally:
                        # Restore original method
                        WorkbookParser.assign_names = original_assign_names
                else:
                    raise

            # Classify sheets
            panel_sheets, termination_sheets = ExcelTransformer.classify_sheets(sheet_names)

            logger.info(f"Detected {len(panel_sheets)} panel sheets: {panel_sheets}")
            logger.info(f"Detected {len(termination_sheets)} termination sheets: {termination_sheets}")

            # Extract terminated clinic IDs
            terminated_ids = ExcelTransformer.extract_terminated_clinic_ids(input_path, termination_sheets)

            # Process each panel sheet
            results = []
            output_files = []

            for sheet in panel_sheets:
                logger.info(f"Processing sheet: {sheet}")

                # Transform the sheet with geocoding preference
                result = ExcelTransformer.transform_sheet(input_path, sheet, terminated_ids, use_google_api)

                if result['success']:
                    df = result['dataframe']

                    # Check if this sheet has mixed Singapore/Malaysia data
                    has_country_column = 'Country' in df.columns
                    has_mixed_countries = False

                    if has_country_column:
                        countries = df['Country'].unique()
                        has_mixed_countries = len([c for c in countries if c in ['SINGAPORE', 'MALAYSIA']]) > 1
                        logger.info(f"Sheet '{sheet}' countries detected: {list(countries)}")

                    if has_mixed_countries:
                        # Separate Singapore and Malaysia clinics
                        df_sg = df[df['Country'] == 'SINGAPORE'].copy()
                        df_my = df[df['Country'] == 'MALAYSIA'].copy()

                        logger.info(f"Separating sheet '{sheet}': {len(df_sg)} Singapore clinics, {len(df_my)} Malaysia clinics")

                        # Save Singapore file
                        if len(df_sg) > 0:
                            sanitized_name = ExcelTransformer.sanitize_filename(sheet)
                            sg_filename = f"{job_id}_{sanitized_name}_Singapore.xlsx"
                            sg_path = os.path.join(output_dir, sg_filename)
                            df_sg.to_excel(sg_path, index=False)

                            results.append({
                                'sheet_name': f"{sheet} (Singapore)",
                                'output_filename': sg_filename,
                                'output_path': sg_path,
                                'records_processed': len(df_sg),
                                'terminated_clinics_filtered': result['terminated_clinics_filtered'],
                                'geocoding_stats': {
                                    'total_records': len(df_sg),
                                    'successful_geocodes': df_sg['Latitude'].notna().sum(),
                                    'success_rate': f"{(df_sg['Latitude'].notna().sum()/len(df_sg)*100):.1f}%"
                                }
                            })
                            output_files.append(sg_filename)

                        # Save Malaysia file
                        if len(df_my) > 0:
                            sanitized_name = ExcelTransformer.sanitize_filename(sheet)
                            my_filename = f"{job_id}_{sanitized_name}_Malaysia.xlsx"
                            my_path = os.path.join(output_dir, my_filename)
                            df_my.to_excel(my_path, index=False)

                            results.append({
                                'sheet_name': f"{sheet} (Malaysia)",
                                'output_filename': my_filename,
                                'output_path': my_path,
                                'records_processed': len(df_my),
                                'terminated_clinics_filtered': 0,
                                'geocoding_stats': {
                                    'total_records': len(df_my),
                                    'successful_geocodes': df_my['Latitude'].notna().sum(),
                                    'success_rate': f"{(df_my['Latitude'].notna().sum()/len(df_my)*100):.1f}%"
                                }
                            })
                            output_files.append(my_filename)

                        logger.info(f"SUCCESS: Separated sheet '{sheet}' into Singapore ({len(df_sg)} records) and Malaysia ({len(df_my)} records)")
                    else:
                        # Single country or no country column - save as one file
                        sanitized_name = ExcelTransformer.sanitize_filename(sheet)
                        output_filename = f"{job_id}_{sanitized_name}.xlsx"
                        output_path = os.path.join(output_dir, output_filename)

                        # Save the transformed dataframe
                        df.to_excel(output_path, index=False)

                        # Store result info
                        sheet_result = {
                            'sheet_name': sheet,
                            'output_filename': output_filename,
                            'output_path': output_path,
                            'records_processed': result['records_processed'],
                            'terminated_clinics_filtered': result['terminated_clinics_filtered'],
                            'geocoding_stats': result['geocoding_stats']
                        }
                        results.append(sheet_result)
                        output_files.append(output_filename)

                        logger.info(f"SUCCESS: Processed sheet '{sheet}': {result['records_processed']} records")
                else:
                    logger.error(f"FAILED: Could not process sheet '{sheet}': {result['message']}")
                    return {
                        'success': False,
                        'message': f"Failed to process sheet '{sheet}': {result['message']}",
                        'error_details': result.get('error_details', '')
                    }

            if not results:
                return {
                    'success': False,
                    'message': 'No panel sheets found to process. Expected sheets with names containing: GP, TCM, dental, clinic, or panel.'
                }

            # Calculate summary statistics
            total_records = sum(r['records_processed'] for r in results)
            total_geocodes = sum(r['geocoding_stats']['successful_geocodes'] for r in results)

            return {
                'success': True,
                'message': f'Successfully processed {len(results)} sheets with {total_records} total records',
                'sheets_processed': len(results),
                'total_records': total_records,
                'terminated_clinics_filtered': len(terminated_ids),
                'output_files': output_files,
                'results': results,
                'summary_stats': {
                    'total_successful_geocodes': total_geocodes,
                    'overall_geocoding_rate': f"{(total_geocodes/total_records*100):.1f}%" if total_records > 0 else "0%"
                }
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error processing multi-sheet file: {str(e)}',
                'error_details': traceback.format_exc()
            }

class BatchProcessor:
    def __init__(self):
        self.batch_jobs = {}  # Store batch job status
        self.lock = threading.Lock()

    def create_batch_job(self, batch_id, file_count):
        """Create a new batch processing job"""
        with self.lock:
            self.batch_jobs[batch_id] = {
                'status': 'processing',
                'total_files': file_count,
                'completed_files': 0,
                'failed_files': 0,
                'results': [],
                'created_at': datetime.now().isoformat()
            }

    def update_batch_progress(self, batch_id, file_result):
        """Update progress for a batch job"""
        with self.lock:
            if batch_id in self.batch_jobs:
                self.batch_jobs[batch_id]['results'].append(file_result)
                if file_result.get('success', False):
                    self.batch_jobs[batch_id]['completed_files'] += 1
                else:
                    self.batch_jobs[batch_id]['failed_files'] += 1

                # Check if batch is complete
                total_processed = self.batch_jobs[batch_id]['completed_files'] + self.batch_jobs[batch_id]['failed_files']
                if total_processed >= self.batch_jobs[batch_id]['total_files']:
                    self.batch_jobs[batch_id]['status'] = 'completed'

    def get_batch_status(self, batch_id):
        """Get status of a batch job"""
        with self.lock:
            return self.batch_jobs.get(batch_id, None)

# Global batch processor instance
batch_processor = BatchProcessor()

def process_single_file_in_batch(file_data, batch_id, use_google_api=True):
    """Process a single file as part of a batch job"""
    try:
        file_content = file_data['content']
        original_filename = file_data['filename']
        job_id = str(uuid.uuid4())

        # Save uploaded file
        input_filename = f"{job_id}_input.xlsx"
        input_path = os.path.join(UPLOAD_FOLDER, input_filename)

        with open(input_path, 'wb') as f:
            f.write(file_content)

        # Validate file content (using safe method that handles corrupted XML)
        try:
            # Use the same safe reading approach as transform_excel_multi_sheet
            try:
                xl_file = pd.ExcelFile(input_path)
                sheet_names = xl_file.sheet_names
            except ValueError as e:
                if "could not assign names" in str(e) or "invalid XML" in str(e):
                    logger.warning(f"Batch file has corrupted metadata, using patched validation for {original_filename}")
                    import openpyxl
                    from openpyxl.reader.workbook import WorkbookParser

                    # Save original method
                    original_assign_names = WorkbookParser.assign_names

                    def patched_assign_names(self):
                        """Patched version that skips invalid print titles"""
                        try:
                            original_assign_names(self)
                        except ValueError as ve:
                            if "not a valid print titles definition" in str(ve):
                                logger.warning(f"Skipping invalid print title during validation: {ve}")
                                pass
                            else:
                                raise

                    # Apply patch
                    WorkbookParser.assign_names = patched_assign_names

                    try:
                        xl_file = pd.ExcelFile(input_path)
                        sheet_names = xl_file.sheet_names
                    finally:
                        # Restore original method
                        WorkbookParser.assign_names = original_assign_names
                else:
                    raise
            logger.info(f"Batch file validation passed for {original_filename} (job {job_id})")
        except Exception as validation_error:
            if os.path.exists(input_path):
                os.remove(input_path)
            raise ValueError(f"Invalid Excel file: {original_filename}")

        # Transform file with geocoding preference
        result = ExcelTransformer.transform_excel_multi_sheet(input_path, PROCESSED_FOLDER, job_id, use_google_api)

        # Clean up input file
        if os.path.exists(input_path):
            os.remove(input_path)

        if result['success']:
            file_result = {
                'success': True,
                'filename': original_filename,
                'job_id': job_id,
                'sheets_processed': result['sheets_processed'],
                'total_records': result['total_records'],
                'terminated_clinics_filtered': result['terminated_clinics_filtered'],
                'output_files': result['output_files'],
                'download_urls': [f'/download/{job_id}/{filename}' for filename in result['output_files']],
                'results': result['results'],  # Individual sheet results
                'summary_stats': result['summary_stats']
            }
        else:
            file_result = {
                'success': False,
                'filename': original_filename,
                'error': result['message'],
                'details': result.get('error_details', '')
            }

        # Update batch progress
        batch_processor.update_batch_progress(batch_id, file_result)

        return file_result

    except Exception as e:
        error_result = {
            'success': False,
            'filename': file_data.get('filename', 'unknown'),
            'error': str(e),
            'details': traceback.format_exc()
        }
        batch_processor.update_batch_progress(batch_id, error_result)
        return error_result

@app.route('/upload/batch', methods=['POST'])
def upload_batch():
    """Handle batch upload of multiple Excel files"""
    try:
        # Check if files are provided
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400

        files = request.files.getlist('files')
        if not files or len(files) == 0:
            return jsonify({'error': 'No files selected'}), 400

        # Extract geocoding preference (default: True)
        use_google_api = request.form.get('use_google_api', 'true').lower() == 'true'
        logger.info(f"Batch upload - Google Maps API geocoding: {'ENABLED' if use_google_api else 'DISABLED'}")

        # Validate file count (limit to 10 files per batch)
        MAX_BATCH_SIZE = 10
        if len(files) > MAX_BATCH_SIZE:
            return jsonify({'error': f'Too many files. Maximum {MAX_BATCH_SIZE} files allowed per batch.'}), 400

        # Validate each file
        file_data_list = []
        for file in files:
            if file.filename == '':
                continue

            if not file.filename.lower().endswith(('.xlsx', '.xls')):
                return jsonify({'error': f'Invalid file format: {file.filename}. Please upload Excel files only.'}), 400

            # File size validation (50MB limit per file)
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Seek back to beginning

            MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
            if file_size > MAX_FILE_SIZE:
                return jsonify({'error': f'File too large: {file.filename}. Maximum size is 50MB per file.'}), 413

            # Read file content
            file_content = file.read()
            file_data_list.append({
                'content': file_content,
                'filename': file.filename,
                'size': file_size
            })

        if not file_data_list:
            return jsonify({'error': 'No valid files provided'}), 400

        # Generate batch ID
        batch_id = str(uuid.uuid4())

        # Create batch job
        batch_processor.create_batch_job(batch_id, len(file_data_list))

        # Process files - use concurrent processing if available, otherwise sequential
        if CONCURRENT_SUPPORT and len(file_data_list) > 1:
            # Concurrent processing for better performance
            max_workers = min(len(file_data_list), 2)  # Reduced from 3 to 2 for free tier
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all files for processing with geocoding preference
                future_to_file = {
                    executor.submit(process_single_file_in_batch, file_data, batch_id, use_google_api): file_data['filename']
                    for file_data in file_data_list
                }

                # Collect results as they complete
                results = []
                for future in as_completed(future_to_file):
                    try:
                        result = future.result(timeout=300)  # 5 minute timeout per file
                        results.append(result)
                    except Exception as e:
                        filename = future_to_file[future]
                        error_result = {
                            'success': False,
                            'filename': filename,
                            'error': f'Processing timeout or error: {str(e)}'
                        }
                        results.append(error_result)
                        batch_processor.update_batch_progress(batch_id, error_result)
        else:
            # Sequential processing fallback
            results = []
            for file_data in file_data_list:
                try:
                    result = process_single_file_in_batch(file_data, batch_id, use_google_api)
                    results.append(result)
                except Exception as e:
                    error_result = {
                        'success': False,
                        'filename': file_data['filename'],
                        'error': f'Processing error: {str(e)}'
                    }
                    results.append(error_result)
                    batch_processor.update_batch_progress(batch_id, error_result)

        # Get final batch status
        batch_status = batch_processor.get_batch_status(batch_id)

        successful_files = [r for r in results if r.get('success', False)]
        failed_files = [r for r in results if not r.get('success', False)]

        return jsonify({
            'batch_id': batch_id,
            'message': f'Batch processing completed. {len(successful_files)} files processed successfully, {len(failed_files)} failed.',
            'total_files': len(file_data_list),
            'successful_files': len(successful_files),
            'failed_files': len(failed_files),
            'results': results,
            'batch_status': batch_status
        })

    except Exception as e:
        logger.error(f"Batch upload error: {str(e)}")
        return jsonify({
            'error': 'Internal server error during batch processing',
            'details': str(e)
        }), 500

@app.route('/batch/status/<batch_id>', methods=['GET'])
def get_batch_status(batch_id):
    """Get status of a batch processing job"""
    try:
        status = batch_processor.get_batch_status(batch_id)
        if not status:
            return jsonify({'error': 'Batch job not found'}), 404

        return jsonify(status)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/batch/download/<batch_id>', methods=['GET'])
def download_batch(batch_id):
    """Download all files from a batch processing job as ZIP"""
    try:
        batch_status = batch_processor.get_batch_status(batch_id)
        if not batch_status:
            return jsonify({'error': 'Batch job not found'}), 404

        if batch_status['status'] != 'completed':
            return jsonify({'error': 'Batch processing not completed yet'}), 400

        # Collect all successful results
        successful_results = [r for r in batch_status['results'] if r.get('success', False)]

        if not successful_results:
            return jsonify({'error': 'No successful files to download'}), 404

        import zipfile
        import tempfile
        import glob

        # Create temporary zip file
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')

        with zipfile.ZipFile(temp_zip.name, 'w') as zipf:
            for result in successful_results:
                job_id = result['job_id']
                original_filename = result['filename']

                # Find all files for this job
                pattern = os.path.join(PROCESSED_FOLDER, f"{job_id}_*.xlsx")
                matching_files = glob.glob(pattern)

                for file_path in matching_files:
                    filename = os.path.basename(file_path)
                    # Create descriptive archive names: originalname_sheetname.xlsx
                    sheet_part = filename.replace(f"{job_id}_", "").replace(".xlsx", "")
                    base_name = os.path.splitext(original_filename)[0]
                    arc_name = f"{base_name}_{sheet_part}.xlsx"
                    zipf.write(file_path, arc_name)

        return send_file(
            temp_zip.name,
            as_attachment=True,
            download_name=f'batch_{batch_id}_results.zip',
            mimetype='application/zip'
        )

    except Exception as e:
        logger.error(f"Batch download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/geocode', methods=['POST'])
def geocode_address():
    """Standalone geocoding endpoint for testing"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        postal_code = data.get('postal_code')
        address = data.get('address')
        
        if not postal_code and not address:
            return jsonify({'error': 'Either postal_code or address must be provided'}), 400
        
        geocoding_service = GeocodingService()
        lat, lng, method = geocoding_service.geocode(postal_code, address)
        
        if lat is not None and lng is not None:
            google_maps_url = f"https://maps.google.com/?q={lat},{lng}"
            return jsonify({
                'success': True,
                'latitude': lat,
                'longitude': lng,
                'method': method,
                'google_maps_url': google_maps_url,
                'postal_code': postal_code,
                'address': address
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Could not geocode the provided postal code or address',
                'postal_code': postal_code,
                'address': address
            }), 404
            
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Enhanced health check with deployment diagnostics"""
    try:
        start_time = datetime.now()

        # Quick health check first
        health_info = {
            'status': 'healthy',
            'timestamp': start_time.isoformat(),
            'deployment': {
                'environment': 'deployment' if (os.getenv('RENDER') or os.getenv('VERCEL') or os.getenv('HEROKU')) else 'local',
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                'flask_env': os.getenv('FLASK_ENV', 'development')
            }
        }

        # Try geocoding service initialization (with timeout protection)
        try:
            geocoding_service = GeocodingService()

            # Check postal code lookup status
            postal_status = len(geocoding_service.postal_code_lookup) > 0

            # Check Google Maps API status
            google_api_configured = geocoding_service.google_api_key is not None
            google_api_working = geocoding_service.geolocator is not None

            health_info['geocoding'] = {
                'postal_code_lookup': {
                    'enabled': postal_status,
                    'postal_codes_loaded': len(geocoding_service.postal_code_lookup)
                },
                'google_maps_api': {
                    'configured': google_api_configured,
                    'working': google_api_working,
                    'api_key_present': '****' + geocoding_service.google_api_key[-4:] if google_api_configured else None
                }
            }

        except Exception as geocoding_error:
            health_info['geocoding'] = {
                'error': str(geocoding_error),
                'status': 'geocoding_service_failed_but_app_running'
            }

        # Calculate response time
        end_time = datetime.now()
        health_info['response_time_ms'] = int((end_time - start_time).total_seconds() * 1000)

        return jsonify(health_info)

    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Basic request validation
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # File extension validation
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Invalid file format. Please upload Excel files only.'}), 400

        # File size validation (50MB limit)
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        if hasattr(file, 'content_length') and file.content_length > MAX_FILE_SIZE:
            return jsonify({'error': 'File too large. Maximum size is 50MB.'}), 413

        # Content length validation (for chunked requests)
        if request.content_length and request.content_length > MAX_FILE_SIZE:
            return jsonify({'error': 'File too large. Maximum size is 50MB.'}), 413

        # Filename validation
        if len(file.filename) > 255:
            return jsonify({'error': 'Filename too long. Maximum 255 characters.'}), 400

        # Security: prevent path traversal
        import re
        if re.search(r'[<>:"|?*]|\.\.', file.filename):
            return jsonify({'error': 'Invalid characters in filename.'}), 400

        # Extract geocoding preference (default: True)
        use_google_api = request.form.get('use_google_api', 'true').lower() == 'true'
        logger.info(f"Single upload - Google Maps API geocoding: {'ENABLED' if use_google_api else 'DISABLED'}")

        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Save uploaded file
        input_filename = f"{job_id}_input.xlsx"
        input_path = os.path.join(UPLOAD_FOLDER, input_filename)
        file.save(input_path)

        # Validate file content is actually Excel
        try:
            # Quick validation by attempting to read file structure
            pd.ExcelFile(input_path).sheet_names
            logger.info(f"File validation passed for job {job_id}: {file.filename}")
        except Exception as validation_error:
            # Clean up invalid file
            if os.path.exists(input_path):
                os.remove(input_path)
            logger.warning(f"File validation failed for {file.filename}: {validation_error}")
            return jsonify({'error': 'Invalid Excel file. File appears to be corrupted or not a valid Excel format.'}), 400

        # Transform file with multi-sheet support and geocoding preference
        result = ExcelTransformer.transform_excel_multi_sheet(input_path, PROCESSED_FOLDER, job_id, use_google_api)

        if result['success']:
            # Build download URLs for each output file
            download_urls = [f'/download/{job_id}/{filename}' for filename in result['output_files']]

            return jsonify({
                'job_id': job_id,
                'message': result['message'],
                'sheets_processed': result['sheets_processed'],
                'total_records': result['total_records'],
                'terminated_clinics_filtered': result['terminated_clinics_filtered'],
                'output_files': result['output_files'],
                'download_urls': download_urls,
                'results': result['results'],
                'summary_stats': result['summary_stats']
            })
        else:
            return jsonify({
                'error': result['message'],
                'details': result.get('error_details', '')
            }), 500

    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/download/<job_id>/<filename>', methods=['GET'])
def download_specific_file(job_id, filename):
    """Download a specific output file by job ID and filename"""
    try:
        # Validate filename belongs to this job ID
        if not filename.startswith(job_id):
            return jsonify({'error': 'Invalid file for this job'}), 400

        output_path = os.path.join(PROCESSED_FOLDER, filename)

        if not os.path.exists(output_path):
            return jsonify({'error': 'File not found'}), 404

        # Extract sheet name from filename for better download name
        # Format: {job_id}_{sheet_name}.xlsx
        sheet_part = filename.replace(f"{job_id}_", "").replace(".xlsx", "")
        download_name = f"transformed_{sheet_part}.xlsx"

        return send_file(
            output_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<job_id>', methods=['GET'])
def download_file(job_id):
    """Legacy endpoint - download first available file or create zip if multiple files"""
    try:
        # Look for files with this job_id
        import glob
        pattern = os.path.join(PROCESSED_FOLDER, f"{job_id}_*.xlsx")
        matching_files = glob.glob(pattern)

        if not matching_files:
            return jsonify({'error': 'No files found for this job'}), 404

        if len(matching_files) == 1:
            # Single file - return directly
            output_path = matching_files[0]
            filename = os.path.basename(output_path)
            sheet_part = filename.replace(f"{job_id}_", "").replace(".xlsx", "")
            download_name = f"transformed_{sheet_part}.xlsx"

            return send_file(
                output_path,
                as_attachment=True,
                download_name=download_name,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            # Multiple files - create zip
            import zipfile
            import tempfile

            # Create temporary zip file
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')

            with zipfile.ZipFile(temp_zip.name, 'w') as zipf:
                for file_path in matching_files:
                    filename = os.path.basename(file_path)
                    sheet_part = filename.replace(f"{job_id}_", "").replace(".xlsx", "")
                    arc_name = f"transformed_{sheet_part}.xlsx"
                    zipf.write(file_path, arc_name)

            return send_file(
                temp_zip.name,
                as_attachment=True,
                download_name='transformed_templates.zip',
                mimetype='application/zip'
            )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status/<job_id>', methods=['GET'])
def job_status(job_id):
    """Get status of processing job with support for multiple output files"""
    try:
        import glob

        # Look for files with this job_id
        pattern = os.path.join(PROCESSED_FOLDER, f"{job_id}_*.xlsx")
        matching_files = glob.glob(pattern)

        if not matching_files:
            return jsonify({'status': 'not_found'}), 404

        # Gather information about all files
        files_info = []
        total_size = 0
        earliest_time = None

        for file_path in matching_files:
            file_stats = os.stat(file_path)
            filename = os.path.basename(file_path)
            sheet_part = filename.replace(f"{job_id}_", "").replace(".xlsx", "")

            file_info = {
                'filename': filename,
                'sheet_name': sheet_part,
                'file_size': file_stats.st_size,
                'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                'download_url': f'/download/{job_id}/{filename}'
            }
            files_info.append(file_info)
            total_size += file_stats.st_size

            if earliest_time is None or file_stats.st_ctime < earliest_time:
                earliest_time = file_stats.st_ctime

        return jsonify({
            'status': 'completed',
            'files_count': len(files_info),
            'total_size': total_size,
            'created_at': datetime.fromtimestamp(earliest_time).isoformat() if earliest_time else None,
            'files': files_info,
            'download_all_url': f'/download/{job_id}'  # Legacy endpoint for zip download
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def startup_check():
    """Perform startup checks to ensure all dependencies are available"""
    try:
        logger.info("Starting Excel Transformer Backend...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Flask environment: {os.environ.get('FLASK_ENV', 'development')}")
        logger.info(f"Concurrent processing: {'enabled' if CONCURRENT_SUPPORT else 'disabled (sequential fallback)'}")

        # Test basic imports
        import pandas as pd
        logger.info(f"Pandas version: {pd.__version__}")

        # Test geocoding service initialization (non-blocking)
        try:
            geocoding_service = GeocodingService()
            logger.info("Geocoding service initialized successfully")
        except Exception as e:
            logger.warning(f"Geocoding service initialization issue: {e}")

        logger.info("Startup checks completed successfully")
        return True

    except Exception as e:
        logger.error(f"Startup check failed: {e}")
        return False

# Perform startup check
startup_check()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)