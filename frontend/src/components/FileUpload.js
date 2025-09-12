import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

const FileUpload = ({ onFileUpload, isProcessing }) => {
  const [isDragActive, setIsDragActive] = useState(false);

  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
    setIsDragActive(false);
    
    if (rejectedFiles.length > 0) {
      const error = rejectedFiles[0].errors[0];
      alert(`File rejected: ${error.message}`);
      return;
    }
    
    if (acceptedFiles.length > 0) {
      onFileUpload(acceptedFiles[0]);
    }
  }, [onFileUpload]);

  const {
    getRootProps,
    getInputProps,
    isDragActive: dropzoneIsDragActive,
  } = useDropzone({
    onDrop,
    onDragEnter: () => setIsDragActive(true),
    onDragLeave: () => setIsDragActive(false),
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    multiple: false,
    disabled: isProcessing
  });

  return (
    <div className="card">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">
        Upload Excel File
      </h2>
      <p className="text-gray-600 mb-6">
        Upload your Excel file to transform it into the desired template format.
        The system will automatically:
      </p>
      <ul className="text-sm text-gray-600 mb-6 space-y-1">
        <li>• Combine telephone & remarks fields</li>
        <li>• Combine operating hours into consolidated format</li>
        <li>• Extract postal codes from address details</li>
      </ul>
      
      <div
        {...getRootProps()}
        className={`upload-area ${isDragActive || dropzoneIsDragActive ? 'dragover' : ''} ${
          isProcessing ? 'opacity-50 cursor-not-allowed' : ''
        }`}
      >
        <input {...getInputProps()} />
        
        <div className="space-y-4">
          <div className="mx-auto w-16 h-16 text-gray-400">
            <svg
              fill="none"
              stroke="currentColor"
              viewBox="0 0 48 48"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
              />
            </svg>
          </div>
          
          {isProcessing ? (
            <div className="space-y-2">
              <div className="animate-spin mx-auto w-8 h-8 text-blue-600">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
              </div>
              <p className="text-lg font-medium text-gray-700">Processing...</p>
              <p className="text-sm text-gray-500">Please wait while we transform your file</p>
            </div>
          ) : isDragActive || dropzoneIsDragActive ? (
            <div className="space-y-2">
              <p className="text-lg font-medium text-blue-700">Drop the file here</p>
              <p className="text-sm text-blue-600">Release to upload</p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-lg font-medium text-gray-700">
                Drag & drop your Excel file here
              </p>
              <p className="text-sm text-gray-500">
                or <span className="text-blue-600 font-medium">click to browse</span>
              </p>
              <p className="text-xs text-gray-400">
                Supports: .xlsx, .xls files
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FileUpload;