# Hospital bill extraction

The pipeline runs locally and retains evidence instead of repairing values from invoice-specific assumptions.

## Recognition and extraction

- `ocr.py` explicitly selects RapidOCR's PP-OCRv6 small detector and recognizer. Pages are rendered at twice their PDF dimensions; oversized pages are rendered at the largest scale that keeps each side within 5,000 pixels (the OCR preprocessing bound) instead of being rejected.
- `ocr_types.py` retains text, confidence, pixel coordinates, and crop retries. Confidence scores are model outputs, not calibrated correctness probabilities.
- `fields.py` associates values with labels using relative text geometry and competing column headings. Candidate selection accepts every format supported by its parser, including separated dates and HRNs with internal letters. Payment-table entries under Other Schemes are summed from the amount column and kept as table evidence.
- Payment amounts come from the bill-level payment box. Inpatient bills repeat the payment labels in a per-institution `SUMMARY` table whose scheme rows print 0.00; that section (until the next `CHARGES`/`PAYMENT SUMMARY`/`PAYMENT OPTIONS` heading) is excluded. A currency sign read as `5` is never taken as an amount.
- `Page x of y` tolerates common misreads of "of" (`cf`, `(.`, `o'`). An HRN slot that holds only a printed dash is detected from its pixels, because OCR does not detect the dash itself.
- Identifiers are printed in capitals, so a lowercase `l` reading is treated as `I`.
- Field crops are deskewed and read again when recognition confidence is below 0.98, parsing fails, or payments do not reconcile. Identifiers are always retried because character substitutions can have high confidence.
- A recognition-only call changes RapidOCR's instance settings, so every subsequent page read explicitly re-enables detection, classification, and recognition.
- Identifier masking preserves token boundaries when matching formatted identifiers. NRIC-labelled fields mask both stacked and inline value regions independently of recognized digits, including merged label/value boxes, overlapping boxes, and skewed rows. Unsupported labels and values crossing a competing field boundary reject the page before a downloadable PDF is produced. Field extraction runs again on the masked image.

## Grouping and uncertainty

- `merging.py` groups consecutive invoice parts using physical adjacency, `Page x of y`, and compatible reference readings. Confusable characters help match continuation pages; they do not rewrite identifiers.
- When a page number is clipped, its readable part number can be checked against the total explicitly printed on another part. The missing printed count still produces a pagination review note, which is preserved in Excel.
- `evidence.py` selects only values observed by OCR. Independent page/location agreement ranks candidates. Conflicting readings at confidence 0.90 or higher remain provisional, even when one candidate is better supported.
- When readings of a bill reference or HRN differ only by confusable characters (1/I/L, 0/O, …), the reading that fits the issuer layout (SingHealth bill `H` + 9 digits + letter + 4 digits, NUHS bill 8 digits + letter, SingHealth HRN `H` + 11 digits + letter) is chosen. Otherwise conflicts stay provisional.
- Missing or low-confidence values remain marked for review. An absent scheme label means zero when the invoice's pagination is complete or when total = present schemes + cash payable holds exactly. HRN is `-` when the header page prints no HRN label or a dash in its slot; a real HRN printed elsewhere in the invoice takes precedence. A present scheme with an unreadable amount remains unknown.
- Payment reconciliation includes Other Schemes. When exactly one combination of credible (≥0.90) readings satisfies total = schemes + cash, those readings are selected; an exact reconciliation also clears low-confidence flags on single readings. It never supplies a missing decimal or invents a payment amount.
- Separate versions with the same exact bill reference (e.g. an interim and a finalised invoice) keep the latest bill date; superseded versions contribute no review notes, only a single document note. Missing invoice parts are named (`page 2 of 2 not found in the PDF`). Conflicts within one paginated invoice retain their source evidence.
- Row review notes travel with each row (`review_notes`); completed results keep only document-level notes in `document_warnings`, so rows dropped during cross-file consolidation leave no stale notes.

## Results and export

The frontend displays read-only values. Flagged cells expose alternative readings and source pages. The Excel export keeps its eight data columns; provisional cells receive comments and a separate Review notes sheet. Unknown values export as blanks rather than zero.

