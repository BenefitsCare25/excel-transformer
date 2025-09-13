from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import os
import uuid
import re
from datetime import datetime
import traceback
import googlemaps
from geopy.geocoders import GoogleV3
from dotenv import load_dotenv
from functools import lru_cache

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
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        self._initialize_google_maps_clients()
        self.postal_code_lookup = self._load_postal_code_lookup()
        self.geocode_stats = {'postal_matches': 0, 'api_calls': 0, 'failures': 0}
    
    def _initialize_google_maps_clients(self):
        """Initialize Google Maps API clients with status logging"""
        if not self.google_api_key:
            print("Google Maps API: NOT CONFIGURED - Using postal code lookup only")
            self.gmaps = None
            self.geolocator = None
            return
        
        try:
            self.gmaps = googlemaps.Client(key=self.google_api_key)
            self.geolocator = GoogleV3(api_key=self.google_api_key)
            print("Google Maps API: CONFIGURED")
        except Exception as e:
            print(f"Google Maps API: FAILED - {e}")
            self.gmaps = None
            self.geolocator = None
    
    
    @lru_cache(maxsize=1)
    def _load_postal_code_lookup(self):
        """Load postal code lookup table from master file"""
        # Try each path in order of preference
        master_file_path = None
        for path in POSTAL_CODE_PATHS:
            if path and os.path.exists(path):
                master_file_path = path
                break
        
        if not master_file_path:
            print("Postal Code Lookup: NO FILE FOUND - Google Maps API only")
            return {}
        
        try:
            df = pd.read_excel(master_file_path)
            
            # Create dictionary for fast lookup: {postal_code: (lat, lng)}
            lookup = {}
            for _, row in df.iterrows():
                # Handle postal code formatting - convert to 6-digit string with leading zeros
                postal_code_raw = row['PostalCode']
                if pd.notna(postal_code_raw):
                    # Convert to int first to remove .0, then format with leading zeros
                    postal_code = f"{int(float(postal_code_raw)):06d}"
                else:
                    continue
                
                lat = row['Latitude'] if pd.notna(row['Latitude']) else None
                lng = row['Longitude'] if pd.notna(row['Longitude']) else None
                if lat is not None and lng is not None:
                    lookup[postal_code] = (float(lat), float(lng))
            
            print(f"Postal Code Lookup: {len(lookup)} Singapore postal codes loaded")
            return lookup
            
        except Exception as e:
            print(f"Postal Code Lookup: FAILED - {e}")
            return {}
    
    def geocode_by_postal_code(self, postal_code):
        """Get coordinates by postal code lookup"""
        if not postal_code or str(postal_code).strip() in ('None', '', 'nan'):
            return None, None
        
        try:
            # Normalize postal code to 6-digit format with leading zeros
            postal_code_str = str(postal_code).strip()
            postal_code_normalized = f"{int(float(postal_code_str)):06d}"
            
            if postal_code_normalized in self.postal_code_lookup:
                self.geocode_stats['postal_matches'] += 1
                lat, lng = self.postal_code_lookup[postal_code_normalized]
                return lat, lng
        except (ValueError, TypeError, AttributeError) as e:
            # Log invalid postal code format for debugging
            print(f"Invalid postal code format: {postal_code} - {e}")
        
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
            print(f"Address geocoding failed for '{address}': {e}")
            return None, None
    
    def geocode(self, postal_code, address):
        """Main geocoding method: try postal code first, then address"""
        # Try postal code lookup first
        lat, lng = self.geocode_by_postal_code(postal_code)
        if lat is not None and lng is not None:
            return lat, lng, 'postal_code'
        
        # Fallback to address geocoding
        lat, lng = self.geocode_by_address(address)
        if lat is not None and lng is not None:
            return lat, lng, 'address'
        
        return None, None, 'failed'
    
    def get_stats(self):
        """Get geocoding statistics"""
        return self.geocode_stats.copy()

