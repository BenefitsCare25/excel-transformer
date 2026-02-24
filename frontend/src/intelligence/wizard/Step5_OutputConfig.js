import React, { useState } from 'react';
import { processComparison, downloadResult } from '../services/intelApi';

function Toggle({ label, desc, value, onChange }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
      <div>
        <p className="text-sm font-medium text-gray-800">{label}</p>
        {desc && <p className="text-xs text-gray-500">{desc}</p>}
      </div>
      <button
        onClick={() => onChange(!value)}
        className={`relative w-10 h-5 rounded-full transition-colors ${value ? 'bg-blue-500' : 'bg-gray-300'}`}
      >
        <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${value ? 'translate-x-5' : 'translate-x-0.5'}`} />
      </button>
    </div>
  );
}

function SummaryBadge({ label, value, color }) {
  const colors = {
    green: 'bg-green-50 border-green-200 text-green-700',
    red: 'bg-red-50 border-red-200 text-red-700',
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-700',
    gray: 'bg-gray-50 border-gray-200 text-gray-700',
  };
  return (
    <div className={`rounded-lg border p-3 text-center ${colors[color] || colors.gray}`}>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs mt-1">{label}</p>
    </div>
  );
}

export default function Step5_OutputConfig({ wizard }) {
  const { state, update, buildTemplate } = wizard;
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [previewRows, setPreviewRows] = useState(null);

  const oc = state.outputConfig;
  const updateOC = (partial) => update({ outputConfig: { ...oc, ...partial } });

  const handleDryRun = async () => {
    setRunning(true);
    setError(null);
    const template = buildTemplate();
    try {
      const data = await processComparison(state.sessionId, template, true);
      if (data.error) { setError(data.error); return; }
      setPreviewRows(data.preview);
    } catch (e) {
      setError('Processing failed. Check that the server is running.');
    } finally {
      setRunning(false);
    }
  };

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    const template = buildTemplate();
    try {
      const data = await processComparison(state.sessionId, template, false);
      if (data.error) { setError(data.error); return; }
      setResult(data);
    } catch (e) {
      setError('Processing failed. Check that the server is running.');
    } finally {
      setRunning(false);
    }
  };

  const handleDownload = async () => {
    if (!result) return;
    await downloadResult(state.sessionId, result.download_id, result.filename);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-800 mb-1">Output Configuration</h2>
        <p className="text-sm text-gray-500">Configure what to include in the comparison report.</p>
      </div>

      {/* Template Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Template / Report Name</label>
        <input
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={state.templateName}
          onChange={(e) => update({ templateName: e.target.value })}
        />
      </div>

      {/* Output filename */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Output Filename Template</label>
        <input
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={oc.output_filename_template || 'comparison_{date}'}
          onChange={(e) => updateOC({ output_filename_template: e.target.value })}
        />
        <p className="text-xs text-gray-400 mt-1">Use {'{date}'} for today's date</p>
      </div>

      {/* Toggles */}
      <div className="bg-gray-50 rounded-xl p-4">
        <Toggle
          label="Add Remarks Column"
          desc="Append outcome labels as a column in the report"
          value={oc.add_remarks_column}
          onChange={(v) => updateOC({ add_remarks_column: v })}
        />
        <Toggle
          label="Include Summary Sheet"
          desc="Add a Summary tab with counts of additions, deletions, changes"
          value={oc.include_summary_sheet}
          onChange={(v) => updateOC({ include_summary_sheet: v })}
        />
        <Toggle
          label="Highlight Changed Cells"
          desc="Color individual cells that changed (in addition to row-level color)"
          value={oc.highlight_changed_cells}
          onChange={(v) => updateOC({ highlight_changed_cells: v })}
        />
      </div>

      {/* Preview */}
      {previewRows && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Preview (first 20 rows)</h3>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="text-xs w-full">
              <thead>
                <tr className="bg-gray-50">
                  {previewRows.length > 0 && Object.keys(previewRows[0]).filter(k => !['source', 'color', 'changed_fields'].includes(k)).map(k => (
                    <th key={k} className="px-2 py-2 text-left text-gray-600 font-medium border-b border-gray-200">{k}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((row, i) => (
                  <tr key={i} style={{ backgroundColor: row.color || 'transparent' }}>
                    {Object.entries(row).filter(([k]) => !['source', 'color', 'changed_fields'].includes(k)).map(([k, v]) => (
                      <td key={k} className="px-2 py-1.5 border-b border-gray-100 text-gray-700">{String(v ?? '')}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Result summary */}
      {result && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4">
          <p className="text-green-800 font-semibold mb-3">✓ Comparison complete!</p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4">
            <SummaryBadge label="Total" value={result.summary?.total || 0} color="gray" />
            <SummaryBadge label="Additions" value={result.summary?.additions || 0} color="green" />
            <SummaryBadge label="Deletions" value={result.summary?.deletions || 0} color="red" />
            <SummaryBadge label="Changes" value={result.summary?.changes || 0} color="yellow" />
            <SummaryBadge label="Unchanged" value={result.summary?.unchanged || 0} color="gray" />
          </div>
          <button
            onClick={handleDownload}
            className="px-5 py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download {result.filename}
          </button>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{error}</div>
      )}

      <div className="flex justify-between gap-3">
        <button onClick={() => update({ step: 4 })} className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors">
          ← Back
        </button>
        <div className="flex gap-3">
          <button
            onClick={handleDryRun}
            disabled={running || !state.sessionId}
            className="px-4 py-2 border border-blue-400 text-blue-700 font-medium rounded-lg hover:bg-blue-50 disabled:opacity-50 transition-colors"
          >
            {running ? 'Running...' : 'Preview (20 rows)'}
          </button>
          <button
            onClick={handleRun}
            disabled={running || !state.sessionId}
            className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            {running ? (
              <>
                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Processing...
              </>
            ) : 'Run Comparison'}
          </button>
        </div>
      </div>
    </div>
  );
}
