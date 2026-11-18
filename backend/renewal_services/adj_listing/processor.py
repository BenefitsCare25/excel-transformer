"""Combined Adj Listing: previous- and current-year renewal listings -> one adjustment workbook.

Every employee in the previous listing gets a row carrying last year's premium, every employee
in the current listing gets a row priced at last year's premium too (see pricing.py), and each
Headcount row adjusts by (current - previous) / 365 * pro-rata days. Continuing staff net to
zero per employee in the invoice summary even when the renewal changed the rates; joiners and
leavers do not.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .pricing import price_rows
from .reader import LIFE_PRODUCTS, PRODUCT_ORDER, Listing, ListingRow, read_listing
from .rules import (
    HEADCOUNT, NAMED, BasisDecision, age_next_birthday, decide_basis, entity_mapping, match_rows,
)

logger = logging.getLogger(__name__)

YEAR_DAYS = 365
GST_RATE = 0.09


@dataclass
class OutputRow:
    row: ListingRow
    current: bool
    label: str
    entity: str
    renewal_date: Optional[datetime]
    age: Optional[float]
    decisions: Dict[str, BasisDecision]
    group: int = -1
    priced: Dict[str, Optional[float]] = field(default_factory=dict)  # premium the Adj formula uses


@dataclass
class EmployeeGroup:
    """One person across both years; `key` is written on every Adj row so SUMIFS never double-counts."""
    entity: str
    name: str
    emp_id: str
    key: str


@dataclass
class AdjReport:
    prev: Listing
    curr: Listing
    products: List[str]
    show_admin: set
    rows: List[OutputRow]
    groups: List[EmployeeGroup]
    limits: Dict[str, Dict[str, dict]]
    days: int
    client: str
    entity_map: Dict[str, str]
    warnings: List[str] = field(default_factory=list)

    @property
    def scope(self) -> str:
        has_life = any(p in LIFE_PRODUCTS for p in self.products)
        has_medical = any(p not in LIFE_PRODUCTS for p in self.products)
        return 'Life & Medical' if has_life and has_medical else ('Life' if has_life else 'Medical')


def _resolve_limits(code: str, own: Listing, other: Listing, entered: Dict) -> Tuple[dict, dict]:
    values, sources = {}, {}
    for key in ('fcl', 'age'):
        if entered.get(key) is not None:
            values[key], sources[key] = float(entered[key]), 'Entered on screen'
            continue
        for listing in (own, other):
            if key in listing.header_limits.get(code, {}):
                values[key] = listing.header_limits[code][key]
                sources[key] = f"Header of {listing.filename}"
                break
    return values, sources


def _decide_rows(listing: Listing, current: bool, limits: Dict, entity_map: Dict[str, str],
                 prior: Dict[int, Dict[str, BasisDecision]]) -> List[OutputRow]:
    out = []
    for idx, row in enumerate(listing.rows):
        age = age_next_birthday(row.emp.get('dob'), listing.renewal_date)
        decisions = {}
        for code in listing.products:
            prior_basis = prior.get(idx, {}).get(code)
            year_limits = limits.get(code, {}).get('curr' if current else 'prev', {})
            decisions[code] = decide_basis(
                row.products.get(code, {}), code in LIFE_PRODUCTS, age, year_limits,
                prior_basis.basis if prior_basis else None,
            )
        entity = row.emp.get('entity') or ''
        out.append(OutputRow(row, current, listing.label, entity_map.get(entity, entity),
                             listing.renewal_date, age, decisions))
    return out


def _build_groups(prev_rows: List[OutputRow], curr_rows: List[OutputRow],
                  matches: Dict[int, int]) -> List[EmployeeGroup]:
    members: List[List[OutputRow]] = []
    for row in prev_rows:
        row.group = len(members)
        members.append([row])
    for j, row in enumerate(curr_rows):
        if j in matches:
            row.group = prev_rows[matches[j]].group
            members[row.group].append(row)
        else:
            row.group = len(members)
            members.append([row])
    groups = []
    for number, rows in enumerate(members, start=1):
        latest = rows[-1]
        groups.append(EmployeeGroup(latest.entity, latest.row.emp.get('name', ''),
                                    latest.row.emp.get('emp_id', ''), f"E{number:05d}"))
    return groups


def _limit_warnings(prev: Listing, curr: Listing, limits: Dict) -> List[str]:
    warnings = []
    for listing, year in ((prev, 'prev'), (curr, 'curr')):
        for code, product in listing.products.items():
            if code not in LIFE_PRODUCTS or 'admin' in product.cols:
                continue
            used = limits.get(code, {}).get(year, {})
            if 'fcl' not in used and 'age' not in used:
                warnings.append(f"{listing.filename}: no FCL or age limit for {code}, so every {code} employee "
                                f"with a premium is treated as Headcount. Enter the limits on screen.")
            elif 'age' in used and listing.renewal_date is None:
                warnings.append(f"{listing.filename}: renewal date not found, so the {code} age limit could not be checked.")
    return warnings


def _history_warnings(prev: Listing, prev_rows: List[OutputRow]) -> List[str]:
    """A previous listing without a basis column has no earlier year to apply the 'already Named' rule."""
    warnings = []
    for code, product in prev.products.items():
        if code not in LIFE_PRODUCTS or 'admin' in product.cols:
            continue
        names = [r.row.emp.get('name', '') for r in prev_rows
                 if r.decisions.get(code) and r.decisions[code].over_limit and r.decisions[code].basis == NAMED]
        if names:
            shown = ', '.join(names[:5]) + (' ...' if len(names) > 5 else '')
            warnings.append(
                f"{prev.filename} has no {code} Administration Basis column, so {len(names)} over-limit "
                f"employee(s) are Named for {prev.label}: {shown}. If any were billed as Headcount that year, "
                f"add a '{code} Administration Basis' column to that listing and run again.")
    return warnings


def _unrecognised_basis_warnings(prev: Listing, curr: Listing, rows: List[OutputRow]) -> List[str]:
    counts: Counter = Counter()
    for row in rows:
        filename = (curr if row.current else prev).filename
        for code, decision in row.decisions.items():
            if decision.unrecognised:
                counts[(filename, code, decision.unrecognised)] += 1
    return [f"{filename}: {code} Administration Basis '{value}' is neither Headcount nor Named on {count} row(s); "
            f"those rows were classified by the FCL / age rule." for (filename, code, value), count in counts.items()]


def _client_label(entered: str, groups: List[EmployeeGroup]) -> str:
    cleaned = re.sub(r'[\\/*?:\[\]&<>|"]', '', entered or '').strip()[:40]
    if cleaned:
        return cleaned
    entities = Counter(g.entity for g in groups if g.entity)
    return entities.most_common(1)[0][0][:40] if entities else 'Renewal'


def build_report(prev: Listing, curr: Listing, days: int, client_label: str,
                 entered_limits: Dict[str, Dict]) -> AdjReport:
    matches = match_rows(prev.rows, curr.rows)
    entity_map = entity_mapping(prev.rows, curr.rows, matches)
    codes = [c for c in PRODUCT_ORDER if c in prev.products or c in curr.products]
    limits = {}
    for code in codes:
        if code in LIFE_PRODUCTS:
            prev_vals, prev_src = _resolve_limits(code, prev, curr, entered_limits.get(code, {}))
            curr_vals, curr_src = _resolve_limits(code, curr, prev, entered_limits.get(code, {}))
            limits[code] = {'prev': prev_vals, 'curr': curr_vals,
                            'prev_source': prev_src, 'curr_source': curr_src}
    prev_rows = _decide_rows(prev, False, limits, {}, {})
    prior = {j: prev_rows[i].decisions for j, i in matches.items()}
    curr_rows = _decide_rows(curr, True, limits, entity_map, prior)
    pricing_warnings = price_rows(prev_rows, curr_rows, matches, prev.label)
    groups = _build_groups(prev_rows, curr_rows, matches)
    rows = prev_rows + curr_rows
    show_admin = {c for c in codes if c not in LIFE_PRODUCTS
                  and any(r.decisions.get(c) and r.decisions[c].basis == NAMED for r in rows)}
    warnings = (prev.warnings + curr.warnings + _limit_warnings(prev, curr, limits)
                + _history_warnings(prev, prev_rows) + _unrecognised_basis_warnings(prev, curr, rows)
                + pricing_warnings)
    return AdjReport(prev, curr, codes, show_admin, rows, groups, limits, days,
                     _client_label(client_label, groups), entity_map, warnings)


def _product_summary(report: AdjReport) -> List[dict]:
    factor = report.days / YEAR_DAYS
    summaries = []
    for code in report.products:
        stats = {'prev_hc': 0, 'curr_hc': 0, 'prev_named': 0, 'curr_named': 0,
                 'prev_premium': 0.0, 'curr_premium': 0.0}
        for row in report.rows:
            decision = row.decisions.get(code)
            if decision is None:
                continue
            year = 'curr' if row.current else 'prev'
            if decision.basis == HEADCOUNT:
                stats[f'{year}_hc'] += 1
                stats[f'{year}_premium'] += row.priced.get(code) or 0.0
            elif decision.basis == NAMED:
                stats[f'{year}_named'] += 1
        adj = (stats['curr_premium'] - stats['prev_premium']) * factor
        life = code in LIFE_PRODUCTS
        summaries.append({
            'name': code, 'type': 'Life' if life else 'Medical', **stats,
            'prev_premium': round(stats['prev_premium'], 2), 'curr_premium': round(stats['curr_premium'], 2),
            'adjustment': round(adj, 2),
            'adjustment_with_gst': round(adj if life else adj * (1 + GST_RATE), 2),
        })
    return summaries


def basis_review(report: AdjReport) -> List[dict]:
    """Named rows and over-limit exceptions, for on-screen review and the Notes sheet."""
    review = []
    for row in report.rows:
        for code, decision in row.decisions.items():
            if decision.basis != NAMED and not decision.over_limit:
                continue
            values = row.row.products.get(code, {})
            review.append({
                'period': row.label, 'name': row.row.emp.get('name', ''), 'emp_id': row.row.emp.get('emp_id', ''),
                'product': code, 'age': round(row.age, 2) if row.age is not None else None,
                'sum_insured': values.get('eligible_si') if values.get('eligible_si') is not None else values.get('present_si'),
                'basis': decision.basis, 'reason': decision.reason,
            })
    return review


def _listing_info(listing: Listing) -> dict:
    return {
        'filename': listing.filename, 'sheet': listing.sheet_name, 'label': listing.label,
        'renewal_date': listing.renewal_date.strftime('%d/%m/%Y') if listing.renewal_date else None,
        'rows': len(listing.rows),
    }


def summarise(report: AdjReport) -> dict:
    prev_groups = {r.group for r in report.rows if not r.current}
    curr_groups = {r.group for r in report.rows if r.current}
    return {
        'client': report.client, 'scope': report.scope, 'pro_rata_days': report.days,
        'previous': _listing_info(report.prev), 'current': _listing_info(report.curr),
        'employee_summary': {
            'prev_total': len(prev_groups), 'curr_total': len(curr_groups),
            'common': len(prev_groups & curr_groups), 'added': len(curr_groups - prev_groups),
            'removed': len(prev_groups - curr_groups),
        },
        'products': _product_summary(report),
        'basis_review': basis_review(report),
        'limits': {code: {'previous': v['prev'], 'current': v['curr']} for code, v in report.limits.items()},
        'entity_mapping': report.entity_map,
        'warnings': report.warnings,
    }


def process_adj_listing(file1_path: str, file2_path: str, file1_name: str, file2_name: str,
                        output_path: str, pro_rata_days: int = 183, client_label: str = '',
                        limits: Optional[Dict[str, Dict]] = None) -> dict:
    """Entry point used by the API route. Raises ValueError for user-fixable input problems."""
    from .writer import write_report

    first, second = read_listing(file1_path, file1_name), read_listing(file2_path, file2_name)
    if first.year == second.year:
        raise ValueError(f"Both files are policy year {first.year}. Upload one previous-year and one current-year listing.")
    prev, curr = (first, second) if first.year < second.year else (second, first)
    report = build_report(prev, curr, pro_rata_days, client_label, limits or {})
    write_report(report, output_path)
    result = summarise(report)
    result['display_filename'] = f"{report.client} - {prev.label} Adj ({report.scope}).xlsx"
    logger.info("Adj listing generated: %s -> %s (%d rows, products=%s, warnings=%d)",
                prev.label, curr.label, len(report.rows), report.products, len(report.warnings))
    return result
