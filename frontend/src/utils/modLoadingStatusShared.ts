import { apiFetch } from '@/utils/apiBase'

const LOADING_STATUS_TIMEOUT_MS = 12_000

export type ModLoadingStatusData = Record<string, unknown>

let inflight: Promise<ModLoadingStatusData | null> | null = null

/**
 * 合并 App 开屏与 modsStore 重试对 GET /api/mods/loading-status 的调用。
 */
export function fetchModLoadingStatusShared(): Promise<ModLoadingStatusData | null> {
  if (inflight) return inflight
  inflight = (async () => {
    try {
      const response = await apiFetch('/api/mods/loading-status', {
        timeoutMs: LOADING_STATUS_TIMEOUT_MS,
      })
      if (!response.ok) return null
      const body = await response.json()
      if (!body?.success || !body?.data) return null
      return body.data as ModLoadingStatusData
    } catch {
      return null
    }
  })().finally(() => {
    inflight = null
  })
  return inflight
}
