"""Excel file handling utilities for Mediacorp ADC Processor."""

import pandas as pd
from typing import Tuple, Dict, List


class ExcelHandler:
    """Handles Excel file read/write operations with pandas and openpyxl."""

    def load_el_file(self, file_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load Employee Listing file with main data and Category Mapping.

        Args:
            file_path: Path to the Excel file

        Returns:
            Tuple of (main_data_df, category_mapping_df)
        """
        xl = pd.ExcelFile(file_path)
        main_df = pd.read_excel(xl, sheet_name=0)

        category_df = pd.DataFrame()
        if 'Category Mapping' in xl.sheet_names:
            raw_mapping = pd.read_excel(xl, sheet_name='Category Mapping', header=None)
            category_df = self._parse_category_mapping(raw_mapping)

        return main_df, category_df

    def _parse_category_mapping(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """Parse the Category Mapping sheet to extract the mapping table."""
        if raw_df.empty or len(raw_df) < 3:
            return pd.DataFrame(columns=['Mediacorp Category', 'AIA Category'])

        mapping_data = []
        for idx, row in raw_df.iterrows():
            if idx < 1:
                continue
            if idx == 1:
                continue

            mediacorp_cat = row.iloc[0] if pd.notna(row.iloc[0]) else None
            aia_cat = row.iloc[1] if len(row) > 1 and pd.notna(row.iloc[1]) else None

            if mediacorp_cat is None or str(mediacorp_cat).strip() == '':
                continue
            if 'formula' in str(mediacorp_cat).lower():
                break
            if 'total' in str(mediacorp_cat).lower():
                break

            mapping_data.append({
                'Mediacorp Category': str(mediacorp_cat).strip(),
                'AIA Category': str(aia_cat).strip() if aia_cat else ''
            })

        return pd.DataFrame(mapping_data)

    def load_dl_file(self, file_path: str) -> pd.DataFrame:
        """Load Dependant Listing file."""
        return pd.read_excel(file_path, sheet_name=0)

    def save_multi_sheet_excel(self, file_path: str, sheets: Dict[str, pd.DataFrame]) -> str:
        """Save multiple DataFrames to an Excel file with separate sheets."""
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            for sheet_name, df in sheets.items():
                safe_name = sheet_name[:31]
                df.to_excel(writer, sheet_name=safe_name, index=False)

        return file_path

    def get_sheet_names(self, file_path: str) -> List[str]:
        """Get list of sheet names from an Excel file."""
        xl = pd.ExcelFile(file_path)
        return xl.sheet_names


excel_handler = ExcelHandler()
