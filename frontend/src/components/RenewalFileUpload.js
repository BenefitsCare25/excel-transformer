import React from 'react';
import { useDropzone } from 'react-dropzone';
import './Renewal.css';

const XLSX_ACCEPT = {
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
};

const RenewalFileUpload = ({ label, description, file, onDrop, isProcessing }) => {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: XLSX_ACCEPT,
    multiple: false,
    disabled: isProcessing,
  });
  const state = isDragActive ? 'is-dragging' : file ? 'has-file' : '';

  return (
    <div className="flex-1">
      <span className="renewal-label">{label}</span>
      <div {...getRootProps({ className: `renewal-drop ${state} ${isProcessing ? 'is-disabled' : ''}` })}>
        <input {...getInputProps({ 'aria-label': label })} />
        {file ? (
          <div className="flex items-center justify-center gap-2">
            <svg className="w-6 h-6 renewal-drop-ok" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="renewal-file-name" title={file.name}>{file.name}</span>
          </div>
        ) : (
          <div>
            <svg className="w-10 h-10 mx-auto mb-2 renewal-drop-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-sm renewal-muted">{description}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default RenewalFileUpload;
