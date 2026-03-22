import api from './index';

export const printApi = {
  getPrinters() {
    return api.get('/api/printers');
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

  listLabels() {
    return api.get('/api/print/list_labels');
  },

  printSingleLabel(data) {
    return api.post('/api/print/single_label', data);
  },

  printByFilename(filename) {
    return api.post(`/api/print/${encodeURIComponent(filename)}`, {});
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
