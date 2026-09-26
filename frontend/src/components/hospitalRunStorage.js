const RUNS_KEY = 'hospital-bill-runs';
const PENDING_KEY = 'hospital-bill-pending-batch';
const validId = (value) => typeof value === 'string' && /^[0-9a-f]{32}$/.test(value);

export function readRuns() {
  try {
    const value = JSON.parse(window.localStorage.getItem(RUNS_KEY) || '[]');
    return Array.isArray(value) ? value.filter((run) => run &&
      validId(run.run_id) && typeof run.filename === 'string')
      .map((run) => ({ ...run, archived: run.archived === true })) : [];
  } catch (_) {
    return [];
  }
}

export function saveRuns(runs) {
  if (runs.length) window.localStorage.setItem(RUNS_KEY, JSON.stringify(runs));
  else window.localStorage.removeItem(RUNS_KEY);
}

export function readPendingBatch() {
  try {
    const value = JSON.parse(window.localStorage.getItem(PENDING_KEY) || 'null');
    return value && validId(value.batch_id) ? value : null;
  } catch (_) {
    return null;
  }
}

export function savePendingBatch(batchId) {
  window.localStorage.setItem(PENDING_KEY, JSON.stringify({ batch_id: batchId }));
}

export function clearPendingBatch() {
  window.localStorage.removeItem(PENDING_KEY);
}
