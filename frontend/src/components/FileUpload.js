import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

const FileUpload = ({ onFileUpload, isProcessing, fileQueue = [], onRemoveFile }) => {
  const [isDragActive, setIsDragActive] = useState(false);

  const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
    setIsDragActive(false);

    if (rejectedFiles.length > 0) {
      const error = rejectedFiles[0].errors[0];
      alert(`File rejected: ${error.message}`);
      return;
    }

    if (acceptedFiles.length > 0) {
      // Handle multiple files
      onFileUpload(acceptedFiles);
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
    multiple: true,
    disabled: isProcessing
  });

  return (
    <div className="card">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">
        Upload Excel Files
      </h2>
      <p className="text-gray-600 mb-6">
        Upload one or more Excel files to transform them into the desired template format.
      </p>
      
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
                Drag & drop your Excel files here
              </p>
              <p className="text-sm text-gray-500">
                or <span className="text-blue-600 font-medium">click to browse</span>
              </p>
              <p className="text-xs text-gray-400">
                Supports: .xlsx, .xls files • Multiple files allowed
              </p>
            </div>
          )}
        </div>
      </div>

      {/* File Queue Display */}
      {fileQueue.length > 0 && (
        <div className="mt-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">
            Selected Files ({fileQueue.length})
          </h3>
          <div className="space-y-2">
            {fileQueue.map((fileItem, index) => (
              <div key={index} className="flex items-center justify-between bg-gray-50 p-3 rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 flex items-center justify-center bg-blue-100 rounded">
                    <svg className="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2H4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{fileItem.file.name}</p>
                    <p className="text-xs text-gray-500">
                      {(fileItem.file.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {fileItem.status === 'pending' && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                      Pending
                    </span>
                  )}
                  {fileItem.status === 'processing' && (
                    <div className="flex items-center space-x-2">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        Processing...
                      </span>
                      <div className="w-16 bg-gray-200 rounded-full h-2">
                        <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '50%' }}></div>
                      </div>
                    </div>
                  )}
                  {fileItem.status === 'completed' && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      Completed
                    </span>
                  )}
                  {fileItem.status === 'error' && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                      Error
                    </span>
                  )}
                  {!isProcessing && onRemoveFile && (
                    <button
                      onClick={() => onRemoveFile(index)}
                      className="text-gray-400 hover:text-red-500 transition-colors"
                      title="Remove file"
                    >
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUpload;