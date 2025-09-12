import React from 'react';

const ProcessingStatus = ({ status, result, onDownload, onReset }) => {
  if (status === 'idle') return null;

  return (
    <div className="card mt-6">
      <h3 className="text-xl font-bold text-gray-800 mb-4">Processing Status</h3>
      
      {status === 'processing' && (
        <div className="flex items-center space-x-3">
          <div className="animate-spin w-5 h-5 text-blue-600">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </div>
          <span className="text-gray-700">Transforming your Excel file...</span>
        </div>
      )}
      
      {status === 'success' && result && (
        <div className="space-y-4">
          <div className="flex items-center space-x-2">
            <div className="w-5 h-5 text-green-600">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <span className="text-green-700 font-medium">
              Processing completed successfully!
            </span>
          </div>
          
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-sm text-green-800">
              <strong>Records processed:</strong> {result.records_processed}
            </p>
            <p className="text-sm text-green-700 mt-1">
              {result.message}
            </p>
          </div>
          
          <div className="flex space-x-3">
            <button
              onClick={onDownload}
              className="btn-primary"
            >
              <svg className="w-4 h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Download Transformed File
            </button>
            <button
              onClick={onReset}
              className="btn-secondary"
            >
              Transform Another File
            </button>
          </div>
        </div>
      )}
      
      {status === 'error' && result && (
        <div className="space-y-4">
          <div className="flex items-center space-x-2">
            <div className="w-5 h-5 text-red-600">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
            <span className="text-red-700 font-medium">
              Processing failed
            </span>
          </div>
          
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-800 font-medium">
              Error: {result.error}
            </p>
            {result.details && (
              <details className="mt-2">
                <summary className="text-xs text-red-600 cursor-pointer hover:text-red-800">
                  Show technical details
                </summary>
                <pre className="text-xs text-red-700 mt-2 p-2 bg-red-100 rounded overflow-x-auto">
                  {result.details}
                </pre>
              </details>
            )}
          </div>
          
          <button
            onClick={onReset}
            className="btn-secondary"
          >
            Try Again
          </button>
        </div>
      )}
    </div>
  );
};

export default ProcessingStatus;