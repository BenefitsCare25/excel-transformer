"""iXchange output file generation for Step 4."""

import pandas as pd
from datetime import datetime
from typing import Dict, Optional
from .date_utils import get_today_ddmmyy


class IXchangeGenerator:
    """
    Generates the final iXchange output file.

    Output file: Mediacorp - Employee ADC (iXchange)_DDMMYY.xlsx
    Contains only records with ADC activity (non-empty remarks).
    """

    OUTPUT_COLUMNS = [
        'ADC Remarks',
        'Entity',
        'Staff ID',
        'Employee Name',
        'Identification No.',
        'Date of Birth',
        'Gender',
        'Marital Status',
        'Date of Hire',
        'Last Day of Service',
        'Email Address',
        'Mobile Phone',
        'Flex Category',
    ]

    EL_COL_MAPPING = {
        'Entity': 0,
        'Staff ID': 1,
        'Employee Name': 3,
        'Identification No.': 4,
        'Date of Birth': 5,
        'Gender': 6,
        'Marital Status': 7,
        'Date of Hire': 12,
        'Last Day of Service': 14,
        'Email Address': 17,
        'Mobile Phone': 18,
    }

    def __init__(self):
        pass

    def generate(
        self,
        processed_el_df: pd.DataFrame,
        filter_adc_only: bool = True
    ) -> pd.DataFrame:
        """Generate iXchange output DataFrame."""
        output_data = {}

        for col_name in self.OUTPUT_COLUMNS:
            if col_name == 'Flex Category':
                output_data[col_name] = processed_el_df['Flex Category'].copy()
            elif col_name == 'ADC Remarks':
                output_data[col_name] = processed_el_df['ADC Remarks'].copy()
            else:
                col_idx = self.EL_COL_MAPPING[col_name]
                if col_idx < len(processed_el_df.columns):
                    output_data[col_name] = processed_el_df.iloc[:, col_idx].copy()
                else:
                    output_data[col_name] = ''

        output_df = pd.DataFrame(output_data)

        if filter_adc_only:
            output_df = output_df[
                output_df['ADC Remarks'].notna() &
                (output_df['ADC Remarks'].astype(str).str.strip() != '')
            ].copy()

        return output_df

    def generate_filename(self, prefix: str = "Mediacorp - Employee ADC (iXchange)") -> str:
        """Generate output filename with date."""
        date_str = get_today_ddmmyy()
        return f"{prefix}_{date_str}.xlsx"


def create_combined_output(
    processed_el_df: pd.DataFrame,
    processed_dl_df: pd.DataFrame,
    output_path: Optional[str] = None
) -> Dict[str, pd.DataFrame]:
    """
    Create combined output with multiple sheets.

    Sheets:
    1. Processed EL - Full employee listing with categories and remarks
    2. Processed DL - Full dependant listing with comparison columns
    3. Employee - 13-column iXchange format (ADC records only)
    """
    generator = IXchangeGenerator()
    ixchange_df = generator.generate(processed_el_df, filter_adc_only=True)

    # Filter Processed EL to only rows with non-empty ADC Remarks
    filtered_el = processed_el_df[
        processed_el_df['ADC Remarks'].notna() &
        (processed_el_df['ADC Remarks'].astype(str).str.strip() != '')
    ].copy()

    # Move ADC Remarks to first column for Processed EL
    el_cols = ['ADC Remarks'] + [c for c in filtered_el.columns if c != 'ADC Remarks']
    filtered_el = filtered_el[el_cols]

    # Move Inspro ADC Remarks to first column for Processed DL
    dl_remarks_col = 'Inspro ADC Remarks'
    if dl_remarks_col in processed_dl_df.columns:
        dl_cols = [dl_remarks_col] + [c for c in processed_dl_df.columns if c != dl_remarks_col]
        processed_dl_df = processed_dl_df[dl_cols]

    sheets = {
        'Processed EL': filtered_el,
        'Processed DL': processed_dl_df,
        'Employee': ixchange_df
    }

    return sheets


ixchange_generator = IXchangeGenerator()
