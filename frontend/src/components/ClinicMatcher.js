import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

const ClinicMatcher = () => {
  const [baseFile, setBaseFile] = useState(null);
  const [comparisonFile, setComparisonFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  // Base file dropzone
  const onDropBase = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setBaseFile(acceptedFiles[0]);
      setResults(null);
      setError(null);
    }
  }, []);

  const {
    getRootProps: getBaseRootProps,
    getInputProps: getBaseInputProps,
    isDragActive: isBaseDragActive
  } = useDropzone({
    onDrop: onDropBase,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    multiple: false,
    disabled: isProcessing
  });

  // Comparison file dropzone
  const onDropComparison = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setComparisonFile(acceptedFiles[0]);
      setResults(null);
      setError(null);
    }
  }, []);

  const {
    getRootProps: getComparisonRootProps,
    getInputProps: getComparisonInputProps,
    isDragActive: isComparisonDragActive
  } = useDropzone({
    onDrop: onDropComparison,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    multiple: false,
    disabled: isProcessing
  });

  const handleMatch = async () => {
    if (!baseFile || !comparisonFile) {
      alert('Please upload both files before matching');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setResults(null);

    const formData = new FormData();
    formData.append('base_file', baseFile);
    formData.append('comparison_file', comparisonFile);

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      const response = await fetch(`${apiUrl}/match-clinics`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (response.ok) {
        setResults(data);

        // Auto-download the results file
        if (data.download_filename) {
          const downloadUrl = `${apiUrl}/download-match/${data.download_filename}`;
          const link = document.createElement('a');
          link.href = downloadUrl;
          link.download = data.download_filename;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }
      } else {
        setError(data.error || 'An error occurred while matching clinics');
      }
    } catch (err) {
      setError('Failed to connect to the server. Please ensure the backend is running.');
      console.error('Match error:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setBaseFile(null);
    setComparisonFile(null);
    setResults(null);
    setError(null);
  };

  return (
    <div className="space-y-6">
      {/* Instructions Card */}
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">
          Clinic Name Matcher
        </h2>
        <p className="text-gray-600 mb-4">
          Upload two Excel files to compare clinic lists. The system will identify matching clinics and those that appear in only one file.
        </p>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm text-gray-700">
          <p className="font-medium text-blue-900 mb-2">How it works:</p>
          <ul className="space-y-1 text-blue-800">
            <li>• <strong>Base File (Left):</strong> Your master clinic list</li>
            <li>• <strong>Comparison File (Right):</strong> Any Excel file with clinic names to compare</li>
            <li>• The system extracts clinic names and performs case-insensitive matching</li>
            <li>• Results show: Matched clinics, Unmatched in Base, Unmatched in Comparison</li>
            <li>• Results automatically download as a single Excel file with 3 sheets</li>
          </ul>
        </div>
      </div>

      {/* Dual Upload Section */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Base File Dropzone */}
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">Base File (Master List)</h3>
            <div
              {...getBaseRootProps()}
              className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                isBaseDragActive
                  ? 'border-blue-500 bg-blue-50'
                  : baseFile
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-300 hover:border-gray-400 bg-white'
              } ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <input {...getBaseInputProps()} />

              {baseFile ? (
                <div className="space-y-3">
                  <div className="w-16 h-16 mx-auto text-green-600">
                    <svg fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{baseFile.name}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {(baseFile.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                  {!isProcessing && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setBaseFile(null);
                        setResults(null);
                        setError(null);
                      }}
                      className="text-xs text-red-600 hover:text-red-700 font-medium"
                    >
                      Remove
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="w-12 h-12 mx-auto text-gray-400">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-700">
                      {isBaseDragActive ? 'Drop file here' : 'Drop file or click to browse'}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Upload your master clinic list</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Comparison File Dropzone */}
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-800 mb-3">Comparison File</h3>
            <div
              {...getComparisonRootProps()}
              className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                isComparisonDragActive
                  ? 'border-blue-500 bg-blue-50'
                  : comparisonFile
                  ? 'border-green-500 bg-green-50'
                  : 'border-gray-300 hover:border-gray-400 bg-white'
              } ${isProcessing ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <input {...getComparisonInputProps()} />

              {comparisonFile ? (
                <div className="space-y-3">
                  <div className="w-16 h-16 mx-auto text-green-600">
                    <svg fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{comparisonFile.name}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {(comparisonFile.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                  {!isProcessing && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setComparisonFile(null);
                        setResults(null);
                        setError(null);
                      }}
                      className="text-xs text-red-600 hover:text-red-700 font-medium"
                    >
                      Remove
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="w-12 h-12 mx-auto text-gray-400">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-700">
                      {isComparisonDragActive ? 'Drop file here' : 'Drop file or click to browse'}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Upload file to compare against base</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-6 flex justify-center space-x-4">
          <button
            onClick={handleMatch}
            disabled={!baseFile || !comparisonFile || isProcessing}
            className={`px-6 py-3 font-medium rounded-lg transition-colors ${
              !baseFile || !comparisonFile || isProcessing
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700 shadow-md hover:shadow-lg'
            }`}
          >
            {isProcessing ? (
              <span className="flex items-center space-x-2">
                <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Matching...</span>
              </span>
            ) : (
              'Match Clinics'
            )}
          </button>
          <button
            onClick={handleReset}
            disabled={isProcessing}
            className="px-6 py-3 font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="card bg-red-50 border border-red-200">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Results Display */}
      {results && (() => {
        const totalBase = results.matched_count + results.unmatched_base_count;
        const totalComparison = results.matched_count + results.unmatched_comparison_count;
        const matchedPercentage = totalBase > 0 ? ((results.matched_count / totalBase) * 100).toFixed(1) : 0;
        const unmatchedBasePercentage = totalBase > 0 ? ((results.unmatched_base_count / totalBase) * 100).toFixed(1) : 0;
        const unmatchedComparisonPercentage = totalComparison > 0 ? ((results.unmatched_comparison_count / totalComparison) * 100).toFixed(1) : 0;

        return (
          <div className="card bg-green-50 border border-green-200">
            <h3 className="text-lg font-semibold text-green-900 mb-4">
              Matching Complete!
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div className="bg-white rounded-lg p-4 border border-green-300">
                <div className="text-3xl font-bold text-green-600">{results.matched_count}</div>
                <div className="text-sm text-gray-600 mt-1">Matched Clinics</div>
                <div className="text-xs text-gray-500 mt-1">Found in both files</div>
                <div className="mt-2 pt-2 border-t border-green-200">
                  <div className="text-lg font-semibold text-green-700">{matchedPercentage}%</div>
                  <div className="text-xs text-gray-500">of base file</div>
                </div>
              </div>
              <div className="bg-white rounded-lg p-4 border border-orange-300">
                <div className="text-3xl font-bold text-orange-600">{results.unmatched_base_count}</div>
                <div className="text-sm text-gray-600 mt-1">Only in Base</div>
                <div className="text-xs text-gray-500 mt-1">Not found in comparison</div>
                <div className="mt-2 pt-2 border-t border-orange-200">
                  <div className="text-lg font-semibold text-orange-700">{unmatchedBasePercentage}%</div>
                  <div className="text-xs text-gray-500">of base file</div>
                </div>
              </div>
              <div className="bg-white rounded-lg p-4 border border-purple-300">
                <div className="text-3xl font-bold text-purple-600">{results.unmatched_comparison_count}</div>
                <div className="text-sm text-gray-600 mt-1">Only in Comparison</div>
                <div className="text-xs text-gray-500 mt-1">Not found in base</div>
                <div className="mt-2 pt-2 border-t border-purple-200">
                  <div className="text-lg font-semibold text-purple-700">{unmatchedComparisonPercentage}%</div>
                  <div className="text-xs text-gray-500">of comparison file</div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-lg p-4 border border-green-300">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-900">Results File Downloaded</p>
                  <p className="text-xs text-gray-600 mt-1">
                    File: <span className="font-mono">{results.download_filename}</span>
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Contains 3 sheets: Matched, Unmatched in Base, Unmatched in Comparison
                  </p>
                </div>
                <svg className="h-8 w-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
};

export default ClinicMatcher;
