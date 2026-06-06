import api, { ApiError } from './core';
import type { RequestOptions } from './core';

/**
 * 开发环境下若把 VITE_TEMPLATE_* 配成 http://127.0.0.1:5000/api/... 绝对地址，
 * 用户从局域网 IP 打开前端时，api 封装会跨域直连 5000，预检 Origin（192.168.*）不在白名单则整页 API 全挂。
 * 故在 DEV 且 host 为 localhost/127.0.0.1 时强制改为相对路径，走 Vite 同源代理。
 */
function getConfiguredEndpoint(envKey: string, fallbackPath: string): string {
  const configured = String((import.meta as any)?.env?.[envKey] || '').trim();
  if (!configured) return fallbackPath;
  if (
    import.meta.env.DEV &&
    /^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?\//i.test(configured)
  ) {
    try {
      const u = new URL(configured);
      const path = `${u.pathname}${u.search}`;
      return path || fallbackPath;
    } catch {
      return configured;
    }
  }
  return configured;
}

const TEMPLATE_ENDPOINTS = {
  list: getConfiguredEndpoint('VITE_TEMPLATE_LIST_ENDPOINT', '/api/templates'),
  detail: getConfiguredEndpoint('VITE_TEMPLATE_DETAIL_ENDPOINT', '/api/templates'),
  analyze: getConfiguredEndpoint('VITE_TEMPLATE_ANALYZE_ENDPOINT', '/api/templates/analyze'),
  progress: getConfiguredEndpoint('VITE_TEMPLATE_PROGRESS_ENDPOINT', '/api/templates/progress'),
  create: getConfiguredEndpoint('VITE_TEMPLATE_CREATE_ENDPOINT', '/api/templates/create'),
  update: getConfiguredEndpoint('VITE_TEMPLATE_UPDATE_ENDPOINT', '/api/templates/update'),
  remove: getConfiguredEndpoint('VITE_TEMPLATE_DELETE_ENDPOINT', '/api/templates/delete'),
  extractGrid: getConfiguredEndpoint('VITE_TEMPLATE_EXTRACT_GRID_ENDPOINT', '/api/templates/extract-grid'),
  excelDecompose: getConfiguredEndpoint('VITE_TEMPLATE_DECOMPOSE_ENDPOINT', '/api/excel/template/decompose')
};

function joinPath(base: string, segment: string | number): string {
  const normalizedBase = String(base || '').replace(/\/+$/, '');
  const normalizedSegment = String(segment || '').replace(/^\/+/, '');
  return `${normalizedBase}/${normalizedSegment}`;
}

function wrapServiceAvailabilityError(error: unknown, actionName: string, endpoint: string): never {
  const unavailableStatus = new Set([404, 405, 501]);
  if (error instanceof ApiError && unavailableStatus.has(error.status)) {
    throw new ApiError(`模板${actionName}服务未开放，请检查接口配置：${endpoint}`, error.status, error.data);
  }
  throw error;
}

export const templatePreviewApi = {
  endpoints: TEMPLATE_ENDPOINTS,

  listTemplates(options?: RequestOptions) {
    return api.get(TEMPLATE_ENDPOINTS.list, {}, options || {});
  },

  getTemplateDetail(templateId: string | number) {
    return api.get(joinPath(TEMPLATE_ENDPOINTS.detail, templateId));
  },

  decomposeTemplate(payload: Record<string, any>) {
    return api.post(TEMPLATE_ENDPOINTS.excelDecompose, payload);
  },

  analyzeTemplate(formData: FormData) {
    return api.post(TEMPLATE_ENDPOINTS.analyze, formData);
  },

  getAnalysisProgress(taskId: string | number) {
    return api.get(joinPath(TEMPLATE_ENDPOINTS.progress, taskId));
  },

  async createTemplate(payload: Record<string, any>) {
    try {
      return await api.post(TEMPLATE_ENDPOINTS.create, payload);
    } catch (error) {
      wrapServiceAvailabilityError(error, '创建', TEMPLATE_ENDPOINTS.create);
    }
  },

  async updateTemplate(payload: Record<string, any>) {
    try {
      return await api.post(TEMPLATE_ENDPOINTS.update, payload);
    } catch (error) {
      wrapServiceAvailabilityError(error, '更新', TEMPLATE_ENDPOINTS.update);
    }
  },

  async createTemplateFromGrid(payload: Record<string, any>) {
    try {
      return await api.post(TEMPLATE_ENDPOINTS.create, payload);
    } catch (error) {
      wrapServiceAvailabilityError(error, '创建', TEMPLATE_ENDPOINTS.create);
    }
  },

  async replaceTemplateById(payload: Record<string, any>) {
    try {
      return await api.post(TEMPLATE_ENDPOINTS.update, payload);
    } catch (error) {
      wrapServiceAvailabilityError(error, '替换', TEMPLATE_ENDPOINTS.update);
    }
  },

  deleteTemplate(payload: Record<string, any>) {
    return api.post(TEMPLATE_ENDPOINTS.remove, payload);
  },

  extractGrid(formData: FormData) {
    return api.post(TEMPLATE_ENDPOINTS.extractGrid, formData);
  }
};

export default templatePreviewApi;
