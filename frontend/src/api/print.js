import api from './index';

export const printApi = {
  getPrinters() {
    return api.get('/api/print/printers');
  },

  getDefaultPrinter() {
    return api.get('/api/print/default');
  },

  printDocument(data) {
    return api.post('/api/print/document', data);
  },

  printLabel(data) {
    return api.post('/api/print/label', data);
  },

  validatePrinters() {
    return api.get('/api/print/validate');
  },

  getDocumentPrinter() {
    return api.get('/api/print/document-printer');
  },

  getLabelPrinter() {
    return api.get('/api/print/label-printer');
  }
};

export default printApi;
