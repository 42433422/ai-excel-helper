import { api } from './core';
import type { ApiResponse } from '@/types/api';

export interface SalesContractProduct {
  model_number: string;
  name: string;
  spec: string;
  unit: string;
  quantity: string;
  unit_price: string;
  amount: string;
}

export interface SalesContractGenerateRequest {
  customer_name: string;
  customer_phone?: string;
  contract_date?: string;
  products: SalesContractProduct[];
  return_buckets_expected?: number;
  return_buckets_actual?: number;
  /** 内部模板 id，见 listTemplates() */
  template_id?: string;
}

export interface SalesContractTemplateOption {
  id: string;
  label: string;
  path?: string;
}

export interface SalesContractGenerateResponse {
  success: boolean;
  data?: {
    contract_id: string;
    filename: string;
    file_path: string;
    customer_name: string;
    contract_date: string;
    products: SalesContractProduct[];
    total_quantity: number;
    total_amount: number;
  };
  message?: string;
  error?: string;
}

export interface SalesContractPrintRequest {
  filename: string;
  printer_name?: string;
}

/** 与 FHD ``POST /api/sales-contract/resolve-from-text`` 一致：LLM 抽取 + 主数据对齐 */
export interface SalesContractResolveFromTextResponse {
  success: boolean;
  message?: string;
  data?: {
    customer_name: string;
    products: SalesContractProduct[];
  } | null;
}

export const salesContractApi = {
  listTemplates(): Promise<{
    success: boolean;
    data?: SalesContractTemplateOption[];
    default_id?: string | null;
    message?: string;
  }> {
    return api.get('/api/sales-contract/templates');
  },

  /** 与生成同源：解析当前所选模板（``template_id`` slug）首表表头与示例行；一级读锁下须配置读令牌。 */
  /** 整句订货话术 → 客户名 + 产品行（与 Planner / bridge 同源）；一级读锁下须带读令牌。 */
  resolveFromText(body: { text: string }): Promise<SalesContractResolveFromTextResponse> {
    return api.post<SalesContractResolveFromTextResponse>('/api/sales-contract/resolve-from-text', body);
  },

  getTemplatePreview(params: Record<string, unknown> = {}): Promise<{
    success: boolean;
    message?: string;
    template_hint?: string;
    headers?: string[];
    sample_rows?: Record<string, unknown>[];
    sheet_name?: string;
  }> {
    return api.get('/api/sales-contract/template-preview', params);
  },

  /** 与后端 JSON 一致：顶层 ``success`` / ``data`` / ``message`` / ``error`` */
  generate(data: SalesContractGenerateRequest): Promise<SalesContractGenerateResponse> {
    return api.post<SalesContractGenerateResponse>('/api/sales-contract/generate', data);
  },

  /**
   * 按当前表格行重新写 Excel（与生成同源版式），返回新 ``file_path`` / ``filename`` 供下载。
   * 编辑预览表后应调用，避免仍指向首次生成时的旧文件。
   */
  previewUpdate(body: {
    products: SalesContractProduct[];
    customer_name?: string;
    contract_date?: string;
  }): Promise<{
    success: boolean;
    message?: string;
    file_path?: string;
    filepath?: string;
    filename?: string;
    products?: SalesContractProduct[];
    [k: string]: unknown;
  }> {
    return api.post('/api/sales-contract/preview-update', body);
  },

  print(data: SalesContractPrintRequest): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/sales-contract/print', data);
  },

  download(filename: string): string {
    return `/api/sales-contract/download/${encodeURIComponent(filename)}`;
  },

  list(): Promise<ApiResponse<{ files: Array<{ filename: string; size: number; modified: number }> }>> {
    return api.get<ApiResponse<{ files: Array<{ filename: string; size: number; modified: number }> }>>('/api/sales-contract/list');
  },

  preview(filename?: string): Promise<ApiResponse<any>> {
    if (filename) {
      return api.get<ApiResponse<any>>(`/api/sales-contract/preview/${encodeURIComponent(filename)}`);
    }
    return api.get<ApiResponse<any>>('/api/sales-contract/preview/default');
  },

  previewDefault(): Promise<ApiResponse<{
    customer_name: string;
    contract_date: string;
    products: SalesContractProduct[];
    total_quantity: number;
    total_amount: number;
    return_buckets_expected: number;
    return_buckets_actual: number;
    signatures: Record<string, string>;
  }>> {
    return api.get<ApiResponse<any>>('/api/sales-contract/preview/default');
  }
};

export default salesContractApi;