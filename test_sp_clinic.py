#!/usr/bin/env python3
"""
Test script for SP clinic column extraction enhancements
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

import pandas as pd
from app import ExcelTransformer

def test_sp_clinic_extraction():
    """Test SP clinic specific column extraction"""

    input_file = r"C:\Users\huien\Downloads\AIA - Parkway Shenton Panel SP clinic listing Sep 2025.xlsx"

    print("=== Testing SP Clinic Column Extraction ===")
    print(f"Input file: {input_file}")

    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        return False

    try:
        # Read Excel file to get sheet names
        xl_file = pd.ExcelFile(input_file)
        print(f"Available sheets: {xl_file.sheet_names}")

        # Test SP list sheet
        sheet_name = 'SP list'
        print(f"\n--- Testing Sheet: {sheet_name} ---")

        # Test header detection
        header_row = ExcelTransformer.find_header_row(input_file, sheet_name)
        print(f"Detected header row: {header_row}")

        # Read the sheet with detected header
        df = pd.read_excel(input_file, sheet_name=sheet_name, header=header_row)
        df.columns = df.columns.str.strip()
        print(f"Columns found: {list(df.columns)}")

        # Test column mapping
        col_map = ExcelTransformer.map_columns(df.columns)
        print(f"Column mapping: {col_map}")

        # Check if we got the expected SP clinic columns
        expected_sp_columns = ['clinic_id', 'specialty', 'doctor_name', 'clinic_name', 'address1', 'telephone']
        missing_columns = []

        for expected_col in expected_sp_columns:
            if expected_col not in col_map:
                missing_columns.append(expected_col)

        if missing_columns:
            print(f"WARNING: Missing expected columns: {missing_columns}")
        else:
            print("SUCCESS: All expected SP clinic columns found!")

        # Show sample data for verification
        print(f"\nSample data (first 3 rows):")
        for i in range(min(3, len(df))):
            print(f"Row {i+1}:")
            if 'clinic_id' in col_map:
                print(f"  SP Code: {df.iloc[i][col_map['clinic_id']]}")
            if 'specialty' in col_map:
                print(f"  Specialty: {df.iloc[i][col_map['specialty']]}")
            if 'doctor_name' in col_map:
                print(f"  Doctor: {df.iloc[i][col_map['doctor_name']]}")
            if 'clinic_name' in col_map:
                print(f"  Clinic: {df.iloc[i][col_map['clinic_name']]}")
            if 'address1' in col_map:
                print(f"  Address1: {df.iloc[i][col_map['address1']]}")
            print()

        # Test address construction
        print("--- Testing Address Construction ---")
        addresses = ExcelTransformer.construct_address(df.head(3), col_map)
        for i, addr in enumerate(addresses):
            print(f"Constructed Address {i+1}: {addr}")

        return True

    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_transformation():
    """Test full transformation of SP clinic sheet"""

    input_file = r"C:\Users\huien\Downloads\AIA - Parkway Shenton Panel SP clinic listing Sep 2025.xlsx"

    print("\n=== Testing Full SP Clinic Transformation ===")

    try:
        # Test transformation of SP list sheet
        result = ExcelTransformer.transform_sheet(input_file, 'SP list')

        if not result['success']:
            print(f"Transformation failed: {result['message']}")
            return False

        result_df = result['dataframe']
        print(f"Transformation successful! Shape: {result_df.shape}")
        print(f"Columns: {list(result_df.columns)}")

        # Check key fields
        print("\nKey field statistics:")
        print(f"- Records with Code: {result_df['Code'].notna().sum()}")
        print(f"- Records with Name: {result_df['Name'].notna().sum()}")
        print(f"- Records with Specialty: {result_df['Specialty'].notna().sum()}")
        print(f"- Records with Doctor: {result_df['Doctor'].notna().sum()}")
        print(f"- Records with Address1: {result_df['Address1'].notna().sum()}")
        print(f"- Records with PostalCode: {result_df['PostalCode'].notna().sum()}")

        # Show sample transformed records
        print(f"\nFirst 3 transformed records:")
        for i in range(min(3, len(result_df))):
            print(f"Record {i+1}:")
            print(f"  Code: {result_df.iloc[i]['Code']}")
            print(f"  Name: {result_df.iloc[i]['Name']}")
            print(f"  Specialty: {result_df.iloc[i]['Specialty']}")
            print(f"  Doctor: {result_df.iloc[i]['Doctor']}")
            print(f"  Address1: {result_df.iloc[i]['Address1']}")
            print(f"  PostalCode: {result_df.iloc[i]['PostalCode']}")
            print()

        return True

    except Exception as e:
        print(f"Error during full transformation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing SP Clinic enhancements...")

    success1 = test_sp_clinic_extraction()
    success2 = test_full_transformation()

    if success1 and success2:
        print("\n[SUCCESS] All SP Clinic tests passed!")
    else:
        print("\n[FAILED] Some tests failed!")