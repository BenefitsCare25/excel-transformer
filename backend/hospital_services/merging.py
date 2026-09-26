"""Group invoice continuations and resolve their recorded field evidence."""

from datetime import datetime
from itertools import product
from math import prod

from collections import defaultdict

from .evidence import MIN_FIELD_SCORE, confusable_equal, resolve_field
from .fields import AMOUNT_LABELS, HEADER_LABELS, IDENTIFIER_FORMATS, SCHEMES


FIELD_NAMES = {
    "bill_ref": "bill reference", "bill_date": "bill date", "hrn": "HRN",
    "visit_date": "visit date", "total": "total amount", "medishield": "MediShield Life",
    "medisave": "MediSave", "other_schemes": "other schemes", "cash": "cash payable",
}
AMOUNT_FIELDS = ("total", *SCHEMES, "cash")
MAX_COMBINATIONS = 4096


def _compatible_refs(first: str | None, second: str | None) -> bool:
    return bool(first and second) and confusable_equal(first, second)


def _continues(group: list[dict], page: dict) -> bool:
    previous = group[-1]
    first_part, next_part = previous.get("_pagination"), page.get("_pagination")
    if not first_part or page["pages"][0] != previous["pages"][-1] + 1:
        return False
    if next_part is None:
        if page.get("_pagination_part") != first_part[0] + 1 or first_part[0] >= first_part[1]:
            return False
    elif next_part != (first_part[0] + 1, first_part[1]):
        return False
    if previous["bill_ref"] and page["bill_ref"]:
        return _compatible_refs(previous["bill_ref"], page["bill_ref"])
    return bool(previous["bill_date"] and previous["bill_date"] == page["bill_date"])


def _group_pages(pages: list[dict]) -> list[list[dict]]:
    groups = []
    exact = {}
    current = None
    for page in pages:
        key = (page["bill_ref"], page["bill_date"])
        if current and _continues(current, page):
            current.append(page)
        elif all(key) and key in exact:
            current = exact[key]
            current.append(page)
        else:
            current = [page]
            groups.append(current)
        if all(key):
            exact[key] = current
    return groups


def _pagination_state(group: list[dict]) -> tuple[bool, bool, str | None]:
    """Return (all parts present, header page present, review issue)."""
    pagination = [page["_pagination"] for page in group if page.get("_pagination")]
    counts = {total for _, total in pagination}
    parts = {page.get("_pagination_part") or page["_pagination"][0] for page in group
             if page.get("_pagination_part") or page.get("_pagination")}
    complete = len(counts) == 1 and parts == set(range(1, next(iter(counts)) + 1))
    issue = None
    if pagination and not complete:
        missing = sorted(set(range(1, next(iter(counts)) + 1)) - parts) if len(counts) == 1 else []
        if missing:
            issue = (f"invoice pagination: page{'s' if len(missing) > 1 else ''} "
                     f"{', '.join(map(str, missing))} of {next(iter(counts))} not found in the PDF")
        else:
            issue = "invoice pagination is incomplete or inconsistent"
    return complete, 1 in parts, issue


def _reconciles(values: dict) -> bool:
    paid = sum(values[field] for field in (*SCHEMES, "cash"))
    return abs(round(values["total"] - paid, 2)) <= .01


def _reconcile_candidates(fields: dict) -> dict | None:
    """Return the only combination of credible amount readings that reconciles to the total."""
    choices = []
    for field in AMOUNT_FIELDS:
        state = fields[field]
        options = ([state["value"]] if state["default"] else
                   [candidate["value"] for candidate in state["candidates"] if candidate["score"] >= MIN_FIELD_SCORE])
        if not options:
            return None
        choices.append(options)
    if prod(len(options) for options in choices) > MAX_COMBINATIONS:
        return None
    matches = [values for combination in product(*choices)
               if _reconciles(values := dict(zip(AMOUNT_FIELDS, combination)))]
    return matches[0] if len(matches) == 1 else None


def _field_states(group: list[dict]) -> dict[str, dict]:
    states = {}
    for field in (*HEADER_LABELS, *AMOUNT_LABELS):
        observations = [item for page in group for item in page["_evidence"].get(field, [])]
        value, candidates, unresolved = resolve_field(observations, IDENTIFIER_FORMATS.get(field, ()))
        expected = (any(page["_schemes"].get(field, False) for page in group) if field in SCHEMES
                    else any(page["_presence"].get(field, False) for page in group))
        states[field] = {"value": value, "candidates": candidates, "unresolved": unresolved,
                         "observations": observations, "expected": expected, "default": False}
    return states


