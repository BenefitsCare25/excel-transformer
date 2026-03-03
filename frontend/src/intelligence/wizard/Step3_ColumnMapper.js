import React, { useEffect, useState } from 'react';

const ROLE_LABELS = {
  unique_key: { label: 'Unique Key', color: 'blue', desc: 'Used to match rows between files' },
  compare_fields: { label: 'Compare Fields', color: 'green', desc: 'Fields checked for changes' },
  display_fields: { label: 'Display Only', color: 'purple', desc: 'Shown in output but not compared' },
  ignored_fields: { label: 'Ignore', color: 'gray', desc: 'Excluded from output' },
};

function ColumnChip({ col, role, onRoleChange }) {
  const colorClass = {
    blue: 'bg-blue-100 border-blue-300 text-blue-800',
    green: 'bg-green-100 border-green-300 text-green-800',
    purple: 'bg-purple-100 border-purple-300 text-purple-800',
    gray: 'bg-gray-100 border-gray-300 text-gray-500',
    orange: 'bg-orange-100 border-orange-300 text-orange-700',
  };

  const typeColor = col.detected_type === 'formula' ? 'orange' : col.detected_type === 'date' ? 'purple' :
    col.detected_type === 'numeric' ? 'blue' : 'gray';

  return (
    <div className="flex items-center gap-2 p-2 border rounded-lg bg-white hover:shadow-sm transition-shadow">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 truncate">{col.name}</p>
        <span className={`text-xs px-1.5 py-0.5 rounded ${colorClass[typeColor]}`}>{col.detected_type}</span>
      </div>
      <select
        value={role}
        onChange={(e) => onRoleChange(col.name, e.target.value)}
        className="text-xs border border-gray-200 rounded px-2 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        {Object.entries(ROLE_LABELS).map(([key, { label }]) => (
          <option key={key} value={key}>{label}</option>
        ))}
      </select>
    </div>
  );
}

function RoleSection({ roleKey, info, columns }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className={`w-2 h-2 rounded-full bg-${info.color}-500`} />
        <h4 className="text-sm font-semibold text-gray-700">{info.label}</h4>
        <span className="text-xs text-gray-400 ml-1">— {info.desc}</span>
        <span className="ml-auto text-xs bg-white border border-gray-200 rounded-full px-2 py-0.5 text-gray-500">
          {columns.length}
        </span>
      </div>
      {columns.length === 0 ? (
        <p className="text-xs text-gray-400 italic">No columns assigned</p>
      ) : (
        <div className="flex flex-wrap gap-1">
          {columns.map(name => (
            <span key={name} className="text-xs px-2 py-0.5 bg-white border border-gray-200 rounded-full text-gray-700">{name}</span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Step3_ColumnMapper({ wizard }) {
  const { state, update } = wizard;
  const analysis = state.analysis || {};
  const sheetsA = analysis.file_a?.sheets || [];
  const selectedSheet = sheetsA.find(s => s.name === state.selectedSheets.file_a);
  const allColumns = selectedSheet?.columns || [];

  // Build initial role map from existing columnMapping
  const [roleMap, setRoleMap] = useState(() => {
    const map = {};
    allColumns.forEach(col => { map[col.name] = 'display_fields'; });
    state.columnMapping.unique_key.forEach(n => { map[n] = 'unique_key'; });
    state.columnMapping.compare_fields.forEach(n => { map[n] = 'compare_fields'; });
    state.columnMapping.display_fields?.forEach(n => { map[n] = 'display_fields'; });
    state.columnMapping.ignored_fields?.forEach(n => { map[n] = 'ignored_fields'; });
    return map;
  });

  // Re-initialize when column list changes
  useEffect(() => {
    if (allColumns.length === 0) return;
    setRoleMap(prev => {
      const next = {};
      allColumns.forEach(col => { next[col.name] = prev[col.name] || 'display_fields'; });
      return next;
    });
  }, [selectedSheet?.name]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRoleChange = (colName, newRole) => {
    setRoleMap(prev => ({ ...prev, [colName]: newRole }));
  };

  const getColumnsByRole = (role) =>
    Object.entries(roleMap).filter(([, r]) => r === role).map(([n]) => n);

  const handleContinue = () => {
    update({
      columnMapping: {
        unique_key: getColumnsByRole('unique_key'),
        compare_fields: getColumnsByRole('compare_fields'),
        display_fields: getColumnsByRole('display_fields'),
        ignored_fields: getColumnsByRole('ignored_fields'),
        formula_fields: state.columnMapping.formula_fields || {},
      },
      step: 4,
    });
  };

  const canContinue = getColumnsByRole('unique_key').length > 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-800 mb-1">Map Columns</h2>
        <p className="text-sm text-gray-500">
          Assign a role to each column. The <strong>Unique Key</strong> identifies matching rows between files.
        </p>
      </div>

      {/* Role summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {Object.entries(ROLE_LABELS).map(([key, info]) => (
          <RoleSection key={key} roleKey={key} info={info} columns={getColumnsByRole(key)} />
        ))}
      </div>

      {/* Column list */}
      <div>
        <h3 className="text-sm font-semibold text-gray-600 mb-3">All Columns — Assign Roles</h3>
        {allColumns.length === 0 ? (
          <p className="text-sm text-gray-400 italic">No columns detected. Go back and select a sheet.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-96 overflow-y-auto pr-1">
            {allColumns.map(col => (
              <ColumnChip
                key={col.name}
                col={col}
                role={roleMap[col.name] || 'display_fields'}
                onRoleChange={handleRoleChange}
              />
            ))}
          </div>
        )}
      </div>

      {!canContinue && (
        <div className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3">
          Assign at least one column as <strong>Unique Key</strong> to continue.
        </div>
      )}

      <div className="flex justify-between">
        <button onClick={() => update({ step: 2 })} className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors">
          ← Back
        </button>
        <button
          onClick={handleContinue}
          disabled={!canContinue}
          className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          Build Rules →
        </button>
      </div>
    </div>
  );
}
