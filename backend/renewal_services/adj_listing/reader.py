"""Read an 'Employee Listing YYYY' sheet into normalised rows for the Adj Listing report.

Two header layouts are supported (auto-detected by the shared header detector):
- Two-row: merged product banners ("GROUP TERM LIFE (GTL)") above a sub-header row.
- Single-row: one header row where each product column carries its code ("GTL Premium").
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import openpyxl

from ..renewal_processor import (
    PRODUCT_TYPE_ABBREVS,
    _ABBREV_RE,
    _detect_header_rows,
    _find_employee_listing_sheet,
    _header_key,
    _normalize,
    _parse_date_value,
    _to_float,
)

logger = logging.getLogger(__name__)

PRODUCT_ORDER = ('GTL', 'GDD', 'GPA', 'GDI', 'GHS', 'GMM', 'GP', 'SP', 'GD')
LIFE_PRODUCTS = frozenset(c for c in PRODUCT_ORDER if PRODUCT_TYPE_ABBREVS[c.lower()] == 1)

_PHRASE_CODES = (
    ('term life', 'GTL'), ('dread disease', 'GDD'), ('personal accident', 'GPA'),
    ('disability income', 'GDI'), ('major medical', 'GMM'), ('hospital', 'GHS'),
    ('surgical', 'GHS'), ('general practitioner', 'GP'), ('specialist', 'SP'), ('dental', 'GD'),
)
_FCL_RE = re.compile(
    r'\b(?:NEL|FCL|free\s*cover\s*limit|non[-\s]*evidence\s*limit)\b\s*[:\-]?\s*(?:S?\$)?\s*'
    r'(\d[\d,]*(?:\.\d+)?)\s*([km])?\b', re.IGNORECASE)
_AMOUNT_SUFFIX = {'k': 1_000, 'm': 1_000_000}
_AGE_RE = re.compile(r'\bage\s*(?:limit)?\s*[:\-]?\s*(\d{2,3})\b', re.IGNORECASE)
_DATE_RANGE_RE = re.compile(
    r'(\d{1,2})\s*([A-Za-z]{3,9})\.?,?\s*(\d{4})\s*(?:-|–|to)\s*\d{1,2}\s*[A-Za-z]{3,9}\.?,?\s*\d{4}')
_DOB_RE = re.compile(r'\bd\.?\s?o\.?\s?b\b')
_ID_NO_RE = re.compile(r'\b(?:id|ic|fin)\s*(?:no|number)\b')

TEXT_FIELDS = frozenset({'admin', 'basis', 'plan_type', 'family'})
MONEY_FIELDS = frozenset({'premium', 'loading_premium'})
DATE_FIELDS = frozenset({'dob', 'doh', 'lds'})
SAVED_RESULT_FIELDS = {'premium': 'premium', 'eligible_si': 'eligible sum insured', 'present_si': 'sum insured'}


@dataclass
class ProductColumns:
    code: str
    life: bool
    cols: Dict[str, List[int]] = field(default_factory=dict)
    header_texts: List[str] = field(default_factory=list)

    def add(self, field_name: str, col: int, text: str) -> bool:
        """Register a column; False when the field already has its (single) column."""
        self.header_texts.append(text)
        cols = self.cols.setdefault(field_name, [])
        if field_name == 'uw_decision' or not cols:
            cols.append(col)
            return True
        return False


@dataclass
class ListingRow:
    source_row: int
    emp: Dict[str, Any]
    products: Dict[str, Dict[str, Any]]


@dataclass
class Listing:
    filename: str
    sheet_name: str
    year: int
    renewal_date: Optional[datetime]
    products: Dict[str, ProductColumns]
    header_limits: Dict[str, Dict[str, float]]
    rows: List[ListingRow]
    warnings: List[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        """Policy period label, e.g. '2024-2025' for a 1 Jul 2024 renewal."""
        if self.renewal_date is None:
            return f"{self.year}-{self.year + 1}"
        start = self.renewal_date
        end_year = start.year if (start.month, start.day) == (1, 1) else start.year + 1
        return str(start.year) if end_year == start.year else f"{start.year}-{end_year}"


def product_code(text: str) -> Optional[str]:
    """Canonical product code for a banner or header ('GROUP TERM LIFE (GTL)' -> 'GTL')."""
    value = _normalize(text)
    if not value:
        return None
    match = _ABBREV_RE.search(value)
    if match:
        return match.group(0).upper()
    lowered = value.lower()
    return next((code for phrase, code in _PHRASE_CODES if phrase in lowered), None)


def _product_field(key: str) -> Optional[str]:
    """Classify a product column header (space-free lowercase) into a field name."""
    if 'typeofadministration' in key or 'administrationbasis' in key or ('headcount' in key and 'named' in key):
        return 'admin'
    if 'decision' in key:
        return 'uw_decision'
    if any(k in key for k in ('status', 'sentto', 'sentdate', 'acceptancedate', 'letter')):
        return None
    ordered = (
        ('applicablesuminsured', 'loading_si'), ('premiumrate', 'loading_rate'),
        ('loadingrate', 'loading_rate'), ('extrahealth', 'loading_premium'),
        ('loadingpremium', 'loading_premium'), ('recreational', 'loading_premium'),
        ('pending', 'pending_si'), ('lastaccepted', 'last_accepted_si'),
        ('eligiblesuminsured', 'eligible_si'), ('suminsured', 'present_si'),
    )
    for token, name in ordered:
        if token in key:
            return name
    if 'premium' in key:
        return None if ('gst' in key or 'w/' in key) else 'premium'
    if 'plantype' in key:
        return 'plan_type'
    if 'family' in key:
        return 'family'
    if any(k in key for k in ('category', 'basis', 'plan')):
        return 'basis'
    return None


def _employee_field(text: str) -> Optional[str]:
    """Classify a non-product column header into an employee field."""
    key = _header_key(text)
    spaced = ' '.join(_normalize(text).lower().split())
    if key == 'entity':
        return 'entity'
    if any(k in key for k in ('empid', 'employeeid', 'staffid', 'employeeno', 'staffno')):
        return 'emp_id'
    if 'name' in key and not any(k in key for k in ('dependant', 'spouse', 'child', 'bank', 'user', 'entity', 'company')):
        return 'name'
    if 'dateofbirth' in key or 'birthdate' in key or _DOB_RE.search(spaced):
        return 'dob'
    if (any(k in key for k in ('nric', 'identification', 'passport', 'nationalid'))
            or _ID_NO_RE.search(spaced) or key.rstrip('.') == 'fin'):
        return 'nric'
    exact = {'familygroup': 'family_group', 'familygrouping': 'family_group', 'spouse': 'spouse',
             'child': 'child', 'children': 'child', 'remarks': 'remarks', 'remark': 'remarks'}
    if key in exact:
        return exact[key]
    contains = (
        (('salary',), 'salary'),
        (('dateofhire', 'hiredate', 'dateofjoin', 'joindate', 'dateofemployment'), 'doh'),
        (('lastdayofservice', 'lastdateofservice', 'dateofexit', 'terminationdate', 'dateofleaving'), 'lds'),
        (('medicalplancategory', 'medicalcategory'), 'medical_category'),
        (('department',), 'department'), (('costcentre', 'costcenter'), 'cost_centre'),
        (('designation', 'jobtitle'), 'designation'), (('countryofwork',), 'country'),
        (('email',), 'email'),
    )
    return next((name for tokens, name in contains if any(t in key for t in tokens)), None)


def _sections(ws, banner_row: int) -> List[Tuple[int, int, str]]:
    """Banner sections on a two-row header, each extended to the next banner's start."""
    found, covered = [], set()
    for merged in ws.merged_cells.ranges:
        if merged.min_row <= banner_row <= merged.max_row:
            value = ws.cell(row=merged.min_row, column=merged.min_col).value
            if value:
                found.append([merged.min_col, merged.max_col, _normalize(value)])
            covered.update(range(merged.min_col, merged.max_col + 1))
    for col in range(1, ws.max_column + 1):
        value = ws.cell(row=banner_row, column=col).value
        if value and col not in covered:
            found.append([col, col, _normalize(value)])
    found.sort()
    for i, section in enumerate(found):
        next_start = found[i + 1][0] if i + 1 < len(found) else ws.max_column + 1
        section[1] = max(section[1], next_start - 1)
    return [tuple(s) for s in found]


