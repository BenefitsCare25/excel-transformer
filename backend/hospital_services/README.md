# Hospital bill extraction

The pipeline runs locally and retains evidence instead of repairing values from invoice-specific assumptions.

## Recognition and extraction

- `ocr.py` explicitly selects RapidOCR's PP-OCRv6 small detector and recognizer. Pages are rendered at twice their PDF dimensions, bounded at 5,000 pixels per side; the OCR preprocessing limit matches that bound to avoid silently reducing scan detail.
- `ocr_types.py` retains text, confidence, pixel coordinates, and crop retries. Confidence scores are model outputs, not calibrated correctness probabilities.
- `fields.py` associates values with labels using relative text geometry and competing column headings. Candidate selection accepts every format supported by its parser, including separated dates and HRNs with internal letters. Payment-table entries under Other Schemes are summed from the amount column and kept as table evidence.
- Field crops are deskewed and read again when recognition confidence is below 0.98, parsing fails, or payments do not reconcile. Identifiers are always retried because character substitutions can have high confidence.
- A recognition-only call changes RapidOCR's instance settings, so every subsequent page read explicitly re-enables detection, classification, and recognition.
- Identifier masking preserves token boundaries when matching formatted identifiers. NRIC-labelled fields mask both stacked and inline value regions independently of recognized digits, including merged label/value boxes, overlapping boxes, and skewed rows. Unsupported labels and values crossing a competing field boundary reject the page before a downloadable PDF is produced. Field extraction runs again on the masked image.

## Grouping and uncertainty

- `merging.py` groups consecutive invoice parts using physical adjacency, `Page x of y`, and compatible reference readings. Confusable characters help match continuation pages; they do not rewrite identifiers.
- When a page number is clipped, its readable part number can be checked against the total explicitly printed on another part. The missing printed count still produces a pagination review note, which is preserved in Excel.
- `evidence.py` selects only values observed by OCR. Independent page/location agreement ranks candidates. Conflicting readings at confidence 0.90 or higher remain provisional, even when one candidate is better supported.
- Missing or low-confidence values remain marked for review. Absent scheme labels mean zero only when the invoice's pagination is complete. A present scheme with an unreadable amount remains unknown.
- Payment reconciliation includes Other Schemes. It triggers recognition retries and review; it never supplies a missing decimal or invents a payment amount.
- Separate versions with the same exact bill reference retain the latest bill date and produce a warning. Conflicts within one paginated invoice retain their source evidence.

## Results and export

The frontend displays read-only values. Flagged cells expose alternative readings and source pages. The Excel export keeps its eight data columns; provisional cells receive comments and a separate Review notes sheet. Unknown values export as blanks rather than zero.

Completed jobs are persisted snapshots. Re-upload PDFs after a pipeline change to obtain new results; reopening an older saved run does not reprocess it. OCR alone cannot guarantee the correct character when source pixels are ambiguous; resolving those fields requires a clearer scan or an authoritative bill record.

## Document batches and recovery

- One batch request uploads all selected PDFs before OCR begins. Each batch accepts one to five PDFs, with the existing 25 MB per-file limit. The persistent queue accepts at most 20 unfinished documents and runs one OCR document at a time to bound model memory.
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

This verifies these supplied scans and the documented edge cases; it does not establish perfect recognition for every invoice format. Changes require deployment and fresh processing of existing saved runs.
