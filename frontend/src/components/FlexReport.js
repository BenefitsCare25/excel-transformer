import React, { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import apiService from '../services/api';
import FlexRunResult from './FlexRunResult';

const EXCEL_ACCEPT = {
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.ms-excel.sheet.macroEnabled.12': ['.xlsm'],
};

const nextMonth = () => {
  const date = new Date();
  date.setDate(1);
  date.setMonth(date.getMonth() + 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
};

const formatSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
};

// A real .xlsx/.xlsm is a ZIP archive (starts with "PK"). A password-protected workbook,
// and the old binary .xls format, are both OLE2 compound documents (D0 CF 11 E0) — either
// clears the extension filter yet fails server-side with "Can't find workbook in OLE2
// compound document". Sniff the first bytes before accepting. (The server names which of
// the two it is; client-side we give both fixes.)
const validateExcelSignature = async (file) => {
  try {
    const bytes = new Uint8Array(await file.slice(0, 8).arrayBuffer());
    if (bytes[0] === 0x50 && bytes[1] === 0x4b) return null; // "PK" -> ZIP / real xlsx
    if (bytes[0] === 0xd0 && bytes[1] === 0xcf && bytes[2] === 0x11 && bytes[3] === 0xe0) {
      return "Excel can't open this as a workbook — it's either password-protected or an old .xls saved with a .xlsx name. If it has a password, remove it (File → Info → Protect Workbook → Encrypt with Password → clear it). Otherwise use File → Save As → Excel Workbook (.xlsx). Then upload again.";
    }
    return "This isn't a valid .xlsx/.xlsm workbook. Re-save it in Excel as Excel Workbook (.xlsx), then upload again.";
  } catch {
    return null; // Reading failed — let the server perform the final check.
  }
};

const UploadSlot = ({ slot, file, errorMsg, onDrop, onReject, isProcessing }) => {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDropRejected: onReject,
    accept: EXCEL_ACCEPT,
    multiple: false,
    disabled: isProcessing,
  });

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {slot.label}
        {slot.required ? (
          <span className="ml-2 px-1.5 py-0.5 text-xs bg-blue-100 text-blue-800 rounded">Required</span>
        ) : (
          <span className="ml-2 px-1.5 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">Optional</span>
        )}
      </label>
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-5 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-blue-500 bg-blue-50'
            : errorMsg
            ? 'border-red-400 bg-red-50'
            : file
            ? 'border-green-400 bg-green-50'
            : 'border-gray-300 hover:border-blue-400'
        } ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />
        {file ? (
          <div className="flex items-center justify-center space-x-2">
            <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <div className="min-w-0">
              <p className="text-sm text-green-700 truncate">{file.name}</p>
              <p className="text-xs text-green-600">{formatSize(file.size)}</p>
            </div>
          </div>
        ) : (
          <div>
            <svg className="w-8 h-8 mx-auto text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-sm text-gray-500">Drop file or click to browse</p>
            <p className="text-xs text-gray-400 mt-0.5">.xlsx or .xlsm</p>
          </div>
        )}
      </div>
      {errorMsg && (
        <p className="mt-1.5 text-xs text-red-600">{errorMsg}</p>
      )}
    </div>
  );
};

