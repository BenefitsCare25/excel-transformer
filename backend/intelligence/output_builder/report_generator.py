"""
Generates Excel comparison reports using openpyxl.
Follows the same PatternFill pattern as the main app.
"""
import io
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from typing import Any, Dict, List, Optional
from datetime import datetime


def _hex_to_fill(hex_color: Optional[str]) -> Optional[PatternFill]:
    """Convert #RRGGBB to openpyxl PatternFill. Always create new Fill objects."""
    if not hex_color:
        return None
    color = hex_color.lstrip('#')
    if len(color) == 6:
        return PatternFill(start_color=color, end_color=color, fill_type='solid')
    return None


def _make_header_fill() -> PatternFill:
    return PatternFill(start_color='366092', end_color='366092', fill_type='solid')


def _make_header_font() -> Font:
    return Font(bold=True, color='FFFFFF', name='Calibri', size=11)


def _make_summary_title_fill() -> PatternFill:
    return PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')


def build_comparison_report(
    result: Dict[str, Any],
    template_name: str,
    compare_fields: List[str],
    key_fields: List[str],
    display_fields: List[str],
    add_remarks: bool = True,
    include_summary: bool = True,
    highlight_changed_cells: bool = True,
) -> bytes:
    """
    Build an Excel workbook from the rule executor result dict.

    Returns raw bytes of the .xlsx file.
    """
    wb = openpyxl.Workbook()

    # ── Main comparison sheet ──────────────────────────────────────────────────
    ws = wb.active
    ws.title = 'Comparison'[:31]

    all_fields = list(dict.fromkeys(key_fields + display_fields + compare_fields))
    headers = all_fields[:]
    if add_remarks:
        headers.append('Remarks')

    # Write headers
    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.fill = _make_header_fill()
        cell.font = _make_header_font()
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # Write data rows
    changed_cells = {}  # (row, col) → True for highlighting
    for row_idx, row_data in enumerate(result.get('rows', []), start=2):
        row_color = row_data.get('color')
        changed_fields = set(row_data.get('changed_fields', []))
        row_fill = _hex_to_fill(row_color)

        for col_idx, field in enumerate(all_fields, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=row_data.get(field))
            cell.alignment = Alignment(vertical='center', wrap_text=False)

            # Row-level coloring
            if row_fill:
                cell.fill = PatternFill(
                    start_color=row_fill.start_color.rgb,
                    end_color=row_fill.end_color.rgb,
                    fill_type='solid'
                )

            # Override with cell-level change highlight if applicable
            if highlight_changed_cells and field in changed_fields and row_color is None:
                cell.fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')

        if add_remarks:
            rem_col = len(all_fields) + 1
            rem_cell = ws.cell(row=row_idx, column=rem_col, value=row_data.get('remarks', ''))
            rem_cell.alignment = Alignment(vertical='center')
            if row_fill:
                rem_cell.fill = PatternFill(
                    start_color=row_fill.start_color.rgb,
                    end_color=row_fill.end_color.rgb,
                    fill_type='solid'
                )

    # Auto-fit column widths (capped at 40)
    for col_idx in range(1, len(headers) + 1):
        col_letter = get_column_letter(col_idx)
        max_len = 10
        for row_idx in range(1, ws.max_row + 1):
            cell_val = ws.cell(row=row_idx, column=col_idx).value
            if cell_val:
                max_len = max(max_len, min(len(str(cell_val)), 40))
        ws.column_dimensions[col_letter].width = max_len + 2

    ws.freeze_panes = 'A2'

    # ── Summary sheet ──────────────────────────────────────────────────────────
    if include_summary:
        summary_data = result.get('summary', {})
        ws_sum = wb.create_sheet(title='Summary')

        ws_sum.cell(row=1, column=1, value=f'{template_name} — Comparison Summary').font = Font(bold=True, size=14)
        ws_sum.cell(row=2, column=1, value=f'Generated: {datetime.now().strftime("%d %b %Y %H:%M")}')

        summary_rows = [
            ('Total rows processed', summary_data.get('total', 0)),
            ('Additions (new in File B)', summary_data.get('additions', 0)),
            ('Deletions (removed from File A)', summary_data.get('deletions', 0)),
            ('Changes (modified fields)', summary_data.get('changes', 0)),
            ('Unchanged', summary_data.get('unchanged', 0)),
        ]

        for i, (label, val) in enumerate(summary_rows, start=4):
            label_cell = ws_sum.cell(row=i, column=1, value=label)
            val_cell = ws_sum.cell(row=i, column=2, value=val)
            label_cell.fill = _make_summary_title_fill()
            label_cell.font = Font(bold=True)

        ws_sum.column_dimensions['A'].width = 40
        ws_sum.column_dimensions['B'].width = 15

    # Serialize to bytes
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
