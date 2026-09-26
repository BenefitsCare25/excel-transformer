"""Group invoice continuations and resolve their recorded field evidence."""

from .evidence import resolve_field
from .fields import AMOUNT_LABELS, HEADER_LABELS, SCHEMES


FIELD_NAMES = {
    "bill_ref": "bill reference", "bill_date": "bill date", "hrn": "HRN",
    "visit_date": "visit date", "total": "total amount", "medishield": "MediShield Life",
    "medisave": "MediSave", "other_schemes": "other schemes", "cash": "cash payable",
}
CONFUSABLES = (frozenset("0O"), frozenset("1IL"), frozenset("2Z"), frozenset("5S"), frozenset("8B"))


def _compatible_refs(first: str | None, second: str | None) -> bool:
    if not first or not second:
        return False
    if len(first) != len(second):
        return False
    return all(a == b or any({a, b} <= group for group in CONFUSABLES)
               for a, b in zip(first.upper(), second.upper()))


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


def _resolve_invoice(group: list[dict]) -> tuple[dict, list[str]]:
    row = {"pages": sorted({number for page in group for number in page["pages"]}),
           "review_fields": [], "field_candidates": {}, "evidence": {},
           "pagination_evidence": [item for page in group for item in page.get("_pagination_evidence", [])]}
    issues = []
    pagination = [page["_pagination"] for page in group if page.get("_pagination")]
    counts = {total for _, total in pagination}
    parts = {page.get("_pagination_part") or page["_pagination"][0] for page in group
             if page.get("_pagination_part") or page.get("_pagination")}
    complete = (len(counts) == 1 and parts == set(range(1, next(iter(counts)) + 1)))
    if pagination and not complete:
        issues.append("invoice pagination is incomplete or inconsistent")
    if any(page.get("_pagination_evidence") and page.get("_pagination_review") for page in group):
        issues.append("invoice pagination has uncertain OCR readings")
    for field in (*HEADER_LABELS, *AMOUNT_LABELS):
        observations = [item for page in group for item in page["_evidence"].get(field, [])]
        value, candidates, unresolved = resolve_field(observations)
        expected = (any(page["_schemes"].get(field, False) for page in group) if field in SCHEMES
                    else any(page["_presence"].get(field, False) for page in group))
        if value is None and field in SCHEMES and not expected and complete:
            value, unresolved = 0.0, False
        if value is None and field == "hrn" and not expected and complete:
            value, unresolved = "-", False
        if unresolved:
            row["review_fields"].append(field)
            if not candidates:
                issues.append(f"{FIELD_NAMES[field]} could not be read")
            elif len([candidate for candidate in candidates if candidate["score"] >= .90]) > 1:
                alternatives = " / ".join(str(candidate["value"]) for candidate in candidates)
                issues.append(f"{FIELD_NAMES[field]} has conflicting OCR readings: {alternatives}")
            else:
                issues.append(f"{FIELD_NAMES[field]} has low OCR confidence")
        row[field] = value
        row["field_candidates"][field] = candidates
        row["evidence"][field] = observations
    if all(row[field] is not None for field in ("total", *SCHEMES, "cash")):
        paid = sum(row[field] for field in (*SCHEMES, "cash"))
        if abs(round(paid - row["total"], 2)) > .01:
            issues.append("payment amounts do not reconcile to total")
            row["review_fields"].extend(field for field in AMOUNT_LABELS if field not in row["review_fields"])
    name = row["bill_ref"] or f"Pages {', '.join(map(str, row['pages']))}"
    row["review_notes"] = issues
    return row, [f"{name}: {issue}; review source pages {', '.join(map(str, row['pages']))}." for issue in issues]


def merge_pages(pages: list[dict]) -> tuple[list[dict], list[str]]:
    resolved = [_resolve_invoice(group) for group in _group_pages(pages)]
    warnings = [warning for _, issues in resolved for warning in issues]
    latest = {}
    for index, (row, _) in enumerate(resolved):
        key = row["bill_ref"] or f"unreadable-{index}"
        previous = latest.get(key)
        if previous and previous["bill_date"] != row["bill_date"]:
            warnings.append(f"{key}: separate invoice versions have different bill dates; latest version kept.")
        if not previous or (row["bill_date"] or "") > (previous["bill_date"] or ""):
            latest[key] = row
    rows = sorted(latest.values(), key=lambda row: (row["bill_date"] or "", row["bill_ref"] or ""))
    return rows, list(dict.fromkeys(warnings))
