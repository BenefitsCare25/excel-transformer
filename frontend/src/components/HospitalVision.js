import React, { useRef, useState } from 'react';
import HospitalResults from './HospitalResults';
import useHospitalJobs from './useHospitalJobs';
import './HospitalVision.css';

export default function HospitalVision() {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const {
    files, busy, downloading, result, error, progress,
    selectFiles, process, updateRow, download,
  } = useHospitalJobs();

  const onDrop = (event) => {
    event.preventDefault();
    setDragging(false);
    selectFiles(event.dataTransfer.files);
  };

  return (
    <section className="hospital-vision" aria-label="Hospital Bill">
      <div className="hospital-panel hospital-upload">
        <div
          className={`hospital-drop ${dragging ? 'is-dragging' : ''}`}
          onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <div className="hospital-file-icon" aria-hidden="true">PDF</div>
          <strong>{files.length ? `${files.length} PDF${files.length === 1 ? '' : 's'} selected` : 'Drop hospital bills here'}</strong>
          <span>{files.length ? files.map((file) => file.name).join(' · ') : 'Up to 5 PDFs · 25 MB and 100 pages each'}</span>
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf,.pdf"
            multiple
            disabled={busy}
            className="hospital-file-input"
            onChange={(event) => {
              selectFiles(event.target.files);
              event.target.value = '';
            }}
            aria-label="Choose hospital bill PDFs"
          />
          <button type="button" className="hospital-button secondary" disabled={busy} onClick={() => inputRef.current?.click()}>
            Choose PDFs
          </button>
        </div>
        <div className="hospital-actions">
          <button type="button" className="hospital-button primary" disabled={!files.length || busy} onClick={process}>
            {busy ? 'Processing…' : 'Process bills'}
          </button>
        </div>
      </div>

      {error && <div className="hospital-alert error" role="alert">{error}</div>}
      {busy && progress && (
        <p className="hospital-status" role="status">
          {progress.state === 'reconnecting'
            ? `Reconnecting to ${progress.filename}…`
            : `${progress.filename}: ${progress.total_pages
              ? `${progress.completed_pages} of ${progress.total_pages} pages`
              : 'Starting OCR…'}`}
        </p>
      )}

      {result && (
        <HospitalResults
          result={result}
          busy={busy}
          downloading={downloading}
          updateRow={updateRow}
          download={download}
        />
      )}
    </section>
  );
}
