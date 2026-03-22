import { api } from './index';
import type { ApiResponse } from '@/types/api';

export const ocrApi = {
  recognizeText(data: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/ocr/recognize', data);
  },

  extractStructured(data: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/ocr/extract', data);
  },

  analyzeText(data: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/ocr/analyze', data);
  },

  recognizeAndExtract(data: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/ocr/recognize-and-extract', data);
  }
};

export default ocrApi;
