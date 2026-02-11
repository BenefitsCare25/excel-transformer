import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
const UPLOAD_TIMEOUT = parseInt(process.env.REACT_APP_UPLOAD_TIMEOUT) || 300000; // 5 minutes default

class ApiService {
  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      timeout: UPLOAD_TIMEOUT,
    });
  }

  async uploadFile(file, useGoogleMapsApi = true) {
    const formData = new FormData();
    formData.append('file', file);

    // Add geocoding preference to form data
    formData.append('use_google_api', useGoogleMapsApi ? 'true' : 'false');

    try {
      const response = await this.api.post('/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          // Upload progress tracking (can be used for UI progress bars)
          console.log(`Upload progress: ${Math.round((progressEvent.loaded * 100) / progressEvent.total)}%`);
        },
      });

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Upload failed',
        details: error.response?.data?.details || error.message,
      };
    }
  }

  async uploadBatch(files, useGoogleMapsApi = true) {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });

    // Add geocoding preference to form data
    formData.append('use_google_api', useGoogleMapsApi ? 'true' : 'false');

    try {
      const response = await this.api.post('/upload/batch', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 600000, // 10 minutes for batch processing
        onUploadProgress: (progressEvent) => {
          // Batch upload progress tracking
          console.log(`Batch upload progress: ${Math.round((progressEvent.loaded * 100) / progressEvent.total)}%`);
        },
      });

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Batch upload failed',
        details: error.response?.data?.details || error.message,
      };
    }
  }

  async downloadFile(jobId, filename = null) {
    try {
      // Use specific file endpoint if filename provided, otherwise use legacy endpoint
      const endpoint = filename ? `/download/${jobId}/${filename}` : `/download/${jobId}`;

      const response = await this.api.get(endpoint, {
        responseType: 'blob',
      });

      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      // Get filename from response headers or use default
      const contentDisposition = response.headers['content-disposition'];
      let downloadFilename = filename ? `transformed_${filename}` : 'transformed_template.xlsx';

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          downloadFilename = filenameMatch[1];
        }
      }

      link.setAttribute('download', downloadFilename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Download failed',
      };
    }
  }

  async downloadAllFiles(jobId) {
    try {
      const response = await this.api.get(`/download/${jobId}`, {
        responseType: 'blob',
      });

      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      // Get filename from response headers or use default
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'transformed_templates.zip';

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Download failed',
      };
    }
  }

  async getJobStatus(jobId) {
    try {
      const response = await this.api.get(`/status/${jobId}`);
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Status check failed',
      };
    }
  }

  async getBatchStatus(batchId) {
    try {
      const response = await this.api.get(`/batch/status/${batchId}`);
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Batch status check failed',
      };
    }
  }

  async downloadBatch(batchId) {
    try {
      const response = await this.api.get(`/batch/download/${batchId}`, {
        responseType: 'blob',
      });

      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      // Get filename from response headers or use default
      const contentDisposition = response.headers['content-disposition'];
      let filename = `batch_${batchId}_results.zip`;

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Batch download failed',
      };
    }
  }

  async healthCheck() {
    try {
      const response = await this.api.get('/health');
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        error: 'Backend server is not available',
      };
    }
  }

  // Mediacorp ADC Processor API functions
  async processMCFiles(files) {
    const formData = new FormData();
    formData.append('new_el', files.new_el);
    formData.append('old_el', files.old_el);
    formData.append('new_dl', files.new_dl);
    formData.append('old_dl', files.old_dl);

    try {
      const response = await this.api.post('/api/mc/process', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minutes for processing
      });

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Processing failed',
        details: error.response?.data?.details || error.message,
      };
    }
  }

  async downloadMCFile(filename) {
    try {
      const response = await this.api.get(`/api/mc/download/${filename}`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Download failed',
      };
    }
  }

  async mcHealthCheck() {
    try {
      const response = await this.api.get('/api/mc/health');
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        error: 'Mediacorp ADC service is not available',
      };
    }
  }

  // GP Panel Comparison API functions
  async compareGPPanels(previousFile, currentFile) {
    const formData = new FormData();
    formData.append('previous', previousFile);
    formData.append('current', currentFile);

    try {
      const response = await this.api.post('/api/gp-panel/compare', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minutes for processing
      });

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Comparison failed',
        details: error.response?.data?.details || error.message,
      };
    }
  }

  async downloadGPPanelReport(filename) {
    try {
      const response = await this.api.get(`/api/gp-panel/download/${filename}`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Download failed',
      };
    }
  }

  // Renewal Comparison API functions
  async processRenewalComparison(file1, file2, proRataDivisor = 2) {
    const formData = new FormData();
    formData.append('file_1', file1);
    formData.append('file_2', file2);
    formData.append('pro_rata_divisor', proRataDivisor);

    try {
      const response = await this.api.post('/api/renewal/compare', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000,
      });

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Comparison failed',
        details: error.response?.data?.details || error.message,
      };
    }
  }

  async downloadRenewalReport(filename) {
    try {
      const response = await this.api.get(`/api/renewal/download/${filename}`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Download failed',
      };
    }
  }

  async gpPanelHealthCheck() {
    try {
      const response = await this.api.get('/api/gp-panel/health');
      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        error: 'GP Panel service is not available',
      };
    }
  }
}

const apiServiceInstance = new ApiService();
export default apiServiceInstance;