const FlexReport = () => {
  const [companies, setCompanies] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [files, setFiles] = useState({});
  const [fileErrors, setFileErrors] = useState({});
  const [payMonth, setPayMonth] = useState(nextMonth);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showPending, setShowPending] = useState(false);

  useEffect(() => {
    const loadCompanies = async () => {
      const response = await apiService.getFlexCompanies();
      if (response.success) {
        const list = response.data.companies || [];
        setCompanies(list);
        const firstActive = list.find((company) => company.status === 'active');
        if (firstActive) setSelectedId(firstActive.id);
      } else {
        setError(response.details ? `${response.error}: ${response.details}` : response.error);
      }
      setIsLoading(false);
    };

    loadCompanies();
  }, []);

  const activeCompanies = companies.filter((company) => company.status === 'active');
  const pendingCompanies = companies.filter((company) => company.status !== 'active');
  const selected = companies.find((company) => company.id === selectedId) || null;

  const handleSelect = (companyId) => {
    setSelectedId(companyId);
    setFiles({});
    setFileErrors({});
    setResult(null);
    setError(null);
  };

  const clearSlot = (key, setter) =>
    setter((prev) => {
      if (!(key in prev)) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });

  const handleDrop = useCallback((key) => async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;
    const file = acceptedFiles[0];
    const sigError = await validateExcelSignature(file);
    if (sigError) {
      clearSlot(key, setFiles);
      setFileErrors((prev) => ({ ...prev, [key]: sigError }));
      return;
    }
    setFiles((prev) => ({ ...prev, [key]: file }));
    clearSlot(key, setFileErrors);
    setError(null);
    setResult(null);
  }, []);

  const handleReject = useCallback((key) => () => {
    clearSlot(key, setFiles);
    setFileErrors((prev) => ({ ...prev, [key]: 'Only .xlsx or .xlsm files are accepted.' }));
  }, []);

  const missingRequired = selected
    ? selected.files.filter((slot) => slot.required && !files[slot.key])
    : [];
  // Firefox and Safari fall back to a plain text box for <input type="month">, so the
  // value is only trustworthy after an explicit YYYY-MM check.
  const payMonthValid = /^\d{4}-(0[1-9]|1[0-2])$/.test(payMonth);
  const canGenerate = Boolean(selected) && missingRequired.length === 0 && payMonthValid;

  const handleGenerate = async () => {
    if (missingRequired.length > 0) {
      setError(`Missing required file(s): ${missingRequired.map((slot) => slot.label).join('; ')}`);
      return;
    }
    if (!payMonthValid) {
      setError('Enter the payment month as YYYY-MM, for example 2026-09.');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setResult(null);

    const response = await apiService.runFlexReport(selected.id, files, `${payMonth}-01`);
    if (response.success) {
      setResult(response.data);
    } else {
      setError(response.details ? `${response.error}: ${response.details}` : response.error);
    }
    setIsProcessing(false);
  };

  const handleDownload = async (index, filename) => {
    const response = await apiService.downloadFlexOutput(result.run_id, index, filename);
    if (!response.success) setError(`Download failed: ${response.error}`);
  };

  const handleDownloadAll = async () => {
    const response = await apiService.downloadFlexAll(result.run_id);
    if (!response.success) setError(`Download failed: ${response.error}`);
  };

  const handleReset = () => {
    setFiles({});
    setFileErrors({});
    setResult(null);
    setError(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-800 mb-1">Flex Report</h2>
        <p className="text-sm text-gray-600">
          Generate each client company's monthly flexible benefits reimbursement pack. Pick the company, upload its
          input files, set the payment month, and download the generated outputs together with a validation breakdown.
          Every company has its own upload slots and transformation rules.
        </p>
        <div className="mt-3 px-3 py-2 bg-gray-50 border border-gray-200 rounded-md">
          <p className="text-xs text-gray-600">
            <span className="font-semibold">Data handling:</span> uploaded payroll files are deleted as soon as the
            outputs are generated, and the generated files are removed from the server 30 minutes after the run.
          </p>
        </div>
      </div>

      {/* Company registry */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-800 mb-1">Client Company</h3>
        <p className="text-xs text-gray-500 mb-4">
          {activeCompanies.length} configured · {pendingCompanies.length} pending setup
        </p>

        {isLoading ? (
          <p className="text-sm text-gray-500">Loading companies…</p>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {activeCompanies.map((company) => {
                const isSelected = company.id === selectedId;
                return (
                  <button
                    key={company.id}
                    onClick={() => handleSelect(company.id)}
                    disabled={isProcessing}
                    className={`text-left p-3 border rounded-lg transition-colors disabled:opacity-50 ${
                      isSelected
                        ? 'border-blue-600 bg-blue-50'
                        : 'border-gray-200 bg-white hover:border-blue-400 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0"></span>
                      <span className={`text-sm font-medium ${isSelected ? 'text-blue-800' : 'text-gray-800'}`}>
                        {company.name}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      {company.files.length} upload slot{company.files.length === 1 ? '' : 's'}
                    </p>
                  </button>
                );
              })}
            </div>

            {pendingCompanies.length > 0 && (
              <div className="mt-4">
                <button
                  onClick={() => setShowPending(!showPending)}
                  className="flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-800"
                >
                  <svg
                    className={`w-4 h-4 transition-transform ${showPending ? 'rotate-180' : ''}`}
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                  <span>
                    {showPending ? 'Hide' : 'Show'} {pendingCompanies.length} companies pending setup
                  </span>
                </button>
                {showPending && (
                  <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
                    {pendingCompanies.map((company) => (
                      <div
                        key={company.id}
                        className="p-2 border border-gray-200 bg-gray-50 rounded-md flex items-center space-x-2"
                      >
                        <span className="w-2 h-2 rounded-full bg-gray-300 flex-shrink-0"></span>
                        <span className="text-xs text-gray-500 truncate">{company.name}</span>
                      </div>
                    ))}
                  </div>
                )}
                {showPending && (
                  <p className="text-xs text-gray-400 mt-2">
                    Each pending company goes live once its transformation rules are added as an adapter module.
                  </p>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Run configuration */}
      {selected && (
        <div className="card">
          <div className="mb-4">
            <h3 className="text-lg font-semibold text-gray-800">{selected.name}</h3>
            <p className="text-sm text-gray-600 mt-1">{selected.notes}</p>
          </div>

          <div className="mb-6">
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Step 1 · Input files</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {selected.files.map((slot) => (
                <UploadSlot
                  key={slot.key}
                  slot={slot}
                  file={files[slot.key]}
                  errorMsg={fileErrors[slot.key]}
                  onDrop={handleDrop(slot.key)}
                  onReject={handleReject(slot.key)}
                  isProcessing={isProcessing}
                />
              ))}
            </div>
          </div>

          <div className="mb-6">
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Step 2 · Payment month</h4>
            <div className="flex items-center space-x-3">
              <input
                type="month"
                pattern="\d{4}-\d{2}"
                placeholder="YYYY-MM"
                value={payMonth}
                onChange={(event) => setPayMonth(event.target.value)}
                disabled={isProcessing}
                className={`px-3 py-2 border rounded-md text-sm focus:ring-blue-500 focus:border-blue-500 ${
                  payMonthValid ? 'border-gray-300' : 'border-red-400 bg-red-50'
                }`}
              />
              <span className={`text-xs ${payMonthValid ? 'text-gray-500' : 'text-red-600'}`}>
                {payMonthValid
                  ? 'Payment lands on the 28th of this month'
                  : 'Enter the month as YYYY-MM, for example 2026-09'}
              </span>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start">
                <svg className="w-5 h-5 text-red-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div>
                  <p className="text-sm font-medium text-red-800">Error</p>
                  <p className="text-sm text-red-700">{typeof error === 'object' ? JSON.stringify(error) : error}</p>
                </div>
              </div>
            </div>
          )}

          {isProcessing && (
            <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center">
                <svg className="animate-spin w-5 h-5 text-blue-500 mr-3" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span className="text-sm text-blue-700">Generating {selected.name} output files…</span>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500">
              {missingRequired.length > 0
                ? `Waiting for: ${missingRequired.map((slot) => slot.label).join(', ')}`
                : 'All required files selected'}
            </p>
            <div className="flex space-x-3">
              <button
                onClick={handleReset}
                disabled={isProcessing}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 disabled:opacity-50"
              >
                Reset
              </button>
              <button
                onClick={handleGenerate}
                disabled={!canGenerate || isProcessing}
                className="px-6 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isProcessing ? 'Processing...' : 'Generate Output Files'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Result */}
      {result && (
        <FlexRunResult result={result} onDownload={handleDownload} onDownloadAll={handleDownloadAll} />
      )}

      {/* How it works */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">How it works</h3>
        <div className="grid md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold">1</div>
            <h4 className="text-sm font-medium text-gray-700">Pick Company</h4>
            <p className="text-xs text-gray-500 mt-1">Each company declares its own upload slots and rules</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-purple-100 rounded-full flex items-center justify-center text-purple-600 font-bold">2</div>
            <h4 className="text-sm font-medium text-gray-700">Upload &amp; Set Month</h4>
            <p className="text-xs text-gray-500 mt-1">Claims, leavers, listing and the prior month's payroll template</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-green-100 rounded-full flex items-center justify-center text-green-600 font-bold">3</div>
            <h4 className="text-sm font-medium text-gray-700">Validate</h4>
            <p className="text-xs text-gray-500 mt-1">Errors hold rows out of the outputs; warnings are flagged only</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-orange-100 rounded-full flex items-center justify-center text-orange-600 font-bold">4</div>
            <h4 className="text-sm font-medium text-gray-700">Download</h4>
            <p className="text-xs text-gray-500 mt-1">Individual files or the whole pack as a single zip</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FlexReport;
