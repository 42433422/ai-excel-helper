import type { Router, RouteRecordRaw } from 'vue-router';

export type ModRouteApiEntry = { mod_id: string; routes_path: string };

/** 避免 main.ts 首屏失败、initialize 稍后成功时重复 addRoute */
const registeredModIds = new Set<string>();

function extractRoutesFromModule(m: Record<string, unknown>): RouteRecordRaw[] {
  for (const v of Object.values(m)) {
    if (!Array.isArray(v) || v.length === 0) continue;
    const first = v[0] as Record<string, unknown>;
    if (
      first &&
      typeof first.path === 'string' &&
      (typeof first.component === 'function' || typeof first.components === 'object')
    ) {
      return v as RouteRecordRaw[];
    }
  }
  return [];
}

const modRouteLoaders = import.meta.glob('../../../mods/*/frontend/routes.js') as Record<
  string,
  () => Promise<Record<string, unknown>>
>;

function findGlobKeyForMod(modId: string): string | undefined {
  const suffix = `/mods/${modId}/frontend/routes.js`;
  const norm = (s: string) => s.replace(/\\/g, '/');
  return Object.keys(modRouteLoaders).find((k) => norm(k).endsWith(suffix));
}

/**
 * Registers mod Vue routes (from mods/<id>/frontend/routes.js) on the app router.
 * Must run after router is created and before navigating to mod paths.
 */
export async function registerModRoutes(
  router: Router,
  entries: ModRouteApiEntry[] | undefined | null
): Promise<void> {
  if (!entries?.length) return;

  for (const { mod_id } of entries) {
    if (!mod_id || registeredModIds.has(mod_id)) continue;
    const key = findGlobKeyForMod(mod_id);
    if (!key || !modRouteLoaders[key]) {
      console.warn(`[mods] No routes bundle for mod "${mod_id}" (expected mods/${mod_id}/frontend/routes.js)`);
      continue;
    }
    try {
      const mod = await modRouteLoaders[key]();
      const routes = extractRoutesFromModule(mod);
      for (const r of routes) {
        router.addRoute(r);
      }
      if (routes.length) {
        registeredModIds.add(mod_id);
        console.info(`[mods] Registered ${routes.length} route(s) for "${mod_id}"`);
      } else if (import.meta.env.DEV) {
        console.warn(
          `[mods] No routes extracted from "${mod_id}" bundle — check routes.js exports (named route array).`
        );
      }
    } catch (e) {
      console.error(`[mods] Failed to load routes for "${mod_id}":`, e);
      if (import.meta.env.DEV) {
        console.info(
          '[mods] Hint: after adding mods/*/frontend/routes.js, run `npm run build` (or dev restart) so Vite includes the glob.'
        );
      }
    }
  }
}
