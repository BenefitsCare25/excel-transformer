import React, { useState, useEffect } from 'react';
import FileUpload from './components/FileUpload';
import ProcessingStatus from './components/ProcessingStatus';
import apiService from './services/api';
import './index.css';

function App() {
  const [processingStatus, setProcessingStatus] = useState('idle');
  const [result, setResult] = useState(null);
  const [backendHealth, setBackendHealth] = useState(null);
  const [fileQueue, setFileQueue] = useState([]);
  const [batchResults, setBatchResults] = useState([]);
  const [batchId, setBatchId] = useState(null);

  // Check backend health on component mount
  useEffect(() => {
    const checkHealth = async () => {
      const healthResult = await apiService.healthCheck();
      setBackendHealth(healthResult.success);
    };
    
    checkHealth();
  }, []);

  const handleFileUpload = async (files) => {
    // Convert file objects to queue items with status tracking
    const newFileItems = files.map((file, index) => ({
      id: `${Date.now()}_${index}`,
      file,
      status: 'pending',
      jobId: null,
      result: null,
      error: null
    }));

    setFileQueue(prev => [...prev, ...newFileItems]);
  };

  const handleProcessFiles = async () => {
    if (fileQueue.length === 0) return;

    setProcessingStatus('processing');
    setBatchResults([]);

    // Set all files to processing status
    setFileQueue(prev =>
      prev.map(item => ({ ...item, status: 'processing' }))
    );

    // Use batch upload API for concurrent processing
    const files = fileQueue.map(item => item.file);
    const batchResult = await apiService.uploadBatch(files);

    if (batchResult.success) {
      const results = batchResult.data.results;

      // Store batch ID for download functionality
      setBatchId(batchResult.data.batch_id);

      // Update file queue with results
      setFileQueue(prev =>
        prev.map((item, index) => {
          const result = results.find(r => r.filename === item.file.name);
          if (result) {
            return {
              ...item,
              status: result.success ? 'completed' : 'error',
              jobId: result.job_id || null,
              result: result.success ? result : null,
              error: result.success ? null : result.error
            };
          }
          return { ...item, status: 'error', error: 'Unknown error' };
        })
      );

      setBatchResults(results);
      setProcessingStatus('success');
    } else {
      // Handle batch processing failure
      setFileQueue(prev =>
        prev.map(item => ({
          ...item,
          status: 'error',
          error: batchResult.error
        }))
      );

      setBatchResults([{
        success: false,
        fileName: 'Batch Processing',
        error: batchResult.error
      }]);
      setProcessingStatus('error');
    }
  };

  const handleRemoveFile = (indexToRemove) => {
    setFileQueue(prev => prev.filter((_, index) => index !== indexToRemove));
  };

  const handleClearQueue = () => {
    setFileQueue([]);
    setBatchResults([]);
    setBatchId(null);
    setProcessingStatus('idle');
  };

  const handleDownload = async (jobId, filename = null) => {
    if (!jobId) return;

    const downloadResult = await apiService.downloadFile(jobId, filename);
    if (!downloadResult.success) {
      alert(`Download failed: ${downloadResult.error}`);
    }
  };

  const handleDownloadAll = async (jobId) => {
    if (!jobId) return;

    const downloadResult = await apiService.downloadAllFiles(jobId);
    if (!downloadResult.success) {
      alert(`Download failed: ${downloadResult.error}`);
    }
  };

  const handleDownloadAllBatch = async () => {
    if (batchId) {
      // Use batch download for all files at once
      const downloadResult = await apiService.downloadBatch(batchId);
      if (!downloadResult.success) {
        alert(`Batch download failed: ${downloadResult.error}`);
      }
    } else {
      // Fallback to individual downloads
      const completedFiles = fileQueue.filter(item => item.status === 'completed');

      for (const fileItem of completedFiles) {
        if (fileItem.jobId) {
          await handleDownloadAll(fileItem.jobId);
        }
      }
    }
  };

  const handleReset = () => {
    setProcessingStatus('idle');
    setResult(null);
    setFileQueue([]);
    setBatchResults([]);
    setBatchId(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">
            Excel Template Transformer
          </h1>
        </header>

        {/* Backend Status Indicator */}
        <div className="max-w-4xl mx-auto mb-6">
          <div className="flex items-center justify-center space-x-2 text-sm">
            <div className={`w-2 h-2 rounded-full ${backendHealth ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className={backendHealth ? 'text-green-700' : 'text-red-700'}>
              Backend {backendHealth ? 'Online' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto">
          {backendHealth === false ? (
            <div className="card">
              <div className="text-center py-8">
                <div className="w-16 h-16 mx-auto mb-4 text-red-500">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-red-700 mb-2">Backend Server Unavailable</h3>
                <p className="text-gray-600 mb-4">
                  The backend server is not running. Please start the Flask server to use the application.
                </p>
                <code className="bg-gray-100 px-3 py-1 rounded text-sm">
                  cd backend && python app.py
                </code>
              </div>
            </div>
          ) : (
            <>
              {/* File Upload Component */}
              <FileUpload
                onFileUpload={handleFileUpload}
                isProcessing={processingStatus === 'processing'}
                fileQueue={fileQueue}
                onRemoveFile={handleRemoveFile}
              />

              {/* Batch Processing Controls */}
              {fileQueue.length > 0 && (
                <div className="mt-6 card">
                  <div className="flex flex-col sm:flex-row gap-4 items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <span className="text-sm text-gray-600">
                        {fileQueue.length} file{fileQueue.length > 1 ? 's' : ''} selected
                      </span>
                      <span className="text-xs text-gray-500">
                        ({fileQueue.filter(f => f.status === 'completed').length} completed,{' '}
                        {fileQueue.filter(f => f.status === 'error').length} failed)
                      </span>
                    </div>
                    <div className="flex space-x-3">
                      <button
                        onClick={handleClearQueue}
                        disabled={processingStatus === 'processing'}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50"
                      >
                        Clear All
                      </button>
                      <button
                        onClick={handleProcessFiles}
                        disabled={processingStatus === 'processing' || fileQueue.every(f => f.status !== 'pending')}
                        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                      >
                        {processingStatus === 'processing' ? 'Processing...' : 'Process Files'}
                      </button>
                      {fileQueue.some(f => f.status === 'completed') && (
                        <button
                          onClick={handleDownloadAllBatch}
                          className="px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                        >
                          Download All
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Batch Results Display */}
              {batchResults.length > 0 && (
                <div className="mt-6 card">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">
                    Processing Results
                  </h3>
                  <div className="space-y-3">
                    {batchResults.map((result, index) => (
                      <div key={index} className="flex items-center justify-between bg-gray-50 p-3 rounded-lg">
                        <div>
                          <p className="text-sm font-medium text-gray-900">{result.fileName}</p>
                          {result.success ? (
                            <p className="text-xs text-green-600">
                              ✓ {result.sheets_processed} sheets processed, {result.total_records} records
                            </p>
                          ) : (
                            <p className="text-xs text-red-600">✗ {result.error}</p>
                          )}
                        </div>
                        {result.success && result.job_id && (
                          <div className="flex space-x-2">
                            <button
                              onClick={() => handleDownloadAll(result.job_id)}
                              className="px-3 py-1 text-xs font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
                            >
                              Download
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Legacy Processing Status Component for single file compatibility */}
              {result && !batchResults.length && (
                <ProcessingStatus
                  status={processingStatus}
                  result={result}
                  onDownload={handleDownload}
                  onDownloadAll={handleDownloadAll}
                  onReset={handleReset}
                />
              )}
            </>
          )}

          {/* Information Section */}
          <div className="mt-8 space-y-6">
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">
                How it works
              </h3>
              <div className="grid md:grid-cols-3 gap-4">
                <div className="text-center p-4">
                  <div className="w-12 h-12 mx-auto mb-3 text-blue-600">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <h4 className="font-medium text-gray-800 mb-1">1. Upload</h4>
                  <p className="text-sm text-gray-600">
                    Upload multiple Excel files simultaneously for batch processing
                  </p>
                </div>
                <div className="text-center p-4">
                  <div className="w-12 h-12 mx-auto mb-3 text-green-600">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </div>
                  <h4 className="font-medium text-gray-800 mb-1">2. Process</h4>
                  <p className="text-sm text-gray-600">
                    Concurrent processing of multiple files with real-time progress
                  </p>
                </div>
                <div className="text-center p-4">
                  <div className="w-12 h-12 mx-auto mb-3 text-purple-600">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <h4 className="font-medium text-gray-800 mb-1">3. Download</h4>
                  <p className="text-sm text-gray-600">
                    Batch download all results as single ZIP archive
                  </p>
                </div>
              </div>
            </div>

            <div className="card">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">
                Processing Features
              </h3>
              <ul className="space-y-2 text-sm text-gray-700">
                <li className="flex items-start space-x-2">
                  <span className="text-blue-600 mt-0.5">•</span>
                  <span><strong>Batch Upload:</strong> Upload up to 10 Excel files simultaneously for concurrent processing</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-green-600 mt-0.5">•</span>
                  <span><strong>Multi-Sheet Processing:</strong> Automatically detects and processes GP, TCM, SP clinic, and other panel sheets</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-red-600 mt-0.5">•</span>
                  <span><strong>Termination Filtering:</strong> Removes terminated clinics from panel listings based on termination sheets</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-purple-600 mt-0.5">•</span>
                  <span><strong>Real-time Progress:</strong> Track processing status for each file with visual progress indicators</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-orange-600 mt-0.5">•</span>
                  <span><strong>Batch Download:</strong> Download all processed files in a single ZIP archive with organized naming</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="text-center mt-12 py-6 border-t border-gray-200">
        </footer>
      </div>
    </div>
  );
}

export default App;