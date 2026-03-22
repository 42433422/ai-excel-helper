// 统一导出所有 API 模块
// 基础 API 类
export { api, ApiError, API_BASE, default as apiDefault } from './core';

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
