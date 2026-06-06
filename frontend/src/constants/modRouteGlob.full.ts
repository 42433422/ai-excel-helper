type RouteModuleLoader = () => Promise<Record<string, unknown>>

export const modRouteGlob = import.meta.glob('../../../mods/*/frontend/routes.js') as Record<
  string,
  RouteModuleLoader
>
