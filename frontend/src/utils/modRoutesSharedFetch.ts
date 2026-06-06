import { apiFetch } from '@/utils/apiBase'

const MOD_ROUTES_TIMEOUT_MS = 25_000
import type { ModRouteApiEntry } from '@/router/registerModRoutes'

/**
 * 合并 ``main.ts`` 预取与 ``modsStore.fetchModRoutes`` 对 ``GET /api/mods/routes`` 的调用，
 * 同一时刻只发一条请求，减轻冷启动时重复打后端。
 */
let inflight: Promise<ModRouteApiEntry[] | null> | null = null

export function fetchModRoutesPayloadShared(): Promise<ModRouteApiEntry[] | null> {
  if (inflight) return inflight
  inflight = (async () => {
    try {
      const response = await apiFetch('/api/mods/routes', {
        timeoutMs: MOD_ROUTES_TIMEOUT_MS,
      })
      if (!response.ok) return null
      const data = await response.json()
      if (data.success && Array.isArray(data.data)) {
        return data.data as ModRouteApiEntry[]
      }
      return null
    } catch (e) {
      if (import.meta.env.DEV) {
        console.warn('[modRoutesShared] /api/mods/routes:', e)
      }
      return null
    }
  })().finally(() => {
    inflight = null
  })
  return inflight
}
