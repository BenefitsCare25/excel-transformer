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
            
            # Clean and format address for Singapore
            address_str = str(address).strip()
            if 'singapore' not in address_str.lower():
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
    def find_header_row(file_path):
        """Find the actual header row by looking for clinic-related keywords"""
        df_raw = pd.read_excel(file_path, header=None)
        
        for idx, row in df_raw.iterrows():
            row_values = [str(val) for val in row.values if pd.notna(val)]
            row_text = ' '.join(row_values).lower()
            
            # Look specifically for the S/N and IHP CLINIC ID pattern
            if 's/n' in row_text and 'clinic' in row_text and 'id' in row_text:
                return idx
                
        # Default fallback
        return 4
    
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
    def transform_excel(input_path, output_path):
        """Transform source Excel to target template format with geocoding"""
        try:
            # Initialize geocoding service
            geocoding_service = GeocodingService()
            
            # Find the correct header row
            header_row = ExcelTransformer.find_header_row(input_path)
            
            # Read the source file
            df_source = pd.read_excel(input_path, header=header_row)
            df_source.columns = df_source.columns.str.strip()
            
            # Create transformed dataframe
            df_transformed = pd.DataFrame()
            
            # Direct mappings
            df_transformed['Code'] = df_source['IHP CLINIC ID']
            df_transformed['Name'] = df_source['CLINIC NAME']
            df_transformed['Zone'] = df_source['REGION']
            df_transformed['Area'] = df_source['AREA']
            df_transformed['Specialty'] = None  # Not available in source
            df_transformed['Doctor'] = None  # Not available in source
            df_transformed['Address1'] = df_source['ADDRESS']
            df_transformed['Address2'] = None
            df_transformed['Address3'] = None
            
            # Extract postal codes from address
            df_transformed['PostalCode'] = df_source['ADDRESS'].apply(
                ExcelTransformer.extract_postal_code
            )
            
            df_transformed['Country'] = 'SINGAPORE'
            
            # Combine phone and remarks
            df_transformed['PhoneNumber'] = df_source.apply(
                lambda row: ExcelTransformer.combine_phone_remarks(
                    row['TEL NO.'], row['REMARKS']
                ), axis=1
            )
            
            # Combine operating hours
            df_transformed['MonToFri'] = df_source.apply(
                lambda row: ExcelTransformer.combine_operating_hours(row, 'weekday'), axis=1
            )
            df_transformed['Saturday'] = df_source.apply(
                lambda row: ExcelTransformer.combine_operating_hours(row, 'saturday'), axis=1
            )
            df_transformed['Sunday'] = df_source.apply(
                lambda row: ExcelTransformer.combine_operating_hours(row, 'sunday'), axis=1
            )
            df_transformed['PublicHoliday'] = df_source.apply(
                lambda row: ExcelTransformer.combine_operating_hours(row, 'public_holiday'), axis=1
            )
            
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
            
            # Save transformed file
            df_transformed.to_excel(output_path, index=False)
            
            # Get geocoding statistics
            stats = geocoding_service.get_stats()
            successful_geocodes = sum(1 for lat in latitudes if lat is not None)
            postal_matches = len([m for m in geocoding_methods if m == 'postal_code'])
            address_matches = len([m for m in geocoding_methods if m == 'address'])
            
            return {
                'success': True,
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
                'message': f'Error transforming file: {str(e)}',
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
        
        # Transform file
        output_filename = f"{job_id}_transformed.xlsx"
        output_path = os.path.join(PROCESSED_FOLDER, output_filename)
        
        result = ExcelTransformer.transform_excel(input_path, output_path)
        
        if result['success']:
            return jsonify({
                'job_id': job_id,
                'message': result['message'],
                'records_processed': result['records_processed'],
                'download_url': f'/download/{job_id}'
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

@app.route('/download/<job_id>', methods=['GET'])
def download_file(job_id):
    try:
        output_filename = f"{job_id}_transformed.xlsx"
        output_path = os.path.join(PROCESSED_FOLDER, output_filename)
        
        if not os.path.exists(output_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            output_path,
            as_attachment=True,
            download_name='transformed_template.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status/<job_id>', methods=['GET'])
def job_status(job_id):
    try:
        output_filename = f"{job_id}_transformed.xlsx"
        output_path = os.path.join(PROCESSED_FOLDER, output_filename)
        
        if os.path.exists(output_path):
            file_stats = os.stat(output_path)
            return jsonify({
                'status': 'completed',
                'file_size': file_stats.st_size,
                'created_at': datetime.fromtimestamp(file_stats.st_ctime).isoformat()
            })
        else:
            return jsonify({'status': 'not_found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)