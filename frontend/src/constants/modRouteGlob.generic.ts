type RouteModuleLoader = () => Promise<Record<string, unknown>>

/** generic 发行构建：预打包全部通用 bridge 的 routes.js（与 GENERIC_HOST_MOD_IDS 对齐） */
export const modRouteGlob = {
  ...import.meta.glob('../../../mods/xcagi-planner-bridge/frontend/routes.js'),
  ...import.meta.glob('../../../mods/xcagi-erp-domain-bridge/frontend/routes.js'),
  ...import.meta.glob('../../../mods/xcagi-workflow-visualization-bridge/frontend/routes.js'),
  ...import.meta.glob('../../../mods/xcagi-approval-bridge/frontend/routes.js'),
  ...import.meta.glob('../../../mods/xcagi-lan-license-bridge/frontend/routes.js'),
  ...import.meta.glob('../../../mods/xcagi-model-payment-bridge/frontend/routes.js'),
  ...import.meta.glob('../../../mods/xcagi-neuro-bus-bridge/frontend/routes.js'),
  ...import.meta.glob('../../../mods/xcagi-office-employee-pack-bridge/frontend/routes.js'),
  ...import.meta.glob('../../../mods/xcagi-customer-service-bridge/frontend/routes.js'),
} as Record<string, RouteModuleLoader>
