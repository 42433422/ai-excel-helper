import api from './index';

export const printApi = {
  getPrinters() {
    return api.get('/api/printers');
  },

  printAllLabels(data = {}) {
    return api.post('/api/print/all_labels', data);
  },

  printLabel(modelNumber, quantity = 1) {
    return api.post('/api/print/label', {
      model_number: modelNumber,
      quantity: quantity
    });
  },

  listLabels() {
    return api.get('/api/print/list_labels');
  },

  downloadLabel(filename) {
    return api.download(`/商标导出/${encodeURIComponent(filename)}`);
  }
};

export default printApi;
