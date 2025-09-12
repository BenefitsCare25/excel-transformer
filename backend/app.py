from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import os
import uuid
import re
from datetime import datetime
import traceback

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

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
        """Transform source Excel to target template format"""
        try:
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
            
            # Not available in source data
            df_transformed['Latitude'] = None
            df_transformed['Longitude'] = None
            df_transformed['GoogleMapURL'] = None
            
            # Save transformed file
            df_transformed.to_excel(output_path, index=False)
            
            return {
                'success': True,
                'message': f'Successfully transformed {len(df_transformed)} records',
                'records_processed': len(df_transformed)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error transforming file: {str(e)}',
                'error_details': traceback.format_exc()
            }

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

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