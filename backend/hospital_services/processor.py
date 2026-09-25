"""Process scanned hospital bills without sending raw pages to a remote service."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
import gc
import math
import re
from typing import Callable

import cv2
import fitz
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from rapidocr import RapidOCR


HEADERS = (
    "Bill Ref No.", "Bill Date", "HRN", "Visit Date",
    "Total Amount (After Govt Subsidy)", "Payable by Medishield Life",
    "Payable by Medisave", "Total Amount Payable\nCash",
)
ID_PATTERN = re.compile(r"(?<![A-Z0-9])[STFGM][0-9X*]{7}[A-Z0-9X*](?![A-Z0-9])", re.I)
MASKED_ID_PATTERN = re.compile(r"(?<![A-Z0-9])[A-Z0-9]*[X*]{3,}[A-Z0-9]*(?![A-Z0-9])", re.I)
DATE_PATTERN = re.compile(r"(?<!\d)(\d{1,2})\s+([A-Z]{3})\s+(\d{4})\b", re.I)
MONEY_PATTERN = re.compile(r"^-?\d{1,3}(?:,\d{3})*(?:\.\d{2})$")
REF_PATTERN = re.compile(r"^(?:\d{8}[A-Z]|H\d{8,}[A-Z0-9]*)$", re.I)
HRN_PATTERN = re.compile(r"\b[A-Z]\d{3,}[A-Z0-9]{6,}\b", re.I)
MAX_PAGES = 100
MAX_BYTES = 25 * 1024 * 1024


def _identifier(text: str) -> bool:
    compact = re.sub(r"[\s.\-]", "", text.upper())
    if ID_PATTERN.search(compact):
        return True
    return any(
        len(match.group()) >= 8 and len(match.group()) <= 12
        for match in MASKED_ID_PATTERN.finditer(compact)
    )


def _lines(image: np.ndarray, engine: RapidOCR) -> list[tuple[str, np.ndarray]]:
    result = engine(image)
    if not result.txts:
        return []
    return [(str(text).strip(), np.asarray(box)) for text, box in zip(result.txts, result.boxes)]


def _redact_image(image: np.ndarray, lines: list[tuple[str, np.ndarray]]) -> int:
    count = 0
    for text, box in lines:
        if not _identifier(text):
            continue
        x1 = max(0, int(box[:, 0].min()) - 5)
        x2 = min(image.shape[1], int(box[:, 0].max()) + 6)
        y1 = max(0, int(box[:, 1].min()) - 4)
        y2 = min(image.shape[0], int(box[:, 1].max()) + 5)
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 0), -1)
        count += 1
    return count


def _date(text: str):
    match = DATE_PATTERN.search(text)
    if not match:
        return None
    try:
        return datetime.strptime(" ".join(match.groups()).upper(), "%d %b %Y").date()
    except ValueError:
        return None


def _nearby_date(texts: list[str], label: str):
    for index, text in enumerate(texts):
        if label in text.upper():
            for candidate in texts[index:index + 7]:
                found = _date(candidate)
                if found:
                    return found
    return None


def _money_near(texts: list[str], label: str):
    for index, text in enumerate(texts):
        if label not in text.upper():
            continue
        for candidate in texts[index + 1:index + 5]:
            value = candidate.strip().replace(" ", "").replace("$", "")
            if MONEY_PATTERN.fullmatch(value):
                return abs(float(value.replace(",", "")))
    return None


def _extract_page(lines: list[tuple[str, np.ndarray]], page_number: int) -> dict | None:
    texts = [text for text, _ in lines]
    ref = next((text.upper() for text in texts[:30] if REF_PATTERN.fullmatch(text)), None)
    bill_date = _nearby_date(texts[:30], "BILL DATE")
    if not ref or not bill_date:
        return None
    visit_date = _nearby_date(texts[:35], "VISIT DATE") or _nearby_date(texts[:35], "ADMISSION DATE")
    hrn = next((match.group() for text in texts[:45] for match in HRN_PATTERN.finditer(text)
                if match.group().upper() != ref and not _identifier(match.group())), None)
    return {
        "bill_ref": ref,
        "bill_date": bill_date.isoformat(),
        "hrn": hrn or "",
        "visit_date": visit_date.isoformat() if visit_date else "",
        "total": _money_near(texts, "TOTAL AMOUNT (AFTER GOVT SUBSIDY)"),
        "medishield": _money_near(texts, "PAYABLE BY MEDISHIELD LIFE"),
        "medisave": _money_near(texts, "PAYABLE BY MEDISAVE"),
        "pages": [page_number],
    }


def _merge_pages(pages: list[dict]) -> tuple[list[dict], list[str]]:
    groups = {}
    for page in pages:
        key = (page["bill_ref"], page["bill_date"])
        if key not in groups:
            groups[key] = page
            continue
        entry = groups[key]
        entry["pages"].extend(page["pages"])
        for field in ("hrn", "visit_date", "total", "medishield", "medisave"):
            if entry[field] in (None, "") and page[field] not in (None, ""):
                entry[field] = page[field]

    latest = {}
    warnings = []
    for entry in groups.values():
        previous = latest.get(entry["bill_ref"])
        if not previous or entry["bill_date"] > previous["bill_date"]:
            latest[entry["bill_ref"]] = entry
        if previous and entry["bill_date"] != previous["bill_date"]:
            warnings.append(f'{entry["bill_ref"]}: multiple bill dates found; latest version kept.')
    rows = sorted(latest.values(), key=lambda row: (row["bill_date"], row["bill_ref"]))
    for row in rows:
        if not row["hrn"]:
            row["hrn"] = "-"
        for field in ("medishield", "medisave"):
            if row[field] is None:
                row[field] = 0.0
        if row["total"] is None:
            warnings.append(f'{row["bill_ref"]}: total amount needs review.')
        if not row["visit_date"]:
            warnings.append(f'{row["bill_ref"]}: visit date needs review.')
    return rows, warnings


def process_pdf(
    source: bytes, on_page: Callable[[int, int], None] | None = None
) -> tuple[bytes, list[dict], int, list[str]]:
    if len(source) > MAX_BYTES:
        raise ValueError("PDF is too large (25 MB limit).")
    if not source.startswith(b"%PDF-"):
        raise ValueError("Upload a valid PDF file.")
    try:
        document = fitz.open(stream=source, filetype="pdf")
    except Exception as exc:
        raise ValueError("Could not open the PDF.") from exc
    if document.is_encrypted:
        raise ValueError("PDF is encrypted. Upload an unencrypted copy.")
    if not len(document):
        raise ValueError("PDF contains no pages.")
    if len(document) > MAX_PAGES:
        raise ValueError(f"PDF has {len(document)} pages; the limit is {MAX_PAGES} pages per file.")

    engine = RapidOCR(params={
        "EngineConfig.onnxruntime.intra_op_num_threads": 2,
        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
        "Global.log_level": "warning",
    })
    redacted = fitz.open()
    extracted = []
    redaction_count = 0
    unreadable = []
    if on_page:
        on_page(0, len(document))
    for page_number, page in enumerate(document, 1):
        if page.rect.width * 2 > 5000 or page.rect.height * 2 > 5000:
            raise ValueError(f"Page {page_number}: page dimensions are too large.")
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
            pixmap.height, pixmap.width, 3).copy()
        original_lines = _lines(image, engine)
        count = _redact_image(image, original_lines)
        if any("NRIC" in text.upper() for text, _ in original_lines) and count == 0:
            raise ValueError(f"Page {page_number}: identifier could not be located for safe redaction.")
        redaction_count += count
        clean_lines = _lines(image, engine)
        if any(_identifier(text) for text, _ in clean_lines):
            raise ValueError(f"Page {page_number}: an identifier remains after redaction.")
        data = _extract_page(clean_lines, page_number)
        if data:
            extracted.append(data)
        else:
            unreadable.append(page_number)
        ok, png = cv2.imencode(".png", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        if not ok:
            raise ValueError(f"Page {page_number}: could not create redacted page.")
        output_page = redacted.new_page(width=page.rect.width, height=page.rect.height)
        output_page.insert_image(output_page.rect, stream=png.tobytes())
        if on_page:
            on_page(page_number, len(document))
        gc.collect()
    document.close()
    rows, warnings = _merge_pages(extracted)
    if unreadable:
        warnings.append(f"Pages without a readable bill reference: {', '.join(map(str, unreadable))}.")
    if not rows:
        raise ValueError("No bill rows could be extracted. Please use a clearer scan.")
    pdf_bytes = redacted.tobytes(garbage=4, deflate=True)
    redacted.close()
    return pdf_bytes, rows, redaction_count, warnings


def make_workbook(rows: list[dict]) -> bytes:
    if not isinstance(rows, list) or not 1 <= len(rows) <= 500:
        raise ValueError("Provide 1 to 500 reviewed bill rows.")
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet.append(HEADERS)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4B7A")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    sheet.row_dimensions[1].height = 34
    widths = (22, 16, 22, 16, 27, 25, 22, 25)
    for column, width in zip("ABCDEFGH", widths):
        sheet.column_dimensions[column].width = width
    for index, row in enumerate(rows, 2):
        ref = str(row.get("bill_ref", "")).strip().upper()
        if not REF_PATTERN.fullmatch(ref):
            raise ValueError(f"Row {index}: invalid bill reference.")
        hrn = str(row.get("hrn") or "-").strip()
        if not re.fullmatch(r"[A-Za-z0-9-][A-Za-z0-9 /-]{0,39}", hrn):
            raise ValueError(f"Row {index}: invalid HRN.")
        try:
            bill_date = datetime.strptime(row["bill_date"], "%Y-%m-%d")
            visit_date = datetime.strptime(row["visit_date"], "%Y-%m-%d") if row.get("visit_date") else None
            total = float(row["total"])
            medishield = float(row.get("medishield") or 0)
            medisave = float(row.get("medisave") or 0)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Row {index}: check dates and amounts.") from exc
        if min(total, medishield, medisave) < 0:
            raise ValueError(f"Row {index}: amounts must be zero or greater.")
        if not all(math.isfinite(value) for value in (total, medishield, medisave)):
            raise ValueError(f"Row {index}: amounts must be finite numbers.")
        sheet.append((ref, bill_date, hrn, visit_date,
                      total, medishield, medisave, f"=E{index}-F{index}-G{index}"))
        for col in ("B", "D"):
            sheet[f"{col}{index}"].number_format = "dd mmm yyyy"
        for col in ("E", "F", "G", "H"):
            sheet[f"{col}{index}"].number_format = '#,##0.00'
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:H{len(rows) + 1}"
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
