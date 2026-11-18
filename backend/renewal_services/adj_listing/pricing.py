"""Price the current-year rows at the previous year's premium.

The Adj measures headcount movement during the previous policy year, so both blocks use that
year's rates. A continuing employee's current-year row carries their own premium from last year
and nets to zero even when the renewal changed the rates; a joiner takes last year's premium for
the same cover (sum insured for life, plan / plan type / family grouping for medical).
"""

from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Dict, Hashable, List, Tuple

from .reader import LIFE_PRODUCTS
from .rules import HEADCOUNT, sum_insured

if TYPE_CHECKING:
    from .processor import OutputRow

OWN, COVER, CHANGED, MISSING = 'own', 'cover', 'changed', 'missing'
_MEDICAL_COVER = ('basis', 'plan_type', 'family')


def _cover(code: str, values: Dict) -> Hashable:
    if code in LIFE_PRODUCTS:
        return sum_insured(values)
    return tuple(' '.join(str(values.get(k) or '').lower().split()) for k in _MEDICAL_COVER)


def _premium_by_cover(rows: List['OutputRow'], code: str) -> Dict[Hashable, float]:
    """Most common previous-year premium per cover, so a pro-rated leaver never sets the rate."""
    counts: Dict[Hashable, Counter] = defaultdict(Counter)
    for out in rows:
        values = out.row.products.get(code, {})
        if values.get('premium'):
            counts[_cover(code, values)][values['premium']] += 1
    return {cover: counter.most_common(1)[0][0] for cover, counter in counts.items()}


def _price(code: str, values: Dict, last: Dict, by_cover: Dict[Hashable, float]) -> Tuple[float, str]:
    cover = _cover(code, values)
    if last.get('premium'):
        last_cover = _cover(code, last)
        if cover == last_cover:
            return last['premium'], OWN
        if code in LIFE_PRODUCTS and cover and last_cover:
            return round(last['premium'] * cover / last_cover, 2), CHANGED
    if cover in by_cover:
        return by_cover[cover], CHANGED if last.get('premium') else COVER
    return values['premium'], MISSING


def _warning(code: str, status: str, names: List[str], prev_label: str) -> str:
    shown = ', '.join(names[:5]) + (' ...' if len(names) > 5 else '')
    if status == MISSING:
        return (f"{code}: no {prev_label} premium for the same cover, so {len(names)} current-year row(s) keep this "
                f"year's premium and do not net to zero: {shown}. Check these rows.")
    return (f"{code}: cover changed for {len(names)} continuing employee(s), priced at the {prev_label} premium "
            f"for the new cover, so their adjustment is not zero: {shown}.")


def price_rows(prev_rows: List['OutputRow'], curr_rows: List['OutputRow'],
               matches: Dict[int, int], prev_label: str) -> List[str]:
    """Set `priced` on every row; returns warnings for Headcount rows that need a check."""
    for out in prev_rows:
        out.priced = {code: values.get('premium') for code, values in out.row.products.items()}
    tables: Dict[str, Dict[Hashable, float]] = {}
    flagged: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for j, out in enumerate(curr_rows):
        last_year = prev_rows[matches[j]].row.products if j in matches else {}
        for code, values in out.row.products.items():
            if not values.get('premium'):
                out.priced[code] = values.get('premium')
                continue
            if code not in tables:
                tables[code] = _premium_by_cover(prev_rows, code)
            out.priced[code], status = _price(code, values, last_year.get(code, {}), tables[code])
            decision = out.decisions.get(code)
            if status in (CHANGED, MISSING) and decision is not None and decision.basis == HEADCOUNT:
                flagged[(code, status)].append(out.row.emp.get('name', ''))
    return [_warning(code, status, names, prev_label) for (code, status), names in flagged.items()]
