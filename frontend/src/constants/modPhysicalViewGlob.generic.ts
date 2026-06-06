type ViewLoader = () => Promise<{ default: unknown }>

/** generic 发行构建：与 GENERIC_HOST_MOD_IDS / modRouteGlob.generic 对齐的 Mod 物理视图 */
export const modPhysicalViewGlob = {
  ...import.meta.glob('../../../mods/xcagi-planner-bridge/frontend/views/**/*.vue'),
  ...import.meta.glob('../../../mods/xcagi-erp-domain-bridge/frontend/views/**/*.vue'),
  ...import.meta.glob('../../../mods/xcagi-workflow-visualization-bridge/frontend/views/**/*.vue'),
  ...import.meta.glob('../../../mods/xcagi-approval-bridge/frontend/views/**/*.vue'),
  ...import.meta.glob('../../../mods/xcagi-lan-license-bridge/frontend/views/**/*.vue'),
  ...import.meta.glob('../../../mods/xcagi-model-payment-bridge/frontend/views/**/*.vue'),
  ...import.meta.glob('../../../mods/xcagi-neuro-bus-bridge/frontend/views/**/*.vue'),
  ...import.meta.glob('../../../mods/xcagi-office-employee-pack-bridge/frontend/views/**/*.vue'),
  ...import.meta.glob('../../../mods/xcagi-customer-service-bridge/frontend/views/**/*.vue'),
} as Record<string, ViewLoader>
