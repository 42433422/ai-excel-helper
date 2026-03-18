import api from './index';

export const excelApi = {
  getTemplates(params = {}) {
    return api.get('/api/excel/templates', params);
  },

  saveTemplate(data) {
    return api.post('/api/excel/template/save', data);
  },

  decomposeTemplate(data) {
    return api.post('/api/excel/template/decompose', data);
  },

  uploadExcel(formData) {
    return api.post('/api/excel/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  extractData(data) {
    return api.post('/api/excel/data/extract', data);
  },

  generateExcel(data) {
    return api.post('/api/excel/data/generate', data);
  }
};

export default excelApi;