class ExcelTransformer:
    @staticmethod
    def find_header_row(file_path, sheet_name=None):
        """Find the actual header row by looking for clinic-related keywords"""
        df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)

        for idx, row in df_raw.iterrows():
            row_values = [str(val) for val in row.values if pd.notna(val)]
            row_text = ' '.join(row_values).lower()

            # Enhanced header detection patterns
            header_patterns = [
                # Primary pattern: S/N with clinic ID
                ('s/n' in row_text and 'clinic' in row_text and 'id' in row_text),
                # Alternative patterns for different sheet layouts
                ('s/n' in row_text and 'region' in row_text and 'area' in row_text),
                ('s/n' in row_text and 'clinic' in row_text and 'name' in row_text),
                ('no.' in row_text and 'clinic' in row_text and 'name' in row_text),
                # For termination sheets
                ('no.' in row_text and 'region' in row_text and 'area' in row_text),
                # Minimum viable header (region + clinic name)
                ('region' in row_text and 'clinic' in row_text and len(row_values) >= 5)
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
        """Classify sheets into panel sheets and termination sheets"""
        panel_sheets = []
        termination_sheets = []

        for sheet in sheet_names:
            sheet_lower = sheet.lower()
            # Identify termination sheets
            if any(term in sheet_lower for term in ['terminat', 'remov', 'cancel', 'delist']):
                termination_sheets.append(sheet)
            # Identify panel sheets (GP, TCM, dental, etc.)
            elif any(panel in sheet_lower for panel in ['gp', 'tcm', 'dental', 'clinic', 'panel']):
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
                df = pd.read_excel(file_path, sheet_name=sheet, header=header_row)
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
                    print(f"Extracted {len(clinic_ids)} terminated clinic IDs from sheet '{sheet}'")
                else:
                    print(f"Warning: Could not find clinic ID column in termination sheet '{sheet}'")

            except Exception as e:
                print(f"Error processing termination sheet '{sheet}': {e}")

        print(f"Total terminated clinic IDs: {len(terminated_ids)}")
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
        """Map available columns to expected template columns"""
        column_mapping = {}

        # Define column mapping patterns (case-insensitive)
        mappings = {
            'clinic_id': ['ihp clinic id', 'provider code', 'clinic id', 'id'],
            'clinic_name': ['clinic name', 'name'],
            'region': ['region'],
            'area': ['area'],
            'address': ['address'],
            'telephone': ['tel no.', 'tel', 'phone', 'telephone'],
            'remarks': ['remarks', 'comment', 'note'],
            'mon_fri_am': ['mon - fri (am)', 'monday - friday'],
            'mon_fri_pm': ['mon - fri (pm)', 'monday - friday (evening)'],
            'mon_fri_night': ['mon - fri (night)'],
            'sat_am': ['sat (am)', 'saturday'],
            'sat_pm': ['sat (pm)'],
            'sat_night': ['sat (night)'],
            'sun_am': ['sun (am)', 'sunday'],
            'sun_pm': ['sun (pm)'],
            'sun_night': ['sun (night)'],
            'holiday_am': ['public holiday (am)', 'public holiday'],
            'holiday_pm': ['public holiday (pm)'],
            'holiday_night': ['public holiday (night)']
        }

        # Convert all column names to lowercase for comparison, handling NaN values
        df_cols_lower = {}
        for col in df_columns:
            if pd.notna(col) and isinstance(col, str):
                df_cols_lower[col.lower().strip()] = col

        # Find best match for each expected column
        for expected_col, patterns in mappings.items():
            for pattern in patterns:
                if pattern in df_cols_lower:
                    column_mapping[expected_col] = df_cols_lower[pattern]
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

                print(f"Inferred column mapping based on position: {inferred_mapping}")

        return inferred_mapping
    
    @staticmethod
    def extract_postal_code(address):
        """Extract postal code from Singapore address"""
        if pd.isna(address):
            return None
        
        # Look for SINGAPORE followed by 6 digits
        match = re.search(r'SINGAPORE\s+(\d{6})', str(address))
        return match.group(1) if match else None
    
    @staticmethod
    def combine_phone_remarks(phone, remarks):
        """Combine telephone number with remarks"""
        phone_str = str(phone) if pd.notna(phone) else ""
        remarks_str = str(remarks) if pd.notna(remarks) else ""
        
        if remarks_str and remarks_str.lower() != 'nan':
            return f"{phone_str} - {remarks_str}"
        return phone_str
    
    @staticmethod
    def combine_operating_hours(row, day_type):
        """Combine AM, PM, NIGHT hours for a specific day type"""
        if day_type == 'weekday':
            am = row.get('MON - FRI (AM)', 'CLOSED')
            pm = row.get('MON - FRI (PM)', 'CLOSED')
            night = row.get('MON - FRI (NIGHT)', 'CLOSED')
        elif day_type == 'saturday':
            am = row.get('SAT (AM)', 'CLOSED')
            pm = row.get('SAT (PM)', 'CLOSED')
            night = row.get('SAT (NIGHT)', 'CLOSED')
        elif day_type == 'sunday':
            am = row.get('SUN (AM)', 'CLOSED')
            pm = row.get('SUN (PM)', 'CLOSED')
            night = row.get('SUN (NIGHT)', 'CLOSED')
        elif day_type == 'public_holiday':
            am = row.get('PUBLIC HOLIDAY (AM)', 'CLOSED')
            pm = row.get('PUBLIC HOLIDAY (PM)', 'CLOSED')
            night = row.get('PUBLIC HOLIDAY (NIGHT)', 'CLOSED')
        else:
            return 'CLOSED/CLOSED/CLOSED'
        
        # Handle NaN values
        am = 'CLOSED' if pd.isna(am) else str(am)
        pm = 'CLOSED' if pd.isna(pm) else str(pm)
        night = 'CLOSED' if pd.isna(night) else str(night)
        
        return f"{am}/{pm}/{night}"

    @staticmethod
    def combine_operating_hours_flexible(df_source, col_map, day_type):
        """Combine operating hours using flexible column mapping"""
        # Define column keys for each day type
        if day_type == 'weekday':
            am_key, pm_key, night_key = 'mon_fri_am', 'mon_fri_pm', 'mon_fri_night'
        elif day_type == 'saturday':
            am_key, pm_key, night_key = 'sat_am', 'sat_pm', 'sat_night'
        elif day_type == 'sunday':
            am_key, pm_key, night_key = 'sun_am', 'sun_pm', 'sun_night'
        elif day_type == 'public_holiday':
            am_key, pm_key, night_key = 'holiday_am', 'holiday_pm', 'holiday_night'
        else:
            return ['CLOSED/CLOSED/CLOSED'] * len(df_source)

        result = []
        for _, row in df_source.iterrows():
            am = row.get(col_map.get(am_key, ''), 'CLOSED') if am_key in col_map else 'CLOSED'
            pm = row.get(col_map.get(pm_key, ''), 'CLOSED') if pm_key in col_map else 'CLOSED'
            night = row.get(col_map.get(night_key, ''), 'CLOSED') if night_key in col_map else 'CLOSED'

            # Handle NaN values
            am = 'CLOSED' if pd.isna(am) else str(am)
            pm = 'CLOSED' if pd.isna(pm) else str(pm)
            night = 'CLOSED' if pd.isna(night) else str(night)

            result.append(f"{am}/{pm}/{night}")

        return result
    
    @staticmethod
    def transform_sheet(input_path, sheet_name, terminated_ids=None):
        """Transform a single sheet to target template format with geocoding"""
        try:
            # Initialize geocoding service
            geocoding_service = GeocodingService()
            
            # Find the correct header row for this sheet
            header_row = ExcelTransformer.find_header_row(input_path, sheet_name)
            
            # Read the source sheet
            df_source = pd.read_excel(input_path, sheet_name=sheet_name, header=header_row)
            df_source.columns = df_source.columns.str.strip()
            
            # Create transformed dataframe
            df_transformed = pd.DataFrame()
            
            # Map columns flexibly
            col_map = ExcelTransformer.map_columns(df_source.columns)
            print(f"Column mapping for sheet '{sheet_name}': {col_map}")

            # If column mapping failed, try to infer from data structure
            if 'clinic_name' not in col_map:
                print(f"Standard column mapping failed for '{sheet_name}', attempting inference...")
                inferred_map = ExcelTransformer.infer_columns_from_data(df_source)
                if 'clinic_name' in inferred_map:
                    col_map.update(inferred_map)
                    print(f"Successfully inferred columns for sheet '{sheet_name}'")
                else:
                    raise ValueError(f"Sheet '{sheet_name}' missing required 'clinic name' column after inference attempt")

            # Filter out terminated clinics if provided
            if terminated_ids and 'clinic_id' in col_map:
                initial_count = len(df_source)
                df_source = df_source[~df_source[col_map['clinic_id']].astype(str).str.strip().isin(terminated_ids)]
                filtered_count = len(df_source)
                print(f"Filtered out {initial_count - filtered_count} terminated clinics from sheet '{sheet_name}'")

            # Flexible mappings using column mapping
            df_transformed['Code'] = df_source[col_map['clinic_id']] if 'clinic_id' in col_map else ''
            df_transformed['Name'] = df_source[col_map['clinic_name']]
            df_transformed['Zone'] = df_source[col_map['region']] if 'region' in col_map else ''
            df_transformed['Area'] = df_source[col_map['area']] if 'area' in col_map else ''
            df_transformed['Specialty'] = None  # Not available in source
            df_transformed['Doctor'] = None  # Not available in source
            df_transformed['Address1'] = df_source[col_map['address']] if 'address' in col_map else ''
            df_transformed['Address2'] = None
            df_transformed['Address3'] = None

            # Extract postal codes from address (only for Singapore addresses)
            def extract_postal_code_smart(address, country):
                """Extract postal code only for Singapore addresses"""
                if country == 'SINGAPORE':
                    return ExcelTransformer.extract_postal_code(address)
                else:
                    return None  # Don't extract postal codes for non-Singapore addresses

            if 'address' in col_map:
                # We need to detect country first before extracting postal codes
                temp_countries = df_source[col_map['address']].apply(
                    lambda addr: 'MALAYSIA' if any(indicator in str(addr).lower() for indicator in [
                        'malaysia', 'johor', 'kuala lumpur', 'selangor', 'penang', 'perak',
                        'kedah', 'kelantan', 'terengganu', 'pahang', 'negeri sembilan',
                        'melaka', 'sabah', 'sarawak', 'perlis', 'putrajaya', 'labuan',
                        'johor bahru', 'kl', 'shah alam', 'petaling jaya'
                    ]) else 'SINGAPORE'
                )

                df_transformed['PostalCode'] = df_source[col_map['address']].combine(
                    temp_countries, extract_postal_code_smart
                )
            else:
                df_transformed['PostalCode'] = None

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
            
            # Operating hours (flexible mapping)
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
    def transform_excel_multi_sheet(input_path, output_dir, job_id):
        """Transform Excel file with multiple sheets to multiple output files"""
        try:
            # Get all sheet names
            xl_file = pd.ExcelFile(input_path)
            sheet_names = xl_file.sheet_names

            # Classify sheets
            panel_sheets, termination_sheets = ExcelTransformer.classify_sheets(sheet_names)

            print(f"Detected {len(panel_sheets)} panel sheets: {panel_sheets}")
            print(f"Detected {len(termination_sheets)} termination sheets: {termination_sheets}")

            # Extract terminated clinic IDs
            terminated_ids = ExcelTransformer.extract_terminated_clinic_ids(input_path, termination_sheets)

            # Process each panel sheet
            results = []
            output_files = []

            for sheet in panel_sheets:
                print(f"Processing sheet: {sheet}")

                # Transform the sheet
                result = ExcelTransformer.transform_sheet(input_path, sheet, terminated_ids)

                if result['success']:
                    # Generate output filename
                    sanitized_name = ExcelTransformer.sanitize_filename(sheet)
                    output_filename = f"{job_id}_{sanitized_name}.xlsx"
                    output_path = os.path.join(output_dir, output_filename)

                    # Save the transformed dataframe
                    result['dataframe'].to_excel(output_path, index=False)

                    # Store result info
                    sheet_result = {
                        'sheet_name': sheet,
                        'output_filename': output_filename,
                        'output_path': output_path,
                        'records_processed': result['records_processed'],
                        'geocoding_stats': result['geocoding_stats']
                    }
                    results.append(sheet_result)
                    output_files.append(output_filename)

                    print(f"SUCCESS: Processed sheet '{sheet}': {result['records_processed']} records")
                else:
                    print(f"FAILED: Could not process sheet '{sheet}': {result['message']}")
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
    """Enhanced health check with API status"""
    geocoding_service = GeocodingService()
    
    # Check postal code lookup status
    postal_status = len(geocoding_service.postal_code_lookup) > 0
    
    # Check Google Maps API status
    google_api_configured = geocoding_service.google_api_key is not None
    google_api_working = geocoding_service.geolocator is not None
    
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'geocoding': {
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
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Invalid file format. Please upload Excel files only.'}), 400

        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Save uploaded file
        input_filename = f"{job_id}_input.xlsx"
        input_path = os.path.join(UPLOAD_FOLDER, input_filename)
        file.save(input_path)

        # Transform file with multi-sheet support
        result = ExcelTransformer.transform_excel_multi_sheet(input_path, PROCESSED_FOLDER, job_id)

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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)