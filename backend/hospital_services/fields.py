"""Associate invoice labels with nearby OCR observations using text geometry."""

from datetime import datetime
import re

import numpy as np

from .evidence import resolve_field
from .ocr_types import OcrItem


DATE_PATTERN = re.compile(r"(?<!\d)(\d{1,2})[\s./-]*([A-Z]{3})[\s./-]*(\d{4})\b", re.I)
MONEY_PATTERN = re.compile(r"^-?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{2})$")
REF_PATTERN = re.compile(r"^(?:\d{8}[A-Z]|H\d{8,}[A-Z0-9]*)$", re.I)
HRN_PATTERN = re.compile(r"^[A-Z]\d{3,}[A-Z0-9]{6,}$", re.I)
PAGE_PATTERN = re.compile(r"PAGE\s*(\d+)\s*OF\s*(\d+)", re.I)
PAGE_LABEL = re.compile(r"\bPAGE\s*\d+\s*OF", re.I)
PAGE_PART = re.compile(r"\bPAGE\s*(\d+)\s*OF", re.I)
HEADER_LABELS = {
    "bill_ref": ("BILLREFNO", "BILLRFNO", "BILLREFERENCENO"),
    "bill_date": ("BILLDATE",),
    "hrn": ("HRN",),
    "visit_date": ("VISITDATE", "ADMISSIONDATE"),
}
AMOUNT_LABELS = {
    "total": ("TOTALAMOUNTAFTERGOVTSUBSIDY",),
    "medishield": ("PAYABLEBYMEDISHIELDLIFE", "MEDISHIELDLIFE"),
    "medisave": ("PAYABLEBYMEDISAVE", "MEDISAVECANCERPAYER"),
    "other_schemes": ("PAYABLEBYOTHERSCHEMES",),
    "cash": ("TOTALAMOUNTPAYABLE",),
}
COMPETING_HEADERS = (*sum(HEADER_LABELS.values(), ()), "LOCATION", "PATIENTNAME", "NRIC", "MRN", "FIN")
SCHEMES = ("medishield", "medisave", "other_schemes")


