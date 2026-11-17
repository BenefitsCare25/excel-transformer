"""Excel output for the Adj Listing report: Adj sheet, invoice summary and run notes."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter, quote_sheetname

from .processor import GST_RATE, YEAR_DAYS, AdjReport, OutputRow
from .reader import LIFE_PRODUCTS
from .rules import HEADCOUNT

MONEY = '"$"#,##0.00'
WHOLE = '#,##0'
DATE = 'dd/mm/yyyy'
RED = 'FFFF0000'
CURRENT_ROW_FILL = '92D050'
KEY_HEADER_FILL = 'FFFF00'
PRODUCT_FILLS = {
    'GTL': '92D050', 'GDD': '9BC2E6', 'GPA': 'C9C9C9', 'GDI': 'D9D2E9', 'GHS': 'F4B183',
    'GMM': 'FFE699', 'GP': 'C6E0B4', 'SP': 'BDD7EE', 'GD': 'F8CBAD',
}
INVOICE_SHEET = 'Adj Invoice Summary'
THIN = Side(style='thin')
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

EMPLOYEE_COLUMNS = (
    ('renewal', 'Renewal', 11, None), ('emp_id', 'EMP ID', 11, '@'), ('entity', 'Entity', 22, None),
    ('name', 'Employee Name', 34, None), ('nric', 'Identification No.', 15, '@'),
    ('dob', 'Date of Birth', 12, DATE), ('age', 'Age Next Birthday (at renewal)', 12, '0.00'),
    ('salary', 'Monthly Salary', 12, MONEY), ('doh', 'Date of Hire', 12, DATE),
    ('lds', 'Last Day of Service', 12, DATE), ('medical_category', 'Medical Plan Category', 16, None),
    ('family_group', 'Family Group', 9, None), ('spouse', 'Spouse', 8, None), ('child', 'Child', 8, None),
    ('department', 'Department', 24, None), ('cost_centre', 'Cost Centre', 16, None),
    ('remarks', 'Remarks', 20, None), ('emp_id_2', 'EMP ID', 11, '@'),
    ('designation', 'Designation', 28, None), ('country', 'Country Of Work', 12, None),
)
LIFE_FIELDS = (
    ('admin', '{p} Administration Basis', 16, None), ('basis', '{p} EE Basis of Cover', 28, None),
    ('eligible_si', '{p} EE Eligible Sum Insured', 14, WHOLE),
    ('pending_si', '{p} EE Sum Insured Pending U/W', 14, WHOLE),
    ('last_accepted_si', '{p} EE Last Accepted Sum Insured', 14, WHOLE),
    ('uw_decision', '{p} UW Decision', 20, None), ('loading_rate', '{p} Health Loading Rate', 12, '0.0000'),
    ('loading_premium', '{p} Health Loading Premium', 14, MONEY),
    ('prev_premium', '{prev} {p} Premium', 14, MONEY), ('curr_premium', '{curr} {p} Premium', 14, MONEY),
    ('adj', '{p} Adj Premium', 14, MONEY),
)
MEDICAL_FIELDS = (
    ('basis', '{p} Plan/Basis of Cover', 28, None), ('plan_type', '{p} Plan Type', 12, None),
    ('family', '{p} Family Grouping', 10, None),
    ('prev_premium', '{prev} {p} Premium', 14, MONEY), ('curr_premium', '{curr} {p} Premium', 14, MONEY),
    ('adj', '{p} Premium Adj', 14, MONEY), ('adj_gst', '{p} Adj Premium with GST', 14, MONEY),
)
ADJ_FIELDS = ('adj', 'adj_gst')
MATCH_KEY = 'match_key'


@dataclass
class Column:
    key: str
    header: str
    width: float
    number_format: Optional[str]
    product: Optional[str] = None


def _fill(rgb: str) -> PatternFill:
    return PatternFill(start_color=rgb, end_color=rgb, fill_type='solid')


def put(ws, row: int, column: int, value, formula: bool = False):
    """Write a cell; text from the listings that starts with '=' stays text, never a formula."""
    cell = ws.cell(row=row, column=column, value=value)
    if not formula and isinstance(value, str) and value.startswith('='):
        cell.data_type = 's'
    return cell


def safe_sheet_title(text: str) -> str:
    return re.sub(r"[\\/*?:\[\]&']", '', text).strip()[:31] or 'Adj'


def _columns(report: AdjReport) -> List[Column]:
    columns = [Column(k, h, w, f) for k, h, w, f in EMPLOYEE_COLUMNS]
    for code in report.products:
        spec = LIFE_FIELDS if code in LIFE_PRODUCTS else MEDICAL_FIELDS
        if code in report.show_admin:
            spec = (LIFE_FIELDS[0],) + spec
        for name, header, width, fmt in spec:
            text = header.format(p=code, prev=report.prev.label, curr=report.curr.label)
            columns.append(Column(f"{code}.{name}", text, width, fmt, code))
    columns.append(Column(MATCH_KEY, 'Match Key (used by Adj Invoice Summary)', 14, '@'))
    return columns


def _loading_premium(values: Dict) -> Optional[float]:
    if values.get('loading_premium') is not None:
        return values['loading_premium']
    rate, sum_insured = values.get('loading_rate'), values.get('loading_si')
    return round(rate * sum_insured / 1000, 2) if rate and sum_insured else None


def _employee_value(key: str, out: OutputRow, r: int, letters: Dict[str, str]):
    emp = out.row.emp
    if key == 'renewal':
        return out.label
    if key == 'entity':
        return out.entity or None
    if key == 'emp_id_2':
        return emp.get('emp_id') or None
    if key == 'age':
        dob, at = emp.get('dob'), out.renewal_date
        if isinstance(dob, datetime) and at is not None:
            return f"=YEARFRAC({letters['dob']}{r},DATE({at.year},{at.month},{at.day}),1)+1"
        return None
    value = emp.get(key)
    return None if value == '' else value


def _product_value(col: Column, out: OutputRow, r: int, letters: Dict[str, str], days: int):
    code, name = col.key.split('.', 1)
    values = out.row.products.get(code, {})
    decision = out.decisions.get(code)
    headcount = decision is not None and decision.basis == HEADCOUNT
    if name == 'admin':
        return decision.basis or None if decision else None
    if name in ('prev_premium', 'curr_premium'):
        return values.get('premium') if (name == 'curr_premium') == out.current else None
    if name == 'adj':
        prev, curr = letters[f"{code}.prev_premium"], letters[f"{code}.curr_premium"]
        return f"=({curr}{r}-{prev}{r})/{YEAR_DAYS}*{days}" if headcount else None
    if name == 'adj_gst':
        return f"={letters[f'{code}.adj']}{r}*{1 + GST_RATE:g}" if headcount else None
    if name == 'last_accepted_si':
        accepted = values.get('last_accepted_si')
        return accepted if accepted is not None else values.get('present_si')
    if name == 'loading_premium':
        return _loading_premium(values)
    value = values.get(name)
    return None if value == '' else value


def _write_header(ws, columns: List[Column]) -> None:
    for c, col in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=c, value=col.header)
        is_adj = col.key.split('.')[-1] in ADJ_FIELDS
        cell.font = Font(bold=True, color='FFFFFFFF' if col.key == 'renewal' else (RED if is_adj else None))
        cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        if col.key == 'renewal':
            cell.fill = _fill('000000')
        elif col.key in ('emp_id', 'lds'):
            cell.fill = _fill(KEY_HEADER_FILL)
        elif col.product:
            cell.fill = _fill(PRODUCT_FILLS.get(col.product, 'D9D9D9'))
        ws.column_dimensions[get_column_letter(c)].width = col.width
    ws.row_dimensions[1].height = 48


def _write_totals(ws, columns: List[Column], letters: Dict[str, str], last_row: int) -> None:
    total_row, gst_row = last_row + 2, last_row + 3
    ws.cell(row=total_row, column=4, value='Total').font = Font(bold=True)
    for c, col in enumerate(columns, start=1):
        name = col.key.split('.')[-1]
        if name not in ADJ_FIELDS:
            continue
        letter = letters[col.key]
        cell = ws.cell(row=total_row, column=c, value=f"=SUBTOTAL(9,{letter}2:{letter}{last_row})")
        cell.font, cell.number_format = Font(bold=True, color=RED), MONEY
        if name == 'adj' and col.product not in LIFE_PRODUCTS:
            gst = ws.cell(row=gst_row, column=c, value=f"={letter}{total_row}*{GST_RATE:g}")
            gst.font, gst.number_format = Font(bold=True, color=RED), MONEY
            ws.cell(row=gst_row, column=4, value=f"GST {GST_RATE:.0%} on premium adjustment").font = Font(bold=True)


def write_adj_sheet(ws, report: AdjReport) -> Dict[str, str]:
    """Write the combined listing; returns column key -> letter for cross-sheet formulas."""
    columns = _columns(report)
    letters = {col.key: get_column_letter(i) for i, col in enumerate(columns, start=1)}
    _write_header(ws, columns)
    current_fill = _fill(CURRENT_ROW_FILL)
    adj_font = Font(bold=True, color=RED)
    for r, out in enumerate(report.rows, start=2):
        for c, col in enumerate(columns, start=1):
            is_formula = col.key == 'age' or col.key.split('.')[-1] in ADJ_FIELDS
            if col.key == MATCH_KEY:
                value = report.groups[out.group].key
            elif col.product:
                value = _product_value(col, out, r, letters, report.days)
            else:
                value = _employee_value(col.key, out, r, letters)
            cell = put(ws, r, c, value, formula=is_formula)
            if col.number_format:
                cell.number_format = col.number_format
            if col.key.split('.')[-1] in ADJ_FIELDS:
                cell.font = adj_font
            if out.current:
                cell.fill = current_fill
    last_row = len(report.rows) + 1
    _write_totals(ws, columns, letters, last_row)
    ws.freeze_panes = 'E2'
    ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{last_row}"
    return letters


def _summary_products(report: AdjReport, letters: Dict[str, str]):
    items = []
    for code in report.products:
        if code in LIFE_PRODUCTS:
            items.append((code, f"Sum of {code} Adj Premium", letters[f"{code}.adj"]))
        else:
            items.append((f"{code} (With GST)", f"Sum of {code} Adj Premium with GST", letters[f"{code}.adj_gst"]))
    return items


def _style_box(ws, row: int, first: int, last: int, bold: bool = False, fmt: Optional[str] = None) -> None:
    for c in range(first, last + 1):
        cell = ws.cell(row=row, column=c)
        cell.border = BOX
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        if bold:
            cell.font = Font(bold=True)
        if fmt and c > 3:
            cell.number_format = fmt


def _entity_groups(report: AdjReport) -> Dict[str, List[int]]:
    order: Dict[str, List[int]] = {}
    for idx, group in enumerate(report.groups):
        order.setdefault(group.entity or '(No entity)', []).append(idx)
    return order


def write_invoice_sheet(ws, report: AdjReport, adj_title: str, letters: Dict[str, str]) -> None:
    """Per-entity adjustment totals (for DN/CN reconciliation) and the per-employee breakdown."""
    products = _summary_products(report, letters)
    entities = _entity_groups(report)
    last_col = 3 + len(products) + 1
    first_amt, last_amt = get_column_letter(4), get_column_letter(last_col - 1)
    headers = [f"{report.scope} Adjustment ({report.prev.label})", 'Entity', 'Debit/Credit Note No.']
    headers += [label for label, _, _ in products] + ['Total Premium Payable']
    for c, text in enumerate(headers, start=1):
        ws.cell(row=1, column=c, value=text)
    _style_box(ws, 1, 1, last_col, bold=True)
    breakdown_header = len(entities) + 5
    entity_total_rows = _write_breakdown(ws, report, adj_title, letters, products, entities, breakdown_header)
    for i, (entity, total_row) in enumerate(entity_total_rows.items(), start=2):
        ws.cell(row=i, column=1, value=f"{report.prev.label} Adj DN/CN")
        put(ws, i, 2, entity)
        ws.cell(row=i, column=3).fill = _fill(KEY_HEADER_FILL)
        for c in range(4, last_col):
            ws.cell(row=i, column=c, value=f"=ROUND({get_column_letter(c)}{total_row},2)")
        ws.cell(row=i, column=last_col, value=f"=SUM({first_amt}{i}:{last_amt}{i})")
        _style_box(ws, i, 1, last_col, fmt=MONEY)
    total_row = len(entities) + 2
    put(ws, total_row, 2, f"{report.client} Adjustment Premium")
    for c in range(4, last_col + 1):
        letter = get_column_letter(c)
        ws.cell(row=total_row, column=c, value=f"=SUM({letter}2:{letter}{total_row - 1})")
    _style_box(ws, total_row, 1, last_col, bold=True, fmt=MONEY)
    for c in range(2, last_col + 1):
        ws.cell(row=total_row, column=c).fill = _fill(KEY_HEADER_FILL)
        ws.cell(row=total_row, column=c).font = Font(bold=True, color=RED)
    for c, width in enumerate([30, 40, 18] + [16] * len(products) + [18], start=1):
        ws.column_dimensions[get_column_letter(c)].width = width
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = f"A{breakdown_header + 1}"


def _write_breakdown(ws, report, adj_title, letters, products, entities, header_row) -> Dict[str, int]:
    sheet_ref = quote_sheetname(adj_title)
    key_col = letters[MATCH_KEY]
    last_col = 3 + len(products) + 1
    labels = ['Entity', 'Employee Name', 'EMP ID'] + [label for _, label, _ in products] + ['Total']
    for c, text in enumerate(labels, start=1):
        ws.cell(row=header_row, column=c, value=text)
    _style_box(ws, header_row, 1, last_col, bold=True)
    ws.row_dimensions[header_row].height = 44
    row = header_row + 1
    entity_totals: Dict[str, int] = {}
    for entity, group_ids in entities.items():
        first = row
        for n, gid in enumerate(group_ids):
            group = report.groups[gid]
            put(ws, row, 1, entity if n == 0 else None)
            put(ws, row, 2, group.name)
            put(ws, row, 3, group.emp_id or None).number_format = '@'
            for c, (_, _, adj_letter) in enumerate(products, start=4):
                ws.cell(row=row, column=c, value=(
                    f"=SUMIFS({sheet_ref}!${adj_letter}:${adj_letter},"
                    f"{sheet_ref}!${key_col}:${key_col},\"{group.key}\")"
                )).number_format = MONEY
            ws.cell(row=row, column=last_col, value=f"=SUM(D{row}:{get_column_letter(last_col - 1)}{row})").number_format = MONEY
            row += 1
        put(ws, row, 1, f"{entity} Total")
        for c in range(4, last_col + 1):
            letter = get_column_letter(c)
            ws.cell(row=row, column=c, value=f"=SUM({letter}{first}:{letter}{row - 1})")
        _style_box(ws, row, 1, last_col, bold=True, fmt=MONEY)
        entity_totals[entity] = row
        row += 1
    ws.cell(row=row, column=1, value='Grand Total')
    for c in range(4, last_col + 1):
        letter = get_column_letter(c)
        refs = ','.join(f"{letter}{r}" for r in entity_totals.values())
        ws.cell(row=row, column=c, value=f"=SUM({refs})")
    _style_box(ws, row, 1, last_col, bold=True, fmt=MONEY)
    return entity_totals


def write_report(report: AdjReport, path: str) -> None:
    from .notes import write_notes_sheet

    wb = openpyxl.Workbook()
    adj_ws = wb.active
    adj_ws.title = safe_sheet_title(f"{report.client} Adj")
    letters = write_adj_sheet(adj_ws, report)
    write_invoice_sheet(wb.create_sheet(INVOICE_SHEET), report, adj_ws.title, letters)
    write_notes_sheet(wb.create_sheet('Notes'), report)
    try:
        wb.save(path)
    finally:
        wb.close()
