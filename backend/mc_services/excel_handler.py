"""Excel and CSV file handling utilities for Mediacorp ADC Processor."""

import pandas as pd
import logging
from typing import Tuple, Dict, List
from .csv_processor import parse_pipe_delimited_csv, is_csv_file
from .category_mapper import get_default_category_mapping_df

logger = logging.getLogger(__name__)


class ExcelHandler:
    """Handles Excel/CSV file read/write operations."""

    def load_el_file(self, file_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load Employee Listing file (XLSX or CSV) with Category Mapping.

        For CSV: parses pipe-delimited data, uses hardcoded category mapping.
        For XLSX: reads normally, checks for embedded Category Mapping sheet.

        Returns:
            Tuple of (main_data_df, category_mapping_df)
        """
        if is_csv_file(file_path):
            main_df = parse_pipe_delimited_csv(file_path, file_type='el')
            category_df = get_default_category_mapping_df()
            logger.info(f"Loaded EL from CSV: {len(main_df)} rows, using hardcoded category mapping")
            return main_df, category_df

        xl = pd.ExcelFile(file_path)
        main_df = pd.read_excel(xl, sheet_name=0)

        category_df = pd.DataFrame()
        if 'Category Mapping' in xl.sheet_names:
            raw_mapping = pd.read_excel(xl, sheet_name='Category Mapping', header=None)
            category_df = self._parse_category_mapping(raw_mapping)

        # Fall back to hardcoded mapping if no Category Mapping sheet found
        if category_df.empty:
            category_df = get_default_category_mapping_df()
            logger.info("No Category Mapping sheet found in XLSX, using hardcoded mapping")

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
        """Load Dependant Listing file (XLSX or CSV)."""
        if is_csv_file(file_path):
            df = parse_pipe_delimited_csv(file_path, file_type='dl')
            logger.info(f"Loaded DL from CSV: {len(df)} rows")
            return df

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