def _employee_columns(headers: Dict[int, str], product_cols: set) -> Dict[str, int]:
    """First column (left to right) for each employee field, skipping product columns."""
    emp_cols: Dict[str, int] = {}
    for col in sorted(headers):
        if col in product_cols:
            continue
        name = _employee_field(headers[col])
        if name and name not in emp_cols:
            emp_cols[name] = col
    return emp_cols


def _assign_admin(products: Dict[str, 'ProductColumns'], admin_cols: List[int], headers: Dict[int, str],
                  starts: Dict[str, int]) -> None:
    """Products without their own basis column take the nearest one to their left."""
    for code, product in products.items():
        left = [c for c in admin_cols if c < starts[code]]
        if 'admin' not in product.cols and left:
            product.add('admin', max(left), headers[max(left)])


def _map_two_row(ws, banner_row: int, headers: Dict[int, str], notes: List[str]):
    products: Dict[str, ProductColumns] = {}
    starts: Dict[str, int] = {}
    used: set = set()
    admin_cols = [c for c, t in headers.items() if _product_field(_header_key(t)) == 'admin']
    for start, end, name in _sections(ws, banner_row):
        code = product_code(name)
        if code is None:
            continue
        if code in products:
            notes.append(f"a second '{name}' banner also maps to {code}; only the first {code} section is read")
            continue
        product = products[code] = ProductColumns(code, code in LIFE_PRODUCTS)
        starts[code] = start
        for col in range(start, end + 1):
            text = headers.get(col, '')
            name_field = _product_field(_header_key(text))
            if name_field and name_field != 'admin':
                used.add(col)
                if not product.add(name_field, col, text):
                    notes.append(f"'{text}' also looks like the {code} {name_field} column and was ignored")
            elif name_field is None and product_code(text):
                used.add(col)
        product.header_texts.append(name)
    _assign_admin(products, admin_cols, headers, starts)
    return products, _employee_columns(headers, used | set(admin_cols))


