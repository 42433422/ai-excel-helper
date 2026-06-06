import { api, ApiError } from './core';

export interface DocumentTemplateRow {
  slug: string;
  display_name: string;
  role: string;
  is_default?: boolean;
  sort_order?: number;
  storage_relpath?: string;
  /** 后端 ``document_templates.file_format``：docx | xls | xlsx | xlsm 等 */
  file_format?: string;
}

export async function listDocumentTemplates(role?: string): Promise<{
  success: boolean;
  data?: DocumentTemplateRow[];
  default_id?: string | null;
  message?: string;
}> {
  const params: Record<string, string> = {};
  if (role) params.role = role;
  try {
    return await api.get('/api/document-templates', params);
  } catch (e) {
    // 兼容后端尚未挂载该路由时的冷启动窗口，避免页面初始化直接报错。
    if (e instanceof ApiError && e.status === 404) {
      return {
        success: true,
        data: [],
        default_id: null,
        message: 'document-templates route not ready'
      };
    }
    throw e;
  }
}
