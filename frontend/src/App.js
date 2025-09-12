import React, { useState, useEffect } from 'react';
import FileUpload from './components/FileUpload';
import ProcessingStatus from './components/ProcessingStatus';
import apiService from './services/api';
import './index.css';

function App() {
  const [processingStatus, setProcessingStatus] = useState('idle');
  const [result, setResult] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [backendHealth, setBackendHealth] = useState(null);

  // Check backend health on component mount
  useEffect(() => {
    const checkHealth = async () => {
      const healthResult = await apiService.healthCheck();
      setBackendHealth(healthResult.success);
    };
    
    checkHealth();
  }, []);

  const handleFileUpload = async (file) => {
    setProcessingStatus('processing');
    setResult(null);
    setJobId(null);

    const uploadResult = await apiService.uploadFile(file);

    if (uploadResult.success) {
      setProcessingStatus('success');
      setResult(uploadResult.data);
      setJobId(uploadResult.data.job_id);
    } else {
      setProcessingStatus('error');
      setResult({
        error: uploadResult.error,
        details: uploadResult.details,
      });
    }
  };

  const handleDownload = async () => {
    if (!jobId) return;

    const downloadResult = await apiService.downloadFile(jobId);
    if (!downloadResult.success) {
      alert(`Download failed: ${downloadResult.error}`);
    }
  };

  const handleReset = () => {
    setProcessingStatus('idle');
    setResult(null);
    setJobId(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">
            Excel Template Transformer
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Automatically transform your Excel files to match the desired template format. 
            Upload your clinic data file and get a standardized template-compliant file instantly.
          </p>
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
              />

              {/* Processing Status Component */}
              <ProcessingStatus
                status={processingStatus}
                result={result}
                onDownload={handleDownload}
                onReset={handleReset}
              />
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
                    Upload your Excel file with clinic data
                  </p>
                </div>
                <div className="text-center p-4">
                  <div className="w-12 h-12 mx-auto mb-3 text-green-600">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </div>
                  <h4 className="font-medium text-gray-800 mb-1">2. Transform</h4>
                  <p className="text-sm text-gray-600">
                    Automatic data processing and formatting
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
                    Get your transformed template file
                  </p>
                </div>
              </div>
            </div>

            <div className="card">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">
                Transformations Applied
              </h3>
              <ul className="space-y-2 text-sm text-gray-700">
                <li className="flex items-start space-x-2">
                  <span className="text-green-600 mt-0.5">•</span>
                  <span><strong>Phone & Remarks:</strong> Combines telephone number with remarks/notes</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-green-600 mt-0.5">•</span>
                  <span><strong>Operating Hours:</strong> Consolidates AM/PM/Night hours into standard format</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-green-600 mt-0.5">•</span>
                  <span><strong>Postal Codes:</strong> Extracts postal codes from Singapore addresses</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-green-600 mt-0.5">•</span>
                  <span><strong>Field Mapping:</strong> Maps clinic ID, name, region, area to template format</span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="text-center mt-12 py-6 border-t border-gray-200">
          <p className="text-gray-500 text-sm">
            Excel Template Transformer v1.0 - Built with React & Flask
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;