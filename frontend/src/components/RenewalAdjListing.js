import React, { useCallback, useState } from 'react';
import apiService from '../services/api';
import RenewalFileUpload from './RenewalFileUpload';
import RenewalAdjGuide from './RenewalAdjGuide';
import RenewalAdjResult from './RenewalAdjResult';
import './Renewal.css';

const LIFE_PRODUCTS = ['GTL', 'GDD', 'GPA', 'GDI'];
const DEFAULT_DIVISOR = '2';
const emptyLimits = () => Object.fromEntries(LIFE_PRODUCTS.map((code) => [code, { fcl: '', age: '' }]));

/** '800,000' / '$800,000' -> 800000; blank -> null; anything else -> NaN. */
const parseNumber = (raw) => {
  const text = String(raw).replace(/[\s,$]/g, '');
  return text === '' ? null : Number(text);
};

const limitsPayload = (limits) => Object.fromEntries(
  Object.entries(limits)
    .map(([code, { fcl, age }]) => [code, Object.fromEntries(
      [['fcl', parseNumber(fcl)], ['age', parseNumber(age)]].filter(([, value]) => value !== null),
    )])
    .filter(([, entry]) => Object.keys(entry).length > 0),
);

const validationError = (file1, file2, divisor, limits) => {
  if (!file1 || !file2) return 'Upload both renewal listings.';
  const divisorValue = parseNumber(divisor);
  if (!Number.isInteger(divisorValue) || divisorValue < 1 || divisorValue > 12) {
    return 'Pro-rata divisor must be a whole number from 1 to 12.';
  }
  for (const [code, { fcl, age }] of Object.entries(limits)) {
    const fclValue = parseNumber(fcl);
    const ageValue = parseNumber(age);
    if (fclValue !== null && !(fclValue >= 0)) return `${code} FCL must be a number of 0 or more, e.g. 800,000.`;
    if (ageValue !== null && !(ageValue >= 1 && ageValue <= 120)) return `${code} age limit must be a number from 1 to 120.`;
  }
  return null;
};

