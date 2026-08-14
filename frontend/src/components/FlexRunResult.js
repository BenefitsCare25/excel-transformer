import React, { useState } from 'react';

// Neutral headline counts. The include/exclude money split lives in SubmissionBreakdown.
const STAT_TILES = [
  { key: 'grand_total', label: 'Breakdown Total (SGD)', money: true },
  { key: 'payroll_total', label: 'Payroll Total (SGD)', money: true },
  { key: 'breakdown_rows', label: 'Breakdown Rows' },
  { key: 'payroll_rows', label: 'Payroll Rows' },
  { key: 'employees', label: 'Employees' },
];

const money = (value) =>
  value == null
    ? '—'
    : Number(value).toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// How each disposition is grouped and styled in the action breakdown.
const GROUPS = [
  {
    key: 'blocked',
    title: 'Decisions needed — held back from the payroll file',
    intro: 'These claims are in the Summary/Breakdown report but were NOT written to the IT15. Decide each before submitting.',
    box: 'border-red-200 bg-red-50',
    amount: 'text-red-700',
  },
  {
    key: 'held',
    title: 'Held out of all files — fix the source and re-run',
    intro: 'These claims could not be placed anywhere. Correct the source data and generate again.',
    box: 'border-red-200 bg-red-50',
    amount: 'text-red-700',
  },
  {
    key: 'excluded',
    title: 'Auto-excluded from payroll — informational',
    intro: 'Matched to a leaver final-pay email and correctly kept off the payroll. No action needed to submit.',
    box: 'border-gray-200 bg-gray-50',
    amount: 'text-gray-700',
  },
  {
    key: 'warn',
    title: 'Warnings — included in the payroll, review before submitting',
    intro: 'These rows are on the payroll file; the flags are advisory.',
    box: 'border-amber-200 bg-amber-50',
    amount: 'text-amber-700',
  },
];

// Action pill colour by recommendation.
const actionPill = (action) => {
  if (action === 'Exclude from payroll') return 'bg-slate-200 text-slate-700';
  if (action === 'Split / include') return 'bg-amber-100 text-amber-800';
  if (action === 'Fix & re-run') return 'bg-red-100 text-red-800';
  if (action === 'Decide') return 'bg-amber-100 text-amber-800';
  return 'bg-gray-100 text-gray-600';
};

const groupTotal = (rows) =>
  rows.reduce((sum, r) => sum + (r.amount != null ? Number(r.amount) : 0), 0);

const SubmissionBreakdown = ({ stats }) => {
  const grand = Number(stats.grand_total) || 0;
  const payroll = stats.payroll_total != null
    ? Number(stats.payroll_total)
    : grand - (Number(stats.excluded_final_pay) || 0) - (Number(stats.blocked_mismatch) || 0);
  const excluded = Number(stats.excluded_final_pay) || 0;
  const blocked = Number(stats.blocked_mismatch) || 0;
  const held = Number(stats.held_total) || 0;

  const Row = ({ label, value, sub, tone }) => (
    <div className={`flex items-center justify-between py-1.5 ${sub ? 'pl-4' : ''}`}>
      <span className={`text-sm ${sub ? 'text-gray-500' : 'text-gray-700 font-medium'}`}>{label}</span>
      <span className={`text-sm font-mono ${tone || (sub ? 'text-gray-500' : 'text-gray-800')}`}>{value}</span>
    </div>
  );

  return (
    <div className="mb-4 p-4 border border-gray-200 rounded-lg bg-white">
      <h4 className="text-sm font-semibold text-gray-800 mb-2">What gets submitted</h4>
      <div className="divide-y divide-gray-100">
        <Row label="Summary / Breakdown report (all approved claims)" value={money(grand)} />
        <div className="py-1">
          <Row label="Removed from the payroll file:" value="" />
          <Row sub label="Excluded — final pay (auto)" value={`− ${money(excluded)}`} tone="text-gray-500" />
          <Row sub label="Blocked — pending your decision" value={`− ${money(blocked)}`} tone={blocked > 0 ? 'text-red-600' : 'text-gray-500'} />
        </div>
        <div className="flex items-center justify-between py-2">
          <span className="text-sm font-semibold text-gray-900">IT15 Payroll file — to submit</span>
          <span className="text-base font-bold font-mono text-gray-900">{money(payroll)}</span>
        </div>
        {held > 0 && (
          <Row label="Held out of all files — fix & re-run" value={money(held)} tone="text-red-600" />
        )}
      </div>
    </div>
  );
};

