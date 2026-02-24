import { useState, useCallback } from 'react';

const STORAGE_KEY = 'intel_wizard_state';

const INITIAL_STATE = {
  step: 1,
  sessionId: null,
  fileA: null,
  fileB: null,
  analysis: null,
  selectedSheets: { file_a: null, file_b: null },
  columnMapping: { unique_key: [], compare_fields: [], display_fields: [], ignored_fields: [], formula_fields: {} },
  rules: [],
  outputConfig: { add_remarks_column: true, include_summary_sheet: true, highlight_changed_cells: true, output_filename_template: 'comparison_{date}' },
  templateName: 'Custom Comparison',
  appliedTemplate: null,
  result: null,
};

function safeParse(str) {
  try { return JSON.parse(str); } catch { return null; }
}

export function useWizardState() {
  const [state, setState] = useState(() => {
    const saved = sessionStorage.getItem(STORAGE_KEY);
    const parsed = saved ? safeParse(saved) : null;
    // Don't restore file objects (not serializable), just wizard config
    if (parsed) {
      return { ...INITIAL_STATE, ...parsed, fileA: null, fileB: null };
    }
    return INITIAL_STATE;
  });

  const update = useCallback((partial) => {
    setState(prev => {
      const next = { ...prev, ...partial };
      // Persist to sessionStorage (skip File objects)
      const { fileA, fileB, ...persistable } = next;
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(persistable));
      return next;
    });
  }, []);

  const reset = useCallback(() => {
    sessionStorage.removeItem(STORAGE_KEY);
    setState(INITIAL_STATE);
  }, []);

  const goToStep = useCallback((step) => {
    update({ step });
  }, [update]);

  const buildTemplate = useCallback(() => {
    const { templateName, selectedSheets, columnMapping, rules, outputConfig } = state;
    return {
      template_name: templateName,
      sheet_config: {
        file_a_sheet: selectedSheets.file_a || 'Sheet1',
        file_b_sheet: selectedSheets.file_b || selectedSheets.file_a || 'Sheet1',
        header_row: 0,
      },
      column_mapping: columnMapping,
      rules,
      output_config: outputConfig,
    };
  }, [state]);

  return { state, update, reset, goToStep, buildTemplate };
}