const LimitsTable = ({ limits, onChange, disabled }) => (
  <fieldset>
    <legend className="renewal-label">FCL and age limits (life products)</legend>
    <p className="text-xs renewal-muted mb-2">
      Leave blank to use the limit printed in a listing header, e.g. &ldquo;NEL: $800,000 or age 71&rdquo;.
      Flat listings have no header limits, so enter them here.
    </p>
    <table className="renewal-table">
      <thead>
        <tr>
          <th scope="col">Product</th>
          <th scope="col">FCL (S$)</th>
          <th scope="col">Age limit</th>
        </tr>
      </thead>
      <tbody>
        {LIFE_PRODUCTS.map((code) => (
          <tr key={code}>
            <th scope="row">{code}</th>
            {['fcl', 'age'].map((field) => (
              <td key={field}>
                <input
                  type="text"
                  inputMode="decimal"
                  className="renewal-input"
                  placeholder="From header"
                  aria-label={`${code} ${field === 'fcl' ? 'FCL' : 'age limit'}`}
                  value={limits[code][field]}
                  disabled={disabled}
                  onChange={(e) => onChange(code, field, e.target.value)}
                />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </fieldset>
);

const AdjIntro = () => {
  const [showGuide, setShowGuide] = useState(false);
  return (
    <>
      <div>
        <h2 className="text-xl font-semibold renewal-text mb-1">Combined Adj Listing</h2>
        <p className="text-sm renewal-muted">
          Puts both policy years in one Adj sheet, both priced at last year&apos;s premium so continuing staff
          net to zero, with a pro-rated adjustment on each Headcount row. Also builds an invoice summary per
          entity and per employee.
        </p>
      </div>
      <div>
        <button type="button" className="renewal-disclosure" aria-expanded={showGuide} onClick={() => setShowGuide(!showGuide)}>
          <span>Input &amp; output template</span>
          <span aria-hidden="true">{showGuide ? '−' : '+'}</span>
        </button>
        {showGuide && <div className="mt-3"><RenewalAdjGuide /></div>}
      </div>
    </>
  );
};

const AdjSettings = ({ clientLabel, setClientLabel, proRataDivisor, setProRataDivisor, disabled }) => (
  <div className="space-y-4">
    <div>
      <label className="renewal-label" htmlFor="adj-client">Client label (optional)</label>
      <input id="adj-client" type="text" maxLength={40} className="renewal-input" placeholder="e.g. MCST 1216"
        value={clientLabel} disabled={disabled} onChange={(e) => setClientLabel(e.target.value)} />
      <p className="text-xs renewal-muted mt-1">Names the Adj sheet and the file. Defaults to the main entity.</p>
    </div>
    <div>
      <label className="renewal-label" htmlFor="adj-divisor">Pro-rata divisor</label>
      <input id="adj-divisor" type="text" inputMode="numeric" className="renewal-input w-32"
        value={proRataDivisor} disabled={disabled} onChange={(e) => setProRataDivisor(e.target.value)} />
      <p className="text-xs renewal-muted mt-1">2 = changes assumed mid-year. Each row adjusts by (current − previous) / divisor.</p>
    </div>
  </div>
);

const RenewalAdjListing = () => {
  const [files, setFiles] = useState({ first: null, second: null });
  const [clientLabel, setClientLabel] = useState('');
  const [proRataDivisor, setProRataDivisor] = useState(DEFAULT_DIVISOR);
  const [limits, setLimits] = useState(emptyLimits);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const selectFile = useCallback((slot, accepted) => {
    if (accepted.length > 0) {
      setFiles((prev) => ({ ...prev, [slot]: accepted[0] }));
      setError(null);
      setResult(null);
    }
  }, []);
  const handleFirstDrop = useCallback((accepted) => selectFile('first', accepted), [selectFile]);
  const handleSecondDrop = useCallback((accepted) => selectFile('second', accepted), [selectFile]);
  const updateLimit = (code, field, value) => setLimits((prev) => ({ ...prev, [code]: { ...prev[code], [field]: value } }));

  const handleGenerate = async () => {
    const problem = validationError(files.first, files.second, proRataDivisor, limits);
    if (problem) {
      setError(problem);
      return;
    }
    setIsProcessing(true);
    setError(null);
    setResult(null);
    try {
      const response = await apiService.processRenewalAdjListing(files.first, files.second, {
        proRataDivisor: parseNumber(proRataDivisor), clientLabel: clientLabel.trim(), limits: limitsPayload(limits),
      });
      if (response.success) setResult(response.data);
      else setError(response.details ? `${response.error}: ${response.details}` : response.error);
    } catch (err) {
      setError(err.message || 'The Adj listing could not be generated.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = async () => {
    const download = await apiService.downloadRenewalReport(result.download_filename, result.display_filename);
    if (!download.success) setError(`Download failed: ${download.error}`);
  };

  const handleReset = () => {
    setFiles({ first: null, second: null });
    setClientLabel('');
    setProRataDivisor(DEFAULT_DIVISOR);
    setLimits(emptyLimits());
    setResult(null);
    setError(null);
  };

  return (
    <div className="space-y-6">
      <div className="card space-y-6">
        <AdjIntro />
        <div className="grid gap-6 md:grid-cols-2">
          <RenewalFileUpload label="Renewal listing 1" description='Sheet "Employee Listing YYYY", e.g. Employee Listing 2024'
            file={files.first} onDrop={handleFirstDrop} isProcessing={isProcessing} />
          <RenewalFileUpload label="Renewal listing 2" description='Sheet "Employee Listing YYYY", e.g. Employee Listing 2025'
            file={files.second} onDrop={handleSecondDrop} isProcessing={isProcessing} />
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          <AdjSettings clientLabel={clientLabel} setClientLabel={setClientLabel} proRataDivisor={proRataDivisor}
            setProRataDivisor={setProRataDivisor} disabled={isProcessing} />
          <LimitsTable limits={limits} onChange={updateLimit} disabled={isProcessing} />
        </div>
        {error && <div className="renewal-alert error" role="alert">{error}</div>}
        {isProcessing && <div className="renewal-alert info" role="status">Building the Adj listing…</div>}
        <div className="flex justify-end gap-3">
          <button type="button" className="queue-button neutral" onClick={handleReset} disabled={isProcessing}>Reset</button>
          <button type="button" className="queue-button primary" onClick={handleGenerate}
            disabled={!files.first || !files.second || isProcessing}>
            {isProcessing ? 'Generating…' : 'Generate Adj Listing'}
          </button>
        </div>
      </div>
      {result && <RenewalAdjResult result={result} onDownload={handleDownload} />}
    </div>
  );
};

export default RenewalAdjListing;
