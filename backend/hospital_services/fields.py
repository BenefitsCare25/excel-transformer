"""Read hospital invoice fields from OCR text and its page coordinates."""

from dataclasses import dataclass
from datetime import date, datetime
import re

import numpy as np


DATE_PATTERN = re.compile(r"(?<!\d)(\d{1,2})[\s./-]+([A-Z]{3})[\s./-]+(\d{4})\b", re.I)
MONEY_PATTERN = re.compile(r"^-?\d{1,3}(?:,\d{3})*(?:\.\d{2})$")
REF_PATTERN = re.compile(r"^(?:\d{8}[A-Z]|H\d{8,}[A-Z0-9]*)$", re.I)
HRN_PATTERN = re.compile(r"^[A-Z]\d{3,}[A-Z0-9]{6,}$", re.I)


@dataclass(frozen=True)
class OcrItem:
    text: str
    box: np.ndarray

    @property
    def left(self) -> float:
        return float(self.box[:, 0].min())

    @property
    def right(self) -> float:
        return float(self.box[:, 0].max())

    @property
    def top(self) -> float:
        return float(self.box[:, 1].min())

    @property
    def bottom(self) -> float:
        return float(self.box[:, 1].max())

    @property
    def center_y(self) -> float:
        return float(self.box[:, 1].mean())

    def row_y_at(self, x: float) -> float:
        left_y = float((self.box[0, 1] + self.box[3, 1]) / 2)
        right_y = float((self.box[1, 1] + self.box[2, 1]) / 2)
        span = float(self.box[1, 0] - self.box[0, 0])
        slope = (right_y - left_y) / span if span else 0.0
        return left_y + slope * (x - float(self.box[0, 0]))


def _key(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def _label_matches(text: str, label: str) -> bool:
    key = _key(text)
    return label in key or (label == "BILLREFNO" and key == "BILLRFNO")


def _date(text: str) -> date | None:
    match = DATE_PATTERN.search(text)
    if not match:
        return None
    try:
        return datetime.strptime(" ".join(match.groups()).upper(), "%d %b %Y").date()
    except ValueError:
        return None


def _reference(text: str) -> str | None:
    value = text.strip().rstrip(".,:").upper()
    return value if REF_PATTERN.fullmatch(value) else None


def _hrn(text: str) -> str | None:
    value = text.strip().upper()
    return value if HRN_PATTERN.fullmatch(value) else None


def _header_value(items: list[OcrItem], label: str, parse):
    labels = sorted((item for item in items if _label_matches(item.text, label)),
                    key=lambda item: item.top)
    for heading in labels:
        inline = parse(heading.text)
        if inline is not None:
            return inline
        candidates = []
        for item in items:
            if item is heading:
                continue
            value = parse(item.text)
            if value is None:
                continue
            dx = item.left - heading.left
            dy = item.top - heading.top
            if -15 <= dx <= 230 and -15 <= dy <= 55:
                candidates.append((abs(dy - 18) + abs(dx) / 12, value))
        if candidates:
            return min(candidates, key=lambda candidate: candidate[0])[1]
    return None


def _reference_by_date(items: list[OcrItem], bill_date: date) -> str | None:
    candidates = []
    for item in items[:30]:
        ref = _reference(item.text)
        if ref is None:
            continue
        for dated in items[:30]:
            if _date(dated.text) != bill_date:
                continue
            dx = dated.left - item.left
            distance = abs(dated.center_y - item.row_y_at(dated.left))
            if 30 <= dx <= 350 and distance <= 14:
                candidates.append((distance, dx, ref))
    return min(candidates)[2] if candidates else None


def _amount(items: list[OcrItem], label: str) -> float | None:
    labels = sorted((item for item in items if label in _key(item.text)), key=lambda item: item.top)
    for heading in labels:
        candidates = []
        for item in items:
            value = item.text.strip().replace(" ", "").replace("$", "")
            if not MONEY_PATTERN.fullmatch(value):
                continue
            if not 5 <= item.left - heading.right <= 900:
                continue
            distance = abs(item.center_y - heading.row_y_at(item.left))
            if distance <= 14:
                candidates.append((distance, abs(float(value.replace(",", "")))))
        if candidates:
            return min(candidates, key=lambda candidate: candidate[0])[1]
    return None


def extract_page(lines: list[tuple[str, np.ndarray]], page_number: int) -> dict | None:
    items = [OcrItem(text, box) for text, box in lines]
    bill_date = _header_value(items, "BILLDATE", _date)
    hrn = _header_value(items, "HRN", _hrn)
    ref = _header_value(items, "BILLREFNO", _reference)
    if ref == hrn:
        ref = None
    if not ref and bill_date:
        ref = _reference_by_date(items, bill_date)
    if not ref or not bill_date:
        return None
    visit_date = (_header_value(items, "VISITDATE", _date)
                  or _header_value(items, "ADMISSIONDATE", _date))
    return {
        "bill_ref": ref,
        "bill_date": bill_date.isoformat(),
        "hrn": hrn or "",
        "visit_date": visit_date.isoformat() if visit_date else "",
        "total": _amount(items, "TOTALAMOUNTAFTERGOVTSUBSIDY"),
        "medishield": (_amount(items, "PAYABLEBYMEDISHIELDLIFE")
                       or _amount(items, "MEDISHIELDLIFE")),
        "medisave": (_amount(items, "PAYABLEBYMEDISAVE")
                     or _amount(items, "MEDISAVECANCERPAYER")),
        "other_schemes": _amount(items, "PAYABLEBYOTHERSCHEMES"),
        "cash": _amount(items, "TOTALAMOUNTPAYABLE"),
        "pages": [page_number],
    }
