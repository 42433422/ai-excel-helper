import api, { ApiError } from './index';

function getConfiguredEndpoint(envKey: string, fallbackPath: string): string {
  const configured = String((import.meta as any)?.env?.[envKey] || '').trim();
  return configured || fallbackPath;
}

const TEMPLATE_ENDPOINTS = {
  list: getConfiguredEndpoint('VITE_TEMPLATE_LIST_ENDPOINT', '/api/templates/list'),
  detail: getConfiguredEndpoint('VITE_TEMPLATE_DETAIL_ENDPOINT', '/api/templates/detail'),
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

  listTemplates() {
    return api.get(TEMPLATE_ENDPOINTS.list);
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
