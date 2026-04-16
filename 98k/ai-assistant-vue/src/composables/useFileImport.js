import { ref, reactive } from 'vue';
import api from '../api/index';

export const FILE_TYPES = {
  EXCEL: ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel'],
  CSV: ['text/csv'],
  IMAGE: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
  PDF: ['application/pdf'],
  WORD: ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
};

export const FILE_EXTENSIONS = {
  EXCEL: ['.xlsx', '.xls'],
  CSV: ['.csv'],
  IMAGE: ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
  PDF: ['.pdf'],
  WORD: ['.doc', '.docx']
};

export function useFileImport() {
  const uploading = ref(false);
  const progress = ref(0);
  const progressText = ref('准备上传...');
  const status = reactive({
    show: false,
    type: '',
    message: ''
  });
  const currentFile = ref(null);
  const error = ref(null);

  const API_ENDPOINTS = {
    general: '/api/ai/file/analyze',
    product_import: '/api/ai/file/analyze',
    customers_import: '/api/customers/import',
    order_parse: '/api/ai/file/analyze',
    materials_import: '/api/ai/file/analyze'
  };

  function detectFileType(file) {
    const fileName = file.name.toLowerCase();
    const mimeType = file.type;

    if (FILE_TYPES.EXCEL.includes(mimeType) || FILE_EXTENSIONS.EXCEL.some(ext => fileName.endsWith(ext))) {
      return 'excel';
    }
    if (FILE_TYPES.CSV.includes(mimeType) || FILE_EXTENSIONS.CSV.some(ext => fileName.endsWith(ext))) {
      return 'csv';
    }
    if (FILE_TYPES.IMAGE.includes(mimeType) || FILE_EXTENSIONS.IMAGE.some(ext => fileName.endsWith(ext))) {
      return 'image';
    }
    if (FILE_TYPES.PDF.includes(mimeType) || FILE_EXTENSIONS.PDF.some(ext => fileName.endsWith(ext))) {
      return 'pdf';
    }
    if (FILE_TYPES.WORD.includes(mimeType) || FILE_EXTENSIONS.WORD.some(ext => fileName.endsWith(ext))) {
      return 'word';
    }
    return 'other';
  }

  function resetState() {
    uploading.value = false;
    progress.value = 0;
    progressText.value = '准备上传...';
    status.show = false;
    status.type = '';
    status.message = '';
    currentFile.value = null;
    error.value = null;
  }

  function setStatus(type, message, show = true) {
    status.show = show;
    status.type = type;
    status.message = message;
  }

  function updateProgress(percent, text) {
    progress.value = percent;
    progressText.value = text || `${percent}%`;
  }

  async function uploadFile(file, purpose = 'general', onProgress) {
    if (!file) {
      setStatus('error', '请选择文件');
      return null;
    }

    uploading.value = true;
    currentFile.value = file;
    error.value = null;
    resetState();
    uploading.value = true;

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('purpose', purpose);

      const endpoint = API_ENDPOINTS[purpose] || API_ENDPOINTS.general;

      const response = await api.post(endpoint, formData, {
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            updateProgress(percentCompleted, `上传中：${file.name}`);
            if (onProgress) {
              onProgress(percentCompleted, file.name);
            }
          }
        }
      });

      updateProgress(100, '上传完成');
      
      if (response.success) {
        setStatus('success', response.message || '导入成功');
        return response;
      } else {
        setStatus('error', response.message || '导入失败');
        return null;
      }
    } catch (err) {
      console.error('File upload error:', err);
      const errorMessage = err.message || '网络错误，请检查网络连接';
      setStatus('error', errorMessage);
      error.value = err;
      return null;
    } finally {
      uploading.value = false;
    }
  }

  async function uploadCustomersImport(file, onProgress) {
    return uploadFile(file, 'customers_import', onProgress);
  }

  async function uploadProductImport(file, onProgress) {
    return uploadFile(file, 'product_import', onProgress);
  }

  async function uploadOrderParse(file, onProgress) {
    return uploadFile(file, 'order_parse', onProgress);
  }

  async function uploadMaterialsImport(file, onProgress) {
    return uploadFile(file, 'materials_import', onProgress);
  }

  async function uploadMultipleFiles(files, purpose = 'general', onFileComplete) {
    if (!files || files.length === 0) {
      setStatus('error', '没有可处理的文件');
      return [];
    }

    uploading.value = true;
    error.value = null;
    const results = [];
    const totalFiles = files.length;

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        currentFile.value = file;
        const startPercent = Math.round((i / totalFiles) * 100);
        updateProgress(startPercent, `处理中：${file.name}`);

        const result = await uploadFile(file, purpose);
        results.push({
          file: file.name,
          type: detectFileType(file),
          success: !!result,
          data: result
        });

        if (onFileComplete) {
          onFileComplete(results[results.length - 1], i + 1, totalFiles);
        }
      }

      const successCount = results.filter(r => r.success).length;
      if (successCount === totalFiles) {
        setStatus('success', `已完成 ${totalFiles} 个文件导入`);
      } else if (successCount > 0) {
        setStatus('success', `成功 ${successCount}/${totalFiles} 个文件`);
      } else {
        setStatus('error', '所有文件导入失败');
      }

      updateProgress(100, '全部完成');
      return results;
    } catch (err) {
      console.error('Batch upload error:', err);
      setStatus('error', err.message || '批量上传失败');
      error.value = err;
      return results;
    } finally {
      uploading.value = false;
    }
  }

  return {
    uploading,
    progress,
    progressText,
    status,
    currentFile,
    error,
    detectFileType,
    resetState,
    uploadFile,
    uploadCustomersImport,
    uploadProductImport,
    uploadOrderParse,
    uploadMaterialsImport,
    uploadMultipleFiles
  };
}

export default useFileImport;