def _map_single_row(headers: Dict[int, str], notes: List[str]):
    products: Dict[str, ProductColumns] = {}
    starts: Dict[str, int] = {}
    used, loose_admin = set(), []
    for col in sorted(headers):
        text = headers[col]
        code = product_code(text)
        name_field = _product_field(_header_key(text))
        if code and name_field:
            product = products.setdefault(code, ProductColumns(code, code in LIFE_PRODUCTS))
            starts.setdefault(code, col)
            used.add(col)
            if not product.add(name_field, col, text):
                notes.append(f"'{text}' also looks like the {code} {name_field} column and was ignored")
        elif code:
            used.add(col)
        elif name_field == 'admin':
            loose_admin.append(col)
    _assign_admin(products, loose_admin, headers, starts)
    return products, _employee_columns(headers, used | set(loose_admin))


def _header_limits(products: Dict[str, ProductColumns]) -> Dict[str, Dict[str, float]]:
    """FCL / age limit printed in header text, e.g. 'NEL: $800,000 or age 71' or 'FCL $800K'."""
    limits = {}
    for code, product in products.items():
        for text in product.header_texts:
            fcl = _FCL_RE.search(text or '')
            if not fcl:
                continue
            multiplier = _AMOUNT_SUFFIX.get((fcl.group(2) or '').lower(), 1)
            entry = {'fcl': float(fcl.group(1).replace(',', '')) * multiplier}
            age = _AGE_RE.search(text[fcl.start():])
            if age:
                entry['age'] = float(age.group(1))
            limits[code] = entry
            break
    return limits


def _parse_text_date(day: str, month: str, year: str) -> Optional[datetime]:
    for fmt in ('%d %B %Y', '%d %b %Y'):
        try:
            return datetime.strptime(f"{day} {month} {year}", fmt)
        except ValueError:
            continue
    return None


def _renewal_date(ws, header_row: int, data_start: int, year: int) -> Optional[datetime]:
    """Start of a policy period text ('1 July 2024 - 30 June 2025'), else the header-area date
    in the sheet's year that appears most often (earliest on a tie)."""
    for row in ws.iter_rows(min_row=1, max_row=min(data_start, ws.max_row), values_only=True):
        for value in row:
            match = _DATE_RANGE_RE.search(value) if isinstance(value, str) else None
            parsed = _parse_text_date(*match.groups()) if match else None
            if parsed and parsed.year in (year - 1, year):
                return parsed
    dates = Counter()
    for row in ws.iter_rows(min_row=1, max_row=header_row, values_only=True):
        for value in row:
            if isinstance(value, datetime) and value.year == year:
                dates[value.replace(hour=0, minute=0, second=0, microsecond=0)] += 1
    if not dates:
        return None
    return max(dates.items(), key=lambda item: (item[1], -item[0].toordinal()))[0]


def _id_text(value) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return _normalize(value)


def _emp_value(field_name: str, value):
    if field_name in DATE_FIELDS:
        parsed = _parse_date_value(value)
        return parsed if parsed is not None else _normalize(value)
    if field_name in ('emp_id', 'nric'):
        text = _id_text(value)
        return text.upper() if field_name == 'nric' else text
    if field_name == 'salary':
        number = _to_float(value)
        return number if number is not None else _normalize(value)
    return _normalize(value)


