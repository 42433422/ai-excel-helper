import { api } from './index';
import type { ApiResponse } from '@/types/api';

export interface ExcelTemplate {
  id: string;
  name: string;
  category: 'label_print' | 'excel' | string;
  template_type: string;
  file_path: string;
  is_active: boolean;
  preview_capable: boolean;
  source: 'db' | 'file' | string;
  exists?: boolean;
  filename?: string;
  template_name?: string;
  [key: string]: any;
}

function normalizeTemplateDto(tpl: any = {}): ExcelTemplate {
  const templateType = String(tpl.template_type || '');
  const inferCategory =
    /(标签|label|print|打印)/i.test(templateType) ? 'label_print' : 'excel';
  const filePath = tpl.file_path || tpl.path || '';
  return {
    ...tpl,
    id: String(tpl.id ?? ''),
    name: tpl.name || tpl.template_name || tpl.filename || '未命名模板',
    category: tpl.category || inferCategory,
    template_type: tpl.template_type || '',
    file_path: filePath,
    is_active: Boolean(tpl.is_active ?? true),
    preview_capable: Boolean(tpl.preview_capable ?? (tpl.exists && filePath)),
    source: tpl.source || 'db'
  };
}

export const excelApi = {
  async getTemplates(params: Record<string, any> = {}): Promise<ApiResponse<{ templates: ExcelTemplate[] }>> {
    const res = await api.get<ApiResponse<{ templates: any[] }>>('/api/excel/templates', params);
    const templates = Array.isArray((res.data as any)?.templates) ? (res.data as any).templates : [];
    return {
      ...res,
      data: {
        templates: templates.map(normalizeTemplateDto)
      }
    };
  },

  saveTemplate(data: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/excel/template/save', data);
  },

  decomposeTemplate(data: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/excel/template/decompose', data);
  },

  uploadExcel(formData: FormData): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/excel/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  extractData(data: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/excel/data/extract', data);
  },

  generateExcel(data: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/excel/data/generate', data);
  },

  normalizeTemplateDto
};

export function normalizeTemplateDtoList(items: any[] = []): ExcelTemplate[] {
  return (Array.isArray(items) ? items : []).map(normalizeTemplateDto);
}

export default excelApi;