def _apply_absent_values(group: list[dict], fields: dict, complete: bool, has_header_page: bool) -> None:
    """Fill values the invoice does not print, only when the document proves they are empty."""
    hrn = fields["hrn"]
    if hrn["value"] is None and (any(page.get("_hrn_dash") for page in group)
                                 or (not hrn["expected"] and (complete or has_header_page))):
        hrn.update(value="-", unresolved=False, default=True)
    absent = [field for field in SCHEMES if fields[field]["value"] is None and not fields[field]["expected"]]
    if not absent:
        return
    present = [field for field in AMOUNT_FIELDS if field not in absent]
    # Arithmetic proves the absence only when every printed amount it relies on was read reliably.
    proven = complete or (all(fields[field]["value"] is not None and not fields[field]["unresolved"]
                              for field in present) and _reconciles(
        {**{field: fields[field]["value"] for field in present}, **{field: 0.0 for field in absent}}))
    if proven:
        for field in absent:
            fields[field].update(value=0.0, unresolved=False, default=True)


def _reconcile_amounts(fields: dict) -> None:
    """Settle amount readings with the invoice's own arithmetic: total = schemes + cash."""
    choice = _reconcile_candidates(fields)
    if choice is None:
        return
    for field, value in choice.items():
        # Readings that were themselves flagged (e.g. a doubtful payment-table component) stay flagged.
        flagged = any(item.get("unresolved") for item in fields[field]["observations"] if item["value"] == value)
        fields[field].update(value=value, unresolved=flagged)


def _resolve_invoice(group: list[dict]) -> dict:
    row = {"pages": sorted({number for page in group for number in page["pages"]}),
           "review_fields": [], "field_candidates": {}, "evidence": {},
           "pagination_evidence": [item for page in group for item in page.get("_pagination_evidence", [])]}
    issues = []
    complete, has_header_page, pagination_issue = _pagination_state(group)
    if pagination_issue:
        issues.append(pagination_issue)
    if any(page.get("_pagination_evidence") and page.get("_pagination_review") for page in group):
        issues.append("invoice pagination has uncertain OCR readings")
        complete = False
    fields = _field_states(group)
    _apply_absent_values(group, fields, complete, has_header_page)
    _reconcile_amounts(fields)
    for field, state in fields.items():
        if state["unresolved"]:
            row["review_fields"].append(field)
            credible = [candidate for candidate in state["candidates"] if candidate["score"] >= MIN_FIELD_SCORE]
            if not state["candidates"]:
                issues.append(f"{FIELD_NAMES[field]} could not be read")
            elif len(credible) > 1:
                alternatives = " / ".join(str(candidate["value"]) for candidate in state["candidates"])
                issues.append(f"{FIELD_NAMES[field]} has conflicting OCR readings: {alternatives}")
            else:
                issues.append(f"{FIELD_NAMES[field]} has low OCR confidence")
        row[field] = state["value"]
        row["field_candidates"][field] = state["candidates"]
        row["evidence"][field] = state["observations"]
    if all(row[field] is not None for field in AMOUNT_FIELDS) and not _reconciles(row):
        issues.append("payment amounts do not reconcile to total")
        row["review_fields"].extend(field for field in AMOUNT_LABELS if field not in row["review_fields"])
    row["review_notes"] = issues
    return row


def _format_date(value: str | None) -> str:
    return datetime.strptime(value, "%Y-%m-%d").strftime("%d %b %Y") if value else "an unreadable date"


def _versions(resolved: list[tuple[list[dict], dict]]) -> list[tuple[list[dict], dict]]:
    """Recombine groups of one bill that no readable bill date separates into versions."""
    dates = {row["bill_date"] for _, row in resolved if row["bill_date"]}
    if len(resolved) == 1 or len(dates) > 1:
        return resolved
    group = sorted((page for pages, _ in resolved for page in pages), key=lambda page: page["pages"][0])
    return [(group, _resolve_invoice(group))]


def merge_pages(pages: list[dict]) -> tuple[list[dict], list[str]]:
    """Return one row per bill (its latest version) and document-level notes."""
    by_reference = defaultdict(list)
    for index, group in enumerate(_group_pages(pages)):
        row = _resolve_invoice(group)
        by_reference[row["bill_ref"] or f"unreadable-{index}"].append((group, row))
    rows, notes = [], []
    for key, resolved in by_reference.items():
        versions = [row for _, row in _versions(resolved)]
        dated = [row for row in versions if row["bill_date"]]
        undated = [row for row in versions if not row["bill_date"]]
        # A part whose bill date is unreadable cannot be assigned to one of several dated versions;
        # it is reported as its own row with the unread date flagged rather than dropped.
        rows.extend(undated)
        if not dated:
            continue
        newest = max(dated, key=lambda row: row["bill_date"])
        rows.append(newest)
        for older in dated:
            if older is not newest:
                notes.append(f"{key}: the version dated {_format_date(older['bill_date'])} (pages "
                             f"{', '.join(map(str, older['pages']))}) is superseded by the version dated "
                             f"{_format_date(newest['bill_date'])}; only the latest version is reported.")
    rows.sort(key=lambda row: (row["bill_date"] or "", row["bill_ref"] or "", row["pages"][0]))
    return rows, list(dict.fromkeys(notes))
