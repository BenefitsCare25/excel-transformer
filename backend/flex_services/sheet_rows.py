"""Insert rows into a client-authored worksheet the way Excel's Insert Rows does.

openpyxl's own insert_rows only moves cell values: totals, data validations, conditional
formats, row properties, merged cells and references from other sheets keep pointing at
the old rows. These helpers move all of them together.
"""
import re
from copy import copy

from openpyxl.formatting.formatting import ConditionalFormattingList
from openpyxl.formula.tokenizer import Token, Tokenizer, TokenizerError
from openpyxl.formula.translate import Translator
from openpyxl.worksheet.cell_range import CellRange, MultiCellRange
from openpyxl.worksheet.formula import ArrayFormula

_CELL_REF = re.compile(r'^(\$?[A-Z]{1,3}\$?)(\d+)$')


def shift_rows(start, end, boundary, shift):
    """Row span after `shift` rows are opened below row `boundary`.

    Rows past the boundary move down; a span ending on the boundary (the last data row)
    grows to cover the new rows, as when Excel inserts inside a range.
    """
    return (start + shift if start > boundary else start,
            end + shift if end >= boundary else end)


def _tokens(formula):
    try:
        return Tokenizer(formula).items
    except TokenizerError:
        return None


def _sheet_ref(token, sheet, own_sheet):
    """(prefix, A1 matches) when `token` is a cell/range reference to `sheet`, else None.

    An unprefixed reference belongs to the formula's own sheet, so it counts only when the
    formula lives on `sheet`. Whole columns, named ranges and other sheets are skipped.
    """
    if token.type != Token.OPERAND or token.subtype != Token.RANGE:
        return None
    prefix, bang, ref = token.value.rpartition('!')
    target = prefix.strip("'").replace("''", "'") if bang else (sheet if own_sheet else '')
    refs = [_CELL_REF.match(part) for part in ref.split(':')]
    if target.casefold() != sheet.casefold() or len(refs) not in (1, 2) or not all(refs):
        return None
    return prefix + bang, refs


def range_rows(formula, sheet, column):
    """(first, last) row of each reference in `formula` to `column` on its own `sheet`."""
    spans = []
    for token in _tokens(formula) or []:
        found = _sheet_ref(token, sheet, own_sheet=True)
        if found and all(m.group(1).replace('$', '') == column for m in found[1]):
            spans.append((int(found[1][0].group(2)), int(found[1][-1].group(2))))
    return spans


def _shift_formula(formula, sheet, boundary, shift, own_sheet):
    """`formula` with its references to `sheet` re-pointed; unparseable text is left as is."""
    tokens = _tokens(formula)
    if tokens is None:
        return formula
    out = ['=']
    for token in tokens:
        value = token.value
        found = _sheet_ref(token, sheet, own_sheet)
        if found:
            prefix, refs = found
            rows = shift_rows(int(refs[0].group(2)), int(refs[-1].group(2)), boundary, shift)
            value = prefix + ':'.join(f'{m.group(1)}{row}' for m, row in zip(refs, rows))
        out.append(value)
    return ''.join(out)


def _shift_cell_range(ref, boundary, shift):
    return ' '.join(
        CellRange(min_col=r.min_col, min_row=start, max_col=r.max_col, max_row=end).coord
        for r in MultiCellRange(ref).ranges
        for start, end in [shift_rows(r.min_row, r.max_row, boundary, shift)])


def _shift_cell_formula(cell, sheet, boundary, shift, own_sheet):
    value = cell.value
    if isinstance(value, ArrayFormula):
        cell.value = ArrayFormula(_shift_cell_range(value.ref, boundary, shift),
                                  _shift_formula(value.text, sheet, boundary, shift, own_sheet))
    elif cell.data_type == 'f' and isinstance(value, str):
        cell.value = _shift_formula(value, sheet, boundary, shift, own_sheet)


def _move_tail(ws, boundary, shift):
    """Move every row below `boundary` down by `shift`, with its row properties and merges."""
    last_row = ws.max_row
    tail_merges = [m for m in ws.merged_cells.ranges if m.min_row > boundary]
    for merged in tail_merges:
        ws.unmerge_cells(merged.coord)
    ws.move_range(CellRange(min_col=1, min_row=boundary + 1, max_col=ws.max_column, max_row=last_row).coord,
                  rows=shift)
    moved = {r: ws.row_dimensions.pop(r) for r in sorted(k for k in ws.row_dimensions if k > boundary)}
    for r, dimension in moved.items():
        dimension.index = r + shift
        ws.row_dimensions[r + shift] = dimension
    for merged in tail_merges:
        merged.shift(row_shift=shift)
        ws.merge_cells(merged.coord)


def insert_rows_below(ws, boundary, shift, first_data_row):
    """Open `shift` blank rows below row `boundary` of `ws`.

    Rows below the data area move down; every formula outside the data rows, every formula
    on another sheet or defined name pointing here, and every data validation or conditional
    format that reaches the boundary row is re-pointed or grown. Data-row formulas are
    row-relative and left alone.
    """
    if ws.max_row > boundary:
        _move_tail(ws, boundary, shift)
    outside_data = [*range(1, first_data_row), *range(boundary + shift + 1, ws.max_row + 1)]
    for r in outside_data:
        for cell in ws[r]:
            _shift_cell_formula(cell, ws.title, boundary, shift, own_sheet=True)
    for other in ws.parent.worksheets:
        if other is not ws:
            for row in other.iter_rows():
                for cell in row:
                    if cell.data_type == 'f' and ws.title.casefold() in str(getattr(cell.value, 'text', cell.value)).casefold():
                        _shift_cell_formula(cell, ws.title, boundary, shift, own_sheet=False)
    for names in [ws.parent.defined_names, *(s.defined_names for s in ws.parent.worksheets)]:
        for defined in names.values():
            text = defined.attr_text or ''
            if ws.title.casefold() in text.casefold():
                defined.attr_text = _shift_formula('=' + text, ws.title, boundary, shift, own_sheet=False)[1:]

    for dv in ws.data_validations.dataValidation:
        dv.sqref = MultiCellRange(_shift_cell_range(str(dv.sqref), boundary, shift))
    formats = ConditionalFormattingList()
    for cf in ws.conditional_formatting:
        for rule in cf.rules:
            formats.add(_shift_cell_range(str(cf.sqref), boundary, shift), rule)
    ws.conditional_formatting = formats


def copy_row_cell(src, dst):
    """Copy a per-row template cell (value and style) down to `dst`, re-pointing relative refs."""
    value = src.value
    if isinstance(value, ArrayFormula):
        dst.value = ArrayFormula(Translator.translate_range(value.ref, dst.row - src.row, 0),
                                 Translator(value.text, origin=src.coordinate).translate_formula(dst.coordinate))
    elif src.data_type == 'f':
        dst.value = Translator(value, origin=src.coordinate).translate_formula(dst.coordinate)
    else:
        dst.value = value
        dst.data_type = src.data_type
    dst._style = copy(src._style)
