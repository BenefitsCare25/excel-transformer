import React, { useState } from 'react';
import WizardContainer from './wizard/WizardContainer';
import AIChatPanel from './ai/AIChatPanel';
import TemplateGallery from './templates/TemplateGallery';
import { useWizardState } from './hooks/useWizardState';
import { testAIKey } from './services/intelApi';

const PROVIDERS = {
  anthropic: { label: 'Claude (Anthropic)', models: ['claude-haiku-4-5-20251001', 'claude-sonnet-4-6'] },
  openai: { label: 'OpenAI', models: ['gpt-4o-mini', 'gpt-4o'] },
  gemini: { label: 'Google Gemini', models: ['gemini-2.0-flash', 'gemini-2.5-pro-preview-03-25'] },
};

function AISettingsPanel({ aiConfig, onSave, onClose }) {
  const [local, setLocal] = useState({ ...aiConfig });
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    const result = await testAIKey(local);
    setTestResult(result.success ? 'success' : result.error || 'Failed');
    setTesting(false);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-800">AI Provider Settings</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
            <div className="flex flex-col gap-2">
              {Object.entries(PROVIDERS).map(([key, { label }]) => (
                <label key={key} className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="provider" value={key}
                    checked={local.provider === key}
                    onChange={() => setLocal(p => ({ ...p, provider: key, model: PROVIDERS[key].models[0] }))}
                    className="text-blue-600" />
                  <span className="text-sm text-gray-700">{label}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API Key (BYOK)</label>
            <input
              type="password"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder={local.provider === 'anthropic' ? 'sk-ant-...' : local.provider === 'openai' ? 'sk-...' : 'AIza...'}
              value={local.apiKey || ''}
              onChange={(e) => setLocal(p => ({ ...p, apiKey: e.target.value }))}
            />
            <p className="text-xs text-gray-400 mt-1">Stored in browser session only. Never sent to our servers permanently.</p>
          </div>

          {local.provider && PROVIDERS[local.provider] && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
              <select
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={local.model || PROVIDERS[local.provider].models[0]}
                onChange={(e) => setLocal(p => ({ ...p, model: e.target.value }))}
              >
                {PROVIDERS[local.provider].models.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          )}

          <div className="flex items-center gap-2">
            <button
              onClick={handleTest}
              disabled={testing || !local.apiKey}
              className="px-3 py-1.5 text-sm border border-blue-400 text-blue-700 rounded-lg hover:bg-blue-50 disabled:opacity-50 transition-colors"
            >
              {testing ? 'Testing...' : 'Test Key'}
            </button>
            {testResult && (
              <span className={`text-xs ${testResult === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                {testResult === 'success' ? '✓ Connected' : `✗ ${testResult}`}
              </span>
            )}
            <span className="text-xs text-gray-400 ml-auto">
              Or leave empty to use platform key
            </span>
          </div>

          <div className="flex gap-3 pt-2">
            <button onClick={onClose} className="flex-1 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition-colors">
              Cancel
            </button>
            <button
              onClick={() => { onSave(local); onClose(); }}
              className="flex-1 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Save Settings
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const DEFAULT_AI_CONFIG = {
  provider: 'anthropic',
  apiKey: sessionStorage.getItem('intel_ai_key') || '',
  model: 'claude-haiku-4-5-20251001',
};

export default function IntelligencePlatform() {
  const wizard = useWizardState();
  const [aiConfig, setAIConfig] = useState(DEFAULT_AI_CONFIG);
  const [showAISettings, setShowAISettings] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);

  const handleSaveAIConfig = (config) => {
    setAIConfig(config);
    // Persist key to sessionStorage
    if (config.apiKey) sessionStorage.setItem('intel_ai_key', config.apiKey);
    else sessionStorage.removeItem('intel_ai_key');
  };

  const handleApplyTemplate = (tmpl) => {
    wizard.update({
      templateName: tmpl.template_name,
      appliedTemplate: tmpl.slug,
      columnMapping: tmpl.column_mapping,
      rules: tmpl.rules,
      outputConfig: tmpl.output_config,
      selectedSheets: {
        file_a: tmpl.sheet_config?.file_a_sheet,
        file_b: tmpl.sheet_config?.file_b_sheet || tmpl.sheet_config?.file_a_sheet,
      },
      step: wizard.state.sessionId ? 4 : 1,
    });
    setShowTemplates(false);
  };

  const wizardContext = {
    step: wizard.state.step,
    selectedSheets: wizard.state.selectedSheets,
    columnMapping: wizard.state.columnMapping,
    rules: wizard.state.rules,
  };

  return (
    <div className="relative">
      {/* Header toolbar */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">Excel Intelligence</h2>
          <p className="text-sm text-gray-500">Universal Excel comparison wizard with AI assistance</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowTemplates(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-200 rounded-lg hover:border-blue-400 hover:bg-blue-50 text-gray-700 transition-colors"
          >
            <span>📋</span> Templates
          </button>
          <button
            onClick={() => setShowChat(!showChat)}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm border rounded-lg transition-colors ${
              showChat ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-200 hover:border-blue-400 text-gray-700'
            }`}
          >
            <span>✨</span> AI Chat
          </button>
          <button
            onClick={() => setShowAISettings(true)}
            className="p-2 text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
            title="AI Settings"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
          <button
            onClick={wizard.reset}
            className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 transition-colors"
            title="Start over"
          >
            Reset
          </button>
        </div>
      </div>

      {/* AI key indicator */}
      {aiConfig.apiKey && (
        <div className="flex items-center gap-1.5 text-xs text-green-600 mb-4">
          <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
          AI enabled — {aiConfig.provider} / {aiConfig.model}
        </div>
      )}

      {/* Main wizard (with padding-right when chat open) */}
      <div className={`transition-all ${showChat ? 'pr-84' : ''}`}>
        <WizardContainer wizard={wizard} aiConfig={aiConfig} />
      </div>

      {/* Modals */}
      {showAISettings && (
        <AISettingsPanel
          aiConfig={aiConfig}
          onSave={handleSaveAIConfig}
          onClose={() => setShowAISettings(false)}
        />
      )}
      {showTemplates && (
        <TemplateGallery
          onApply={handleApplyTemplate}
          onClose={() => setShowTemplates(false)}
        />
      )}
      <AIChatPanel
        open={showChat}
        onClose={() => setShowChat(false)}
        context={wizardContext}
        aiConfig={aiConfig}
      />
    </div>
  );
}
