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
from .fields import COMPETING_HEADERS, REF_PATTERN, extract_page
from .merging import merge_pages
from .ocr import MAX_IMAGE_SIDE, create_engine, read_lines, retry_fields
from .ocr_types import OcrItem
from .workbook_review import add_review_sheet


HEADERS = (
    "Bill Ref No.", "Bill Date", "HRN", "Visit Date",
    "Total Amount (After Govt Subsidy)", "Payable by Medishield Life",
    "Payable by Medisave", "Total Amount Payable\nCash",
)
ID_PATTERN = re.compile(r"(?<![A-Z0-9])[STFGM](?:[\s.\-]*[0-9XOIL*]){7}[\s.\-]*[A-Z0-9X*](?![A-Z0-9])", re.I)
MASKED_ID_PATTERN = re.compile(r"(?<![A-Z0-9])[A-Z0-9]*[X*]{3,}[A-Z0-9]*(?![A-Z0-9])", re.I)
MAX_PAGES = 100
MAX_BYTES = 25 * 1024 * 1024


def _identifier(text: str) -> bool:
    if ID_PATTERN.search(text):
        return True
    compact = re.sub(r"[\s.\-]", "", text.upper())
    return any(
        len(match.group()) >= 8 and len(match.group()) <= 12
        for match in MASKED_ID_PATTERN.finditer(compact)
    )


def _identifier_regions(lines: list[OcrItem]) -> list[tuple[float, float, float, float]]:
    regions = []
    for item in lines:
        if not re.fullmatch(r"\s*NRIC(?:\s*/\s*(?:FIN|MRN))*\s*[:.]?\s*", item.text, re.I):
            continue
        height = item.height
        boundaries = [other.left for other in lines if other.left > item.right
                      and abs(other.center_y - item.center_y) <= height
                      and any(label in re.sub(r"[^A-Z0-9]", "", other.text.upper())
                              for label in COMPETING_HEADERS)]
        right = min(boundaries, default=item.left + max(item.right - item.left, height * 10))
        regions.append((item.left - 3, item.bottom + 1, right - 3, item.bottom + height * 2.5))
        inline = [other for other in lines if item.right < other.left < right
                  and abs(other.center_y - item.center_y) <= height * .8
                  and re.search(r"[0-9X*]{3}", other.text, re.I)]
        regions.extend((other.left - 3, other.top - 3, other.right + 3, other.bottom + 3) for other in inline)
    return regions


def _redact_image(image: np.ndarray, lines: list[OcrItem]) -> int:
    regions = _identifier_regions(lines)
    for item in lines:
        if not _identifier(item.text):
            continue
        regions.append((item.left - 5, item.top - 4, item.right + 6, item.bottom + 5))
    count = 0
    for left, top, right, bottom in regions:
        x1, x2 = max(0, int(left)), min(image.shape[1], int(right))
        y1, y2 = max(0, int(top)), min(image.shape[0], int(bottom))
        if x2 <= x1 or y2 <= y1:
            continue
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 0), -1)
        count += 1
    return count


def _open_document(source: bytes) -> fitz.Document:
    if len(source) > MAX_BYTES:
        raise ValueError("PDF is too large (25 MB limit).")
    if not source.startswith(b"%PDF-"):
        raise ValueError("Upload a valid PDF file.")
    try:
        document = fitz.open(stream=source, filetype="pdf")
    except Exception as exc:
        raise ValueError("Could not open the PDF.") from exc
    try:
        if document.is_encrypted:
            raise ValueError("PDF is encrypted. Upload an unencrypted copy.")
        if not len(document):
            raise ValueError("PDF contains no pages.")
        if len(document) > MAX_PAGES:
            raise ValueError(f"PDF has {len(document)} pages; the limit is {MAX_PAGES} pages per file.")
    except Exception:
        document.close()
        raise
    return document


def _process_page(page: fitz.Page, page_number: int, engine) -> tuple[np.ndarray, int, dict | None]:
    if page.rect.width * 2 > MAX_IMAGE_SIDE or page.rect.height * 2 > MAX_IMAGE_SIDE:
        raise ValueError(f"Page {page_number}: page dimensions are too large.")
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
        pixmap.height, pixmap.width, 3).copy()
    original_lines = read_lines(image, engine)
    count = _redact_image(image, original_lines)
    if any("NRIC" in item.text.upper() for item in original_lines) and count == 0:
        raise ValueError(f"Page {page_number}: identifier could not be located for safe redaction.")
    clean_lines = retry_fields(image, engine, read_lines(image, engine))
    if any(_identifier(reading.text) for item in clean_lines for reading in item.readings):
        raise ValueError(f"Page {page_number}: an identifier remains after redaction.")
    return image, count, extract_page(clean_lines, page_number)


def process_pdf(
    source: bytes, on_page: Callable[[int, int], None] | None = None
) -> tuple[bytes, list[dict], int, list[str]]:
    extracted = []
    redaction_count = 0
    unreadable = []
    with _open_document(source) as document, fitz.open() as redacted:
        engine = create_engine()
        if on_page:
            on_page(0, len(document))
        for page_number, page in enumerate(document, 1):
            image, count, data = _process_page(page, page_number, engine)
            redaction_count += count
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
        pdf_bytes = redacted.tobytes(garbage=4, deflate=True)
    rows, warnings = merge_pages(extracted)
    if unreadable:
        warnings.append(f"Pages without a readable bill reference: {', '.join(map(str, unreadable))}.")
    if not rows:
        raise ValueError("No bill rows could be extracted. Please use a clearer scan.")
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
        if not isinstance(row, dict):
            raise ValueError(f"Row {index}: provide a bill record.")
        ref = str(row["bill_ref"]).strip().upper() if row.get("bill_ref") is not None else None
        if ref is not None and not REF_PATTERN.fullmatch(ref):
            raise ValueError(f"Row {index}: invalid bill reference.")
        hrn = str(row["hrn"]).strip() if row.get("hrn") is not None else None
        if hrn is not None and not re.fullmatch(r"[A-Za-z0-9-][A-Za-z0-9 /-]{0,39}", hrn):
            raise ValueError(f"Row {index}: invalid HRN.")
        try:
            bill_date = datetime.strptime(row["bill_date"], "%Y-%m-%d") if row.get("bill_date") else None
            visit_date = datetime.strptime(row["visit_date"], "%Y-%m-%d") if row.get("visit_date") else None
            total = float(row["total"]) if row.get("total") is not None else None
            medishield = float(row["medishield"]) if row.get("medishield") is not None else None
            medisave = float(row["medisave"]) if row.get("medisave") is not None else None
            cash = float(row["cash"]) if row.get("cash") is not None else None
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Row {index}: check dates and amounts.") from exc
        amounts = [value for value in (total, medishield, medisave, cash) if value is not None]
        if any(value < 0 for value in amounts):
            raise ValueError(f"Row {index}: amounts must be zero or greater.")
        if not all(math.isfinite(value) for value in amounts):
            raise ValueError(f"Row {index}: amounts must be finite numbers.")
        sheet.append((ref, bill_date, hrn, visit_date,
                      total, medishield, medisave, cash))
        for col in ("B", "D"):
            sheet[f"{col}{index}"].number_format = "dd mmm yyyy"
        for col in ("E", "F", "G", "H"):
            sheet[f"{col}{index}"].number_format = '#,##0.00'
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:H{len(rows) + 1}"
    add_review_sheet(workbook, rows)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
