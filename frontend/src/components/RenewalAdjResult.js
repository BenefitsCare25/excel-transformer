import React, { useState } from 'react';
import './Renewal.css';

const money = new Intl.NumberFormat('en-SG', { style: 'currency', currency: 'SGD' });
const whole = new Intl.NumberFormat('en-SG', { maximumFractionDigits: 0 });
const signClass = (n) => (n > 0 ? 'renewal-pos' : n < 0 ? 'renewal-neg' : '');

const Stat = ({ value, label }) => (
  <div className="renewal-stat">
    <strong>{value}</strong>
    <span>{label}</span>
  </div>
);

const ListingTile = ({ title, info }) => (
  <div className="renewal-panel p-3">
    <p className="text-xs renewal-muted">{title}</p>
    <p className="text-sm font-semibold renewal-text">{info.label}</p>
    <p className="text-xs renewal-muted break-all">{info.filename}</p>
    <p className="text-xs renewal-muted">
      Renewal date: {info.renewal_date || 'not found'} · {info.rows} employees
    </p>
  </div>
);

const ProductTable = ({ result }) => {
  const total = result.products.reduce((sum, p) => sum + p.adjustment_with_gst, 0);
  return (
    <div className="overflow-x-auto">
      <table className="renewal-table">
        <thead>
          <tr>
            <th scope="col">Product</th>
            <th scope="col" className="num">{result.previous.label} Headcount</th>
            <th scope="col" className="num">{result.current.label} Headcount</th>
            <th scope="col" className="num">Named (prev / curr)</th>
            <th scope="col" className="num">{result.previous.label} premium</th>
            <th scope="col" className="num">{result.current.label} premium</th>
            <th scope="col" className="num">Adjustment payable</th>
          </tr>
        </thead>
        <tbody>
          {result.products.map((p) => (
            <tr key={p.name}>
              <th scope="row">{p.name} <span className="renewal-muted font-normal">({p.type})</span></th>
              <td className="num">{p.prev_hc}</td>
              <td className="num">{p.curr_hc}</td>
              <td className="num">{p.prev_named} / {p.curr_named}</td>
              <td className="num">{money.format(p.prev_premium)}</td>
              <td className="num">{money.format(p.curr_premium)}</td>
              <td className={`num font-semibold ${signClass(p.adjustment_with_gst)}`}>{money.format(p.adjustment_with_gst)}</td>
            </tr>
          ))}
          <tr>
            <th scope="row" colSpan={6}>Total</th>
            <td className={`num font-semibold ${signClass(total)}`}>{money.format(total)}</td>
          </tr>
        </tbody>
      </table>
      <p className="text-xs renewal-muted mt-2">
        Premium columns sum Headcount rows only. Adjustment = (current − previous) / 365 × {result.pro_rata_days} days;
        medical products include 9% GST.
      </p>
    </div>
  );
};

const BasisReview = ({ rows }) => {
  const [open, setOpen] = useState(false);
  if (!rows.length) return null;
  return (
    <div className="card">
      <button type="button" className="renewal-disclosure" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span>Named and over-limit employees ({rows.length})</span>
        <span aria-hidden="true">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <div className="overflow-x-auto mt-3">
          <table className="renewal-table">
            <thead>
              <tr>
                {['Policy year', 'Employee', 'EMP ID', 'Product', 'Age', 'Sum insured', 'Basis', 'Reason'].map((h) => (
                  <th key={h} scope="col">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={`${r.period}-${r.emp_id}-${r.product}-${i}`}>
                  <td>{r.period}</td>
                  <td>{r.name}</td>
                  <td>{r.emp_id}</td>
                  <td>{r.product}</td>
                  <td className="num">{r.age ?? '-'}</td>
                  <td className="num">{r.sum_insured != null ? whole.format(r.sum_insured) : '-'}</td>
                  <td><span className={`renewal-badge ${r.basis === 'Named' ? 'named' : ''}`}>{r.basis}</span></td>
                  <td>{r.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const RenewalAdjResult = ({ result, onDownload }) => {
  const emp = result.employee_summary;
  const entityPairs = Object.entries(result.entity_mapping || {});
  return (
    <>
      <div className="card space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold renewal-text">Adj listing ready</h3>
            <p className="text-xs renewal-muted">{result.display_filename}</p>
          </div>
          <button type="button" onClick={onDownload} className="queue-button success">Download Excel</button>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <ListingTile title="Previous year" info={result.previous} />
          <ListingTile title="Current year" info={result.current} />
        </div>
        <div className="grid gap-3 grid-cols-2 md:grid-cols-5">
          <Stat value={emp.prev_total} label="Previous year" />
          <Stat value={emp.curr_total} label="Current year" />
          <Stat value={emp.common} label="Continuing" />
          <Stat value={emp.added} label="Joiners" />
          <Stat value={emp.removed} label="Leavers" />
        </div>
        {entityPairs.map(([from, to]) => (
          <p key={from} className="renewal-alert info">
            Current-year entity &ldquo;{from}&rdquo; is shown as &ldquo;{to}&rdquo; so both years group together.
          </p>
        ))}
      </div>

      {result.warnings.length > 0 && (
        <div className="renewal-alert warning" role="status">
          <p className="font-semibold mb-1">Check before sending ({result.warnings.length})</p>
          <ul className="list-disc ml-5 space-y-1">
            {result.warnings.map((w) => <li key={w}>{w}</li>)}
          </ul>
        </div>
      )}

      <div className="card">
        <h3 className="text-lg font-semibold renewal-text mb-3">Adjustment by product</h3>
        <ProductTable result={result} />
      </div>

      <BasisReview rows={result.basis_review} />
    </>
  );
};

export default RenewalAdjResult;