def _product_values(ws, row: int, product: ProductColumns) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    for name, cols in product.cols.items():
        if name == 'uw_decision':
            parts = [_normalize(ws.cell(row=row, column=c).value) for c in cols]
            values[name] = ' / '.join(p for p in parts if p)
        elif name in TEXT_FIELDS:
            values[name] = _normalize(ws.cell(row=row, column=cols[0]).value)
        else:
            number = _to_float(ws.cell(row=row, column=cols[0]).value)
            values[name] = round(number, 2) if number is not None and name in MONEY_FIELDS else number
    return values


def _read_rows(ws, data_start: int, emp_cols, products) -> List[ListingRow]:
    rows = []
    for row in range(data_start, ws.max_row + 1):
        emp = {name: _emp_value(name, ws.cell(row=row, column=col).value) for name, col in emp_cols.items()}
        if not emp.get('name') or not (emp.get('nric') or emp.get('emp_id') or emp.get('dob')):
            continue
        values = {code: _product_values(ws, row, p) for code, p in products.items()}
        rows.append(ListingRow(source_row=row, emp=emp, products=values))
    return rows


def _check_saved_results(path: str, filename: str, listing: Listing) -> None:
    """Formulas with no saved result read as blank and would silently drop premiums or skip the FCL check."""
    targets: Dict[int, List[Tuple[int, str]]] = {}
    for row in listing.rows:
        for product in listing.products.values():
            for name, label in SAVED_RESULT_FIELDS.items():
                if name in product.cols and row.products[product.code].get(name) is None:
                    targets.setdefault(row.source_row, []).append((product.cols[name][0], f"{product.code} {label}"))
    if not targets:
        return
    unsaved = []
    wb = openpyxl.load_workbook(path, read_only=True)
    try:
        ws = wb[listing.sheet_name]
        first = min(targets)
        for r, values in enumerate(ws.iter_rows(min_row=first, max_row=max(targets), values_only=True), start=first):
            for col, label in targets.get(r, ()):
                value = values[col - 1] if col - 1 < len(values) else None
                if isinstance(value, str) and value.startswith('='):
                    unsaved.append(f"{label}, row {r}")
    finally:
        wb.close()
    if unsaved:
        raise ValueError(
            f"File '{filename}': {len(unsaved)} premium or sum insured formula(s) have no saved result "
            f"(e.g. {unsaved[0]}). Open the file in Excel, save it, and upload it again.")


def read_listing(path: str, filename: str) -> Listing:
    """Load one renewal listing. Raises ValueError with an actionable message on bad input."""
    notes: List[str] = []
    wb = openpyxl.load_workbook(path, data_only=True)
    try:
        sheet_name, year = _find_employee_listing_sheet(wb, filename)
        ws = wb[sheet_name]
        banner_row, header_row, data_start = _detect_header_rows(ws)
        headers = {c: _normalize(ws.cell(row=header_row, column=c).value) for c in range(1, ws.max_column + 1)}
        headers = {c: t for c, t in headers.items() if t}
        if banner_row == header_row:
            products, emp_cols = _map_single_row(headers, notes)
        else:
            products, emp_cols = _map_two_row(ws, banner_row, headers, notes)
        products = {c: p for c, p in products.items() if 'premium' in p.cols or 'eligible_si' in p.cols}
        if 'name' not in emp_cols:
            raise ValueError(f"File '{filename}': no employee name column found in header row {header_row}.")
        if not products:
            raise ValueError(f"File '{filename}': no product columns (GTL, GDD, GHS, GMM, ...) found in header row {header_row}.")
        listing = Listing(
            filename=filename, sheet_name=sheet_name, year=year,
            renewal_date=_renewal_date(ws, header_row, data_start, year),
            products=products, header_limits=_header_limits(products),
            rows=_read_rows(ws, data_start, emp_cols, products),
        )
    finally:
        wb.close()
    if not listing.rows:
        raise ValueError(f"File '{filename}': no employee rows found below header row {header_row}.")
    _check_saved_results(path, filename, listing)
    listing.warnings.extend(f"{filename}: {note}." for note in notes)
    for code, product in listing.products.items():
        if 'premium' not in product.cols:
            listing.warnings.append(f"{filename}: no {code} premium column found - {code} premiums are blank for this year.")
    logger.info(
        "Adj listing read %s: sheet=%s rows=%d products=%s renewal=%s emp_cols=%s",
        filename, sheet_name, len(listing.rows),
        {c: sorted(p.cols) for c, p in products.items()}, listing.renewal_date, sorted(emp_cols),
    )
    return listing