def _key(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _matches(item: OcrItem, labels: tuple[str, ...]) -> bool:
    key = _key(item.text)
    return any(label in key for label in labels)


def _date(text: str) -> str | None:
    match = DATE_PATTERN.search(text)
    if match:
        try:
            return datetime.strptime(" ".join(match.groups()).upper(), "%d %b %Y").date().isoformat()
        except ValueError:
            pass
    return None


def _reference(text: str) -> str | None:
    value = text.strip().rstrip(".,:").upper()
    return value if REF_PATTERN.fullmatch(value) else None


def _hrn(text: str) -> str | None:
    value = text.strip().upper()
    return value if HRN_PATTERN.fullmatch(value) else None


def _money(text: str) -> float | None:
    value = text.strip().replace(" ", "").replace("$", "").replace("−", "-")
    return abs(float(value.replace(",", ""))) if MONEY_PATTERN.fullmatch(value) else None


def parse_pagination(text: str) -> tuple[int, int] | None:
    match = PAGE_PATTERN.search(text)
    if match and 1 <= int(match[1]) <= int(match[2]) <= 100:
        return tuple(map(int, match.groups()))
    return None


PARSERS = {"bill_ref": _reference, "bill_date": _date, "hrn": _hrn, "visit_date": _date}


def _value_hint(item: OcrItem, field: str) -> bool:
    text = item.text.strip()
    if field in ("bill_ref", "hrn"):
        return bool(re.match(r"[A-Z]?\d{6,}", text, re.I))
    return bool(re.search(r"\d{1,2}\s*[A-Z]{3}\s*\d{4}", text, re.I))


def _header_items(items: list[OcrItem], field: str) -> list[OcrItem]:
    labels = HEADER_LABELS[field]
    parser = PARSERS[field]
    selected = []
    for heading in sorted((item for item in items if _matches(item, labels)), key=lambda item: item.top):
        if parser(heading.text) is not None:
            selected.append(heading)
            continue
        height = heading.height
        boundaries = [other.left for other in items if other.left > heading.right
                      and abs(other.center_y - heading.row_y_at(other.left)) <= height
                      and any(label in _key(other.text) for label in COMPETING_HEADERS)]
        right_boundary = min(boundaries, default=float("inf"))
        candidates = []
        for item in items:
            if item is heading or not _value_hint(item, field):
                continue
            if any(label in _key(item.text) for label in COMPETING_HEADERS):
                continue
            dx, dy = item.left - heading.left, item.top - heading.top
            stacked = (-height <= dx <= height * 2 and 0 <= dy <= height * 3.5
                       and item.left < right_boundary)
            inline_distance = abs(item.center_y - heading.row_y_at(item.left))
            inline = item.left >= heading.right - height * .6 and inline_distance <= height * .8 and item.right < right_boundary
            if stacked or inline:
                distance = abs(dy - height) / height + abs(dx) / (height * 4) if stacked else inline_distance / height
                candidates.append((distance, item))
        if candidates:
            selected.append(min(candidates, key=lambda candidate: candidate[0])[1])
    return selected


def _amount_items(items: list[OcrItem], field: str) -> list[OcrItem]:
    selected = []
    headings = [item for item in items if any(_matches(item, labels) for labels in AMOUNT_LABELS.values())]
    for heading in items:
        if not _matches(heading, AMOUNT_LABELS[field]):
            continue
        candidates = []
        for item in items:
            raw = item.text.strip().replace(" ", "").replace("$", "").replace("−", "-")
            if not re.fullmatch(r"-?[\d,.]*\d[\d,.]*", raw) or item.left <= heading.right:
                continue
            distance = abs(item.center_y - heading.row_y_at(item.left))
            if any(other is not heading and other.right < item.left
                   and abs(item.center_y - other.row_y_at(item.left)) < distance
                   for other in headings):
                continue
            if distance <= max(heading.height, item.height) * .8:
                candidates.append((distance / max(heading.height, item.height), item))
        if candidates:
            selected.append(min(candidates, key=lambda candidate: candidate[0])[1])
    return selected


def field_items(items: list[OcrItem]) -> dict[str, list[OcrItem]]:
    fields = {**{field: _header_items(items, field) for field in HEADER_LABELS},
              **{field: _amount_items(items, field) for field in AMOUNT_LABELS}}
    fields["other_schemes"].extend(_table_components(items, "OTHERSCHEMES"))
    return fields


def _table_components(items: list[OcrItem], section: str) -> list[OcrItem]:
    headings = [item for item in items if _key(item.text) == section]
    columns = [item for item in items if _key(item.text) == "AMOUNTPAYABLE"]
    selected = []
    for heading in headings:
        column = next((item for item in columns if item.top < heading.top), None)
        if column is None:
            continue
        boundaries = [item.top for item in items if item.top > heading.bottom
                      and _key(item.text) in ("MEDISHIELDLIFE", "MEDISAVE", "OTHERSCHEMES", "TOTALAMOUNTPAYABLE")]
        bottom = min(boundaries, default=heading.bottom)
        selected.extend(item for item in items if heading.bottom < item.center_y < bottom
                        and item.left >= column.left
                        and re.fullmatch(r"-?[\d,.]*\d[\d,.]*", item.text.strip().replace(" ", "")))
    return selected


def _table_evidence(items: list[OcrItem], page_number: int) -> dict | None:
    components = _table_components(items, "OTHERSCHEMES")
    if not components:
        return None
    observations = []
    for item in components:
        readings = [{"value": _money(reading.text), "raw": reading.text, "score": reading.score,
                     "page": page_number, "box": [item.left, item.top, item.right, item.bottom]}
                    for reading in item.readings]
        value, candidates, unresolved = resolve_field(readings)
        observations.append({"value": value, "raw": [reading["raw"] for reading in readings],
                             "score": next((candidate["score"] for candidate in candidates
                                            if candidate["value"] == value), 0.0),
                             "unresolved": unresolved})
    return {
        "value": round(sum(item["value"] for item in observations), 2)
                 if all(item["value"] is not None for item in observations) else None,
        "raw": str([item["raw"] for item in observations]),
        "score": min(item["score"] for item in observations),
        "page": page_number,
        "box": [min(item.left for item in components), min(item.top for item in components),
                max(item.right for item in components), max(item.bottom for item in components)],
        "source": "payment-table",
        "unresolved": any(item["unresolved"] for item in observations),
    }


def retry_items(items: list[OcrItem]) -> list[OcrItem]:
    selected = {id(item): item for item in items if PAGE_LABEL.search(item.text)
                and (item.score < .98 or parse_pagination(item.text) is None)}
    fields = field_items(items)
    for field, candidates in fields.items():
        parser = PARSERS.get(field, _money)
        for item in candidates:
            if field in ("bill_ref", "hrn") or item.score < .98 or parser(item.text) is None:
                selected[id(item)] = item
    amounts = {field: next((value for item in candidates if (value := _money(item.text)) is not None), None)
               for field, candidates in fields.items() if field in AMOUNT_LABELS}
    if amounts["total"] is not None and amounts["cash"] is not None:
        paid = sum(amounts[field] or 0 for field in (*SCHEMES, "cash"))
        if abs(round(amounts["total"] - paid, 2)) > .01:
            for field in AMOUNT_LABELS:
                selected.update({id(item): item for item in fields[field]})
    return list(selected.values())


def extract_page(lines: list, page_number: int) -> dict | None:
    items = [item if isinstance(item, OcrItem) else OcrItem(item[0], np.asarray(item[1])) for item in lines]
    evidence = {}
    values = {}
    fields = field_items(items)
    table_components = _table_components(items, "OTHERSCHEMES")
    for field, candidates in fields.items():
        parser = PARSERS.get(field, _money)
        observations = []
        for item in candidates:
            if field == "other_schemes" and any(item is component for component in table_components):
                continue
            box = [round(item.left, 1), round(item.top, 1), round(item.right, 1), round(item.bottom, 1)]
            observations.extend({"value": parser(reading.text), "raw": reading.text, "score": reading.score,
                                 "page": page_number, "box": box, "source": reading.source}
                                for reading in item.readings)
        if field == "other_schemes" and (table := _table_evidence(items, page_number)):
            observations.append(table)
        evidence[field] = observations
        values[field] = resolve_field(observations)[0]
    pagination_items = [item for item in items if PAGE_LABEL.search(item.text)]
    pagination_evidence = [{"value": parse_pagination(reading.text), "raw": reading.text,
                           "score": reading.score, "source": reading.source, "page": page_number,
                           "box": [item.left, item.top, item.right, item.bottom]}
                          for item in pagination_items for reading in item.readings]
    pagination, _, pagination_review = resolve_field(pagination_evidence)
    part_readings = [{**observation, "value": int(match[1]) if 1 <= int(match[1]) <= 100 else None}
                     for observation in pagination_evidence if (match := PAGE_PART.search(observation["raw"]))]
    pagination_part = resolve_field(part_readings)[0]
    if not values["bill_ref"] and not pagination_items:
        return None
    return {
        **values,
        "pages": [page_number],
        "_evidence": evidence,
        "_presence": {field: any(_matches(item, labels) for item in items) for field, labels in HEADER_LABELS.items()},
        "_schemes": {
            "medishield": any(_key(item.text).startswith(("PAYABLEBYMEDISHIELDLIFE", "MEDISHIELDLIFE")) for item in items),
            "medisave": any(_key(item.text) == "MEDISAVE" or _key(item.text).startswith(
                ("PAYABLEBYMEDISAVE", "MEDISAVECANCERPAYER")) for item in items),
            "other_schemes": any(_key(item.text).startswith(("PAYABLEBYOTHERSCHEMES", "OTHERSCHEMES")) for item in items),
        },
        "_pagination": pagination,
        "_pagination_part": pagination_part,
        "_pagination_review": pagination_review,
        "_pagination_evidence": pagination_evidence,
    }
