import React, { useEffect, useState } from 'react';
import { aiSuggestTemplate, getTemplate } from '../services/intelApi';
import AISuggestionBanner from '../ai/AISuggestionBanner';

function SheetCard({ sheet, selected, onSelect }) {
  const formulaCols = sheet.formula_summary?.formula_columns || [];
  return (
    <div
      onClick={() => onSelect(sheet.name)}
      className={`border rounded-lg p-4 cursor-pointer transition-colors ${
        selected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-medium text-gray-800">{sheet.name}</h4>
        {selected && <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">Selected</span>}
      </div>
      <div className="flex flex-wrap gap-2 text-xs text-gray-500">
        <span>{sheet.row_count} rows</span>
        <span>•</span>
        <span>{sheet.columns?.length || 0} columns</span>
        {sheet.formula_summary?.total_formula_cells > 0 && (
          <>
            <span>•</span>
            <span className="text-orange-600">{sheet.formula_summary.total_formula_cells} formula cells</span>
          </>
        )}
      </div>
      {formulaCols.length > 0 && (
        <div className="mt-2 text-xs text-orange-600">
          Formula columns: {formulaCols.slice(0, 3).join(', ')}{formulaCols.length > 3 ? ` +${formulaCols.length - 3} more` : ''}
        </div>
      )}
    </div>
  );
}

export default function Step2_SheetSelector({ wizard, aiConfig }) {
  const { state, update } = wizard;
  const analysis = state.analysis || {};
  const sheetsA = analysis.file_a?.sheets || [];
  const sheetsB = analysis.file_b?.sheets || [];
  const hasBothFiles = sheetsB.length > 0;

  const [suggestion, setSuggestion] = useState(null);

  // Auto-suggest from analysis
  useEffect(() => {
    const firstSheet = sheetsA[0];
    if (!firstSheet) return;
    const suggestedSlug = firstSheet.suggested_template;
    if (suggestedSlug) {
      setSuggestion({ slug: suggestedSlug, sheet: firstSheet.name });
    }
  }, [sheetsA]);

  // Set defaults
  useEffect(() => {
    if (sheetsA.length > 0 && !state.selectedSheets.file_a) {
      update({ selectedSheets: { file_a: sheetsA[0].name, file_b: sheetsB[0]?.name || sheetsA[0].name } });
    }
  }, [sheetsA, sheetsB]);

  const handleApplyTemplate = async (slug) => {
    try {
      const tmpl = await getTemplate(slug);
      if (tmpl.error) return;
      update({
        templateName: tmpl.template_name,
        appliedTemplate: slug,
        columnMapping: tmpl.column_mapping,
        rules: tmpl.rules,
        outputConfig: tmpl.output_config,
        selectedSheets: {
          file_a: tmpl.sheet_config?.file_a_sheet || state.selectedSheets.file_a,
          file_b: tmpl.sheet_config?.file_b_sheet || state.selectedSheets.file_b,
        },
        step: 4, // Skip to rule builder when template applied
      });
    } catch (e) {
      console.error('Failed to load template', e);
    }
  };

  const selectedSheetA = sheetsA.find(s => s.name === state.selectedSheets.file_a);
  const canContinue = state.selectedSheets.file_a;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-800 mb-1">Select Sheets</h2>
        <p className="text-sm text-gray-500">Choose which sheet to compare from each file.</p>
      </div>

      {suggestion && (
        <AISuggestionBanner
          slug={suggestion.slug}
          onApply={() => handleApplyTemplate(suggestion.slug)}
          onDismiss={() => setSuggestion(null)}
        />
      )}

      <div className={`grid gap-6 ${hasBothFiles ? 'md:grid-cols-2' : ''}`}>
        <div>
          <h3 className="text-sm font-semibold text-gray-600 mb-3 uppercase tracking-wide">
            File A — {state.fileA?.name || 'Old File'}
          </h3>
          <div className="space-y-2">
            {sheetsA.map(sheet => (
              <SheetCard
                key={sheet.name}
                sheet={sheet}
                selected={state.selectedSheets.file_a === sheet.name}
                onSelect={(name) => update({ selectedSheets: { ...state.selectedSheets, file_a: name } })}
              />
            ))}
          </div>
        </div>

        {hasBothFiles && (
          <div>
            <h3 className="text-sm font-semibold text-gray-600 mb-3 uppercase tracking-wide">
              File B — {state.fileB?.name || 'New File'}
            </h3>
            <div className="space-y-2">
              {sheetsB.map(sheet => (
                <SheetCard
                  key={sheet.name}
                  sheet={sheet}
                  selected={state.selectedSheets.file_b === sheet.name}
                  onSelect={(name) => update({ selectedSheets: { ...state.selectedSheets, file_b: name } })}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Column preview for selected sheet */}
      {selectedSheetA && (
        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Detected Columns in "{selectedSheetA.name}"</h4>
          <div className="flex flex-wrap gap-2">
            {selectedSheetA.columns?.slice(0, 20).map(col => (
              <span key={col.index} className={`text-xs px-2 py-1 rounded-full border ${
                col.detected_type === 'formula' ? 'bg-orange-50 border-orange-300 text-orange-700' :
                col.detected_type === 'date' ? 'bg-purple-50 border-purple-300 text-purple-700' :
                col.detected_type === 'numeric' ? 'bg-blue-50 border-blue-300 text-blue-700' :
                'bg-gray-100 border-gray-300 text-gray-600'
              }`}>
                {col.name} <span className="opacity-60">({col.detected_type})</span>
              </span>
            ))}
            {selectedSheetA.columns?.length > 20 && (
              <span className="text-xs text-gray-400 px-2 py-1">+{selectedSheetA.columns.length - 20} more</span>
            )}
          </div>
        </div>
      )}

      <div className="flex justify-between">
        <button onClick={() => update({ step: 1 })} className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors">
          ← Back
        </button>
        <button
          onClick={() => update({ step: 3 })}
          disabled={!canContinue}
          className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          Configure Columns →
        </button>
      </div>
    </div>
  );
}
