import { api } from './index';
import type { ApiResponse } from '@/types/api';

export interface Printer {
  id: number;
  name: string;
  model?: string;
  is_default: boolean;
  status: 'online' | 'offline' | 'error';
  [key: string]: any;
}

export const printApi = {
  getPrinters(): Promise<ApiResponse<Printer[]>> {
    return api.get<ApiResponse<Printer[]>>('/api/printers');
  },

  getDefaultPrinter(): Promise<ApiResponse<Printer>> {
    return api.get<ApiResponse<Printer>>('/api/print/default');
  },

  printDocument(data: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/print/document', data);
  },

  printLabel(data: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/print/label', data);
  },

  listLabels(): Promise<ApiResponse<any[]>> {
    return api.get<ApiResponse<any[]>>('/api/print/list_labels');
  },

  printSingleLabel(data: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/print/single_label', data);
  },

  printByFilename(filename: string): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>(`/api/print/${encodeURIComponent(filename)}`, {});
  },

  validatePrinters(): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>('/api/print/validate');
  },

  getDocumentPrinter(): Promise<ApiResponse<Printer>> {
    return api.get<ApiResponse<Printer>>('/api/print/document-printer');
  },

  getLabelPrinter(): Promise<ApiResponse<Printer>> {
    return api.get<ApiResponse<Printer>>('/api/print/label-printer');
  },

  getPrinterSelection(): Promise<ApiResponse<{ document_printer?: string; label_printer?: string }>> {
    return api.get<ApiResponse<{ document_printer?: string; label_printer?: string }>>('/api/print/printer-selection');
  },

  savePrinterSelection(data: { document_printer?: string; label_printer?: string }): Promise<ApiResponse<any>> {
    return api.put<ApiResponse<any>>('/api/print/printer-selection', data);
  }
};

export default printApi;
