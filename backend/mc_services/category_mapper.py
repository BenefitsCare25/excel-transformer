"""Category mapping logic for AIA Category and Flex Category determination."""

import pandas as pd
from typing import Optional
from .date_utils import is_blank, is_not_blank


class CategoryMapper:
    """
    Handles AIA Category lookup and Flex Category determination.

    Implements the Excel formulas:
    - AIA Category: VLOOKUP from Category Mapping
    - Flex Category: Complex nested IF logic
    """

    def __init__(self, category_mapping_df: pd.DataFrame):
        """Initialize with category mapping data."""
        self.mapping = {}
        if not category_mapping_df.empty:
            for _, row in category_mapping_df.iterrows():
                mediacorp = row.get('Mediacorp Category', '')
                aia = row.get('AIA Category', '')
                if mediacorp:
                    self.mapping[str(mediacorp).strip()] = str(aia).strip() if aia else ''

    def get_aia_category(self, category: Optional[str]) -> str:
        """Get AIA Category from Mediacorp Category via VLOOKUP."""
        if is_blank(category):
            return ''

        category_str = str(category).strip()
        return self.mapping.get(category_str, '')

    def get_flex_category(
        self,
        last_day_of_service: Optional[str],
        category: Optional[str],
        overseas_assignment: Optional[str],
        employment_type: Optional[str],
        aia_category: str
    ) -> str:
        """Determine Flex Category using complex nested IF logic."""
        lds_blank = is_blank(last_day_of_service)
        cat_blank = is_blank(category)

        if not lds_blank and cat_blank:
            return "Terminated"

        if lds_blank and cat_blank:
            return "Overseas Based except for Malaysia & Thailand"

        if not cat_blank:
            return self._determine_flex_from_details(
                overseas_assignment,
                employment_type,
                aia_category
            )

        return ""

    def _determine_flex_from_details(
        self,
        overseas_assignment: Optional[str],
        employment_type: Optional[str],
        aia_category: str
    ) -> str:
        """Determine Flex Category based on overseas/employment/AIA details."""
        overseas = str(overseas_assignment).strip() if overseas_assignment else ''
        emp_type = str(employment_type).strip() if employment_type else ''
        aia_cat = str(aia_category).strip() if aia_category else ''

        if overseas.lower() == 'secondment':
            return "Regular/FTH/RR (SG) - Secondee"

        if overseas.lower() == 'overseas ee' or 'overseas' in overseas.lower():
            if emp_type.lower() == 'cwf' or 'cwf' in emp_type.lower():
                return "Overseas Based in Malaysia & Thailand - CWF"
            if emp_type.lower() in ('regular', 'fixed term hire') or \
               'regular' in emp_type.lower() or 'fixed' in emp_type.lower():
                return "Overseas Based in Malaysia & Thailand - Reg/FTH/RR"

        if aia_cat in ('Plan A', 'Plan B1', 'Plan C', 'Plan D', 'Plan E'):
            return "Regular/FTH/RR (SG)"

        if aia_cat in ('Plan G', 'Plan H'):
            return "Regular/FTH/RR (SG) - FW"

        if aia_cat == 'Plan F2' and ('intern' in emp_type.lower()):
            return "Interns (SG)"

        if aia_cat in ('Plan F1', 'Plan F2'):
            return "CWF (SG)"

        if aia_cat == 'Plan F3':
            return "CWF (SG) - FW"

        return ""


def apply_category_mapping(
    df: pd.DataFrame,
    category_mapping_df: pd.DataFrame,
    category_col: int = 15,
    lds_col: int = 14,
    overseas_col: int = 8,
    emp_type_col: int = 9
) -> pd.DataFrame:
    """Apply AIA Category and Flex Category to a DataFrame."""
    mapper = CategoryMapper(category_mapping_df)

    df['AIA Category'] = df.iloc[:, category_col].apply(mapper.get_aia_category)

    def calc_flex(row):
        return mapper.get_flex_category(
            last_day_of_service=row.iloc[lds_col] if lds_col < len(row) else None,
            category=row.iloc[category_col] if category_col < len(row) else None,
            overseas_assignment=row.iloc[overseas_col] if overseas_col < len(row) else None,
            employment_type=row.iloc[emp_type_col] if emp_type_col < len(row) else None,
            aia_category=row['AIA Category']
        )

    df['Flex Category'] = df.apply(calc_flex, axis=1)

    return df
