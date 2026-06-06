import type { Router, RouteRecordRaw } from 'vue-router';

export type ModRouteApiEntry = { mod_id: string; routes_path: string };

/** 避免 main.ts 首屏失败、initialize 稍后成功时重复 addRoute */
const registeredModIds = new Set<string>();
/** 缺失 bundle 的 mod 仅提示一次，避免 prefetch + initialize 双路径刷屏 */
const missingBundleNotifiedModIds = new Set<string>();

/** 工作流单员工 Mod 等仅占位 routes.js（export default []），无独立页面 */
function isIntentionallyEmptyRoutesModule(m: Record<string, unknown>): boolean {
  const def = m.default;
  if (Array.isArray(def) && def.length === 0) return true;
  const named = m.modRoutes;
  if (Array.isArray(named) && named.length === 0) return true;
  return false;
}

function extractRoutesFromModule(m: Record<string, unknown>): RouteRecordRaw[] {
  const candidates: RouteRecordRaw[][] = [];
  for (const v of Object.values(m)) {
    if (!Array.isArray(v) || v.length === 0) continue;
    const first = v[0] as Record<string, unknown>;
    if (
      first &&
      typeof first.path === 'string' &&
      (typeof first.component === 'function' || typeof first.components === 'object')
    ) {
      candidates.push(v as RouteRecordRaw[]);
    }
  }
  if (!candidates.length) return [];
  // 优先含 children 的父路由（如 approval-hub），避免误选 modMenu 等无 component 的数组
  candidates.sort((a, b) => {
    const aChild = a.some((r) => Array.isArray((r as RouteRecordRaw).children) && (r as RouteRecordRaw).children!.length > 0);
    const bChild = b.some((r) => Array.isArray((r as RouteRecordRaw).children) && (r as RouteRecordRaw).children!.length > 0);
    if (aChild === bChild) return b.length - a.length;
    return aChild ? -1 : 1;
  });
  return candidates[0]!;
}

import { modRouteGlob } from '@/constants/modRouteGlob';

const modRouteLoaders = modRouteGlob;

function findGlobKeyForMod(modId: string): string | undefined {
  const suffix = `/mods/${modId}/frontend/routes.js`;
  const norm = (s: string) => s.replace(/\\/g, '/');
  return Object.keys(modRouteLoaders).find((k) => norm(k).endsWith(suffix));
}

function modIdFromGlobKey(key: string): string | null {
  const norm = key.replace(/\\/g, '/');
  const m = norm.match(/\/mods\/([^/]+)\/frontend\/routes\.js$/);
  return m?.[1] ? m[1] : null;
}

/** 从 Vite glob 预注册全部 Mod 路由（不依赖 /api/mods/routes 返回时机）。 */
export async function registerAllModRoutesFromGlob(router: Router): Promise<void> {
  const entries: ModRouteApiEntry[] = [];
  const seen = new Set<string>();
  for (const key of Object.keys(modRouteLoaders)) {
    const mod_id = modIdFromGlobKey(key);
    if (!mod_id || seen.has(mod_id)) continue;
    seen.add(mod_id);
    entries.push({ mod_id, routes_path: key });
  }
  if (entries.length) {
    await registerModRoutes(router, entries);
  }
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

  let shouldRefreshCurrentRoute = false;

  for (const { mod_id } of entries) {
    if (!mod_id || registeredModIds.has(mod_id)) continue;
    const key = findGlobKeyForMod(mod_id);
    if (!key || !modRouteLoaders[key]) {
      if (import.meta.env.DEV && !missingBundleNotifiedModIds.has(mod_id)) {
        missingBundleNotifiedModIds.add(mod_id);
        console.info(
          `[mods] Skip mod "${mod_id}": no frontend routes bundle (expected mods/${mod_id}/frontend/routes.js)`
        );
      }
      continue;
    }
    try {
      const mod = await modRouteLoaders[key]();
      const routes = extractRoutesFromModule(mod);
      for (const r of routes) {
        router.addRoute(r);
        const current = router.currentRoute.value;
        if (current.matched.length === 0 && router.resolve(current.fullPath).matched.length > 0) {
          shouldRefreshCurrentRoute = true;
        }
      }
      if (routes.length) {
        registeredModIds.add(mod_id);
        console.info(`[mods] Registered ${routes.length} route(s) for "${mod_id}"`);
      } else if (isIntentionallyEmptyRoutesModule(mod)) {
        registeredModIds.add(mod_id);
        if (import.meta.env.DEV && !missingBundleNotifiedModIds.has(mod_id)) {
          missingBundleNotifiedModIds.add(mod_id);
          console.info(`[mods] "${mod_id}" has no frontend routes (placeholder bundle)`);
        }
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
    // 多个 Mod 连续 dynamic import + addRoute 易形成长任务；让出主线程减轻「点不动」感
    await new Promise<void>((r) => window.setTimeout(r, 0));
  }

  if (shouldRefreshCurrentRoute) {
    await router.replace(router.currentRoute.value.fullPath);
  }
}
