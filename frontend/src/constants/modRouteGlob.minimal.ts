type RouteModuleLoader = () => Promise<Record<string, unknown>>

export const modRouteGlob = {
  ...import.meta.glob('../../../mods/xcagi-planner-bridge/frontend/routes.js'),
  ...import.meta.glob('../../../mods/xcagi-neuro-bus-bridge/frontend/routes.js'),
  ...import.meta.glob('../../../mods/xcagi-office-employee-pack-bridge/frontend/routes.js'),
} as Record<string, RouteModuleLoader>
