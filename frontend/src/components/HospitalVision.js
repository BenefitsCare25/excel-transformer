import React, { useRef, useState } from 'react';
import apiService from '../services/api';
import './HospitalVision.css';

const columns = [
  ['bill_ref', 'Bill Ref No.', 'text'],
  ['bill_date', 'Bill Date', 'date'],
  ['hrn', 'HRN', 'text'],
  ['visit_date', 'Visit Date', 'date'],
  ['total', 'Total After Subsidy', 'number'],
  ['medishield', 'MediShield Life', 'number'],
  ['medisave', 'MediSave', 'number'],
];

function cashPayable(row) {
  if (row.total === '' || row.total == null) return '—';
  return (Number(row.total) - Number(row.medishield || 0) - Number(row.medisave || 0)).toFixed(2);
}

function latestBillRows(rows) {
  const byReference = new Map();
  rows.forEach((row) => {
    const previous = byReference.get(row.bill_ref);
    if (!previous || row.bill_date > previous.bill_date) byReference.set(row.bill_ref, row);
  });
  return [...byReference.values()].sort((a, b) =>
    a.bill_date.localeCompare(b.bill_date) || a.bill_ref.localeCompare(b.bill_ref));
}

function combineResults(completed) {
  const allRows = completed.flatMap((item) => item.rows);
  const rows = latestBillRows(allRows);
  const warnings = completed.flatMap((item) => item.warnings);
  if (rows.length < allRows.length) {
    warnings.push('Repeated bill references were consolidated; the latest bill date was kept.');
  }
  return {
    rows,
    warnings,
    redactions: completed.reduce((sum, item) => sum + item.redactions, 0),
    redacted: completed.map(({ run_id, filename }) => ({ run_id, filename })),
  };
}

