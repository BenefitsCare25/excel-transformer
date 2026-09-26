import { useEffect, useRef, useState } from 'react';
import apiService from '../services/api';
import { readRuns, saveRuns, readPendingBatch, savePendingBatch, clearPendingBatch } from './hospitalRunStorage';

function rowWarnings(row) {
  const name = row.bill_ref || `Pages ${row.pages.join(', ')}`;
  const pages = `page${row.pages.length === 1 ? '' : 's'} ${row.pages.join(', ')}`;
  return (row.review_notes || []).map((note) => `${name}: ${note}; review ${row.source_file} ${pages}.`);
}

function combineResults(completed) {
  // Results saved before document_warnings existed already carry row notes in `warnings`.
  const allRows = completed.flatMap((item) => item.rows.map((row) => ({
    ...row, source_file: item.filename, legacy_notes: !item.document_warnings,
  })));
  const byReference = new Map();
  const superseded = [];
  allRows.forEach((row, index) => {
    // Rows with an unread bill date cannot be ordered against other versions, so they are kept.
    const key = row.bill_ref && row.bill_date ? row.bill_ref : `unreadable-${index}`;
    const previous = byReference.get(key);
    if (!previous || (row.bill_date || '') > (previous.bill_date || '')) byReference.set(key, row);
    if (previous) superseded.push(key);
  });
  const rows = [...byReference.values()].sort((a, b) =>
    (a.bill_date || '').localeCompare(b.bill_date || '') ||
    (a.bill_ref || '').localeCompare(b.bill_ref || ''));
  const warnings = [
    ...completed.flatMap((item) => (item.document_warnings
      ? item.document_warnings.map((warning) => `${item.filename}: ${warning}`)
      : item.warnings || [])),
    ...rows.filter((row) => !row.legacy_notes).flatMap(rowWarnings),
  ];
  if (superseded.length) {
    warnings.push(`Bills found in more than one file were reported once, using the latest bill date: ${[...new Set(superseded)].join(', ')}.`);
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
    saveRuns(runs);
    savedRunsRef.current = runs;
    setSavedRuns(runs);
  };

  const acceptBatch = (batch) => {
    const incomingIds = new Set(batch.runs.map((run) => run.run_id));
    persistRuns([...savedRunsRef.current.filter((run) => !incomingIds.has(run.run_id))
      .map((run) => ({ ...run, archived: true })), ...batch.runs]);
    clearPendingBatch();
    setNotice(`${batch.runs.length} document${batch.runs.length === 1 ? '' : 's'} uploaded. You can close this page; processing continues and results return when you reopen it in this browser.`);
  };

  useEffect(() => {
    const controller = new AbortController();
    controllerRef.current = controller;
    const resume = async () => {
      if (!readPendingBatch() && !savedRunsRef.current.some((run) => !run.archived)) return;
      setBusy(true);
      try {
        const pending = readPendingBatch();
        if (pending) {
          setProgress({ state: 'reconnecting', filename: 'your uploaded documents' });
          const recovered = await apiService.getHospitalBatch(pending.batch_id, controller.signal);
          if (controller.signal.aborted) return;
          if (recovered.success) acceptBatch(recovered.data);
          else {
            if (recovered.status === 404) clearPendingBatch();
            setError(recovered.error);
          }
        }
        const runs = savedRunsRef.current.filter((run) => !run.archived);
        const outcome = await trackRuns(runs, controller.signal, setProgress, setResult);
        if (outcome?.failures.length && !controller.signal.aborted) setError(outcome.failures.join(' '));
      } catch (failure) {
        if (!controller.signal.aborted) setError(failure.message || 'Could not restore saved documents.');
      } finally {
        if (!controller.signal.aborted) {
          setProgress(null);
          setBusy(false);
        }
      }
    };
    resume();
    return () => controllerRef.current?.abort();
    // Restore once per mount; callbacks read the current saved-run ref.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectFiles = (candidates) => {
    if (busy || deleting) return;
    const chosen = Array.from(candidates || []);
    const invalid = chosen.filter((file) => !file.name.toLowerCase().endsWith('.pdf'));
    if (invalid.length) {
      setFiles([]);
      setError(`Only PDF files can be processed: ${invalid.map((file) => file.name).join(', ')}.`);
      return;
    }
    setFiles(chosen);
    setError('');
  };

  const process = async () => {
    if (!files.length || busy || deleting) return;
    if (readPendingBatch()) {
      setError('An earlier upload still needs to reconnect. Reopen this page to restore it before starting another batch.');
      return;
    }
    const controller = new AbortController();
    controllerRef.current = controller;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const batchId = window.crypto.randomUUID().replace(/-/g, '');
      try {
        savePendingBatch(batchId);
      } catch (_) {
        throw new Error('Enable browser storage so uploaded documents can be restored after reopening.');
      }
      setProgress({ state: 'uploading', filename: `${files.length} documents` });
      const started = await apiService.processHospitalBatch(batchId, files);
      let batch = started.data;
      if (!started.success) {
        const recovered = await apiService.getHospitalBatch(batchId, controller.signal);
        if (recovered.success) batch = recovered.data;
        else {
          if (recovered.status === 404) clearPendingBatch();
          throw new Error(started.error);
        }
      }
      acceptBatch(batch);
      if (controller.signal.aborted) return;
      setFiles([]);
      setResult(null);
      const outcome = await trackRuns(batch.runs, controller.signal, setProgress, setResult);
      if (outcome && !controller.signal.aborted) setError(outcome.failures.join(' '));
    } catch (failure) {
      if (!controller.signal.aborted) setError(failure.message || 'Could not upload the documents.');
    } finally {
      if (!controller.signal.aborted) {
        setProgress(null);
        setBusy(false);
      }
    }
  };

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
    try {
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
      if (failures.length) setError(`Some saved data could not be deleted. Retry with the button. ${failures.join(' ')}`);
      else setNotice('Saved hospital bill data was deleted from this server. Downloaded copies on your device remain.');
    } catch (failure) {
      setError(failure.message || 'Could not update saved document history. Please retry.');
    } finally {
      setDeleting(false);
    }
  };

  return { files, busy, downloading, deleting, savedRunCount: savedRuns.length,
    result, error, notice, progress, selectFiles, process, download, deleteSavedData };
}
