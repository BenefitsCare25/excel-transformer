import React from 'react';

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

export default function HospitalResults({ result, busy, downloading, updateRow, download }) {
  return (
    <div className="hospital-panel hospital-results">
      <div className="hospital-results-head">
        <div>
          <h2>{result.rows.length} bill{result.rows.length === 1 ? '' : 's'} found{busy ? ' so far' : ''}</h2>
          <p>{result.redactions} identifier location{result.redactions === 1 ? '' : 's'} blanked. Review the values before exporting.</p>
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
        <button type="button" className="hospital-button primary" disabled={busy || downloading} onClick={() => download('excel')}>
          Download Excel
        </button>
      </div>
    </div>
  );
}
