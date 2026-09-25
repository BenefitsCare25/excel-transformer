import { useEffect, useRef, useState } from 'react';
import apiService from '../services/api';

const STORAGE_KEY = 'hospital-bill-runs';

function readRuns() {
  try {
    const value = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || '[]');
    return Array.isArray(value) ? value.filter((run) =>
      /^[0-9a-f]{32}$/.test(run.run_id) && typeof run.filename === 'string')
      .map((run) => ({ ...run, archived: run.archived === true })) : [];
  } catch (_) {
    return [];
  }
}

function saveRuns(runs) {
  try {
    if (runs.length) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(runs));
    else window.localStorage.removeItem(STORAGE_KEY);
  } catch (_) {
    // Processing remains available when browser storage is disabled.
  }
}

function combineResults(completed) {
  const allRows = completed.flatMap((item) => item.rows);
  const byReference = new Map();
  allRows.forEach((row) => {
    const previous = byReference.get(row.bill_ref);
    if (!previous || row.bill_date > previous.bill_date) byReference.set(row.bill_ref, row);
  });
  const rows = [...byReference.values()].sort((a, b) =>
    a.bill_date.localeCompare(b.bill_date) || a.bill_ref.localeCompare(b.bill_ref));
  const warnings = completed.flatMap((item) => item.warnings);
  if (rows.length < allRows.length) {
    warnings.push('Repeated bill references were consolidated; the latest bill date was kept.');
  }
  return {
    rows, warnings,
    redactions: completed.reduce((sum, item) => sum + item.redactions, 0),
    redacted: completed.map(({ run_id, filename }) => ({ run_id, filename })),
  };
}

async function trackRuns(runs, signal, onProgress, onCompleted) {
  const completed = [];
  const failures = [];
  for (const run of runs) {
    onProgress({ filename: run.filename, completed_pages: 0, total_pages: 0 });
    const response = await apiService.waitForHospitalBill(run.run_id,
      (status) => onProgress({ filename: run.filename, ...status }), signal);
    if (response.cancelled) return null;
    if (response.success) {
      completed.push({ ...response.data, filename: run.filename });
      onCompleted(combineResults(completed));
    } else {
      failures.push(`${run.filename}: ${response.error}`);
    }
  }
  return { completed, failures };
}

export default function useHospitalJobs() {
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [progress, setProgress] = useState(null);
  const [savedRuns, setSavedRuns] = useState(readRuns);
  const controllerRef = useRef(null);
  const savedRunsRef = useRef(savedRuns);

  const persistRuns = (runs) => {
    savedRunsRef.current = runs;
    setSavedRuns(runs);
    saveRuns(runs);
  };

  useEffect(() => {
    const runs = savedRunsRef.current.filter((run) => !run.archived);
    if (!runs.length) return () => controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setBusy(true);
    trackRuns(runs, controller.signal, setProgress, setResult).then((outcome) => {
      if (!outcome || controller.signal.aborted) return;
      setError(outcome.failures.join(' '));
      setProgress(null);
      setBusy(false);
    });
    return () => controllerRef.current?.abort();
  }, []);

  const selectFiles = (candidates) => {
    if (busy || deleting) return;
    const chosen = Array.from(candidates || []);
    if (chosen.length > 5 || chosen.some((file) =>
      !file.name.toLowerCase().endsWith('.pdf') || file.size > 25 * 1024 * 1024)) {
      setFiles([]);
      setError('Choose up to five PDFs, each smaller than 25 MB.');
      return;
    }
    setFiles(chosen);
    setError('');
  };

  const process = async () => {
    if (!files.length || busy || deleting) return;
    const controller = new AbortController();
    controllerRef.current = controller;
    setBusy(true);
    setError('');
    setNotice('');
    setResult(null);
    persistRuns(savedRunsRef.current.map((run) => ({ ...run, archived: true })));
    const completed = [];
    const failures = [];
    for (const file of files) {
      if (controller.signal.aborted) return;
      setProgress({ filename: file.name, completed_pages: 0, total_pages: 0 });
      const started = await apiService.processHospitalBill(file);
      if (!started.success) {
        if (controller.signal.aborted) return;
        failures.push(`${file.name}: ${started.error}`);
        continue;
      }
      const run = { run_id: started.data.run_id, filename: file.name };
      persistRuns([...savedRunsRef.current, run]);
      if (controller.signal.aborted) return;
      const response = await apiService.waitForHospitalBill(run.run_id,
        (status) => setProgress({ filename: file.name, ...status }), controller.signal);
      if (response.cancelled) return;
      if (response.success) {
        completed.push({ ...response.data, filename: file.name });
        setResult(combineResults(completed));
      } else {
        failures.push(`${file.name}: ${response.error}`);
      }
    }
    setError(failures.join(' '));
    setProgress(null);
    setBusy(false);
  };

  const updateRow = (index, key, value) => setResult((current) => ({
    ...current,
    rows: current.rows.map((row, rowIndex) => rowIndex === index ? { ...row, [key]: value } : row),
  }));

  const download = async (kind, runId) => {
    if (!result || downloading || deleting) return;
    setDownloading(true);
    setError('');
    const filename = result.redacted.find((item) => item.run_id === runId)?.filename;
    const response = kind === 'pdf'
      ? await apiService.downloadHospitalPdf(runId, filename)
      : await apiService.exportHospitalWorkbook(result.rows);
    if (!response.success) setError(response.error);
    setDownloading(false);
  };

  const deleteSavedData = async () => {
    const runs = [...savedRunsRef.current];
    if (!runs.length || busy || downloading || deleting) return;
    const count = runs.length;
    if (!window.confirm(`Delete saved extracted data and redacted PDFs for ${count} hospital bill run${count === 1 ? '' : 's'} from this server? Downloaded copies on your device will remain.`)) return;

    setDeleting(true);
    setError('');
    setNotice('');
    const failures = [];
    for (const run of runs) {
      const response = await apiService.deleteHospitalRun(run.run_id);
      if (response.success) {
        persistRuns(savedRunsRef.current.filter(({ run_id }) => run_id !== run.run_id));
      } else {
        failures.push(`${run.filename}: ${response.error}`);
      }
    }
    setResult(null);
    setFiles([]);
    setDeleting(false);
    if (failures.length) setError(`Some saved data could not be deleted. Retry with the button. ${failures.join(' ')}`);
    else setNotice('Saved hospital bill data was deleted from this server. Downloaded copies on your device remain.');
  };

  return { files, busy, downloading, deleting, savedRunCount: savedRuns.length,
    result, error, notice, progress, selectFiles, process, updateRow, download, deleteSavedData };
}