export default function HospitalVision() {
  const inputRef = useRef(null);
  const [files, setFiles] = useState([]);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(null);

  const selectFiles = (candidates) => {
    if (busy) return;
    setResult(null);
    setError('');
    const chosen = Array.from(candidates || []);
    if (chosen.length > 5 || chosen.some((item) =>
      !item.name.toLowerCase().endsWith('.pdf') || item.size > 25 * 1024 * 1024)) {
      setFiles([]);
      setError('Choose up to five PDFs, each smaller than 25 MB.');
      return;
    }
    setFiles(chosen);
  };

  const process = async () => {
    if (!files.length || busy) return;
    setBusy(true);
    setError('');
    setProgress(null);
    setResult(null);
    const completed = [];
    const failures = [];
    for (const file of files) {
      setProgress({ filename: file.name, completed_pages: 0, total_pages: 0 });
      const started = await apiService.processHospitalBill(file);
      if (!started.success) {
        failures.push(`${file.name}: ${started.error}`);
        continue;
      }
      const response = await apiService.waitForHospitalBill(started.data.run_id,
        (status) => setProgress({ filename: file.name, ...status }));
      if (response.success) {
        completed.push({ ...response.data, filename: file.name });
        setResult(combineResults(completed));
      } else failures.push(`${file.name}: ${response.error}`);
    }
    if (failures.length) setError(failures.join(' '));
    setBusy(false);
    setProgress(null);
  };

  const updateRow = (index, key, value) => {
    setResult((current) => ({
      ...current,
      rows: current.rows.map((row, rowIndex) => rowIndex === index ? { ...row, [key]: value } : row),
    }));
  };

  const download = async (kind, runId) => {
    if (!result || downloading) return;
    setDownloading(true);
    setError('');
    const response = kind === 'pdf'
      ? await apiService.downloadHospitalPdf(runId, result.redacted.find((item) => item.run_id === runId)?.filename)
      : await apiService.exportHospitalWorkbook(result.rows);
    if (!response.success) setError(response.error);
    setDownloading(false);
  };

  return (
    <section className="hospital-vision" aria-labelledby="hospital-title">
      <div className="hospital-intro">
        <span className="hospital-eyebrow">OCR / VISION</span>
        <h2 id="hospital-title">Hospital bills to Excel</h2>
        <p>Upload scanned bills. NRIC and FIN-like identifiers are blanked before bill values are read into the template columns.</p>
      </div>

      <div className="hospital-panel">
        <div className="hospital-steps" aria-label="Processing steps">
          <span>1. Upload PDF</span><span>2. Redact identifiers</span><span>3. Review rows</span><span>4. Export</span>
        </div>
        <div
          className={`hospital-drop ${dragging ? 'is-dragging' : ''}`}
          onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            selectFiles(event.dataTransfer.files);
          }}
        >
          <div className="hospital-file-icon" aria-hidden="true">PDF</div>
          <strong>{files.length ? `${files.length} PDF${files.length === 1 ? '' : 's'} selected` : 'Drop hospital bills here'}</strong>
          <span>{files.length ? files.map((item) => item.name).join(' · ') : 'Up to 5 PDFs · 25 MB and 100 pages per file'}</span>
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf,.pdf"
            multiple
            disabled={busy}
            className="hospital-file-input"
            onChange={(event) => {
              selectFiles(event.target.files);
              event.target.value = '';
            }}
            aria-label="Choose hospital bill PDFs"
          />
          <button type="button" className="hospital-button secondary" disabled={busy} onClick={() => inputRef.current?.click()}>
            Choose PDFs
          </button>
        </div>
        <div className="hospital-actions">
          <p>Raw pages are processed on this server without a third-party OCR provider. Redacted PDFs are scheduled for cleanup after 15 minutes.</p>
          <button type="button" className="hospital-button primary" disabled={!files.length || busy} onClick={process}>
            {busy ? 'Redacting and reading…' : 'Process bills'}
          </button>
        </div>
      </div>

      {error && <div className="hospital-alert error" role="alert">{error}</div>}
      {busy && progress && (
        <p className="hospital-status" role="status">
          Processing {progress.filename}: {progress.total_pages
            ? `${progress.completed_pages} of ${progress.total_pages} pages complete`
            : 'starting OCR'}. This may take several minutes. Keep this tab open.
        </p>
      )}

      {result && (
        <div className="hospital-panel hospital-results">
          <div className="hospital-results-head">
            <div>
              <span className="hospital-eyebrow">{busy ? 'PROCESSING / REVIEW' : 'READY FOR REVIEW'}</span>
              <h3>{result.rows.length} bill{result.rows.length === 1 ? '' : 's'} found{busy ? ' so far' : ''}</h3>
              <p>{result.redactions} identifier location{result.redactions === 1 ? '' : 's'} blanked. Check all values against the redacted PDF before exporting.</p>
            </div>
            <div className="hospital-pdf-downloads">
              {result.redacted.map(({ run_id, filename }) => (
                <button key={run_id} type="button" className="hospital-button secondary" disabled={downloading} onClick={() => download('pdf', run_id)}>
                  Redacted PDF · {filename}
                </button>
              ))}
            </div>
          </div>
          {result.warnings.length > 0 && (
            <div className="hospital-alert" role="status">
              <strong>Review notes</strong>
              <ul>{result.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>
            </div>
          )}
          <div className="hospital-table-wrap">
            <table className="hospital-table">
              <thead><tr>{columns.map(([, label]) => <th key={label} scope="col">{label}</th>)}<th scope="col">Cash Payable</th></tr></thead>
              <tbody>
                {result.rows.map((row, index) => (
                  <tr key={`${row.bill_ref}-${index}`}>
                    {columns.map(([key, label, type]) => (
                      <td key={key}>
                        <input
                          aria-label={`${label}, row ${index + 1}`}
                          type={type}
                          min={type === 'number' ? '0' : undefined}
                          step={type === 'number' ? '0.01' : undefined}
                          value={row[key] ?? ''}
                          onChange={(event) => updateRow(index, key, event.target.value)}
                        />
                      </td>
                    ))}
                    <td className="hospital-cash">{cashPayable(row)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="hospital-export">
            <span>Excel follows the eight columns in your template, with a cash payable formula per row.</span>
            <button type="button" className="hospital-button primary" disabled={busy || downloading} onClick={() => download('excel')}>
              Download Excel
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
