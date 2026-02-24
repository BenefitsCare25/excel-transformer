import React from 'react';

const TEMPLATE_LABELS = {
  mediacorp_el: 'Mediacorp Employee ADC',
  gp_panel: 'GP Panel Comparison',
  renewal_comparison: 'Renewal Comparison',
  clinic_matcher: 'Clinic Matcher',
};

export default function AISuggestionBanner({ slug, onApply, onDismiss }) {
  if (!slug || slug === 'none') return null;

  return (
    <div className="flex items-center justify-between bg-blue-50 border border-blue-200 rounded-xl px-4 py-3">
      <div className="flex items-center gap-2">
        <span className="text-blue-500 text-lg">✨</span>
        <div>
          <p className="text-sm font-semibold text-blue-900">Template Detected</p>
          <p className="text-xs text-blue-700">
            This looks like a <strong>{TEMPLATE_LABELS[slug] || slug}</strong> file.
            Apply the template to pre-fill all settings.
          </p>
        </div>
      </div>
      <div className="flex gap-2 ml-4 shrink-0">
        <button
          onClick={onApply}
          className="text-sm px-4 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          Apply Template
        </button>
        <button
          onClick={onDismiss}
          className="text-sm px-3 py-1.5 text-blue-600 hover:text-blue-800 transition-colors"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
