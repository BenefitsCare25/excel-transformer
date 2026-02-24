const BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function getAIHeaders(aiConfig) {
  if (!aiConfig) return {};
  return {
    'X-AI-Provider': aiConfig.provider || 'anthropic',
    'X-AI-Key': aiConfig.apiKey || '',
    'X-AI-Model': aiConfig.model || '',
  };
}

export async function analyzeFiles(fileA, fileB) {
  const form = new FormData();
  form.append('file_a', fileA);
  if (fileB) form.append('file_b', fileB);

  const res = await fetch(`${BASE}/api/intel/analyze`, { method: 'POST', body: form });
  return res.json();
}

export async function processComparison(sessionId, template, dryRun = false) {
  const res = await fetch(`${BASE}/api/intel/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, template, dry_run: dryRun }),
  });
  return res.json();
}

export async function downloadResult(sessionId, resultId, filename) {
  const res = await fetch(`${BASE}/api/intel/download/${sessionId}/${resultId}`);
  if (!res.ok) return false;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename || 'comparison.xlsx';
  a.click();
  URL.revokeObjectURL(url);
  return true;
}

export async function listTemplates() {
  const res = await fetch(`${BASE}/api/intel/templates`);
  return res.json();
}

export async function getTemplate(slug) {
  const res = await fetch(`${BASE}/api/intel/templates/${slug}`);
  return res.json();
}

export async function saveTemplate(template) {
  const res = await fetch(`${BASE}/api/intel/templates`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(template),
  });
  return res.json();
}

export async function aiSuggestTemplate(columns, sheetName, aiConfig) {
  const res = await fetch(`${BASE}/api/intel/ai/suggest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAIHeaders(aiConfig) },
    body: JSON.stringify({ columns, sheet_name: sheetName }),
  });
  return res.json();
}

export async function aiNlToRule(description, columns, aiConfig) {
  const res = await fetch(`${BASE}/api/intel/ai/nl-to-rule`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAIHeaders(aiConfig) },
    body: JSON.stringify({ description, columns }),
  });
  return res.json();
}

export async function aiChat(message, context, aiConfig) {
  const res = await fetch(`${BASE}/api/intel/ai/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAIHeaders(aiConfig) },
    body: JSON.stringify({ message, context }),
  });
  return res.json();
}

export async function testAIKey(aiConfig) {
  const res = await fetch(`${BASE}/api/intel/ai/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAIHeaders(aiConfig) },
    body: JSON.stringify({}),
  });
  return res.json();
}

export async function listProviders() {
  const res = await fetch(`${BASE}/api/intel/providers`);
  return res.json();
}
