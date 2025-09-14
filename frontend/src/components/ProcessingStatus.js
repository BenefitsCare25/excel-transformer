import React from 'react';

const ProcessingStatus = ({ status, result, onDownload, onDownloadAll, onReset }) => {
  if (status === 'idle') return null;

  const isMultipleFiles = result && result.output_files && result.output_files.length > 1;
  const hasResults = result && result.results && result.results.length > 0;

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
          <span className="text-gray-700">Processing Excel sheets and filtering terminated clinics...</span>
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

          {/* Summary Statistics */}
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-2">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="font-medium text-green-800">Sheets Processed:</span>
                <span className="text-green-700 ml-2">{result.sheets_processed}</span>
              </div>
              <div>
                <span className="font-medium text-green-800">Total Records:</span>
                <span className="text-green-700 ml-2">{result.total_records}</span>
              </div>
              <div>
                <span className="font-medium text-green-800">Terminated Clinics Filtered:</span>
                <span className="text-green-700 ml-2">{result.terminated_clinics_filtered || 0}</span>
              </div>
            </div>
            <p className="text-sm text-green-700 mt-2">
              {result.message}
            </p>
          </div>

          {/* Individual Sheet Results */}
          {hasResults && (
            <div className="space-y-3">
              <h4 className="font-medium text-gray-800">Generated Files:</h4>
              <div className="space-y-2">
                {result.results.map((sheetResult, index) => (
                  <div key={index} className="bg-gray-50 border border-gray-200 rounded-lg p-3 flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-medium text-gray-800">{sheetResult.sheet_name}</span>
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                          {sheetResult.records_processed} records
                        </span>
                        {sheetResult.terminated_clinics_filtered > 0 && (
                          <span className="px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded">
                            -{sheetResult.terminated_clinics_filtered} terminated
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-600 mt-1 flex items-center space-x-4">
                        <div>
                          <span className="text-green-600">
                            Geocoding: {sheetResult.geocoding_stats.success_rate}
                          </span>
                          <span className="text-gray-500 ml-1">
                            ({sheetResult.geocoding_stats.successful_geocodes}/{sheetResult.geocoding_stats.total_records})
                          </span>
                        </div>
                        {sheetResult.geocoding_stats.postal_code_matches > 0 && (
                          <div className="text-blue-600">
                            Postal: {sheetResult.geocoding_stats.postal_code_matches}
                          </div>
                        )}
                        {sheetResult.geocoding_stats.address_geocodes > 0 && (
                          <div className="text-purple-600">
                            Address: {sheetResult.geocoding_stats.address_geocodes}
                          </div>
                        )}
                        {sheetResult.terminated_clinics_filtered > 0 && (
                          <div className="text-orange-600">
                            -{sheetResult.terminated_clinics_filtered} terminated
                          </div>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => onDownload(sheetResult.output_filename)}
                      className="btn-primary text-sm py-1 px-3 ml-3"
                    >
                      <svg className="w-3 h-3 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Download
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Download Actions */}
          <div className="flex flex-wrap gap-3">
            {isMultipleFiles && (
              <button
                onClick={onDownloadAll}
                className="btn-primary"
              >
                <svg className="w-4 h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m-4-4h4.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Download All Files (ZIP)
              </button>
            )}
            {!isMultipleFiles && (
              <button
                onClick={() => onDownload()}
                className="btn-primary"
              >
                <svg className="w-4 h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Download Transformed File
              </button>
            )}
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