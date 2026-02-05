import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import apiService from '../services/api';

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

const SummaryDashboard = ({ summary }) => {
  const panelOrder = ['gp_sgp', 'gp_msia', 'tcm'];

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Panel</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Previous</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Current</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Net Change</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-green-600 uppercase tracking-wider">Added</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-red-600 uppercase tracking-wider">Removed</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-yellow-600 uppercase tracking-wider">Updated</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {panelOrder.map(key => {
            const stats = summary[key];
            if (!stats) return null;
            return (
              <tr key={key}>
                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">{stats.label}</td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-center text-gray-500">{stats.previous}</td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-center text-gray-500">{stats.current}</td>
                <td className={`px-4 py-3 whitespace-nowrap text-sm text-center font-medium ${
                  stats.change.startsWith('+') && stats.change !== '+0' ? 'text-green-600' :
                  stats.change.startsWith('-') ? 'text-red-600' : 'text-gray-500'
                }`}>{stats.change}</td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-center">
                  {stats.added > 0 ? (
                    <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full">{stats.added}</span>
                  ) : '0'}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-center">
                  {stats.removed > 0 ? (
                    <span className="px-2 py-1 bg-red-100 text-red-800 rounded-full">{stats.removed}</span>
                  ) : '0'}
                </td>
                <td className="px-4 py-3 whitespace-nowrap text-sm text-center">
                  {stats.updated > 0 ? (
                    <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full">{stats.updated}</span>
                  ) : '0'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

const ChangesTable = ({ changes }) => {
  if (!changes.added.length && !changes.removed.length && !changes.updated.length) {
    return (
      <div className="text-center py-8 text-gray-500">
        <svg className="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p>No changes detected</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Provider Code</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Clinic Name</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Area</th>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Details</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {changes.added.map((clinic, idx) => (
            <tr key={`added-${idx}`} className="bg-green-50">
              <td className="px-3 py-2">
                <span className="px-2 py-1 bg-green-200 text-green-800 text-xs font-medium rounded">ADDED</span>
              </td>
              <td className="px-3 py-2 font-mono text-xs">{clinic.provider_code || '-'}</td>
              <td className="px-3 py-2 font-medium">{clinic.clinic_name}</td>
              <td className="px-3 py-2 text-gray-600">{clinic.area}</td>
              <td className="px-3 py-2 text-gray-500">{clinic.address}</td>
            </tr>
          ))}
          {changes.removed.map((clinic, idx) => (
            <tr key={`removed-${idx}`} className="bg-red-50">
              <td className="px-3 py-2">
                <span className="px-2 py-1 bg-red-200 text-red-800 text-xs font-medium rounded">REMOVED</span>
              </td>
              <td className="px-3 py-2 font-mono text-xs">{clinic.provider_code || '-'}</td>
              <td className="px-3 py-2 font-medium">{clinic.clinic_name}</td>
              <td className="px-3 py-2 text-gray-600">{clinic.area}</td>
              <td className="px-3 py-2 text-gray-500">{clinic.address}</td>
            </tr>
          ))}
          {changes.updated.map((update, idx) => (
            <tr key={`updated-${idx}`} className="bg-yellow-50">
              <td className="px-3 py-2">
                <span className="px-2 py-1 bg-yellow-200 text-yellow-800 text-xs font-medium rounded">UPDATED</span>
              </td>
              <td className="px-3 py-2 font-mono text-xs">{update.new.provider_code || '-'}</td>
              <td className="px-3 py-2 font-medium">{update.new.clinic_name}</td>
              <td className="px-3 py-2 text-gray-600">{update.new.area}</td>
              <td className="px-3 py-2 text-xs text-gray-700">
                {update.changes.map((change, i) => (
                  <div key={i}>{change}</div>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const EmailDraft = ({ draft }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(draft);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="bg-gray-50 rounded-lg p-4">
      <div className="flex justify-between items-center mb-3">
        <h4 className="text-sm font-medium text-gray-700">Email Draft</h4>
        <button
          onClick={handleCopy}
          className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
            copied
              ? 'bg-green-100 text-green-700'
              : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
          }`}
        >
          {copied ? '✓ Copied!' : 'Copy to Clipboard'}
        </button>
      </div>
      <pre className="bg-white border border-gray-200 rounded p-4 text-sm text-gray-700 whitespace-pre-wrap font-sans overflow-x-auto">
        {draft}
      </pre>
    </div>
  );
};

const GPPanelComparison = () => {
  const [files, setFiles] = useState({
    previous: null,
    current: null
  });
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('gp_sgp');
  const [showEmailDraft, setShowEmailDraft] = useState(false);

  const handleFileDrop = useCallback((key) => (acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFiles(prev => ({ ...prev, [key]: acceptedFiles[0] }));
      setError(null);
      setResult(null);
    }
  }, []);

  const bothFilesSelected = files.previous && files.current;

  const handleCompare = async () => {
    if (!bothFilesSelected) {
      setError('Please upload both files');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiService.compareGPPanels(files.previous, files.current);

      if (response.success) {
        setResult(response.data);
      } else {
        setError(response.error || 'Comparison failed');
      }
    } catch (err) {
      setError(err.message || 'An error occurred during comparison');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownload = async () => {
    if (result && result.download_filename) {
      const downloadResult = await apiService.downloadGPPanelReport(result.download_filename);
      if (!downloadResult.success) {
        setError(`Download failed: ${downloadResult.error}`);
      }
    }
  };

  const handleReset = () => {
    setFiles({ previous: null, current: null });
    setResult(null);
    setError(null);
    setShowEmailDraft(false);
  };

  const tabConfig = [
    { key: 'gp_sgp', label: 'GP Singapore' },
    { key: 'gp_msia', label: 'GP Malaysia' },
    { key: 'tcm', label: 'TCM' }
  ];

  return (
    <div className="space-y-6">
      {/* Instructions Card */}
      <div className="card">
        <div className="mb-4">
          <h2 className="text-xl font-semibold text-gray-800 mb-2">
            GP Panel Comparison
          </h2>
          <p className="text-sm text-gray-600">
            Compare HSBC Fullerton GP Panel listings to identify added, removed, and updated clinics across GP Singapore, GP Malaysia/JB, and TCM panels.
          </p>
        </div>

        {/* File Upload Section */}
        <div className="grid grid-cols-2 gap-6 mb-6">
          <FileUploadBox
            label="Previous Month Panel"
            description="Drop previous month's GP Panel .xlsx"
            file={files.previous}
            onDrop={handleFileDrop('previous')}
            isProcessing={isProcessing}
          />
          <FileUploadBox
            label="Current Month Panel"
            description="Drop current month's GP Panel .xlsx"
            file={files.current}
            onDrop={handleFileDrop('current')}
            isProcessing={isProcessing}
          />
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
              <span className="text-sm text-blue-700">Comparing panels...</span>
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
            {isProcessing ? 'Comparing...' : 'Compare Panels'}
          </button>
        </div>
      </div>

      {/* Results Section */}
      {result && (
        <>
          {/* Summary Dashboard */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-800">Comparison Summary</h3>
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
            <SummaryDashboard summary={result.summary} />
          </div>

          {/* Tabbed Changes View */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Detailed Changes</h3>

            {/* Tab Navigation */}
            <div className="border-b border-gray-200 mb-4">
              <nav className="flex space-x-4">
                {tabConfig.map(tab => {
                  const changes = result.changes[tab.key];
                  const hasChanges = changes && (changes.added.length > 0 || changes.removed.length > 0 || changes.updated.length > 0);
                  return (
                    <button
                      key={tab.key}
                      onClick={() => setActiveTab(tab.key)}
                      className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                        activeTab === tab.key
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      {tab.label}
                      {hasChanges && (
                        <span className="ml-2 px-2 py-0.5 text-xs bg-blue-100 text-blue-600 rounded-full">
                          {(changes.added.length || 0) + (changes.removed.length || 0) + (changes.updated.length || 0)}
                        </span>
                      )}
                    </button>
                  );
                })}
              </nav>
            </div>

            {/* Tab Content */}
            <ChangesTable changes={result.changes[activeTab] || { added: [], removed: [], updated: [] }} />
          </div>

          {/* Email Draft Section */}
          <div className="card">
            <button
              onClick={() => setShowEmailDraft(!showEmailDraft)}
              className="w-full flex items-center justify-between text-left"
            >
              <h3 className="text-lg font-semibold text-gray-800">Email Draft</h3>
              <svg
                className={`w-5 h-5 text-gray-500 transition-transform ${showEmailDraft ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {showEmailDraft && (
              <div className="mt-4">
                <EmailDraft draft={result.email_draft} />
              </div>
            )}
          </div>
        </>
      )}

      {/* Information Section */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">How it works</h3>
        <div className="grid md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold">1</div>
            <h4 className="text-sm font-medium text-gray-700">Upload Files</h4>
            <p className="text-xs text-gray-500 mt-1">Previous & current month GP Panel Excel files</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-purple-100 rounded-full flex items-center justify-center text-purple-600 font-bold">2</div>
            <h4 className="text-sm font-medium text-gray-700">Extract Data</h4>
            <p className="text-xs text-gray-500 mt-1">Clinics from GP SGP, GP Msia, and TCM sheets</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-green-100 rounded-full flex items-center justify-center text-green-600 font-bold">3</div>
            <h4 className="text-sm font-medium text-gray-700">Compare</h4>
            <p className="text-xs text-gray-500 mt-1">Identify added, removed & updated clinics</p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 mx-auto mb-2 bg-orange-100 rounded-full flex items-center justify-center text-orange-600 font-bold">4</div>
            <h4 className="text-sm font-medium text-gray-700">Export</h4>
            <p className="text-xs text-gray-500 mt-1">Download Excel report & email draft</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GPPanelComparison;
