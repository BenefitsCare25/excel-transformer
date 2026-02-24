import React, { useEffect, useState } from 'react';
import { listTemplates, getTemplate } from '../services/intelApi';

const TEMPLATE_ICONS = {
  mediacorp_el: '👤',
  gp_panel: '🏥',
  renewal_comparison: '🔄',
  clinic_matcher: '📍',
};

export default function TemplateGallery({ onApply, onClose }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(null);

  useEffect(() => {
    listTemplates().then(data => {
      setTemplates(data.templates || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handleApply = async (slug) => {
    setApplying(slug);
    try {
      const tmpl = await getTemplate(slug);
      if (!tmpl.error) onApply(tmpl);
    } finally {
      setApplying(null);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">Template Gallery</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="text-center py-8 text-gray-400">Loading templates...</div>
          ) : templates.length === 0 ? (
            <div className="text-center py-8 text-gray-400">No templates available</div>
          ) : (
            <div className="grid gap-3">
              {templates.map(tmpl => (
                <div key={tmpl.slug} className="flex items-center justify-between p-4 border border-gray-200 rounded-xl hover:border-blue-300 hover:bg-blue-50 transition-colors">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{TEMPLATE_ICONS[tmpl.slug] || '📋'}</span>
                    <div>
                      <p className="font-medium text-gray-800">{tmpl.name}</p>
                      <p className="text-xs text-gray-500">{tmpl.description}</p>
                      {tmpl.is_builtin && (
                        <span className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded mt-1 inline-block">Built-in</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleApply(tmpl.slug)}
                    disabled={applying === tmpl.slug}
                    className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    {applying === tmpl.slug ? 'Loading...' : 'Apply'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
