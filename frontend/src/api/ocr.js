import api from './index';

export const ocrApi = {
  recognizeText(data) {
    return api.post('/api/ocr/recognize', data);
  },

  extractStructured(data) {
    return api.post('/api/ocr/extract', data);
  },

  analyzeText(data) {
    return api.post('/api/ocr/analyze', data);
  },

  recognizeAndExtract(data) {
    return api.post('/api/ocr/recognize-and-extract', data);
  }
};

export default ocrApi;
