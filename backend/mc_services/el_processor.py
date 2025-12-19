"""Employee Listing processing for Steps 1 and 3."""

import pandas as pd
from typing import List, Dict
from .category_mapper import apply_category_mapping
from .date_utils import format_date_ddmmyy, is_blank, is_not_blank


class ELProcessor:
    """
    Processes Employee Listing files for ADC operations.

    Step 1: Category Tagging (AIA Category + Flex Category)
    Step 3: EL Comparison (detect additions, deletions, changes)
    """

    COL_ENTITY = 0
    COL_STAFF_ID = 1
    COL_LOGIN_ID = 2
    COL_NAME = 3
    COL_ID_NO = 4
    COL_DOB = 5
    COL_GENDER = 6
    COL_MARITAL = 7
    COL_OVERSEAS = 8
    COL_EMP_TYPE = 9
    COL_FOREIGN_PASS = 10
    COL_NATIONALITY = 11
    COL_HIRE_DATE = 12
    COL_INACTIVE = 13
    COL_LDS = 14
    COL_CATEGORY = 15
    COL_DESIGNATION = 16
    COL_EMAIL = 17
    COL_MOBILE = 18
    COL_BANK_CODE = 19
    COL_BANK_ACCT = 20

    def __init__(self):
        pass

    def process_step1_category_tagging(
        self,
        new_el_df: pd.DataFrame,
        category_mapping_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Step 1: Add AIA Category and Flex Category columns."""
        return apply_category_mapping(
            df=new_el_df.copy(),
            category_mapping_df=category_mapping_df,
            category_col=self.COL_CATEGORY,
            lds_col=self.COL_LDS,
            overseas_col=self.COL_OVERSEAS,
            emp_type_col=self.COL_EMP_TYPE
        )

    def process_step3_el_comparison(
        self,
        new_el_df: pd.DataFrame,
        old_el_df: pd.DataFrame
    ) -> tuple:
        """Step 3: Compare new EL vs old EL and generate ADC remarks.

        Returns:
            tuple: (processed_df, statistics_dict)
        """
        old_el_lookup = self._build_staff_lookup(old_el_df)

        adc_remarks = []

        # Statistics tracking
        stats = {
            'additions': 0,
            'deletions': 0,
            'changes': {
                'entity': 0,
                'name': 0,
                'id_no': 0,
                'overseas': 0,
                'employment_type': 0,
                'category': 0,
                'bank_account': 0
            },
            'warnings': {
                'terminated_no_lds': 0,
                'fin_to_nric': 0,
                'check_category': 0,
                'check_with_hr': 0,
                'has_inactive_date': 0
            }
        }

        for idx, row in new_el_df.iterrows():
            staff_id = self._get_safe_value(row, self.COL_STAFF_ID)
            remarks = []

            staff_id_str = str(staff_id).strip() if staff_id else ''

            if staff_id_str not in old_el_lookup:
                hire_date = self._get_safe_value(row, self.COL_HIRE_DATE)
                date_str = format_date_ddmmyy(hire_date)
                remarks.append(f"Addition wef {date_str}" if date_str else "Addition")
                stats['additions'] += 1

                inactive = self._get_safe_value(row, self.COL_INACTIVE)
                if is_not_blank(inactive):
                    remarks.append("Has Inactive Date - Check with HR")
                    stats['warnings']['has_inactive_date'] += 1
                    stats['warnings']['check_with_hr'] += 1
            else:
                old_row = old_el_lookup[staff_id_str]
                change_remarks, change_stats = self._detect_changes_with_stats(row, old_row)

                # Check if this is a termination scenario (Flex Category would be "Terminated")
                new_lds = self._get_safe_value(row, self.COL_LDS)
                new_category = self._get_safe_value(row, self.COL_CATEGORY)
                old_lds = old_row.get('lds')
                is_termination = is_not_blank(new_lds) and is_blank(new_category)
                has_category_change = "Category changed" in change_remarks

                # If termination AND category changed, replace "Category changed" with "Deletion wef xxx"
                if is_termination and has_category_change:
                    date_str = format_date_ddmmyy(new_lds)
                    deletion_remark = f"Deletion wef {date_str}" if date_str else "Deletion"

                    # Replace Category changed with Deletion
                    filtered_remarks = [r for r in change_remarks if r != "Category changed"]
                    filtered_remarks.append(deletion_remark)
                    remarks.extend(filtered_remarks)
                    stats['deletions'] += 1
                else:
                    remarks.extend(change_remarks)
                    # Add deletion if LDS changed from blank to value
                    if is_not_blank(new_lds) and is_blank(old_lds):
                        date_str = format_date_ddmmyy(new_lds)
                        remarks.append(f"Deletion wef {date_str}" if date_str else "Deletion")
                        stats['deletions'] += 1

                # Aggregate change stats
                for key, count in change_stats['changes'].items():
                    stats['changes'][key] += count
                for key, count in change_stats['warnings'].items():
                    stats['warnings'][key] += count

            # Validate: Terminated category should have LDS date
            category = self._get_safe_value(row, self.COL_CATEGORY)
            new_lds = self._get_safe_value(row, self.COL_LDS)
            if self._is_terminated_category(category) and is_blank(new_lds):
                remarks.append("Terminated but no LDS - Check with HR")
                stats['warnings']['terminated_no_lds'] += 1
                stats['warnings']['check_with_hr'] += 1

            adc_remarks.append('; '.join(remarks) if remarks else '')

        new_el_df['ADC Remarks'] = adc_remarks

        return new_el_df, stats

    def _build_staff_lookup(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """Build a lookup dictionary from DataFrame by Staff ID."""
        lookup = {}
        for idx, row in df.iterrows():
            staff_id = self._get_safe_value(row, self.COL_STAFF_ID)
            if staff_id:
                staff_id_str = str(staff_id).strip()
                lookup[staff_id_str] = {
                    'entity': self._get_safe_value(row, self.COL_ENTITY),
                    'name': self._get_safe_value(row, self.COL_NAME),
                    'id_no': self._get_safe_value(row, self.COL_ID_NO),
                    'overseas': self._get_safe_value(row, self.COL_OVERSEAS),
                    'emp_type': self._get_safe_value(row, self.COL_EMP_TYPE),
                    'category': self._get_safe_value(row, self.COL_CATEGORY),
                    'inactive': self._get_safe_value(row, self.COL_INACTIVE),
                    'lds': self._get_safe_value(row, self.COL_LDS),
                    'bank_acct': self._get_safe_value(row, self.COL_BANK_ACCT),
                    'foreign_pass': self._get_safe_value(row, self.COL_FOREIGN_PASS),
                    'designation': self._get_safe_value(row, self.COL_DESIGNATION),
                }
        return lookup

    def _get_safe_value(self, row: pd.Series, col_idx: int):
        """Safely get value from row by column index."""
        try:
            if col_idx < len(row):
                return row.iloc[col_idx]
        except Exception:
            pass
        return None

    def _detect_changes(self, new_row: pd.Series, old_data: Dict) -> List[str]:
        """Detect changes between new and old row data."""
        changes, _ = self._detect_changes_with_stats(new_row, old_data)
        return changes

    def _detect_changes_with_stats(self, new_row: pd.Series, old_data: Dict) -> tuple:
        """Detect changes between new and old row data with statistics.

        Returns:
            tuple: (list of change remarks, stats dict)
        """
        changes = []
        stats = {
            'changes': {
                'entity': 0,
                'name': 0,
                'id_no': 0,
                'overseas': 0,
                'employment_type': 0,
                'category': 0,
                'bank_account': 0
            },
            'warnings': {
                'fin_to_nric': 0,
                'check_category': 0
            }
        }

        comparisons = [
            (self.COL_ENTITY, 'Entity', 'entity', None, 'entity'),
            (self.COL_NAME, 'Name', 'name', None, 'name'),
            (self.COL_ID_NO, 'Identification No.', 'id_no', 'fin_to_nric', 'id_no'),
            (self.COL_OVERSEAS, 'Overseas Assignment', 'overseas', None, 'overseas'),
            (self.COL_EMP_TYPE, 'Employment Type', 'emp_type', 'check_category', 'employment_type'),
            (self.COL_CATEGORY, 'Category', 'category', None, 'category'),
            (self.COL_BANK_ACCT, 'Bank Account', 'bank_acct', None, 'bank_account'),
        ]

        for col_idx, field_name, old_key, special, stat_key in comparisons:
            new_val = self._get_safe_value(new_row, col_idx)
            old_val = old_data.get(old_key)

            if self._values_differ(new_val, old_val):
                change_msg = f"{field_name} changed"
                stats['changes'][stat_key] += 1

                if special == 'fin_to_nric':
                    if self._is_fin_to_nric_change(old_val, new_val):
                        change_msg = "ID changed (FIN to NRIC) - Check Foreign Employment Pass"
                        stats['warnings']['fin_to_nric'] += 1

                if special == 'check_category':
                    change_msg = "Employment Type changed - Check Category/Designation"
                    stats['warnings']['check_category'] += 1

                changes.append(change_msg)

        return changes, stats

    def _values_differ(self, new_val, old_val) -> bool:
        """Compare two values, handling NaN/None cases."""
        if is_blank(new_val) and is_blank(old_val):
            return False
        if is_blank(new_val) or is_blank(old_val):
            return True
        return str(new_val).strip().lower() != str(old_val).strip().lower()

    def _is_fin_to_nric_change(self, old_val, new_val) -> bool:
        """Check if ID change is from FIN to NRIC."""
        if is_blank(old_val) or is_blank(new_val):
            return False

        old_str = str(old_val).strip().upper()
        new_str = str(new_val).strip().upper()

        fin_prefixes = ('F', 'G')
        nric_prefixes = ('S', 'T')

        old_is_fin = old_str and old_str[0] in fin_prefixes
        new_is_nric = new_str and new_str[0] in nric_prefixes

        return old_is_fin and new_is_nric

    def _is_terminated_category(self, category) -> bool:
        """Check if category indicates terminated status."""
        if is_blank(category):
            return False
        cat_str = str(category).strip().lower()
        return 'terminated' in cat_str


el_processor = ELProcessor()
