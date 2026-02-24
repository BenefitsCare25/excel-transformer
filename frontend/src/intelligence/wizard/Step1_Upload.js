import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

function FileDropzone({ label, file, onFile, description }) {
  const onDrop = useCallback((accepted) => {
    if (accepted[0]) onFile(accepted[0]);
  }, [onFile]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'], 'application/vnd.ms-excel': ['.xls'] },
    maxFiles: 1,
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
        isDragActive ? 'border-blue-500 bg-blue-50' : file ? 'border-green-400 bg-green-50' : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'
      }`}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-2">
        {file ? (
          <>
            <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="font-medium text-green-700">{file.name}</p>
            <p className="text-xs text-green-600">{(file.size / 1024).toFixed(1)} KB — Click to replace</p>
          </>
        ) : (
          <>
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="font-medium text-gray-700">{label}</p>
            <p className="text-sm text-gray-500">{description}</p>
            <p className="text-xs text-gray-400">Drag & drop or click to browse (.xlsx, .xls)</p>
          </>
        )}
      </div>
    </div>
  );
}

export default function Step1_Upload({ wizard }) {
  const { state, update } = wizard;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalyze = async () => {
    if (!state.fileA) { setError('Please upload at least File A (old file).'); return; }
    setLoading(true);
    setError(null);

    const form = new FormData();
    form.append('file_a', state.fileA);
    if (state.fileB) form.append('file_b', state.fileB);

    try {
      const res = await fetch('http://localhost:5000/api/intel/analyze', { method: 'POST', body: form });
      const data = await res.json();
      if (data.error) { setError(data.error); return; }

      update({
        sessionId: data.session_id,
        analysis: data,
        step: 2,
      });
    } catch (e) {
      setError('Failed to connect to backend. Make sure the server is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-800 mb-1">Upload Your Files</h2>
        <p className="text-sm text-gray-500">Upload the old and new Excel files to compare. File A is your baseline (old), File B is the updated version.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <FileDropzone
          label="File A — Old / Baseline"
          description="The original file to compare from"
          file={state.fileA}
          onFile={(f) => update({ fileA: f })}
        />
        <FileDropzone
          label="File B — New / Updated (optional)"
          description="The new file to compare against. Leave empty to analyze File A alone."
          file={state.fileB}
          onFile={(f) => update({ fileB: f })}
        />
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">{error}</div>
      )}

      <div className="flex justify-end">
        <button
          onClick={handleAnalyze}
          disabled={!state.fileA || loading}
          className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          {loading ? (
            <>
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Analyzing...
            </>
          ) : 'Analyze Files →'}
        </button>
      </div>
    </div>
  );
}
