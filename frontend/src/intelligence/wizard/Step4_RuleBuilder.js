import React, { useState } from 'react';
import { aiNlToRule } from '../services/intelApi';

const RULE_COLORS = ['#C6EFCE', '#FFC7CE', '#FFEB9C', '#FCE4D6', '#DDEBF7', '#E2EFDA'];

const RULE_TYPE_LABELS = {
  PRESENCE_RULE: { label: 'Presence Rule', icon: '👥', desc: 'Handle rows that only exist in one file' },
  CHANGE_RULE: { label: 'Change Rule', icon: '✏️', desc: 'Detect changed field values' },
  CONDITION_RULE: { label: 'Condition Rule', icon: '🔀', desc: 'IF conditions → outcome label' },
  ROW_MATCH: { label: 'Row Match', icon: '🔗', desc: 'How to match rows between files' },
};

const OPERATORS = [
  'is_empty', 'is_not_empty', 'equals', 'not_equals', 'contains', 'starts_with',
  'changed_from_empty', 'changed_to_empty', 'date_is_before', 'date_is_after',
  'changed_from_pattern', 'changed_to_pattern',
];

function RuleCard({ rule, index, allColumns, onUpdate, onDelete }) {
  const rt = rule.rule_type;
  const typeInfo = RULE_TYPE_LABELS[rt] || { label: rt, icon: '⚙️', desc: '' };
  const cfg = rule.config || {};

  const updateConfig = (partial) => onUpdate(index, { ...rule, config: { ...cfg, ...partial } });

  return (
    <div className="border border-gray-200 rounded-xl p-4 bg-white shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{typeInfo.icon}</span>
          <div>
            <p className="font-medium text-gray-800">{typeInfo.label}</p>
            <p className="text-xs text-gray-500">{typeInfo.desc}</p>
          </div>
        </div>
        <button onClick={() => onDelete(index)} className="text-gray-400 hover:text-red-500 transition-colors p-1">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {rt === 'PRESENCE_RULE' && (
        <div className="grid grid-cols-2 gap-3">
          {['only_in_file_b', 'only_in_file_a'].map(key => (
            <div key={key} className="space-y-1">
              <label className="text-xs text-gray-500 font-medium">{key === 'only_in_file_b' ? 'Only in New File' : 'Only in Old File'}</label>
              <input
                className="w-full text-sm border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Label"
                value={cfg[key]?.outcome_label || ''}
                onChange={(e) => updateConfig({ [key]: { ...cfg[key], outcome_label: e.target.value } })}
              />
              <div className="flex gap-1 flex-wrap">
                {RULE_COLORS.map(c => (
                  <button
                    key={c}
                    onClick={() => updateConfig({ [key]: { ...cfg[key], color: c } })}
                    className={`w-5 h-5 rounded border-2 ${cfg[key]?.color === c ? 'border-gray-600' : 'border-transparent'}`}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {rt === 'CHANGE_RULE' && (
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-500 font-medium">Fields to Compare</label>
            <div className="flex flex-wrap gap-1 mt-1">
              {allColumns.map(col => (
                <button
                  key={col}
                  onClick={() => {
                    const fields = cfg.fields || [];
                    const next = fields.includes(col) ? fields.filter(f => f !== col) : [...fields, col];
                    updateConfig({ fields: next });
                  }}
                  className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
                    (cfg.fields || []).includes(col)
                      ? 'bg-green-100 border-green-400 text-green-800'
                      : 'bg-gray-50 border-gray-200 text-gray-600 hover:border-green-300'
                  }`}
                >
                  {col}
                </button>
              ))}
            </div>
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-xs text-gray-500 font-medium">Outcome Label</label>
              <input
                className="w-full text-sm border border-gray-200 rounded px-2 py-1.5 mt-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
                value={cfg.outcome_label || 'Changed'}
                onChange={(e) => updateConfig({ outcome_label: e.target.value })}
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium">Color</label>
              <div className="flex gap-1 flex-wrap mt-1">
                {RULE_COLORS.map(c => (
                  <button key={c} onClick={() => updateConfig({ color: c })}
                    className={`w-5 h-5 rounded border-2 ${cfg.color === c ? 'border-gray-600' : 'border-transparent'}`}
                    style={{ backgroundColor: c }} />
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {rt === 'CONDITION_RULE' && (
        <div className="space-y-3">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs text-gray-500 font-medium">Conditions</label>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">Join:</span>
                {['AND', 'OR'].map(j => (
                  <button key={j} onClick={() => updateConfig({ condition_join: j })}
                    className={`text-xs px-2 py-0.5 rounded border ${cfg.condition_join === j ? 'bg-blue-100 border-blue-400 text-blue-800' : 'border-gray-200 text-gray-600'}`}>
                    {j}
                  </button>
                ))}
              </div>
            </div>
            {(cfg.conditions || []).map((cond, ci) => (
              <div key={ci} className="flex gap-2 items-center mb-2">
                <select
                  className="text-xs border border-gray-200 rounded px-2 py-1.5 flex-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  value={cond.field || ''}
                  onChange={(e) => {
                    const conds = [...(cfg.conditions || [])];
                    conds[ci] = { ...conds[ci], field: e.target.value };
                    updateConfig({ conditions: conds });
                  }}
                >
                  <option value="">-- Select field --</option>
                  {allColumns.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                <select
                  className="text-xs border border-gray-200 rounded px-2 py-1.5 flex-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  value={cond.operator || ''}
                  onChange={(e) => {
                    const conds = [...(cfg.conditions || [])];
                    conds[ci] = { ...conds[ci], operator: e.target.value };
                    updateConfig({ conditions: conds });
                  }}
                >
                  <option value="">-- Operator --</option>
                  {OPERATORS.map(op => <option key={op} value={op}>{op}</option>)}
                </select>
                {['equals', 'not_equals', 'contains', 'starts_with', 'changed_from_pattern', 'changed_to_pattern', 'date_is_before', 'date_is_after'].includes(cond.operator) && (
                  <input
                    className="text-xs border border-gray-200 rounded px-2 py-1.5 w-24 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    placeholder="value"
                    value={cond.value || ''}
                    onChange={(e) => {
                      const conds = [...(cfg.conditions || [])];
                      conds[ci] = { ...conds[ci], value: e.target.value };
                      updateConfig({ conditions: conds });
                    }}
                  />
                )}
                <button onClick={() => {
                  const conds = (cfg.conditions || []).filter((_, i) => i !== ci);
                  updateConfig({ conditions: conds });
                }} className="text-gray-400 hover:text-red-500">×</button>
              </div>
            ))}
            <button
              onClick={() => updateConfig({ conditions: [...(cfg.conditions || []), { field: '', operator: 'is_not_empty' }] })}
              className="text-xs text-blue-600 hover:text-blue-800"
            >+ Add condition</button>
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-xs text-gray-500 font-medium">Outcome Label</label>
              <input
                className="w-full text-sm border border-gray-200 rounded px-2 py-1.5 mt-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="e.g. Deletion wef {Last Day of Service}"
                value={cfg.outcome_label || ''}
                onChange={(e) => updateConfig({ outcome_label: e.target.value })}
              />
              <p className="text-xs text-gray-400 mt-0.5">Use {'{FieldName}'} to include field values</p>
            </div>
            <div>
              <label className="text-xs text-gray-500 font-medium">Color</label>
              <div className="flex gap-1 flex-wrap mt-1">
                {RULE_COLORS.map(c => (
                  <button key={c} onClick={() => updateConfig({ color: c })}
                    className={`w-5 h-5 rounded border-2 ${cfg.color === c ? 'border-gray-600' : 'border-transparent'}`}
                    style={{ backgroundColor: c }} />
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {rt === 'ROW_MATCH' && (
        <div className="flex gap-4 items-center">
          <div>
            <label className="text-xs text-gray-500 font-medium">Match Method</label>
            <div className="flex gap-2 mt-1">
              {['exact', 'fuzzy'].map(m => (
                <button key={m} onClick={() => updateConfig({ method: m })}
                  className={`text-xs px-3 py-1 rounded border ${cfg.method === m ? 'bg-blue-100 border-blue-400 text-blue-800' : 'border-gray-200 text-gray-600'}`}>
                  {m}
                </button>
              ))}
            </div>
          </div>
          {cfg.method === 'fuzzy' && (
            <div className="flex-1">
              <label className="text-xs text-gray-500 font-medium">Threshold: {cfg.fuzzy_threshold || 0.8}</label>
              <input type="range" min="0.4" max="1.0" step="0.05"
                value={cfg.fuzzy_threshold || 0.8}
                onChange={(e) => updateConfig({ fuzzy_threshold: parseFloat(e.target.value) })}
                className="w-full mt-1" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Step4_RuleBuilder({ wizard, aiConfig }) {
  const { state, update } = wizard;
  const [nlInput, setNlInput] = useState('');
  const [nlLoading, setNlLoading] = useState(false);
  const [nlError, setNlError] = useState(null);

  const allColumns = [
    ...(state.columnMapping.unique_key || []),
    ...(state.columnMapping.compare_fields || []),
    ...(state.columnMapping.display_fields || []),
  ];

  const addRule = (ruleType) => {
    const defaults = {
      PRESENCE_RULE: { only_in_file_b: { outcome_label: 'Addition', color: '#C6EFCE' }, only_in_file_a: { outcome_label: 'Deletion', color: '#FFC7CE' } },
      CHANGE_RULE: { fields: [], outcome_label: 'Changed', color: '#FFEB9C' },
      CONDITION_RULE: { conditions: [], condition_join: 'AND', outcome_label: 'Flagged', color: '#FFC7CE' },
      ROW_MATCH: { method: 'exact', fuzzy_threshold: 0.8 },
    };
    update({ rules: [...state.rules, { rule_type: ruleType, config: defaults[ruleType] || {} }] });
  };

  const updateRule = (index, newRule) => {
    const next = [...state.rules];
    next[index] = newRule;
    update({ rules: next });
  };

  const deleteRule = (index) => {
    update({ rules: state.rules.filter((_, i) => i !== index) });
  };

  const handleNlToRule = async () => {
    if (!nlInput.trim()) return;
    setNlLoading(true);
    setNlError(null);
    try {
      const data = await aiNlToRule(nlInput, allColumns, aiConfig);
      if (data.error) { setNlError(data.error); return; }
      if (data.rule) {
        update({ rules: [...state.rules, data.rule] });
        setNlInput('');
      }
    } catch (e) {
      setNlError('Failed to contact AI. Check your API key in settings.');
    } finally {
      setNlLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-800 mb-1">Build Rules</h2>
        <p className="text-sm text-gray-500">Define comparison logic. Rules are evaluated in order.</p>
      </div>

      {/* Rules list */}
      <div className="space-y-3">
        {state.rules.map((rule, i) => (
          <RuleCard key={i} rule={rule} index={i} allColumns={allColumns} onUpdate={updateRule} onDelete={deleteRule} />
        ))}
        {state.rules.length === 0 && (
          <div className="text-center py-8 border-2 border-dashed border-gray-200 rounded-xl text-sm text-gray-400">
            No rules yet. Add a rule below or describe one in plain English.
          </div>
        )}
      </div>

      {/* Add rule buttons */}
      <div>
        <p className="text-xs text-gray-500 font-medium mb-2">Add Rule:</p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(RULE_TYPE_LABELS).map(([type, { label, icon }]) => (
            <button
              key={type}
              onClick={() => addRule(type)}
              className="text-sm px-3 py-1.5 border border-gray-200 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors text-gray-700"
            >
              {icon} {label}
            </button>
          ))}
        </div>
      </div>

      {/* AI natural language input */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-lg">✨</span>
          <p className="text-sm font-semibold text-blue-800">Describe a rule in plain English</p>
        </div>
        <div className="flex gap-2">
          <input
            className="flex-1 text-sm border border-blue-200 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
            placeholder='e.g. "mark as terminated if Last Day of Service is filled and Category is empty"'
            value={nlInput}
            onChange={(e) => setNlInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) handleNlToRule(); }}
          />
          <button
            onClick={handleNlToRule}
            disabled={!nlInput.trim() || nlLoading}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {nlLoading ? '...' : 'Generate'}
          </button>
        </div>
        {nlError && <p className="text-xs text-red-600 mt-2">{nlError}</p>}
        <p className="text-xs text-blue-600 mt-2">Requires AI API key configured in settings</p>
      </div>

      <div className="flex justify-between">
        <button onClick={() => update({ step: 3 })} className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors">
          ← Back
        </button>
        <button
          onClick={() => update({ step: 5 })}
          className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          Configure Output →
        </button>
      </div>
    </div>
  );
}
