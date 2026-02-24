"""
Classifies Excel formulas into categories: arithmetic, lookup, IF, concat, reference, other.
"""
import re
from typing import Optional


LOOKUP_FUNCS = {'VLOOKUP', 'HLOOKUP', 'INDEX', 'MATCH', 'XLOOKUP', 'LOOKUP'}
AGGREGATE_FUNCS = {'SUM', 'AVERAGE', 'COUNT', 'COUNTA', 'COUNTIF', 'SUMIF', 'MIN', 'MAX',
                   'AVERAGEIF', 'SUMIFS', 'COUNTIFS', 'AVERAGEIFS'}
TEXT_FUNCS = {'CONCATENATE', 'CONCAT', 'TEXTJOIN', 'LEFT', 'RIGHT', 'MID', 'TRIM',
              'UPPER', 'LOWER', 'TEXT', 'LEN', 'SUBSTITUTE', 'REPLACE', 'FIND', 'SEARCH'}
DATE_FUNCS = {'DATE', 'TODAY', 'NOW', 'YEAR', 'MONTH', 'DAY', 'DATEDIF', 'EDATE',
              'EOMONTH', 'NETWORKDAYS', 'WORKDAY'}
LOGIC_FUNCS = {'IF', 'IFS', 'AND', 'OR', 'NOT', 'IFERROR', 'IFNA', 'SWITCH'}
ARITHMETIC_OPS = re.compile(r'[+\-*/]')


def classify_formula(formula: str) -> Optional[str]:
    """
    Classify a single formula string into a type category.

    Returns: 'arithmetic' | 'lookup' | 'IF' | 'concat' | 'reference' |
             'aggregate' | 'date' | 'other' | None
    """
    if not formula or not formula.startswith('='):
        return None

    formula_upper = formula.upper()

    # Extract all function names
    funcs = set(re.findall(r'([A-Z]+)\s*\(', formula_upper))

    if funcs & LOOKUP_FUNCS:
        return 'lookup'
    if funcs & LOGIC_FUNCS:
        return 'IF'
    if funcs & TEXT_FUNCS:
        return 'concat'
    if funcs & DATE_FUNCS:
        return 'date'
    if funcs & AGGREGATE_FUNCS:
        return 'aggregate'

    # Pure cell reference with no function
    if not funcs:
        # Check for arithmetic operators between cell refs
        # e.g., =A1*B1, =D2+E2
        if ARITHMETIC_OPS.search(formula[1:]):
            return 'arithmetic'
        # Simple cell reference like =A1 or =Sheet1!A1
        if re.match(r'^=[A-Z0-9!$]+$', formula.upper()):
            return 'reference'
        return 'arithmetic'

    return 'other'


def classify_column_formulas(formula_list: list) -> Optional[str]:
    """
    Given a list of formula strings for a column, return the dominant formula type.
    """
    types = [classify_formula(f) for f in formula_list if f]
    if not types:
        return None
    # Return the most common type
    from collections import Counter
    counts = Counter(t for t in types if t)
    if not counts:
        return None
    return counts.most_common(1)[0][0]
