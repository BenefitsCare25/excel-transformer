"""Dependant Listing processing for Step 2."""

import pandas as pd
from typing import Dict, Set, Optional
from .date_utils import format_date_ddmmyy, is_blank, is_not_blank


class DLProcessor:
    """
    Processes Dependant Listing files for ADC operations.

    Step 2: DL Comparison and ADC generation
    """

    COL_STAFF_ID = 0
    COL_DEP_ID = 1
    COL_FIRST_NAME = 2
    COL_LAST_NAME = 3
    COL_DEP_ID_NO = 4
    COL_RELATIONSHIP = 5
    COL_GENDER = 6
    COL_DOB = 7
    COL_LDS = 8

    EL_COL_STAFF_ID = 1
    EL_COL_ID_NO = 4
    EL_COL_LDS = 14

    def __init__(self):
        pass

    def process_step2_dl_comparison(
        self,
        new_dl_df: pd.DataFrame,
        old_dl_df: pd.DataFrame,
        processed_el_df: pd.DataFrame,
        file_date: Optional[str] = None
    ) -> tuple:
        """Step 2: DL Comparison and ADC generation.

        Args:
            file_date: DDMMYY string from the new DL file's modification date.
                       Used as the effective date for new dependant ADC remarks.

        Returns:
            tuple: (processed_df, statistics_dict)
        """
        el_id_numbers = self._build_el_id_lookup(processed_el_df)
        el_staff_to_aia = self._build_staff_aia_lookup(processed_el_df)
        el_staff_to_lds = self._build_staff_lds_lookup(processed_el_df)
        old_dep_map = self._build_dep_id_map(old_dl_df)
        old_dep_ids = set(old_dep_map.keys())

        results = {
            'DEP is Employee': [],
            'DEP who are EE': [],
            'DEP ID Check': [],
            'AIA Category': [],
            'Inspro ADC Remarks': [],
            'Change Details': [],
        }

        # Statistics tracking
        stats = {
            'new_spouse': 0,
            'new_child': 0,
            'new_other': 0,
            'deletions': 0,
            'dropoffs': 0,
            'name_nric_changes': 0,
            'warnings': {
                'dep_is_employee': 0,
                'terminated_ee_coverage': 0,
                'check_with_hr': 0
            }
        }

        for idx, row in new_dl_df.iterrows():
            dep_id_no = self._get_safe_value(row, self.COL_DEP_ID_NO)
            staff_id = self._get_safe_value(row, self.COL_STAFF_ID)
            dep_id = self._get_safe_value(row, self.COL_DEP_ID)
            relationship = self._get_safe_value(row, self.COL_RELATIONSHIP)
            dep_id_no_str = str(dep_id_no).strip().upper() if dep_id_no else ''
            staff_id_str = str(staff_id).strip() if staff_id else ''
            dep_id_str = str(dep_id).strip() if dep_id else ''

            is_employee = 'Yes' if dep_id_no_str in el_id_numbers else ''
            results['DEP is Employee'].append(is_employee)
            if is_employee == 'Yes':
                stats['warnings']['dep_is_employee'] += 1

            dep_who_are_ee = ''
            if is_employee == 'Yes':
                ee_lds = el_staff_to_lds.get(dep_id_no_str)
                if is_not_blank(ee_lds):
                    dep_who_are_ee = 'Terminated EE - Check coverage'
                    stats['warnings']['terminated_ee_coverage'] += 1

            results['DEP who are EE'].append(dep_who_are_ee)

            # Check LDS for deletion tracking (used in remarks generation)
            lds_check = ''
            ee_lds = el_staff_to_lds.get(staff_id_str)
            if is_not_blank(ee_lds):
                lds_check = format_date_ddmmyy(ee_lds)
                stats['deletions'] += 1

            is_new = dep_id_str and dep_id_str not in old_dep_ids
            dep_id_check = '#N/A' if is_new else ''
            results['DEP ID Check'].append(dep_id_check)

            aia_cat = el_staff_to_aia.get(staff_id_str, '')
            results['AIA Category'].append(aia_cat)

            change_details = ''
            change_type = None
            if not is_new and dep_id_str and dep_id_str in old_dep_map:
                first_name_new = str(self._get_safe_value(row, self.COL_FIRST_NAME) or '').strip()
                last_name_new = str(self._get_safe_value(row, self.COL_LAST_NAME) or '').strip()
                nric_new = str(dep_id_no or '').strip().upper()
                old = old_dep_map[dep_id_str]
                name_changed = (
                    first_name_new.upper() != old['first_name'].upper() or
                    last_name_new.upper() != old['last_name'].upper()
                )
                nric_changed = nric_new != old['nric']
                if name_changed:
                    old_name = f"{old['first_name']} {old['last_name']}".strip()
                    new_name = f"{first_name_new} {last_name_new}".strip()
                if name_changed and nric_changed:
                    change_type = 'name_nric'
                    change_details = f"Name: '{old_name}' → '{new_name}'; NRIC: '{old['nric']}' → '{nric_new}'"
                elif name_changed:
                    change_type = 'name'
                    change_details = f"Name: '{old_name}' → '{new_name}'"
                elif nric_changed:
                    change_type = 'nric'
                    change_details = f"NRIC: '{old['nric']}' → '{nric_new}'"

            results['Change Details'].append(change_details)
            if change_type:
                stats['name_nric_changes'] += 1

            remarks, remark_type = self._generate_adc_remarks_with_type(
                is_new=is_new,
                relationship=relationship,
                effective_date=file_date,
                lds_check=lds_check,
                is_employee=is_employee,
                dep_who_are_ee=dep_who_are_ee,
                change_type=change_type
            )
            results['Inspro ADC Remarks'].append(remarks)

            # Track statistics by remark type
            if remark_type == 'new_spouse':
                stats['new_spouse'] += 1
            elif remark_type == 'new_child':
                stats['new_child'] += 1
            elif remark_type == 'new_other':
                stats['new_other'] += 1
                stats['warnings']['check_with_hr'] += 1

        result_df = new_dl_df.copy()
        for col_name, values in results.items():
            result_df[col_name] = values

        result_df, dropoff_count = self._add_dropoff_data_with_count(result_df, new_dl_df, old_dl_df)
        stats['dropoffs'] = dropoff_count

        return result_df, stats

    def _build_el_id_lookup(self, el_df: pd.DataFrame) -> Set[str]:
        """Build set of all ID numbers from Employee Listing."""
        id_set = set()
        if el_df is not None and len(el_df.columns) > self.EL_COL_ID_NO:
            for val in el_df.iloc[:, self.EL_COL_ID_NO].dropna():
                id_set.add(str(val).strip().upper())
        return id_set

    def _build_staff_aia_lookup(self, el_df: pd.DataFrame) -> Dict[str, str]:
        """Build Staff ID -> AIA Category lookup."""
        lookup = {}
        if el_df is not None and 'AIA Category' in el_df.columns:
            for idx, row in el_df.iterrows():
                staff_id = row.iloc[self.EL_COL_STAFF_ID] if self.EL_COL_STAFF_ID < len(row) else None
                aia_cat = row['AIA Category']
                if staff_id:
                    lookup[str(staff_id).strip()] = str(aia_cat) if aia_cat else ''
        return lookup

    def _build_staff_lds_lookup(self, el_df: pd.DataFrame) -> Dict[str, str]:
        """Build Staff ID -> Last Day of Service lookup."""
        lookup = {}
        if el_df is not None and len(el_df.columns) > self.EL_COL_LDS:
            for idx, row in el_df.iterrows():
                staff_id = row.iloc[self.EL_COL_STAFF_ID] if self.EL_COL_STAFF_ID < len(row) else None
                lds = row.iloc[self.EL_COL_LDS] if self.EL_COL_LDS < len(row) else None
                if staff_id:
                    lookup[str(staff_id).strip()] = lds
        return lookup

    def _build_dep_id_set(self, dl_df: pd.DataFrame) -> Set[str]:
        """Build set of all Dependent IDs from a Dependant Listing."""
        dep_ids = set()
        if dl_df is not None and len(dl_df.columns) > self.COL_DEP_ID:
            for val in dl_df.iloc[:, self.COL_DEP_ID].dropna():
                dep_ids.add(str(val).strip())
        return dep_ids

    def _build_dep_id_map(self, dl_df: pd.DataFrame) -> Dict[str, dict]:
        """Build Dependent ID → {first_name, last_name, nric} from a Dependant Listing."""
        dep_map = {}
        if dl_df is None or len(dl_df.columns) <= self.COL_DEP_ID:
            return dep_map
        for _, row in dl_df.iterrows():
            dep_id = self._get_safe_value(row, self.COL_DEP_ID)
            if dep_id:
                dep_map[str(dep_id).strip()] = {
                    'first_name': str(self._get_safe_value(row, self.COL_FIRST_NAME) or '').strip(),
                    'last_name': str(self._get_safe_value(row, self.COL_LAST_NAME) or '').strip(),
                    'nric': str(self._get_safe_value(row, self.COL_DEP_ID_NO) or '').strip().upper(),
                }
        return dep_map

    def _get_safe_value(self, row: pd.Series, col_idx: int):
        """Safely get value from row by column index."""
        try:
            if col_idx < len(row):
                return row.iloc[col_idx]
        except Exception:
            pass
        return None

    def _generate_adc_remarks_with_type(
        self,
        is_new: bool,
        relationship: Optional[str],
        effective_date,
        lds_check: str,
        is_employee: str,
        dep_who_are_ee: str,
        change_type: Optional[str] = None
    ) -> tuple:
        """Generate Inspro ADC Remarks with type classification.

        Returns:
            tuple: (remarks_string, remark_type)
            remark_type: 'deletion', 'new_spouse', 'new_child', 'new_other',
                         'name_change', 'nric_change', 'name_nric_change', 'dep_employee', or None
        """
        if lds_check:
            return "Deletion", 'deletion'

        if is_new:
            wef_str = f" wef {effective_date}" if effective_date else ""

            relationship_str = str(relationship).upper() if relationship else ''

            if 'SPOUSE' in relationship_str or 'WIFE' in relationship_str or 'HUSBAND' in relationship_str:
                return f"New Spouse{wef_str}", 'new_spouse'
            elif 'CHILD' in relationship_str or 'SON' in relationship_str or 'DAUGHTER' in relationship_str:
                return f"New Child{wef_str}", 'new_child'
            else:
                return f"New Dependant{wef_str} - Check with HR", 'new_other'

        if change_type == 'name_nric':
            return "Name and NRIC Changed", 'name_nric_change'
        if change_type == 'name':
            return "Name Changed", 'name_change'
        if change_type == 'nric':
            return "NRIC Changed", 'nric_change'

        if is_employee == 'Yes':
            if dep_who_are_ee:
                return dep_who_are_ee, 'dep_employee'
            return "DEP is also Employee - Check coverage", 'dep_employee'

        return '', None

    def _add_dropoff_data(
        self,
        result_df: pd.DataFrame,
        new_dl_df: pd.DataFrame,
        old_dl_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Add column to track records that dropped off."""
        result_df, _ = self._add_dropoff_data_with_count(result_df, new_dl_df, old_dl_df)
        return result_df

    def _add_dropoff_data_with_count(
        self,
        result_df: pd.DataFrame,
        new_dl_df: pd.DataFrame,
        old_dl_df: pd.DataFrame
    ) -> tuple:
        """Add column to track records that dropped off with count.

        Returns:
            tuple: (result_df, dropoff_count)
        """
        new_dep_ids = self._build_dep_id_set(new_dl_df)

        dropoffs = []
        for idx, row in old_dl_df.iterrows():
            old_dep_id = self._get_safe_value(row, self.COL_DEP_ID)
            if old_dep_id:
                old_dep_id_str = str(old_dep_id).strip()
                if old_dep_id_str not in new_dep_ids:
                    dropoffs.append({
                        'Staff ID': self._get_safe_value(row, self.COL_STAFF_ID),
                        'Dependent ID': old_dep_id,
                        'Name': f"{self._get_safe_value(row, self.COL_FIRST_NAME) or ''} {self._get_safe_value(row, self.COL_LAST_NAME) or ''}".strip(),
                        'Status': 'Dropped from listing',
                        'Relationship': self._get_safe_value(row, self.COL_RELATIONSHIP),
                        'Dep NRIC': self._get_safe_value(row, self.COL_DEP_ID_NO),
                        'DOB': self._get_safe_value(row, self.COL_DOB),
                    })

        result_df.attrs['dropoffs'] = dropoffs

        return result_df, len(dropoffs)


dl_processor = DLProcessor()
