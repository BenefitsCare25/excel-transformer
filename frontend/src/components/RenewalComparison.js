import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import apiService from '../services/api';

const PRODUCTS = [
  { abbr: 'GTL', name: 'Group Term Life',                          type: 1 },
  { abbr: 'GDD', name: 'Group Dread Disease',                      type: 1 },
  { abbr: 'GPA', name: 'Group Personal Accident',                  type: 1 },
  { abbr: 'GDI', name: 'Group Disability Income Benefit',          type: 1 },
  { abbr: 'GHS', name: 'Group Hospital & Surgical',                type: 2 },
  { abbr: 'GMM', name: 'Group Major Medical',                      type: 2 },
  { abbr: 'GP',  name: 'Group Clinical General Practitioner',      type: 2 },
  { abbr: 'SP',  name: 'Group Clinical Specialist Insurance',      type: 2 },
  { abbr: 'GD',  name: 'Group Dental Insurance',                   type: 2 },
];

const FileUploadBox = ({ label, description, file, onDrop, isProcessing }) => {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
    },
    multiple: false,
    disabled: isProcessing
  });

  return (
    <div className="flex-1">
      <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-blue-500 bg-blue-50'
            : file
            ? 'border-green-400 bg-green-50'
            : 'border-gray-300 hover:border-blue-400'
        } ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />
        {file ? (
          <div className="flex items-center justify-center space-x-2">
            <svg className="w-6 h-6 text-green-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="text-sm text-green-700 truncate max-w-[200px]">{file.name}</span>
          </div>
        ) : (
          <div>
            <svg className="w-10 h-10 mx-auto text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="text-sm text-gray-500">{description}</p>
          </div>
        )}
      </div>
    </div>
  );
};

