import React from 'react';

const columns = [
  ['bill_ref', 'Bill Ref No.'],
  ['bill_date', 'Bill Date'],
  ['hrn', 'HRN'],
  ['visit_date', 'Visit Date'],
  ['total', 'Total After Subsidy'],
  ['medishield', 'MediShield Life'],
  ['medisave', 'MediSave'],
  ['cash', 'Cash Payable'],
];

function displayValue(key, value) {
  if (value === null || value === undefined || value === '') return '—';
  if (key === 'bill_date' || key === 'visit_date') {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    return match ? `${match[3]}/${match[2]}/${match[1]}` : value;
  }
  if (['total', 'medishield', 'medisave', 'cash'].includes(key)) {
    const amount = Number(value);
    return Number.isFinite(amount) ? amount.toFixed(2) : value;
  }
  return value;
}

function FieldReview({ row, field }) {
  if (!row.review_fields?.includes(field)) return null;
  const candidates = row.field_candidates?.[field] || [];
  return (
    <details className="hospital-field-review">
      <summary>Review</summary>
      <div>
        {candidates.length ? (
          <ul>{candidates.map((candidate, index) => (
            <li key={index}>
              {displayValue(field, candidate.value)} — page{candidate.pages.length === 1 ? '' : 's'} {candidate.pages.join(', ')}
            </li>
          ))}</ul>
        ) : <p>No readable value found.</p>}
        <p>Check {row.source_file || 'source PDF'}, page{row.pages.length === 1 ? '' : 's'} {row.pages.join(', ')}. OCR readings are provisional.</p>
      </div>
    </details>
  );
}

export default function HospitalResults({ result, busy, downloading, download }) {
  return (
    <div className="hospital-panel hospital-results">
      <div className="hospital-results-head">
        <div>
          <h2>{result.rows.length} bill{result.rows.length === 1 ? '' : 's'} found{busy ? ' so far' : ''}</h2>
          <p>{result.redactions} identifier location{result.redactions === 1 ? '' : 's'} blanked. Results are read-only; review the values against the PDFs before exporting.</p>
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
          <thead><tr>{columns.map(([, label]) => <th key={label} scope="col">{label}</th>)}</tr></thead>
          <tbody>
            {result.rows.map((row, index) => (
              <tr key={`${row.bill_ref}-${index}`}>
                {columns.map(([key]) => (
                  <td key={key} className={key === 'cash' ? 'hospital-cash' : undefined}>
                    {displayValue(key, row[key])}
                    <FieldReview row={row} field={key} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="hospital-export">
        <button type="button" className="hospital-button primary" disabled={busy || downloading} onClick={() => download('excel')}>
          Download Excel
        </button>
      </div>
    </div>
  );
}
