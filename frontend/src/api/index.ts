// 统一导出所有 API 模块
import api, { ApiError, API_BASE } from './core';

export { ApiError, API_BASE };
export { api };
export default api;
export const apiDefault = api;

/** 与 `api.get` / `api.post` 等价，供 `import { get, post } from '@/api'` 使用 */
export const get = api.get.bind(api);
export const post = api.post.bind(api);

// 业务 API 模块
export { chatApi } from './chat';
export { productsApi } from './products';
export { customersApi } from './customers';
export { materialsApi } from './materials';
export { ordersApi } from './orders';
export { printApi } from './print';
export { ocrApi } from './ocr';
export { excelApi, normalizeTemplateDtoList } from './excel';
export { wechatApi } from './wechat';
export { mediaApi } from './media';
export { systemApi } from './system';
export { intentPackagesApi } from './intentPackages';