const RenewalComparison = () => {
  const [file1, setFile1] = useState(null);
  const [file2, setFile2] = useState(null);
  const [proRataDivisor, setProRataDivisor] = useState(2);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showNamed, setShowNamed] = useState(false);
  const [showRequirements, setShowRequirements] = useState(false);

  const handleFile1Drop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFile1(acceptedFiles[0]);
      setError(null);
      setResult(null);
    }
  }, []);

  const handleFile2Drop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFile2(acceptedFiles[0]);
      setError(null);
      setResult(null);
    }
  }, []);

  const bothFilesSelected = file1 && file2;

  const handleCompare = async () => {
    if (!bothFilesSelected) {
      setError('Please upload both files');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiService.processRenewalComparison(file1, file2, proRataDivisor);

      if (response.success) {
        setResult(response.data);
      } else {
        const errorMsg = response.details
          ? `${response.error}: ${response.details}`
          : response.error || 'Comparison failed';
        setError(errorMsg);
      }
    } catch (err) {
      setError(err.message || 'An error occurred during comparison');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = async () => {
    if (result && result.download_filename) {
      const downloadResult = await apiService.downloadRenewalReport(result.download_filename);
      if (!downloadResult.success) {
        setError(`Download failed: ${downloadResult.error}`);
      }
    }
  };

  const handleReset = () => {
    setFile1(null);
    setFile2(null);
    setResult(null);
    setError(null);
    setShowNamed(false);
  };

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="card">
        <div className="mb-4">
          <h2 className="text-xl font-semibold text-gray-800 mb-1">Renewal Comparison</h2>
          <p className="text-sm text-gray-600">
            Compare insurance renewal listing files between two policy years to generate an Adjustment Breakdown report.
            Products and years are auto-detected from headers. Only Headcount employees are included.
          </p>
        </div>

        {/* File Requirements Panel */}
        <div className="mb-6 border border-blue-200 rounded-lg overflow-hidden">
          <button
            onClick={() => setShowRequirements(!showRequirements)}
            className="w-full flex items-center justify-between px-4 py-3 bg-blue-50 hover:bg-blue-100 transition-colors text-left"
          >
            <div className="flex items-center space-x-2">
              <svg className="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span className="text-sm font-medium text-blue-800">File Requirements & Supported Products</span>
            </div>
            <svg
              className={`w-4 h-4 text-blue-600 transition-transform ${showRequirements ? 'rotate-180' : ''}`}
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {showRequirements && (
            <div className="px-4 py-4 bg-white space-y-5">

              {/* Sheet Name Requirement */}
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Required Sheet Name</h4>
                <div className="flex items-center space-x-2">
                  <span className="inline-flex items-center px-3 py-1 bg-gray-900 text-green-400 text-xs font-mono rounded">
                    Employee Listing
                  </span>
                  <span className="text-xs text-gray-500">— The workbook must contain a sheet with this exact name</span>
                </div>
              </div>

              {/* Excel Structure */}
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Expected Excel Structure</h4>
                <div className="overflow-x-auto">
                  <table className="text-xs border-collapse w-full">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="border border-gray-300 px-2 py-1 text-left font-medium text-gray-600 w-16">Row</th>
                        <th className="border border-gray-300 px-2 py-1 text-left font-medium text-gray-600">Content</th>
                        <th className="border border-gray-300 px-2 py-1 text-left font-medium text-gray-600">Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="border border-gray-300 px-2 py-1 font-mono text-gray-500">12</td>
                        <td className="border border-gray-300 px-2 py-1">Dates / Premium Rates</td>
                        <td className="border border-gray-300 px-2 py-1 text-gray-500">Year auto-detected from date values; Type 1 rate (e.g. 0.003) read per product column</td>
                      </tr>
                      <tr className="bg-yellow-50">
                        <td className="border border-gray-300 px-2 py-1 font-mono text-gray-500">13</td>
                        <td className="border border-gray-300 px-2 py-1 font-semibold">Product Headers <span className="text-yellow-700">(merged cells)</span></td>
                        <td className="border border-gray-300 px-2 py-1 text-gray-500">Each product spans its columns as a merged cell, e.g. "GTL", "GHS", "GP"</td>
                      </tr>
                      <tr className="bg-blue-50">
                        <td className="border border-gray-300 px-2 py-1 font-mono text-gray-500">14</td>
                        <td className="border border-gray-300 px-2 py-1 font-semibold">Sub-headers <span className="text-blue-700">(column names)</span></td>
                        <td className="border border-gray-300 px-2 py-1 text-gray-500">Must include "Category", "Sum Insured" or "Annual Premium", "Type of Administration"</td>
                      </tr>
                      <tr>
                        <td className="border border-gray-300 px-2 py-1 font-mono text-gray-500">15+</td>
                        <td className="border border-gray-300 px-2 py-1">Employee Data</td>
                        <td className="border border-gray-300 px-2 py-1 text-gray-500">One row per employee/dependent</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Supported Products */}
              <div>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">Supported Products</h4>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <p className="text-xs font-medium text-purple-700 mb-1 uppercase tracking-wide">
                      Type 1 — Sum Insured × Rate
                    </p>
                    <div className="space-y-1">
                      {PRODUCTS.filter(p => p.type === 1).map(p => (
                        <div key={p.abbr} className="flex items-center space-x-2">
                          <span className="inline-block w-10 text-center px-1 py-0.5 bg-purple-100 text-purple-800 text-xs font-bold rounded">
                            {p.abbr}
                          </span>
                          <span className="text-xs text-gray-600">{p.name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-blue-700 mb-1 uppercase tracking-wide">
                      Type 2 — Annual Premium + GST
                    </p>
                    <div className="space-y-1">
                      {PRODUCTS.filter(p => p.type === 2).map(p => (
                        <div key={p.abbr} className="flex items-center space-x-2">
                          <span className="inline-block w-10 text-center px-1 py-0.5 bg-blue-100 text-blue-800 text-xs font-bold rounded">
                            {p.abbr}
                          </span>
                          <span className="text-xs text-gray-600">{p.name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Admin Type Note */}
              <div className="bg-amber-50 border border-amber-200 rounded-md px-3 py-2">
                <p className="text-xs text-amber-800">
                  <span className="font-semibold">Type of Administration:</span> Employees with{' '}
                  <span className="font-mono bg-amber-100 px-1 rounded">Named</span> administration are excluded from
                  the Headcount adjustment. Employees with{' '}
                  <span className="font-mono bg-amber-100 px-1 rounded">Headcount</span> are included.
                  Classification changes between years are flagged in the Summary sheet.
                </p>
              </div>

            </div>
          )}
        </div>

        {/* File Upload Section */}
        <div className="grid grid-cols-2 gap-6 mb-6">
          <FileUploadBox
            label="File 1"
            description="Drop renewal listing .xlsx (auto-detects year)"
            file={file1}
            onDrop={handleFile1Drop}
            isProcessing={isProcessing}
          />
          <FileUploadBox
            label="File 2"
            description="Drop renewal listing .xlsx (auto-detects year)"
            file={file2}
            onDrop={handleFile2Drop}
            isProcessing={isProcessing}
          />
        </div>

        {/* Configuration */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Pro-rata Divisor
          </label>
          <div className="flex items-center space-x-3">
            <input
              type="number"
              min="1"
              max="12"
              value={proRataDivisor}
              onChange={(e) => setProRataDivisor(Math.max(1, Math.min(12, parseInt(e.target.value) || 1)))}
              disabled={isProcessing}
              className="w-20 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
            />
            <span className="text-xs text-gray-500">
              Adjustment premium divided by this value (default: 2 for half-year)
            </span>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start">
              <svg className="w-5 h-5 text-red-500 mr-2 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <div>
                <p className="text-sm font-medium text-red-800">Error</p>
                <p className="text-sm text-red-700">{typeof error === 'object' ? JSON.stringify(error) : error}</p>
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
              <span className="text-sm text-blue-700">Processing renewal comparison...</span>
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
            onClick={handleCompare}
            disabled={!bothFilesSelected || isProcessing}
            className="px-6 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isProcessing ? 'Processing...' : 'Generate Comparison'}
          </button>
        </div>
      </div>

      {/* Results Section */}
      {result && (
        <>
          {/* Detection Summary */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-800">Detection Summary</h3>
              <button
                onClick={handleDownload}
                className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 flex items-center"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Download Report
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">Previous Year</p>
                <p className="text-sm font-medium text-gray-800">
                  {result.previous_year} ({result.previous_filename})
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">Current Year</p>
                <p className="text-sm font-medium text-gray-800">
                  {result.current_year} ({result.current_filename})
                </p>
              </div>
            </div>

            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Products Detected</h4>
              <div className="flex flex-wrap gap-2">
                {result.products.map((p, idx) => (
                  <span key={idx} className={`px-3 py-1 text-xs font-medium rounded-full ${
                    p.type === 'Sum Insured'
                      ? 'bg-purple-100 text-purple-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    {p.name} ({p.type})
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Employee Overview */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Employee Overview</h3>
            <div className="grid grid-cols-5 gap-4">
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-gray-800">{result.employee_summary.prev_total}</p>
                <p className="text-xs text-gray-500">Previous Year</p>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-gray-800">{result.employee_summary.curr_total}</p>
                <p className="text-xs text-gray-500">Current Year</p>
              </div>
              <div className="text-center p-3 bg-blue-50 rounded-lg">
                <p className="text-2xl font-bold text-blue-600">{result.employee_summary.common}</p>
                <p className="text-xs text-gray-500">Common</p>
              </div>
              <div className="text-center p-3 bg-green-50 rounded-lg">
                <p className="text-2xl font-bold text-green-600">{result.employee_summary.added}</p>
                <p className="text-xs text-gray-500">New</p>
              </div>
              <div className="text-center p-3 bg-red-50 rounded-lg">
                <p className="text-2xl font-bold text-red-600">{result.employee_summary.removed}</p>
                <p className="text-xs text-gray-500">Left</p>
              </div>
            </div>
          </div>

          {/* Product Sheet Breakdown */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-800 mb-1">Product Sheet Breakdown</h3>
            <p className="text-xs text-gray-500 mb-4">
              Rows written to each product sheet in the generated Excel report.
            </p>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Type</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      {result.previous_year} Rows
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                      {result.current_year} Rows
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Change</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Named (Prev)</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Named (Curr)</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {result.products.map((p, idx) => {
                    const delta = (p.sheet_curr_rows ?? p.curr_headcount) - (p.sheet_prev_rows ?? p.prev_headcount);
                    const prevRows = p.sheet_prev_rows ?? p.prev_headcount;
                    const currRows = p.sheet_curr_rows ?? p.curr_headcount;
                    return (
                      <tr key={idx}>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{p.name}</td>
                        <td className="px-4 py-3 text-sm text-center">
                          <span className={`px-2 py-1 text-xs rounded-full ${
                            p.type === 'Sum Insured'
                              ? 'bg-purple-100 text-purple-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}>
                            {p.type}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-center font-medium text-gray-800">{prevRows}</td>
                        <td className="px-4 py-3 text-sm text-center font-medium text-gray-800">{currRows}</td>
                        <td className="px-4 py-3 text-sm text-center">
                          <span className={`font-semibold ${
                            delta > 0 ? 'text-green-600' : delta < 0 ? 'text-red-600' : 'text-gray-500'
                          }`}>
                            {delta > 0 ? `+${delta}` : delta}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-center text-gray-500">{p.prev_named}</td>
                        <td className="px-4 py-3 text-sm text-center text-gray-500">{p.curr_named}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Classification Changes */}
          {result.classification_changes && result.classification_changes.length > 0 && (
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">
                Classification Changes
                <span className="ml-2 px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded-full">
                  {result.classification_changes.length}
                </span>
              </h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-yellow-50">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Employee Name</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">DOB</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Previous Type</th>
                      <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Current Type</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {result.classification_changes.map((cc, idx) => (
                      <tr key={idx} className="bg-yellow-50">
                        <td className="px-3 py-2">{cc.product}</td>
                        <td className="px-3 py-2 font-medium">{cc.name}</td>
                        <td className="px-3 py-2 text-gray-600">{cc.dob}</td>
                        <td className="px-3 py-2">
                          <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">{cc.prev_type}</span>
                        </td>
                        <td className="px-3 py-2">
                          <span className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">{cc.curr_type}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Named Employees Excluded (Collapsible) */}
          {result.named_excluded && result.named_excluded.length > 0 && (
            <div className="card">
              <button
                onClick={() => setShowNamed(!showNamed)}
                className="w-full flex items-center justify-between text-left"
              >
                <h3 className="text-lg font-semibold text-gray-800">
                  Named Employees Excluded
                  <span className="ml-2 px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full">
                    {result.named_excluded.length}
                  </span>
                </h3>
                <svg
                  className={`w-5 h-5 text-gray-500 transition-transform ${showNamed ? 'rotate-180' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showNamed && (
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200 text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Employee Name</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">DOB</th>
                        <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Year</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {result.named_excluded.map((ne, idx) => (
                        <tr key={idx}>
                          <td className="px-3 py-2">{ne.product}</td>
                          <td className="px-3 py-2 font-medium">{ne.name}</td>
                          <td className="px-3 py-2 text-gray-600">{ne.dob}</td>
                          <td className="px-3 py-2 text-gray-600">{ne.year}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* How it works */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">How it works</h3>
        <div className="grid md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold">1</div>
            <h4 className="text-sm font-medium text-gray-700">Upload Files</h4>
            <p className="text-xs text-gray-500 mt-1">Two renewal listing Excel files (any order)</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-purple-100 rounded-full flex items-center justify-center text-purple-600 font-bold">2</div>
            <h4 className="text-sm font-medium text-gray-700">Auto-Detect</h4>
            <p className="text-xs text-gray-500 mt-1">Products, types, and years detected from headers</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-green-100 rounded-full flex items-center justify-center text-green-600 font-bold">3</div>
            <h4 className="text-sm font-medium text-gray-700">Compare</h4>
            <p className="text-xs text-gray-500 mt-1">Cancel & re-enroll for Headcount employees</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-orange-100 rounded-full flex items-center justify-center text-orange-600 font-bold">4</div>
            <h4 className="text-sm font-medium text-gray-700">Export</h4>
            <p className="text-xs text-gray-500 mt-1">Download Adjustment Breakdown Excel report</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RenewalComparison;