const ExceptionCard = ({ row, group }) => (
  <div className={`p-3 rounded-lg border ${group.box}`}>
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <p className="text-sm font-semibold text-gray-800 truncate">
          {row.Name || '—'}
          {row.EEID && <span className="ml-1.5 font-mono text-xs text-gray-400">#{row.EEID}</span>}
        </p>
        <p className="text-xs text-gray-500 mt-0.5">{row.Check}</p>
      </div>
      <div className="text-right flex-shrink-0">
        {row.amount != null && (
          <p className={`text-sm font-bold font-mono ${group.amount}`}>{money(row.amount)}</p>
        )}
        {row.action && (
          <span className={`mt-1 inline-block px-2 py-0.5 text-xs font-semibold rounded ${actionPill(row.action)}`}>
            {row.action}
          </span>
        )}
      </div>
    </div>
    <p className="mt-2 text-xs text-gray-600 leading-relaxed">{row.guidance || row.Detail}</p>
  </div>
);

// Fallback for older runs whose validation rows carry no disposition/guidance fields.
const LegacyTable = ({ rows }) => (
  <div className="overflow-x-auto">
    <table className="min-w-full divide-y divide-gray-200 text-sm">
      <thead className="bg-gray-50">
        <tr>
          {['Severity', 'Check', 'EEID', 'Name', 'Detail'].map((h) => (
            <th key={h} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>
          ))}
        </tr>
      </thead>
      <tbody className="bg-white divide-y divide-gray-200">
        {rows.map((row, index) => {
          const isError = row.Sev === 'ERROR';
          return (
            <tr key={index} className={isError ? 'bg-red-50' : 'bg-amber-50'}>
              <td className="px-3 py-2">
                <span className={`px-2 py-0.5 text-xs font-bold font-mono rounded ${
                  isError ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'
                }`}>{row.Sev}</span>
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
);

const FlexRunResult = ({ result, onDownload, onDownloadAll }) => {
  const hasErrors = result.errors > 0;
  const hasWarnings = result.warnings > 0;
  const [showLog, setShowLog] = useState(false);
  const [showValidation, setShowValidation] = useState(hasErrors || hasWarnings);

  const status = hasErrors
    ? {
        label: `${result.errors} ERROR${result.errors > 1 ? 'S' : ''}`,
        pill: 'bg-red-100 text-red-800 border-red-300',
        panel: 'bg-red-50 border-red-200',
        text: 'text-red-800',
        note:
          'Some claims were held back from the payroll file. Work through the decisions below to settle ' +
          'what belongs in the IT15 submission, then download the outputs.',
      }
    : hasWarnings
    ? {
        label: `${result.warnings} WARNING${result.warnings > 1 ? 'S' : ''}`,
        pill: 'bg-amber-100 text-amber-800 border-amber-300',
        panel: 'bg-amber-50 border-amber-200',
        text: 'text-amber-800',
        note: 'Outputs are complete and everything is on the payroll file. Review the noted rows before submitting.',
      }
    : {
        label: 'ALL CHECKS PASSED',
        pill: 'bg-green-100 text-green-800 border-green-300',
        panel: 'bg-green-50 border-green-200',
        text: 'text-green-800',
        note: 'No exceptions found. The payroll file is ready to download and submit.',
      };

  const stats = result.stats || {};
  const tiles = STAT_TILES.filter((tile) => stats[tile.key] != null);
  const rows = result.validation || [];
  const structured = rows.some((r) => r.disposition);
  const grouped = GROUPS.map((g) => ({ ...g, rows: rows.filter((r) => r.disposition === g.key) }))
    .filter((g) => g.rows.length > 0);

  return (
    <>
      {/* Run result */}
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
          <p className={`text-sm ${status.text}`}>{status.note}</p>
        </div>

        {stats.grand_total != null && <SubmissionBreakdown stats={stats} />}

        {tiles.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-4">
            {tiles.map((tile) => (
              <div key={tile.key} className="p-3 bg-gray-50 rounded-lg text-center">
                <p className="text-xl font-bold text-gray-800">
                  {tile.money ? money(stats[tile.key]) : stats[tile.key]}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">{tile.label}</p>
              </div>
            ))}
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

      {/* Action breakdown */}
      {rows.length > 0 && (
        <div className="card">
          <button
            onClick={() => setShowValidation(!showValidation)}
            className="w-full flex items-center justify-between text-left"
          >
            <h3 className="text-lg font-semibold text-gray-800">
              Action Breakdown
              {hasErrors && (
                <span className="ml-2 px-2 py-1 text-xs bg-red-100 text-red-800 rounded-full">
                  {result.errors} to decide
                </span>
              )}
              {hasWarnings && (
                <span className="ml-2 px-2 py-1 text-xs bg-amber-100 text-amber-800 rounded-full">
                  {result.warnings} to review
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
            <div className="mt-4 space-y-5">
              {!structured ? (
                <LegacyTable rows={rows} />
              ) : (
                grouped.map((group) => {
                  const total = groupTotal(group.rows);
                  return (
                    <div key={group.key}>
                      <div className="flex items-baseline justify-between mb-1">
                        <h4 className="text-sm font-semibold text-gray-800">{group.title}</h4>
                        <span className="text-xs text-gray-500">
                          {group.rows.length} {group.rows.length === 1 ? 'item' : 'items'}
                          {total > 0 && <> · SGD {money(total)}</>}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mb-2">{group.intro}</p>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {group.rows.map((row, index) => (
                          <ExceptionCard key={index} row={row} group={group} />
                        ))}
                      </div>
                    </div>
                  );
                })
              )}
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
