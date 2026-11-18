"""Business rules for the Adj Listing report: age, employee matching and basis decisions.

Basis rule (agreed with the business):
- A listing's own Administration Basis column always wins.
- Medical products: premium present -> Headcount.
- Life products: premium present and within the FCL and age limit -> Headcount.
  Over either limit -> Named (billed separately pending underwriting), EXCEPT an employee
  who was already Named the previous year (already underwritten) -> Headcount.
- No premium -> not covered (blank basis, no adjustment).
"""

import calendar
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .reader import ListingRow

HEADCOUNT = 'Headcount'
NAMED = 'Named'
_NAMED_RE = re.compile(r'\bnamed\b')
_HEADCOUNT_RE = re.compile(r'head\s*-?\s*count|\bhc\b')
_SUM_INSURED_FIELDS = ('eligible_si', 'present_si', 'last_accepted_si')


def sum_insured(values: Dict) -> Optional[float]:
    """Sum insured of one life product: eligible, else present, else last accepted."""
    return next((values[k] for k in _SUM_INSURED_FIELDS if values.get(k) is not None), None)


@dataclass
class BasisDecision:
    basis: str
    reason: str
    derived: bool = False
    over_limit: bool = False
    unrecognised: str = ''


def yearfrac_actual(start: datetime, end: datetime) -> float:
    """Excel YEARFRAC(start, end, 1) — actual/actual day count."""
    if start > end:
        start, end = end, start
    days = (end - start).days
    one_year_or_less = (
        start.year == end.year
        or (end.year == start.year + 1 and (end.month, end.day) <= (start.month, start.day))
    )
    if one_year_or_less:
        return days / (366 if _spans_feb29(start, end) else 365)
    years = range(start.year, end.year + 1)
    average = sum(366 if calendar.isleap(y) else 365 for y in years) / len(years)
    return days / average


def _spans_feb29(start: datetime, end: datetime) -> bool:
    if start.year == end.year:
        return calendar.isleap(start.year)
    if calendar.isleap(start.year) and (start.month, start.day) <= (2, 29):
        return True
    return calendar.isleap(end.year) and (end.month, end.day) >= (2, 29)


def age_next_birthday(dob, at: Optional[datetime]) -> Optional[float]:
    """Listing convention: YEARFRAC(DOB, renewal date, 1) + 1."""
    if not isinstance(dob, datetime) or at is None or dob > at:
        return None
    return yearfrac_actual(dob, at) + 1


def canonical_basis(text: str) -> Optional[str]:
    """'Named Basis' -> Named, 'Head-count' / 'HC' -> Headcount, anything else -> None."""
    lowered = (text or '').strip().lower()
    if _NAMED_RE.search(lowered):
        return NAMED
    if _HEADCOUNT_RE.search(lowered):
        return HEADCOUNT
    return None


def decide_basis(values: Dict, life: bool, age: Optional[float],
                 limits: Dict[str, float], prior_basis: Optional[str]) -> BasisDecision:
    """Administration basis for one employee x product x policy year."""
    explicit = (values.get('admin') or '').strip()
    listed = canonical_basis(explicit)
    if listed:
        return BasisDecision(listed, 'Administration basis column in the listing')
    decision = _rule_basis(values, life, age, limits, prior_basis)
    if explicit:
        decision.unrecognised = explicit
        decision.reason = f"Listing basis '{explicit}' not recognised; {decision.reason[0].lower()}{decision.reason[1:]}"
    return decision


def _rule_basis(values: Dict, life: bool, age: Optional[float],
                limits: Dict[str, float], prior_basis: Optional[str]) -> BasisDecision:
    if not values.get('premium'):
        return BasisDecision('', 'No premium - not covered')
    if not life:
        return BasisDecision(HEADCOUNT, 'Premium present')
    insured = sum_insured(values)
    over = []
    fcl, age_limit = limits.get('fcl'), limits.get('age')
    if fcl is not None and insured is not None and insured > fcl:
        over.append(f"sum insured {insured:,.0f} > FCL {fcl:,.0f}")
    if age_limit is not None and age is not None and age > age_limit:
        over.append(f"age {age:.2f} > limit {age_limit:g}")
    if not over:
        return BasisDecision(HEADCOUNT, 'Within FCL and age limit', derived=True)
    detail = '; '.join(over)
    if prior_basis == NAMED:
        return BasisDecision(HEADCOUNT, f"Over limit ({detail}) but already Named last year", True, True)
    return BasisDecision(NAMED, f"Over limit ({detail})", True, True)


def _nric_conflict(a: ListingRow, b: ListingRow) -> bool:
    first, second = a.emp.get('nric'), b.emp.get('nric')
    return bool(first and second and first != second)


def match_rows(prev_rows: List[ListingRow], curr_rows: List[ListingRow]) -> Dict[int, int]:
    """Map current-row index -> previous-row index by NRIC, then EMP ID, then name + DOB.

    The fallbacks never pair two rows whose NRICs are both present and different
    (e.g. a joiner given a leaver's EMP ID).
    """
    def name_dob(row: ListingRow) -> Optional[Tuple[str, str]]:
        name = ' '.join(str(row.emp.get('name', '')).upper().split())
        dob = row.emp.get('dob')
        return (name, dob.strftime('%Y-%m-%d')) if name and isinstance(dob, datetime) else None

    strategies = (
        lambda r: r.emp.get('nric') or None,
        lambda r: r.emp.get('emp_id') or None,
        name_dob,
    )
    matches: Dict[int, int] = {}
    used_prev = set()
    for key_of in strategies:
        index: Dict[object, int] = {}
        for i, row in enumerate(prev_rows):
            key = key_of(row)
            if key is not None and i not in used_prev:
                index.setdefault(key, i)
        for j, row in enumerate(curr_rows):
            if j in matches:
                continue
            key = key_of(row)
            i = index.get(key) if key is not None else None
            if i is not None and i not in used_prev and not _nric_conflict(row, prev_rows[i]):
                matches[j] = i
                used_prev.add(i)
    return matches


def entity_mapping(prev_rows, curr_rows, matches: Dict[int, int]) -> Dict[str, str]:
    """Current-year entity names re-labelled to the previous year's name for the same staff.

    e.g. 'CBRE Pte Ltd (MCST 1216)' -> 'MCST1216' so both years group under one entity.
    """
    votes: Dict[str, Counter] = defaultdict(Counter)
    for j, i in matches.items():
        curr_entity = curr_rows[j].emp.get('entity') or ''
        prev_entity = prev_rows[i].emp.get('entity') or ''
        if curr_entity and prev_entity:
            votes[curr_entity][prev_entity] += 1
    mapping = {}
    for curr_entity, counter in votes.items():
        prev_entity, count = counter.most_common(1)[0]
        if prev_entity != curr_entity and count * 2 > sum(counter.values()):
            mapping[curr_entity] = prev_entity
    return mapping