Completed jobs are persisted snapshots. Re-upload PDFs after a pipeline change to obtain new results; reopening an older saved run does not reprocess it. OCR alone cannot guarantee the correct character when source pixels are ambiguous; resolving those fields requires a clearer scan or an authoritative bill record.

## Document batches and recovery

- One batch request uploads all selected PDFs before OCR begins. There is no limit on the number of PDFs, file size, or page count; uploads are streamed to disk and the redacted PDF is written directly to disk. The persistent queue runs one OCR document at a time (about 15–20 s per page) to bound model memory.
- `queue_store.py` publishes a batch manifest only after every input and queued status is written. File locks serialize acceptance, deletion, and OCR across serving processes. Atomic result writes preserve page progress and completed records.
- `jobs.py` drains accepted work independently of browser polling. Gunicorn's worker initialization hook resumes queued or interrupted documents after a worker restart; requests also start the worker when using another WSGI server. A failed document does not block later documents.
- Raw queued PDFs live inside the private hospital output directory and are removed after their terminal result is saved. Startup also removes unpublished inputs left by an interrupted submission. Saved results and redacted PDFs remain until the user deletes them.
- The browser saves a batch ID before uploading and all returned run IDs after acceptance. Reopening in the same browser restores progress and combines the batch's completed results; the batch ID recovers an accepted upload even if its response was lost. Retrying that ID returns existing jobs instead of duplicating them.
- Keep the page open until the upload confirmation appears. Files that have not reached the server cannot be processed after closing the browser. Clearing browser storage removes the local identifiers used to restore results.

## Verification: 26 September 2026

- Both supplied redacted PDFs were evaluated: 151 scanned pages yielded 74 invoices. All date and payment columns matched the previously reviewed workbook. The ambiguous bill reference was matched for comparison using its recorded alternatives; its displayed value remains provisional.
- Six identifier fields remain ambiguous: one bill reference and five HRNs. A separate pagination warning is retained because the source scan clips the printed page count.
- The redaction, recognition, grouping, and export flow was exercised on six two-page invoices covering the original failures, a malformed amount token, overlapping date boxes, and the clipped page number.
- The frontend build and lint checks passed. A local browser check at desktop and mobile widths found no editable result cells, working review disclosures, and no runtime errors. The browser used supplied OCR fixtures and the real Flask export endpoint in its local test client.
- The complete 74-row export returned HTTP 200, with seven review-note rows and six provisional-cell comments. Unknown amounts were separately verified to export as flagged blanks.
- Review regression checks verified garbled and undetected inline NRIC values in the downloadable PDF, fail-closed handling of unsupported layouts, five supported date styles, and separately boxed alphanumeric HRNs. The existing 29 backend tests passed.
- A real browser uploaded three synthetic scanned PDFs, closed while documents remained queued, and reopened after all three finished. All three read-only rows, redacted PDF downloads, and the combined Excel export were restored without runtime errors. Lost-acknowledgement recovery and idempotent batch submission were verified separately.
- A worker was terminated during processing; another process resumed the interrupted document and drained the queue. A failing document did not block subsequent work. Verification also covered atomic acceptance failure, invalid batch rejection, the queue capacity, deletion guards, and removal of raw queued inputs.

### Re-verification after the NTFGH/NUHS fixes (26 September 2026)

- NTFGH/NUHS PDF (11 pages, previously 16 review notes): 5 bills, every value checked against the scan, no field flagged. The remaining notes are true document facts: two invoices whose page 2 is absent from the PDF, and an interim version superseded by the finalised bill.
- NCSS parts 1 and 2 (151 pages, including the 26.5 MB file previously rejected by the size limit): 74/74 bills. The only review note is the known clipped page count on part 2 pages 97–98 (`Page 2 of` with no total); uncertain page-number readings always produce a note and prevent the invoice from being treated as complete. 71 rows match the reviewed workbook exactly; the other 3 differ only in an HRN's final character, where the reviewed workbook has `1` and the scan (checked visually) prints `I`.
- A 7-document batch including a 60 MB PDF was accepted, streamed to disk, and processed; the NTFGH PDF ran end to end through upload, queue, OCR, redacted PDF download, and Excel export.

This verifies these supplied scans and the documented edge cases; it does not establish perfect recognition for every invoice format. Changes require deployment and fresh processing of existing saved runs.
