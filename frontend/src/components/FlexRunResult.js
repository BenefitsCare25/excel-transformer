import React, { useState } from 'react';

const STAT_TILES = [
  { key: 'grand_total', label: 'Grand Total (SGD)', money: true },
  { key: 'breakdown_rows', label: 'Breakdown Rows' },
  { key: 'payroll_rows', label: 'Payroll Rows' },
  { key: 'employees', label: 'Employees' },
  { key: 'excluded_final_pay', label: 'Excluded — Final Pay', money: true },
  { key: 'blocked_mismatch', label: 'Blocked — Mismatch', money: true, alert: true },
  { key: 'held_total', label: 'Held Out (SGD)', money: true, alert: true },
];

const money = (value) =>
  value == null
    ? '—'
    : Number(value).toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const FlexRunResult = ({ result, onDownload, onDownloadAll }) => {
  const hasErrors = result.errors > 0;
  const hasWarnings = result.warnings > 0;
  const [showLog, setShowLog] = useState(false);
  const [showValidation, setShowValidation] = useState(hasErrors);

  const status = hasErrors
    ? {
        label: `${result.errors} ERROR${result.errors > 1 ? 'S' : ''}`,
        pill: 'bg-red-100 text-red-800 border-red-300',
        panel: 'bg-red-50 border-red-200',
        text: 'text-red-800',
        note:
          'Review the Validation Exceptions Report before submitting. Rows that could not be processed safely ' +
          'were held out of the output files — resolve and re-run, or process them manually.',
      }
    : hasWarnings
    ? {
        label: `${result.warnings} WARNING${result.warnings > 1 ? 'S' : ''}`,
        pill: 'bg-amber-100 text-amber-800 border-amber-300',
        panel: 'bg-amber-50 border-amber-200',
        text: 'text-amber-800',
        note: 'Outputs are complete. Review the noted rows before submitting.',
      }
    : {
        label: 'ALL CHECKS PASSED',
        pill: 'bg-green-100 text-green-800 border-green-300',
        panel: 'bg-green-50 border-green-200',
        text: 'text-green-800',
        note: 'No exceptions found. Outputs are ready to download and submit.',
      };

  const tiles = STAT_TILES.filter((tile) => result.stats && result.stats[tile.key] != null);

  return (
    <>
      {/* Audit result */}
      <div className="card">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-800">Run Result</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {result.company_name} · payment month {result.pay_month} · generated in {result.elapsed_seconds}s
            </p>
          </div>
          <span className={`px-3 py-1 border rounded-md text-xs font-bold tracking-wider font-mono ${status.pill}`}>
            {status.label}
          </span>
        </div>

        <div className={`mb-4 px-4 py-3 border rounded-lg ${status.panel}`}>
          <p className={`text-sm ${status.text}`}>
            {status.note}
            {hasErrors && result.stats?.held_rows > 0 && (
              <>
                {' '}
                <span className="font-semibold">
                  {result.stats.held_rows} claim row{result.stats.held_rows > 1 ? 's' : ''} totalling{' '}
                  {money(result.stats.held_total)} held out.
                </span>
              </>
            )}
          </p>
        </div>

        {tiles.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {tiles.map((tile) => {
              const value = result.stats[tile.key];
              const highlight = tile.alert && Number(value) > 0;
              return (
                <div key={tile.key} className="p-3 bg-gray-50 rounded-lg text-center">
                  <p className={`text-xl font-bold ${highlight ? 'text-red-600' : 'text-gray-800'}`}>
                    {tile.money ? money(value) : value}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">{tile.label}</p>
                </div>
              );
            })}
          </div>
        )}

        {/* Downloads */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            Output Files
            <span className="ml-2 px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded-full">
              {result.outputs.length}
            </span>
          </h4>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={onDownloadAll}
              className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 flex items-center"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Download All (.zip)
            </button>
            {result.outputs.map((output) => (
              <button
                key={output.i}
                onClick={() => onDownload(output.i, output.name)}
                title={output.name}
                className="px-3 py-2 text-sm font-medium text-blue-600 border border-blue-600 rounded-md hover:bg-blue-50 max-w-xs truncate"
              >
                {output.name}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Files are kept for {result.retention_minutes} minutes, then deleted from the server.
          </p>
        </div>
      </div>

      {/* Validation detail */}
      {result.validation && result.validation.length > 0 && (
        <div className="card">
          <button
            onClick={() => setShowValidation(!showValidation)}
            className="w-full flex items-center justify-between text-left"
          >
            <h3 className="text-lg font-semibold text-gray-800">
              Validation Detail
              {hasErrors && (
                <span className="ml-2 px-2 py-1 text-xs bg-red-100 text-red-800 rounded-full">
                  {result.errors} error{result.errors > 1 ? 's' : ''}
                </span>
              )}
              {hasWarnings && (
                <span className="ml-2 px-2 py-1 text-xs bg-amber-100 text-amber-800 rounded-full">
                  {result.warnings} warning{result.warnings > 1 ? 's' : ''}
                </span>
              )}
            </h3>
            <svg
              className={`w-5 h-5 text-gray-500 transition-transform ${showValidation ? 'rotate-180' : ''}`}
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {showValidation && (
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Severity</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Check</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">EEID</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Detail</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {result.validation.map((row, index) => {
                    const isError = row.Sev === 'ERROR';
                    return (
                      <tr key={index} className={isError ? 'bg-red-50' : 'bg-amber-50'}>
                        <td className="px-3 py-2">
                          <span
                            className={`px-2 py-0.5 text-xs font-bold font-mono rounded ${
                              isError ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'
                            }`}
                          >
                            {row.Sev}
                          </span>
                        </td>
                        <td className="px-3 py-2 font-medium text-gray-800">{row.Check}</td>
                        <td className="px-3 py-2 font-mono text-xs text-gray-600">{row.EEID}</td>
                        <td className="px-3 py-2 text-gray-700">{row.Name}</td>
                        <td className="px-3 py-2 text-gray-600">{row.Detail}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Generation log */}
      {result.log && result.log.length > 0 && (
        <div className="card">
          <button onClick={() => setShowLog(!showLog)} className="w-full flex items-center justify-between text-left">
            <h3 className="text-lg font-semibold text-gray-800">Generation Log</h3>
            <svg
              className={`w-5 h-5 text-gray-500 transition-transform ${showLog ? 'rotate-180' : ''}`}
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {showLog && (
            <pre className="mt-4 p-4 bg-gray-900 text-green-400 text-xs font-mono rounded-md overflow-x-auto whitespace-pre-wrap">
              {result.log.join('\n')}
            </pre>
          )}
        </div>
      )}
    </>
  );
};

export default FlexRunResult;
