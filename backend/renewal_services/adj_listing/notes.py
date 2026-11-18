"""'Notes' sheet: inputs used, limits, basis decisions and warnings — the audit trail for a run."""

from datetime import datetime

from openpyxl.styles import Alignment, Font

from .processor import AdjReport, basis_review
from .writer import put

RULES = (
    "Adjustment per Headcount row = (current-year premium - previous-year premium) / pro-rata divisor "
    "(2 = changes assumed mid-year).",
    "Current-year rows use the previous year's premium (the employee's own, else the same cover's), so continuing "
    "staff net to zero when the renewal changes the rates.",
    "An Administration Basis column in a listing always wins.",
    "Without one: medical products with a premium are Headcount.",
    "Life products with a premium within the FCL and age limit are Headcount; over either limit they are Named "
    "(billed separately), unless the employee was already Named the previous year (already underwritten) -> Headcount.",
    "Age = YEARFRAC(Date of Birth, renewal date, 1) + 1 (age next birthday, as in the listings).",
    "Named rows and rows without a premium carry no adjustment.",
)


def _section(ws, row: int, title: str) -> int:
    ws.cell(row=row, column=1, value=title).font = Font(bold=True, size=12)
    return row + 1


def _table(ws, row: int, headers, rows) -> int:
    for c, text in enumerate(headers, start=1):
        ws.cell(row=row, column=c, value=text).font = Font(bold=True)
    row += 1
    for values in rows:
        for c, value in enumerate(values, start=1):
            put(ws, row, c, value)
        row += 1
    return row + 1


def _limit_rows(report: AdjReport):
    for code, entry in report.limits.items():
        for year, listing in (('prev', report.prev), ('curr', report.curr)):
            values, sources = entry[year], entry[f"{year}_source"]
            source = '; '.join(sorted(set(sources.values()))) or 'Not set'
            yield (code, listing.label, values.get('fcl'), values.get('age'), source)


def write_notes_sheet(ws, report: AdjReport) -> None:
    row = _section(ws, 1, 'Adj Listing - run notes')
    listings = [
        (label, listing.filename, listing.sheet_name, listing.label,
         listing.renewal_date.strftime('%d/%m/%Y') if listing.renewal_date else 'Not found', len(listing.rows))
        for label, listing in (('Previous year', report.prev), ('Current year', report.curr))
    ]
    row = _table(ws, row, ('Listing', 'File', 'Sheet', 'Policy period', 'Renewal date', 'Employees'), listings)
    ws.cell(row=row, column=1, value='Pro-rata')
    ws.cell(row=row, column=2, value=f"Divide by {report.divisor}")
    ws.cell(row=row + 1, column=1, value='Generated')
    ws.cell(row=row + 1, column=2, value=datetime.now().strftime('%d/%m/%Y %H:%M'))
    row = _section(ws, row + 3, 'Basis rules')
    for line in RULES:
        ws.cell(row=row, column=1, value=f"- {line}").alignment = Alignment(wrap_text=False)
        row += 1
    row = _section(ws, row + 1, 'FCL / age limits used')
    row = _table(ws, row, ('Product', 'Policy period', 'FCL', 'Age limit', 'Source'), _limit_rows(report))
    row = _section(ws, row, 'Named and over-limit employees')
    review = [(r['period'], r['name'], r['emp_id'], r['product'], r['age'], r['sum_insured'], r['basis'], r['reason'])
              for r in basis_review(report)]
    row = _table(ws, row, ('Policy period', 'Employee', 'EMP ID', 'Product', 'Age', 'Sum insured', 'Basis', 'Reason'),
                 review or [('None',)])
    if report.entity_map:
        row = _section(ws, row, 'Entity names aligned to the previous year')
        row = _table(ws, row, ('Current-year entity', 'Shown as'), report.entity_map.items())
    row = _section(ws, row, 'Warnings')
    for text in report.warnings or ['None']:
        put(ws, row, 1, text)
        row += 1
    for letter, width in zip('ABCDEFGH', (16, 40, 22, 14, 14, 14, 12, 60)):
        ws.column_dimensions[letter].width = width
