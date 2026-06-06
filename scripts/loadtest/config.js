export const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:5000';
export const THRESHOLDS = {
  p99: 500,
  p95: 200,
  avg: 100,
};
/** 与当前 FastAPI 注册路由对齐（见 app/fastapi_routes/__init__.py、mod_store_routes、health_k8s、legacy_auth）。 */
export const API_PATHS = {
  health: '/api/health',
  products: '/api/mod-store/catalog',
  shipments: '/health/liveness',
  auth: '/api/auth/login',
};
