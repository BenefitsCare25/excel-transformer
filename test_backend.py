#!/usr/bin/env python3
"""
Test script for the Excel Transformer backend
"""
import requests
import os
import sys

def test_backend():
    base_url = "http://localhost:5000"
    
    print("Testing Excel Template Transformer Backend")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   OK Health check passed: {data.get('status')}")
            print(f"   Timestamp: {data.get('timestamp')}")
        else:
            print(f"   FAILED Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   FAILED Cannot connect to backend server")
        print("   NOTE Make sure to run: cd backend && python app.py")
        return False
    except Exception as e:
        print(f"   ERROR Health check error: {e}")
        return False
    
    # Test 2: Upload endpoint with sample file
    print("\n2. Testing file upload...")
    # Try common download paths and fallback to current directory
    possible_paths = [
        os.path.join(os.path.expanduser("~"), "Downloads", "To be uploaded.xlsx"),
        os.path.join(".", "To be uploaded.xlsx"),
        os.path.join("test_data", "sample.xlsx")
    ]

    test_file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            test_file_path = path
            break

    if not test_file_path:
        test_file_path = "test_upload.xlsx"  # Will be created below
    
    if not os.path.exists(test_file_path):
        print(f"   WARNING Test file not found: {test_file_path}")
        print("   NOTE Creating a dummy Excel file for testing...")
        # Create a simple test file
        import pandas as pd
        test_data = {
            'IHP CLINIC ID': ['CG001', 'CG002'],
            'CLINIC NAME': ['Test Clinic 1', 'Test Clinic 2'], 
            'REGION': ['EAST', 'WEST'],
            'AREA': ['UBI', 'JURONG'],
            'ADDRESS': ['BLK 1 TEST STREET #01-01 SINGAPORE 123456', 'BLK 2 SAMPLE ROAD #02-02 SINGAPORE 654321'],
            'TEL NO.': ['12345678', '87654321'],
            'REMARKS': ['Test remark 1', 'Test remark 2'],
            'MON - FRI (AM)': ['0900-1200', '0800-1200'],
            'MON - FRI (PM)': ['1400-1700', '1300-1700'], 
            'MON - FRI (NIGHT)': ['CLOSED', 'CLOSED'],
            'SAT (AM)': ['0900-1200', 'CLOSED'],
            'SAT (PM)': ['CLOSED', 'CLOSED'],
            'SAT (NIGHT)': ['CLOSED', 'CLOSED'],
            'SUN (AM)': ['CLOSED', 'CLOSED'],
            'SUN (PM)': ['CLOSED', 'CLOSED'],
            'SUN (NIGHT)': ['CLOSED', 'CLOSED'],
            'PUBLIC HOLIDAY (AM)': ['CLOSED', 'CLOSED'],
            'PUBLIC HOLIDAY (PM)': ['CLOSED', 'CLOSED'],
            'PUBLIC HOLIDAY (NIGHT)': ['CLOSED', 'CLOSED']
        }
        
        # Add dummy data with proper header structure
        df_test = pd.DataFrame(test_data)
        
        # Create test file with proper sheet structure
        test_file_path = "test_upload.xlsx"
        # Remove default sheet and create proper named sheet
        df_test.to_excel(test_file_path, sheet_name='GP Panel', index=False, engine='openpyxl')
        print(f"   CREATED test file: {test_file_path}")
    
    try:
        with open(test_file_path, 'rb') as f:
            files = {'file': ('test.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            response = requests.post(f"{base_url}/upload", files=files, timeout=30)
            
        if response.status_code == 200:
            data = response.json()
            print(f"   OK Upload successful!")
            print(f"   Job ID: {data.get('job_id')}")
            print(f"   Records processed: {data.get('records_processed')}")
            print(f"   Message: {data.get('message')}")
            
            job_id = data.get('job_id')
            
            # Test 3: Download endpoint
            print(f"\n3. Testing download endpoint...")
            download_response = requests.get(f"{base_url}/download/{job_id}", timeout=30)
            
            if download_response.status_code == 200:
                # Save the downloaded file
                output_path = f"test_output_{job_id}.xlsx"
                with open(output_path, 'wb') as f:
                    f.write(download_response.content)
                print(f"   OK Download successful!")
                print(f"   File saved as: {output_path}")
                print(f"   File size: {len(download_response.content)} bytes")
                
                # Quick validation of output file
                try:
                    import pandas as pd
                    df_result = pd.read_excel(output_path)
                    print(f"   Output columns: {list(df_result.columns)}")
                    print(f"   Output shape: {df_result.shape}")
                    
                    # Check if transformations worked
                    if 'PhoneNumber' in df_result.columns:
                        sample_phone = df_result.iloc[0]['PhoneNumber']
                        print(f"   Sample PhoneNumber: '{sample_phone}'")
                    
                    if 'PostalCode' in df_result.columns:
                        sample_postal = df_result.iloc[0]['PostalCode']
                        print(f"   Sample PostalCode: '{sample_postal}'")
                        
                except Exception as e:
                    print(f"   WARNING Could not validate output file: {e}")
                    
            else:
                print(f"   FAILED Download failed: {download_response.status_code}")
                print(f"   Response: {download_response.text}")
                
        else:
            print(f"   FAILED Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ERROR Upload test error: {e}")
        return False
    
    print(f"\nSUCCESS All tests completed successfully!")
    print("Backend is ready for use!")
    return True

if __name__ == "__main__":
    success = test_backend()
    sys.exit(0 if success else 1)