# Hospital bill extraction

The pipeline runs locally and retains evidence instead of repairing values from invoice-specific assumptions.

## Recognition and extraction

- `ocr.py` explicitly selects RapidOCR's PP-OCRv6 small detector and recognizer. Pages are rendered at twice their PDF dimensions, bounded at 5,000 pixels per side; the OCR preprocessing limit matches that bound to avoid silently reducing scan detail.
- `ocr_types.py` retains text, confidence, pixel coordinates, and crop retries. Confidence scores are model outputs, not calibrated correctness probabilities.
- `fields.py` associates values with labels using relative text geometry and competing column headings. Dates tolerate omitted spaces. Payment-table entries under Other Schemes are summed from the amount column and kept as table evidence.
- Field crops are deskewed and read again when recognition confidence is below 0.98, parsing fails, or payments do not reconcile. Identifiers are always retried because character substitutions can have high confidence.
- A recognition-only call changes RapidOCR's instance settings, so every subsequent page read explicitly re-enables detection, classification, and recognition.
- Identifier masking preserves token boundaries when matching formatted identifiers and masks the value region of NRIC-labelled fields even when recognition fails or the input was already redacted. Field extraction runs again on the masked image.

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

## Verification: 26 September 2026

- Both supplied redacted PDFs were evaluated: 151 scanned pages yielded 74 invoices. All date and payment columns matched the previously reviewed workbook. The ambiguous bill reference was matched for comparison using its recorded alternatives; its displayed value remains provisional.
- Six identifier fields remain ambiguous: one bill reference and five HRNs. A separate pagination warning is retained because the source scan clips the printed page count.
- The redaction, recognition, grouping, and export flow was exercised on six two-page invoices covering the original failures, a malformed amount token, overlapping date boxes, and the clipped page number.
- The frontend build and lint checks passed. A local browser check at desktop and mobile widths found no editable result cells, working review disclosures, and no runtime errors. The browser used supplied OCR fixtures and the real Flask export endpoint in its local test client.
- The complete 74-row export returned HTTP 200, with seven review-note rows and six provisional-cell comments. Unknown amounts were separately verified to export as flagged blanks.

This verifies these supplied scans and the documented edge cases; it does not establish perfect recognition for every invoice format. Changes require deployment and fresh processing of existing saved runs.
