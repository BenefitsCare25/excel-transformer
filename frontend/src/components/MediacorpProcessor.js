import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import * as XLSX from 'xlsx';
import apiService from '../services/api';

const CollapsibleDetail = ({ label, count, items, colorClass = 'text-gray-700' }) => {
  const [open, setOpen] = useState(false);
  if (!items || items.length === 0) return null;
  return (
    <div className="bg-white rounded border border-gray-200 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-gray-50 transition-colors"
      >
        <span className={`font-semibold ${colorClass}`}>{count} {label}</span>
        <svg className={`w-4 h-4 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="border-t border-gray-100 max-h-48 overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <th className="px-3 py-1 text-left text-gray-500 font-medium">Staff ID</th>
                <th className="px-3 py-1 text-left text-gray-500 font-medium">Name</th>
                <th className="px-3 py-1 text-left text-gray-500 font-medium">Remark</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {items.map((item, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-3 py-1 text-gray-600 whitespace-nowrap">{item.staff_id}</td>
                  <td className="px-3 py-1 text-gray-800">{item.name}</td>
                  <td className="px-3 py-1 text-gray-500">{item.remark}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const CollapsibleDLDetail = ({ label, count, items, colorClass = 'text-gray-700' }) => {
  const [open, setOpen] = useState(false);
  if (!items || items.length === 0) return null;

  const downloadExcel = (e) => {
    e.stopPropagation();
    const rows = items.map(item => ({
      'Staff ID': item.staff_id || '',
      'Name': item.name || '',
      'Relationship': item.relationship || '',
      'Dep NRIC': item.dep_nric || '',
      'DOB': item.dob || '',
      'Remark': item.remark || '',
    }));
    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, label.replace(/[\\/*?:[\]]/g, '').slice(0, 31));
    XLSX.writeFile(wb, `${label}.xlsx`);
  };

  return (
    <div className="bg-white rounded border border-gray-200 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-gray-50 transition-colors"
      >
        <span className={`font-semibold ${colorClass}`}>{count} {label}</span>
        <div className="flex items-center gap-2">
          <span
            onClick={downloadExcel}
            role="button"
            tabIndex={0}
            onKeyDown={e => e.key === 'Enter' && downloadExcel(e)}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-green-100 text-green-700 hover:bg-green-200 text-xs font-medium"
            title="Download as Excel"
          >
            ↓ Excel
          </span>
          <svg className={`w-4 h-4 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>
      {open && (
        <div className="border-t border-gray-100 max-h-48 overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <th className="px-3 py-1 text-left text-gray-500 font-medium">Staff ID</th>
                <th className="px-3 py-1 text-left text-gray-500 font-medium">Name</th>
                <th className="px-3 py-1 text-left text-gray-500 font-medium">Relationship</th>
                <th className="px-3 py-1 text-left text-gray-500 font-medium">Dep NRIC</th>
                <th className="px-3 py-1 text-left text-gray-500 font-medium">DOB</th>
                <th className="px-3 py-1 text-left text-gray-500 font-medium">Remark</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {items.map((item, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-3 py-1 text-gray-600 whitespace-nowrap">{item.staff_id}</td>
                  <td className="px-3 py-1 text-gray-800">{item.name}</td>
                  <td className="px-3 py-1 text-gray-600">{item.relationship}</td>
                  <td className="px-3 py-1 text-gray-600 whitespace-nowrap">{item.dep_nric}</td>
                  <td className="px-3 py-1 text-gray-600 whitespace-nowrap">{item.dob}</td>
                  <td className="px-3 py-1 text-gray-500">{item.remark}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const getFileType = (filename) => {
  if (!filename) return null;
  const ext = filename.split('.').pop().toLowerCase();
  return ext === 'csv' ? 'CSV' : ext === 'xlsx' ? 'XLSX' : ext.toUpperCase();
};

const formatFileSize = (bytes) => {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const FileTypeBadge = ({ filename }) => {
  const type = getFileType(filename);
  if (!type) return null;
  const isCSV = type === 'CSV';
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold ${
      isCSV ? 'bg-orange-100 text-orange-700 border border-orange-300' : 'bg-emerald-100 text-emerald-700 border border-emerald-300'
    }`}>
      {type}
    </span>
  );
};

const FileUploadBox = ({ label, description, file, onDrop, isProcessing }) => {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'text/csv': ['.csv'],
      'application/csv': ['.csv'],
    },
    multiple: false,
    disabled: isProcessing
  });

  return (
    <div className="flex-1">
      <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-blue-500 bg-blue-50'
            : file
            ? 'border-green-400 bg-green-50'
            : 'border-gray-300 hover:border-blue-400'
        } ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />
        {file ? (
          <div>
            <div className="flex items-center justify-center space-x-2">
              <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="text-sm text-green-700 truncate max-w-[150px]">{file.name}</span>
            </div>
            <div className="flex items-center justify-center space-x-2 mt-1">
              <FileTypeBadge filename={file.name} />
              <span className="text-xs text-gray-500">{formatFileSize(file.size)}</span>
            </div>
          </div>
        ) : (
          <div>
            <svg className="w-8 h-8 mx-auto text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-xs text-gray-500">{description}</p>
          </div>
        )}
      </div>
    </div>
  );
};

const MediacorpProcessor = () => {
  const [files, setFiles] = useState({
    new_el: null,
    old_el: null,
    new_dl: null,
    old_dl: null
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState('');

  const handleFileDrop = useCallback((key) => (acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFiles(prev => ({ ...prev, [key]: acceptedFiles[0] }));
      setError(null);
    }
  }, []);

  const allFilesSelected = Object.values(files).every(f => f !== null);

  const handleProcess = async () => {
    if (!allFilesSelected) {
      setError('Please upload all 4 required files');
      return;
    }

    const invalidFiles = Object.entries(files).filter(([, f]) => {
      const ext = f.name.split('.').pop().toLowerCase();
      return !['xlsx', 'csv'].includes(ext);
    });
    if (invalidFiles.length > 0) {
      setError({
        message: 'Invalid file types detected',
        details: invalidFiles.map(([key, f]) => `${key}: "${f.name}" is not a .xlsx or .csv file`)
      });
      return;
    }

    const fileTypes = Object.entries(files).map(([key, f]) =>
      `${key}: ${getFileType(f.name)} (${formatFileSize(f.size)})`
    );
    console.log('[MC Processor] Starting upload with files:', fileTypes);

    setIsProcessing(true);
    setError(null);
    setResult(null);
    setProgress('Uploading files...');

    try {
      setProgress('Step 0: Uploading & parsing files (CSV auto-detection)...');
      const response = await apiService.processMCFiles(files);

      if (response.success) {
        console.log('[MC Processor] Success:', response.data?.statistics);
        setResult(response.data);
        setProgress('');
      } else {
        const rawDetails = response.details;
        const details = rawDetails
          ? (Array.isArray(rawDetails) ? rawDetails : [rawDetails])
          : null;
        const errObj = {
          message: response.error || 'Processing failed',
          details
        };
        console.error('[MC Processor] Failed:', errObj);
        setError(errObj);
        setProgress('');
      }
    } catch (err) {
      console.error('[MC Processor] Exception:', err);
      setError({ message: err.message || 'An error occurred during processing' });
      setProgress('');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = async (filename) => {
    const fn = filename || (result && result.filename);
    if (fn) {
      const downloadResult = await apiService.downloadMCFile(fn);
      if (!downloadResult.success) {
        setError(`Download failed: ${downloadResult.error}`);
      }
    }
  };

  const handleReset = () => {
    setFiles({ new_el: null, old_el: null, new_dl: null, old_dl: null });
    setResult(null);
    setError(null);
    setProgress('');
  };

  return (
    <div className="space-y-6">
      {/* Main Card */}
      <div className="card">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-2">
            Mediacorp ADC Processor
          </h2>
          <p className="text-sm text-gray-600">
            Process Employee and Dependant Listings to generate ADC output with category mapping.
            Supports raw CSV (pipe-delimited) and Excel (.xlsx) files.
          </p>
        </div>

        {/* Employee Listing Files */}
        <div className="mb-6">
          <h3 className="text-md font-medium text-gray-700 mb-3 flex items-center">
            <svg className="w-5 h-5 mr-2 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            Employee Listing Files
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <FileUploadBox
              label="New Employee Listing"
              description="Drop .xlsx or .csv file here"
              file={files.new_el}
              onDrop={handleFileDrop('new_el')}
              isProcessing={isProcessing}
            />
            <FileUploadBox
              label="Old Employee Listing"
              description="Drop .xlsx or .csv file here"
              file={files.old_el}
              onDrop={handleFileDrop('old_el')}
              isProcessing={isProcessing}
            />
          </div>
        </div>

        {/* Dependant Listing Files */}
        <div className="mb-6">
          <h3 className="text-md font-medium text-gray-700 mb-3 flex items-center">
            <svg className="w-5 h-5 mr-2 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
            Dependant Listing Files
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <FileUploadBox
              label="New Dependant Listing"
              description="Drop .xlsx or .csv file here"
              file={files.new_dl}
              onDrop={handleFileDrop('new_dl')}
              isProcessing={isProcessing}
            />
            <FileUploadBox
              label="Old Dependant Listing"
              description="Drop .xlsx or .csv file here"
              file={files.old_dl}
              onDrop={handleFileDrop('old_dl')}
              isProcessing={isProcessing}
            />
          </div>
        </div>

        {/* Pre-submission Validation Summary */}
        {Object.values(files).some(f => f !== null) && !isProcessing && !result && (
          <div className="mb-4 p-3 bg-slate-50 border border-slate-200 rounded-lg">
            <h4 className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">Upload Summary</h4>
            <div className="grid grid-cols-2 gap-2">
              {[
                { key: 'new_el', label: 'New EL' },
                { key: 'old_el', label: 'Old EL' },
                { key: 'new_dl', label: 'New DL' },
                { key: 'old_dl', label: 'Old DL' },
              ].map(({ key, label }) => (
                <div key={key} className={`flex items-center justify-between px-2 py-1 rounded text-xs ${
                  files[key] ? 'bg-white border border-slate-200' : 'bg-red-50 border border-red-200'
                }`}>
                  <span className={files[key] ? 'text-slate-700' : 'text-red-500 font-medium'}>{label}</span>
                  {files[key] ? (
                    <div className="flex items-center space-x-1.5">
                      <FileTypeBadge filename={files[key].name} />
                      <span className="text-slate-400">{formatFileSize(files[key].size)}</span>
                    </div>
                  ) : (
                    <span className="text-red-400">Missing</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start">
              <svg className="w-5 h-5 text-red-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <p className="text-sm font-medium text-red-800">Error</p>
                <p className="text-sm text-red-700">{typeof error === 'object' ? (error.message || JSON.stringify(error)) : error}</p>
                {error.details && Array.isArray(error.details) && (
                  <ul className="mt-2 text-xs text-red-600 space-y-1 list-disc list-inside">
                    {error.details.map((detail, i) => (
                      <li key={i}>{detail}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Progress Indicator */}
        {isProcessing && (
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center">
              <svg className="animate-spin w-5 h-5 text-blue-500 mr-3" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span className="text-sm text-blue-700">{progress}</span>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end space-x-3">
          <button
            onClick={handleReset}
            disabled={isProcessing}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 disabled:opacity-50"
          >
            Reset
          </button>
          <button
            onClick={handleProcess}
            disabled={!allFilesSelected || isProcessing}
            className="px-6 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isProcessing ? 'Processing...' : 'Process Files'}
          </button>
        </div>
      </div>

      {/* Results Card */}
      {result && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-green-700 flex items-center">
              <svg className="w-6 h-6 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              Processing Complete
            </h3>
          </div>

          {/* File Info from Backend */}
          {result.statistics?.file_info && (
            <div className="mb-4 p-3 bg-slate-50 border border-slate-200 rounded-lg">
              <h4 className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">Files Processed</h4>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(result.statistics.file_info).map(([key, info]) => (
                  <div key={key} className="flex items-center justify-between px-2 py-1 bg-white rounded border border-slate-200 text-xs">
                    <span className="text-slate-700">{key.replace('_', ' ').toUpperCase()}</span>
                    <div className="flex items-center space-x-1.5">
                      <span className={`inline-flex items-center px-1.5 py-0.5 rounded font-bold ${
                        info.type === 'csv' ? 'bg-orange-100 text-orange-700 border border-orange-300' : 'bg-emerald-100 text-emerald-700 border border-emerald-300'
                      }`}>
                        {(info.type || '').toUpperCase()}
                      </span>
                      <span className="text-slate-400">{info.rows || 0} rows</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Basic Statistics */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-600">
                {result.statistics?.employees_processed || 0}
              </div>
              <div className="text-sm text-gray-600">Employees Processed</div>
            </div>
            <div className="bg-purple-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-purple-600">
                {result.statistics?.dependants_processed || 0}
              </div>
              <div className="text-sm text-gray-600">Dependants Processed</div>
            </div>
            <div className="bg-green-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-600">
                {result.statistics?.adc_records || 0}
              </div>
              <div className="text-sm text-gray-600">ADC Records</div>
            </div>
          </div>

          {/* Employee Listing Changes */}
          <div className="bg-blue-50 rounded-lg p-4 mb-4">
            <h4 className="text-sm font-semibold text-blue-800 mb-3 flex items-center">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Employee Listing Changes
            </h4>
            <div className="space-y-2">
              <CollapsibleDetail
                label="Additions"
                count={result.statistics?.el_additions || 0}
                items={result.statistics?.el_details?.additions}
                colorClass="text-green-700"
              />
              <CollapsibleDetail
                label="Deletions"
                count={result.statistics?.el_deletions || 0}
                items={result.statistics?.el_details?.deletions}
                colorClass="text-red-700"
              />
              <CollapsibleDetail
                label="Changes"
                count={result.statistics?.el_details?.changes?.length || 0}
                items={result.statistics?.el_details?.changes}
                colorClass="text-blue-700"
              />
            </div>
            {result.statistics?.el_total_changes > 0 && (
              <div className="mt-2 bg-white rounded p-2">
                <div className="text-xs text-gray-600 flex flex-wrap gap-2">
                  {result.statistics?.el_changes?.entity > 0 && (
                    <span className="bg-gray-100 px-2 py-1 rounded">Entity: {result.statistics.el_changes.entity}</span>
                  )}
                  {result.statistics?.el_changes?.name > 0 && (
                    <span className="bg-gray-100 px-2 py-1 rounded">Name: {result.statistics.el_changes.name}</span>
                  )}
                  {result.statistics?.el_changes?.id_no > 0 && (
                    <span className="bg-gray-100 px-2 py-1 rounded">ID No: {result.statistics.el_changes.id_no}</span>
                  )}
                  {result.statistics?.el_changes?.employment_type > 0 && (
                    <span className="bg-gray-100 px-2 py-1 rounded">Emp Type: {result.statistics.el_changes.employment_type}</span>
                  )}
                  {result.statistics?.el_changes?.bank_account > 0 && (
                    <span className="bg-gray-100 px-2 py-1 rounded">Bank Acct: {result.statistics.el_changes.bank_account}</span>
                  )}
                  {result.statistics?.el_changes?.overseas > 0 && (
                    <span className="bg-gray-100 px-2 py-1 rounded">Overseas: {result.statistics.el_changes.overseas}</span>
                  )}
                  {result.statistics?.el_changes?.category > 0 && (
                    <span className="bg-gray-100 px-2 py-1 rounded">Category: {result.statistics.el_changes.category}</span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Dependant Listing Changes */}
          <div className="bg-purple-50 rounded-lg p-4 mb-4">
            <h4 className="text-sm font-semibold text-purple-800 mb-3 flex items-center">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
              Dependant Listing Changes
            </h4>
            <div className="space-y-2">
              <CollapsibleDLDetail
                label="New Spouse"
                count={result.statistics?.dl_new_spouse || 0}
                items={result.statistics?.dl_details?.new_spouse}
                colorClass="text-pink-700"
              />
              <CollapsibleDLDetail
                label="New Child"
                count={result.statistics?.dl_new_child || 0}
                items={result.statistics?.dl_details?.new_child}
                colorClass="text-indigo-700"
              />
              <CollapsibleDLDetail
                label="New Other"
                count={result.statistics?.dl_new_other || 0}
                items={result.statistics?.dl_details?.new_other}
                colorClass="text-purple-700"
              />
              <CollapsibleDLDetail
                label="Deletions"
                count={result.statistics?.dl_deletions || 0}
                items={result.statistics?.dl_details?.deletions}
                colorClass="text-red-700"
              />
              <CollapsibleDLDetail
                label="Dropoffs"
                count={result.statistics?.dl_dropoffs || 0}
                items={result.statistics?.dl_details?.dropoffs}
                colorClass="text-gray-700"
              />
            </div>
          </div>

          {/* Validation Warnings */}
          {result.statistics?.total_warnings > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
              <h4 className="text-sm font-semibold text-amber-800 mb-3 flex items-center">
                <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                Validation Warnings ({result.statistics?.total_warnings || 0} items - Check with HR)
              </h4>
              <div className="space-y-2">
                {result.statistics?.warnings?.terminated_no_lds > 0 && (
                  <div className="flex items-center text-sm bg-red-100 text-red-800 px-3 py-2 rounded">
                    <span className="w-2 h-2 bg-red-500 rounded-full mr-2"></span>
                    <span className="font-medium">{result.statistics.warnings.terminated_no_lds}</span>
                    <span className="ml-2">Terminated but no LDS - Check with HR</span>
                  </div>
                )}
                {result.statistics?.warnings?.fin_to_nric > 0 && (
                  <div className="flex items-center text-sm bg-yellow-100 text-yellow-800 px-3 py-2 rounded">
                    <span className="w-2 h-2 bg-yellow-500 rounded-full mr-2"></span>
                    <span className="font-medium">{result.statistics.warnings.fin_to_nric}</span>
                    <span className="ml-2">FIN to NRIC - Check Foreign Employment Pass</span>
                  </div>
                )}
                {result.statistics?.warnings?.check_category > 0 && (
                  <div className="flex items-center text-sm bg-yellow-100 text-yellow-800 px-3 py-2 rounded">
                    <span className="w-2 h-2 bg-yellow-500 rounded-full mr-2"></span>
                    <span className="font-medium">{result.statistics.warnings.check_category}</span>
                    <span className="ml-2">Employment Type changed - Check Category/Designation</span>
                  </div>
                )}
                {result.statistics?.warnings?.has_inactive_date > 0 && (
                  <div className="flex items-center text-sm bg-yellow-100 text-yellow-800 px-3 py-2 rounded">
                    <span className="w-2 h-2 bg-yellow-500 rounded-full mr-2"></span>
                    <span className="font-medium">{result.statistics.warnings.has_inactive_date}</span>
                    <span className="ml-2">New employee has Inactive Date - Check with HR</span>
                  </div>
                )}
                {result.statistics?.warnings?.dep_is_employee > 0 && (
                  <div className="flex items-center text-sm bg-blue-100 text-blue-800 px-3 py-2 rounded">
                    <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                    <span className="font-medium">{result.statistics.warnings.dep_is_employee}</span>
                    <span className="ml-2">Dependant is also Employee - Check coverage</span>
                  </div>
                )}
                {result.statistics?.warnings?.terminated_ee_coverage > 0 && (
                  <div className="flex items-center text-sm bg-orange-100 text-orange-800 px-3 py-2 rounded">
                    <span className="w-2 h-2 bg-orange-500 rounded-full mr-2"></span>
                    <span className="font-medium">{result.statistics.warnings.terminated_ee_coverage}</span>
                    <span className="ml-2">Terminated EE as DEP - Check coverage</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Output Information */}
          <div className="bg-gray-50 rounded-lg p-4 mb-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Output File Contains:</h4>
            <ul className="text-sm text-gray-600 space-y-1">
              <li className="flex items-center">
                <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                <strong>Processed EL</strong> - Employee Listing with AIA Category, Flex Category, and ADC Remarks
              </li>
              <li className="flex items-center">
                <span className="w-2 h-2 bg-purple-500 rounded-full mr-2"></span>
                <strong>Processed DL</strong> - Dependant Listing with comparison columns
              </li>
              <li className="flex items-center">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                <strong>Employee</strong> - 13-column format ({result.statistics?.adc_records || 0} records)
              </li>
            </ul>
          </div>

          {/* Download Buttons */}
          <div className="space-y-2">
            <button
              onClick={() => handleDownload(result.filename)}
              className="w-full px-4 py-3 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 flex items-center justify-center"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Download ADC Output
            </button>
            {result.el_filename && (
              <button
                onClick={() => handleDownload(result.el_filename)}
                className="w-full px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 flex items-center justify-center"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Download {result.el_filename}
              </button>
            )}
            {result.dl_filename && (
              <button
                onClick={() => handleDownload(result.dl_filename)}
                className="w-full px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 flex items-center justify-center"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Download {result.dl_filename}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Information Section */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Processing Steps</h3>
        <div className="grid md:grid-cols-5 gap-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-teal-100 rounded-full flex items-center justify-center text-teal-600 font-bold">0</div>
            <h4 className="text-sm font-medium text-gray-700">CSV Import</h4>
            <p className="text-xs text-gray-500 mt-1">Auto-parse pipe-delimited CSV to clean data</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold">1</div>
            <h4 className="text-sm font-medium text-gray-700">Category Tagging</h4>
            <p className="text-xs text-gray-500 mt-1">AIA Category & Flex Category assignment</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-purple-100 rounded-full flex items-center justify-center text-purple-600 font-bold">2</div>
            <h4 className="text-sm font-medium text-gray-700">DL Comparison</h4>
            <p className="text-xs text-gray-500 mt-1">Dependant listing analysis & ADC generation</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-green-100 rounded-full flex items-center justify-center text-green-600 font-bold">3</div>
            <h4 className="text-sm font-medium text-gray-700">EL Comparison</h4>
            <p className="text-xs text-gray-500 mt-1">Employee listing comparison & ADC remarks</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-orange-100 rounded-full flex items-center justify-center text-orange-600 font-bold">4</div>
            <h4 className="text-sm font-medium text-gray-700">Output Generation</h4>
            <p className="text-xs text-gray-500 mt-1">Combined Excel with 3 sheets</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MediacorpProcessor;
