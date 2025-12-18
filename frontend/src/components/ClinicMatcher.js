import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

// Top N Analysis Component - shows detailed table for top N most-visited clinics
const TopNAnalysis = ({ topNData, filterType, reportFilename, onDownloadReport }) => {
  const nValue = filterType === 'top10' ? 10 : 20;

  return (
    <div className="bg-purple-50 rounded-lg border border-purple-200 p-4">
      {/* Header */}
      <div className="mb-4">
        <h4 className="text-md font-semibold text-purple-900">
          Top {nValue} Most-Visited Clinics Analysis
        </h4>
        <p className="text-xs text-gray-600 mt-1">
          Detailed breakdown of your {nValue} highest-utilisation clinics
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="bg-white rounded p-3 border border-purple-300">
          <div className="text-2xl font-bold text-purple-600">{topNData.actual_count}</div>
          <div className="text-xs text-gray-600">Top N Clinics</div>
        </div>
        <div className="bg-white rounded p-3 border border-green-300">
          <div className="text-2xl font-bold text-green-600">{topNData.matched_count}</div>
          <div className="text-xs text-gray-600">Matched</div>
          <div className="text-xs text-green-600 font-medium mt-1">
            {topNData.match_percentage.toFixed(1)}%
          </div>
        </div>
        <div className="bg-white rounded p-3 border border-orange-300">
          <div className="text-2xl font-bold text-orange-600">{topNData.unmatched_count}</div>
          <div className="text-xs text-gray-600">Not Found</div>
        </div>
      </div>

      {/* Detailed Table */}
      <div className="bg-white rounded-lg border border-purple-200 overflow-hidden">
        <div className="overflow-x-auto max-h-96">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-purple-100 sticky top-0">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Rank</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Clinic Name</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-700">Visits</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-gray-700">Amount</th>
                <th className="px-3 py-2 text-center text-xs font-semibold text-gray-700">Status</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Match Details</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {topNData.clinic_details.map((clinic, idx) => (
                <tr key={idx} className={clinic.matched ? 'bg-green-50' : 'bg-orange-50'}>
                  <td className="px-3 py-2 text-sm font-medium text-gray-900">{clinic.rank}</td>
                  <td className="px-3 py-2 text-sm text-gray-900">{clinic.clinic_name}</td>
                  <td className="px-3 py-2 text-sm text-right text-gray-700">
                    {clinic.visit_count?.toLocaleString() || 'N/A'}
                  </td>
                  <td className="px-3 py-2 text-sm text-right text-gray-700">
                    ${clinic.total_amount?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) || '0.00'}
                  </td>
                  <td className="px-3 py-2 text-center">
                    {clinic.matched ? (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-200 text-green-800">
                        ✓ Matched
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-200 text-orange-800">
                        ✗ Not Found
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-600">
                    {clinic.matched ? (
                      <div>
                        <div className="font-medium text-gray-700">{clinic.match_type}</div>
                        <div className="text-gray-500 truncate max-w-xs" title={clinic.matched_to}>
                          → {clinic.matched_to}
                        </div>
                      </div>
                    ) : (
                      <span className="text-gray-400">No match found</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Warning for unmatched top N clinics */}
      {topNData.unmatched_count > 0 && (
        <div className="mt-3 p-3 bg-orange-50 rounded-lg border border-orange-200">
          <div className="flex items-start space-x-2">
            <svg className="h-5 w-5 text-orange-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div>
              <p className="text-sm font-medium text-orange-900">⚠️ Action Required</p>
              <p className="text-xs text-gray-700 mt-1">
                {topNData.unmatched_count} of your top {nValue} most-visited clinics were NOT found in the comparison file.
                These represent significant utilisation that may require attention.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Download Utilisation Report Button */}
      {reportFilename && (
        <div className="mt-4 flex justify-end">
          <button
            onClick={() => onDownloadReport(reportFilename)}
            className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors shadow-sm"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Download Utilisation Report
          </button>
        </div>
      )}
    </div>
  );
};

// Alternative Nearest Clinics Component - shows geographic alternatives for unmatched clinics
const AlternativeNearestClinics = ({ alternativeData }) => {
  if (!alternativeData || !alternativeData.alternatives || alternativeData.alternatives.length === 0) {
    return null;
  }

  return (
    <div className="bg-purple-50 rounded-lg border border-purple-200 p-4">
      {/* Header */}
      <div className="mb-4">
        <h4 className="text-md font-semibold text-purple-900">
          🗺️ Nearest Alternative Clinics for Unmatched Clinics
        </h4>
        <p className="text-xs text-gray-600 mt-1">
          Geographic alternatives for {alternativeData.unmatched_clinic_count} unmatched clinic(s) based on proximity
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-white rounded p-3 border border-purple-300">
          <div className="text-2xl font-bold text-purple-600">
            {alternativeData.unmatched_clinic_count}
          </div>
          <div className="text-xs text-gray-600">Unmatched Clinics</div>
        </div>
        <div className="bg-white rounded p-3 border border-purple-300">
          <div className="text-2xl font-bold text-purple-600">
            {alternativeData.alternatives.reduce((sum, alt) => sum + alt.nearest_clinics.length, 0)}
          </div>
          <div className="text-xs text-gray-600">Alternative Suggestions</div>
        </div>
      </div>

      {/* Alternatives by Clinic */}
      {alternativeData.alternatives.map((clinicAlternatives, idx) => (
        <div key={idx} className="mb-4 last:mb-0">
          {/* Unmatched Clinic Header */}
          <div className="bg-orange-100 rounded-t-lg border border-orange-300 p-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-semibold text-gray-900">
                  {clinicAlternatives.base_clinic_name}
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  Postal: {clinicAlternatives.base_clinic_postal}
                </div>
              </div>
              <div className="text-xs bg-orange-200 text-orange-800 px-2 py-1 rounded">
                NOT FOUND
              </div>
            </div>
          </div>

          {/* Nearest Alternatives Table */}
          <div className="bg-white rounded-b-lg border-x border-b border-orange-300 overflow-hidden">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Rank</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Alternative Clinic</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-gray-700">Address</th>
                  <th className="px-3 py-2 text-right text-xs font-semibold text-gray-700">Distance</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-700">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {clinicAlternatives.nearest_clinics.map((alternative, altIdx) => (
                  <tr key={altIdx} className={alternative.is_matched ? 'bg-blue-50' : 'bg-white'}>
                    <td className="px-3 py-2 text-sm text-gray-900">{alternative.rank}</td>
                    <td className="px-3 py-2">
                      <div className="text-sm font-medium text-gray-900">
                        {alternative.clinic_name}
                      </div>
                      <div className="text-xs text-gray-500">
                        Postal: {alternative.postal_code}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-600 max-w-xs truncate" title={alternative.address}>
                      {alternative.address}
                    </td>
                    <td className="px-3 py-2 text-sm text-right">
                      <span className="font-medium text-purple-700">
                        {alternative.distance_km} km
                      </span>
                    </td>
                    <td className="px-3 py-2 text-center">
                      {alternative.is_matched ? (
                        <div>
                          <span className="inline-block px-2 py-1 rounded-full text-xs font-medium bg-blue-200 text-blue-800 mb-1">
                            ✓ Matched
                          </span>
                          <div className="text-xs text-gray-600">
                            → {alternative.matched_to}
                          </div>
                        </div>
                      ) : (
                        <span className="inline-block px-2 py-1 rounded-full text-xs font-medium bg-gray-200 text-gray-700">
                          Available
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      {/* Info Note */}
      <div className="mt-4 p-3 bg-purple-100 rounded-lg border border-purple-200">
        <div className="flex items-start space-x-2">
          <svg className="h-4 w-4 text-purple-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <p className="text-xs text-purple-900">
            Alternatives are sorted by straight-line distance. "Matched" clinics are already serving other locations.
          </p>
        </div>
      </div>
    </div>
  );
};

const ClinicMatcher = () => {
  const [baseFile, setBaseFile] = useState(null);
  const [comparisonFile, setComparisonFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [excludePolyclinics, setExcludePolyclinics] = useState(false);
  const [excludeHospitals, setExcludeHospitals] = useState(false);
  const [generateReport, setGenerateReport] = useState(false);
  const [topNFilter, setTopNFilter] = useState(null); // null, 'top10', or 'top20'
  const [findAlternatives, setFindAlternatives] = useState(false); // Find nearest alternatives for unmatched clinics
  const [fileInfo, setFileInfo] = useState({ base: null, comparison: null });

  // Validate and get file info from backend
  const validateFile = async (file, fileType) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      const response = await fetch(`${apiUrl}/validate-clinic-file`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const info = await response.json();
        setFileInfo(prev => ({
          ...prev,
          [fileType]: {
            clinicCount: info.clinic_count,
            hasAddressData: info.has_address_data,
            hasPostalCodes: info.has_postal_codes,
            hasUnitNumbers: info.has_unit_numbers,
            hasVisitCounts: info.has_visit_counts,
            supportsTopN: info.supports_top_n_filter,
            matchingStrategy: info.matching_strategy
          }
        }));
      }
    } catch (err) {
      console.error('File validation error:', err);
    }
  };

  // Base file dropzone
  const onDropBase = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setBaseFile(acceptedFiles[0]);
      setResults(null);
      setError(null);
      validateFile(acceptedFiles[0], 'base');
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
      validateFile(acceptedFiles[0], 'comparison');
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
    formData.append('exclude_polyclinics', excludePolyclinics);
    formData.append('exclude_hospitals', excludeHospitals);
    formData.append('generate_report', generateReport);
    if (topNFilter) {
      formData.append('top_n_filter', topNFilter);
    }
    formData.append('find_alternatives', findAlternatives);

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
    setExcludePolyclinics(false);
    setExcludeHospitals(false);
    setGenerateReport(false);
    setTopNFilter(null);
    setFileInfo({ base: null, comparison: null });
  };

  const downloadUtilisationReport = (filename) => {
    const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5000';
    const downloadUrl = `${apiUrl}/download-match/${filename}`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Instructions Card */}
      <div className="card">
        <h2 className="text-2xl font-bold text-gray-800 mb-4">
          Clinic Name Matcher
        </h2>
        <p className="text-gray-600">
          Upload two Excel files to compare clinic lists. The system will identify matching clinics and those that appear in only one file.
        </p>
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
                        setFileInfo(prev => ({ ...prev, base: null }));
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
                        setFileInfo(prev => ({ ...prev, comparison: null }));
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

        {/* File Validation Info */}
        {(fileInfo.base || fileInfo.comparison) && (
          <div className="mt-6 pt-6 border-t border-gray-200">
            <h4 className="text-sm font-medium text-gray-700 mb-3">File Information</h4>
            <div className={`grid gap-4 ${
              fileInfo.base && fileInfo.comparison
                ? 'grid-cols-1 md:grid-cols-2'
                : 'grid-cols-1'
            }`}>
              {/* Base File Info */}
              {fileInfo.base && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-2">
                    <h5 className="text-sm font-semibold text-blue-900">Base File</h5>
                    <svg className="h-5 w-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-blue-800">Clinics detected:</span>
                      <span className="font-semibold text-blue-900">{fileInfo.base.clinicCount}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-blue-800">Address data:</span>
                      <span className={`font-semibold ${fileInfo.base.hasAddressData ? 'text-green-700' : 'text-orange-700'}`}>
                        {fileInfo.base.hasAddressData ? 'Yes' : 'No'}
                      </span>
                    </div>
                    {fileInfo.base.hasAddressData && (
                      <>
                        <div className="flex justify-between">
                          <span className="text-blue-800">Postal codes:</span>
                          <span className="font-semibold text-blue-900">{fileInfo.base.hasPostalCodes}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-blue-800">Unit numbers:</span>
                          <span className="font-semibold text-blue-900">{fileInfo.base.hasUnitNumbers}%</span>
                        </div>
                      </>
                    )}
                    <div className="flex justify-between">
                      <span className="text-blue-800">Visit counts:</span>
                      <span className={`font-semibold ${fileInfo.base.hasVisitCounts > 0 ? 'text-green-700' : 'text-gray-500'}`}>
                        {fileInfo.base.hasVisitCounts}%
                      </span>
                    </div>
                    <div className="pt-2 border-t border-blue-300">
                      <span className="text-xs text-blue-700 font-medium">Strategy: </span>
                      <span className="text-xs text-blue-900">{fileInfo.base.matchingStrategy}</span>
                    </div>
                    {fileInfo.base.supportsTopN && (
                      <div className="mt-2 pt-2 border-t border-green-300">
                        <div className="flex items-center space-x-1">
                          <svg className="h-4 w-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                          <span className="text-xs text-green-700 font-medium">Top N filter supported</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Comparison File Info */}
              {fileInfo.comparison && (
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-2">
                    <h5 className="text-sm font-semibold text-purple-900">Comparison File</h5>
                    <svg className="h-5 w-5 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-purple-800">Clinics detected:</span>
                      <span className="font-semibold text-purple-900">{fileInfo.comparison.clinicCount}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-purple-800">Address data:</span>
                      <span className={`font-semibold ${fileInfo.comparison.hasAddressData ? 'text-green-700' : 'text-orange-700'}`}>
                        {fileInfo.comparison.hasAddressData ? 'Yes' : 'No'}
                      </span>
                    </div>
                    {fileInfo.comparison.hasAddressData && (
                      <>
                        <div className="flex justify-between">
                          <span className="text-purple-800">Postal codes:</span>
                          <span className="font-semibold text-purple-900">{fileInfo.comparison.hasPostalCodes}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-purple-800">Unit numbers:</span>
                          <span className="font-semibold text-purple-900">{fileInfo.comparison.hasUnitNumbers}%</span>
                        </div>
                      </>
                    )}
                    <div className="flex justify-between">
                      <span className="text-purple-800">Visit counts:</span>
                      <span className={`font-semibold ${fileInfo.comparison.hasVisitCounts > 0 ? 'text-green-700' : 'text-gray-500'}`}>
                        {fileInfo.comparison.hasVisitCounts}%
                      </span>
                    </div>
                    <div className="pt-2 border-t border-purple-300">
                      <span className="text-xs text-purple-700 font-medium">Strategy: </span>
                      <span className="text-xs text-purple-900">{fileInfo.comparison.matchingStrategy}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Matching Strategy Info */}
            {(fileInfo.base || fileInfo.comparison) && (
              <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <svg className="h-5 w-5 text-yellow-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-yellow-900">Matching Strategy</p>
                    <p className="text-xs text-yellow-800 mt-1">
                      {(!fileInfo.base?.hasAddressData || !fileInfo.comparison?.hasAddressData) ? (
                        <>
                          <strong>Name-only matching</strong> will be used because one or both files lack address details.
                          The system will match clinics based on exact clinic name matches only.
                        </>
                      ) : (
                        <>
                          <strong>Enhanced multi-level matching</strong> will be used:
                          <ul className="list-disc ml-4 mt-1 space-y-0.5">
                            <li>Level 1: Exact clinic name match</li>
                            <li>Level 2: Same postal code + unit number</li>
                            <li>Level 3: Same block + unit number (fallback)</li>
                          </ul>
                        </>
                      )}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Filter Options */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Filter Options</h4>
          <div className="space-y-3">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={excludePolyclinics}
                onChange={(e) => setExcludePolyclinics(e.target.checked)}
                disabled={isProcessing}
                className="mt-1"
              />
              <div>
                <span className="font-medium text-gray-800">Exclude Polyclinics</span>
                <p className="text-xs text-gray-500">Filter out all polyclinics from matching</p>
              </div>
            </label>
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={excludeHospitals}
                onChange={(e) => setExcludeHospitals(e.target.checked)}
                disabled={isProcessing}
                className="mt-1"
              />
              <div>
                <span className="font-medium text-gray-800">Exclude Government Hospitals</span>
                <p className="text-xs text-gray-500">Filter out 11 government hospitals (SGH, CGH, NUH, TTSH, etc.)</p>
              </div>
            </label>
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={generateReport}
                onChange={(e) => setGenerateReport(e.target.checked)}
                disabled={isProcessing}
                className="mt-1"
              />
              <div>
                <span className="font-medium text-gray-800">Generate Full Utilisation Report (all clinics)</span>
                <p className="text-xs text-gray-500">Create a summary report with all clinic names, visit counts, and total paid amounts</p>
                {topNFilter && (
                  <p className="text-xs text-blue-600 mt-1">
                    ℹ️ Note: When using Top N filter, a utilisation report is auto-generated for the top N clinics only
                  </p>
                )}
              </div>
            </label>
          </div>
        </div>

        {/* Top Clinic Matching Options */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Top Clinic Matching</h4>
          <p className="text-xs text-gray-500 mb-3">
            Select top N most visited clinics from base file for matching (filters applied first, then top N selected)
          </p>

          {/* Warning if base file doesn't support Top N */}
          {fileInfo.base && !fileInfo.base.supportsTopN && (
            <div className="mb-3 bg-orange-50 border border-orange-200 rounded-lg p-3">
              <div className="flex items-start space-x-2">
                <svg className="h-5 w-5 text-orange-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <div className="flex-1">
                  <p className="text-sm font-medium text-orange-900">Top N filter not available</p>
                  <p className="text-xs text-orange-800 mt-1">
                    Base file has insufficient visit count data ({fileInfo.base.hasVisitCounts}% of clinics).
                    Need at least 50% to enable Top N filtering.
                    {fileInfo.base.hasVisitCounts === 0 && " Upload a file with visit counts or transaction-level data (e.g., GP utilisation files)."}
                  </p>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-3">
            <label className={`flex items-start gap-3 ${(!fileInfo.base?.supportsTopN || isProcessing || topNFilter === 'top20') ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}>
              <input
                type="checkbox"
                checked={topNFilter === 'top10'}
                onChange={(e) => setTopNFilter(e.target.checked ? 'top10' : null)}
                disabled={!fileInfo.base?.supportsTopN || isProcessing || topNFilter === 'top20'}
                className="mt-1"
              />
              <div>
                <span className="font-medium text-gray-800">Top 10 Clinics</span>
                <p className="text-xs text-gray-500">Match only the top 10 most visited clinics from base file</p>
              </div>
            </label>
            <label className={`flex items-start gap-3 ${(!fileInfo.base?.supportsTopN || isProcessing || topNFilter === 'top10') ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}>
              <input
                type="checkbox"
                checked={topNFilter === 'top20'}
                onChange={(e) => setTopNFilter(e.target.checked ? 'top20' : null)}
                disabled={!fileInfo.base?.supportsTopN || isProcessing || topNFilter === 'top10'}
                className="mt-1"
              />
              <div>
                <span className="font-medium text-gray-800">Top 20 Clinics</span>
                <p className="text-xs text-gray-500">Match only the top 20 most visited clinics from base file</p>
              </div>
            </label>

            {/* Find Alternatives Option - Available for all unmatched clinics */}
            <label className={`flex items-start gap-3 border-t border-gray-200 pt-3 mt-3 ${isProcessing ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}>
              <input
                type="checkbox"
                checked={findAlternatives}
                onChange={(e) => setFindAlternatives(e.target.checked)}
                disabled={isProcessing}
                className="mt-1"
              />
              <div>
                <span className="font-medium text-gray-800">Find Nearest Alternatives</span>
                <p className="text-xs text-gray-500">
                  {topNFilter
                    ? `For unmatched top ${topNFilter === 'top10' ? '10' : '20'} clinics, find 5 nearest alternatives from comparison file based on geographic distance`
                    : 'For all unmatched clinics, find 5 nearest alternatives from comparison file based on geographic distance'
                  }
                </p>
                <p className="text-xs text-blue-600 mt-1">
                  {topNFilter
                    ? '⚡ Adds ~25s processing time for geocoding'
                    : '⚡ Processing time depends on number of unmatched clinics (may take longer for many clinics)'
                  }
                </p>
              </div>
            </label>
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

            {/* SECTION 1: ALL CLINICS ANALYSIS */}
            <div className="mb-6">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                <h4 className="text-md font-semibold text-blue-900 mb-1">
                  📊 All Clinics Matching Results
                </h4>
                <p className="text-xs text-blue-700">
                  Complete analysis of all {results.base_total} base clinics matched against {results.comparison_total} comparison clinics
                </p>
              </div>

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

            {/* Match Type Breakdown - Show enhanced matching statistics */}
            {results.match_breakdown && (
              <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="mb-3">
                  <p className="text-sm font-semibold text-blue-900">Match Type Breakdown</p>
                  <p className="text-xs text-gray-600 mt-1">
                    How clinics were matched (name, postal code, or address)
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {/* Exact Name Matches */}
                  <div className="bg-white rounded-lg p-4 border border-emerald-300">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="text-2xl font-bold text-emerald-600">
                          {results.match_breakdown.exact_name}
                        </div>
                        <div className="text-sm text-gray-700 font-medium mt-1">Exact Name Match</div>
                      </div>
                      <div className="flex-shrink-0">
                        <svg className="h-6 w-6 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                    </div>
                    <div className="text-xs text-gray-500 mb-2">
                      Clinic names matched exactly
                    </div>
                    <div className="pt-2 border-t border-emerald-200">
                      <div className="flex items-baseline justify-between">
                        <span className="text-lg font-semibold text-emerald-700">
                          {results.match_breakdown_percentages?.exact_name || '0%'}
                        </span>
                        <span className="text-xs text-gray-500">of all matches</span>
                      </div>
                    </div>
                  </div>

                  {/* Postal + Unit Matches */}
                  <div className="bg-white rounded-lg p-4 border border-blue-300">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="text-2xl font-bold text-blue-600">
                          {results.match_breakdown.postal_unit}
                        </div>
                        <div className="text-sm text-gray-700 font-medium mt-1">Postal + Unit Match</div>
                      </div>
                      <div className="flex-shrink-0">
                        <svg className="h-6 w-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                      </div>
                    </div>
                    <div className="text-xs text-gray-500 mb-2">
                      Same postal code & unit number
                    </div>
                    <div className="pt-2 border-t border-blue-200">
                      <div className="flex items-baseline justify-between">
                        <span className="text-lg font-semibold text-blue-700">
                          {results.match_breakdown_percentages?.postal_unit || '0%'}
                        </span>
                        <span className="text-xs text-gray-500">of all matches</span>
                      </div>
                    </div>
                    {results.match_breakdown.postal_unit > 0 && (
                      <div className="mt-2 pt-2 border-t border-blue-100">
                        <div className="flex items-start space-x-1">
                          <svg className="h-3 w-3 text-blue-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                          </svg>
                          <p className="text-xs text-blue-700">
                            Clinics with different names but same location
                          </p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Block + Unit Matches */}
                  <div className="bg-white rounded-lg p-4 border border-indigo-300">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="text-2xl font-bold text-indigo-600">
                          {results.match_breakdown.block_unit}
                        </div>
                        <div className="text-sm text-gray-700 font-medium mt-1">Block + Unit Match</div>
                      </div>
                      <div className="flex-shrink-0">
                        <svg className="h-6 w-6 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                      </div>
                    </div>
                    <div className="text-xs text-gray-500 mb-2">
                      Same block & unit number (fallback)
                    </div>
                    <div className="pt-2 border-t border-indigo-200">
                      <div className="flex items-baseline justify-between">
                        <span className="text-lg font-semibold text-indigo-700">
                          {results.match_breakdown_percentages?.block_unit || '0%'}
                        </span>
                        <span className="text-xs text-gray-500">of all matches</span>
                      </div>
                    </div>
                    {results.match_breakdown.block_unit > 0 && (
                      <div className="mt-2 pt-2 border-t border-indigo-100">
                        <div className="flex items-start space-x-1">
                          <svg className="h-3 w-3 text-indigo-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                          </svg>
                          <p className="text-xs text-indigo-700">
                            Used when postal code unavailable
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Summary insight */}
                {results.match_breakdown.postal_unit > 0 && (
                  <div className="mt-3 p-3 bg-white rounded-lg border border-blue-200">
                    <div className="flex items-start space-x-2">
                      <svg className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                      </svg>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-blue-900">Enhanced Matching Enabled</p>
                        <p className="text-xs text-gray-600 mt-1">
                          Found {results.match_breakdown.postal_unit} additional matches using postal code and address matching.
                          These clinics might have different names but are at the same physical location.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
            </div>
            {/* End of All Clinics Analysis section */}

            {/* SECTION 2: TOP N ANALYSIS (NEW) */}
            {results.top_n_enabled && results.top_n_details && (
              <div className="mb-6 border-t-2 border-gray-300 pt-6">
                <TopNAnalysis
                  topNData={results.top_n_details}
                  filterType={results.top_n_filter_type}
                  reportFilename={results.utilisation_report_filename}
                  onDownloadReport={downloadUtilisationReport}
                />
                {results.top_n_warning && (
                  <div className="mt-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                    <p className="text-xs text-yellow-800">⚠️ {results.top_n_warning}</p>
                  </div>
                )}
              </div>
            )}

            {/* SECTION 3: ALTERNATIVE NEAREST CLINICS */}
            {results.alternative_nearest_details && results.alternative_nearest_details.alternatives && (
              <div className="mb-6 border-t-2 border-gray-300 pt-6">
                <AlternativeNearestClinics alternativeData={results.alternative_nearest_details} />
              </div>
            )}

            {/* Filter Breakdown - Only show if filters were applied */}
            {(results.base_polyclinics_filtered > 0 || results.base_hospitals_filtered > 0 ||
              results.comparison_polyclinics_filtered > 0 || results.comparison_hospitals_filtered > 0) && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-sm font-medium text-gray-700 mb-2">Filters Applied:</p>
                <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
                  {(results.base_polyclinics_filtered > 0 || results.comparison_polyclinics_filtered > 0) && (
                    <div>
                      <span className="font-medium">Polyclinics excluded:</span> {' '}
                      {results.base_polyclinics_filtered + results.comparison_polyclinics_filtered} total
                      <span className="text-xs block text-gray-500 mt-1">
                        ({results.base_polyclinics_filtered} from base, {results.comparison_polyclinics_filtered} from comparison)
                      </span>
                    </div>
                  )}
                  {(results.base_hospitals_filtered > 0 || results.comparison_hospitals_filtered > 0) && (
                    <div>
                      <span className="font-medium">Gov hospitals excluded:</span> {' '}
                      {results.base_hospitals_filtered + results.comparison_hospitals_filtered} total
                      <span className="text-xs block text-gray-500 mt-1">
                        ({results.base_hospitals_filtered} from base, {results.comparison_hospitals_filtered} from comparison)
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Utilisation Report Section - Only show if NOT using Top N (Top N has its own button) */}
            {results.utilisation_report_filename && !results.top_n_enabled && (
              <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="text-sm font-semibold text-blue-900">Utilisation Report Generated</p>
                    <p className="text-xs text-gray-600 mt-1">
                      File: <span className="font-mono">{results.utilisation_report_filename}</span>
                    </p>
                  </div>
                  <svg className="h-6 w-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                    <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                  </svg>
                </div>

                <div className="grid grid-cols-3 gap-3 mb-3">
                  <div className="bg-white rounded p-3 border border-blue-300">
                    <div className="text-2xl font-bold text-blue-600">{results.clinic_count}</div>
                    <div className="text-xs text-gray-600">Clinics</div>
                  </div>
                  <div className="bg-white rounded p-3 border border-blue-300">
                    <div className="text-2xl font-bold text-blue-600">{results.total_visits.toLocaleString()}</div>
                    <div className="text-xs text-gray-600">Total Visits</div>
                  </div>
                  <div className="bg-white rounded p-3 border border-blue-300">
                    <div className="text-2xl font-bold text-blue-600">${results.total_amount.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                    <div className="text-xs text-gray-600">Total Paid Amount</div>
                  </div>
                </div>

                <button
                  onClick={() => downloadUtilisationReport(results.utilisation_report_filename)}
                  className="w-full px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Download Utilisation Report
                </button>
              </div>
            )}

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
