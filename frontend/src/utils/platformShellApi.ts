import { apiFetch, DEFAULT_MOD_API_TIMEOUT_MS } from '@/utils/apiBase'
import type { DeliverableStatus, PlatformShellCapabilities } from '@/constants/platformShell'

let cached: PlatformShellCapabilities | null = null
let deliverableCached: DeliverableStatus | null = null

export async function fetchPlatformShellCapabilities(
  force = false,
): Promise<PlatformShellCapabilities> {
  if (cached && !force) return cached
  const r = await apiFetch('/api/platform-shell/capabilities', {
    timeoutMs: DEFAULT_MOD_API_TIMEOUT_MS,
  })
  if (!r.ok) throw new Error(`platform-shell/capabilities HTTP ${r.status}`)
  const body = await r.json()
  const data = (body?.data || body) as PlatformShellCapabilities
  cached = data
  return data
}

export function isBridgeModInstalled(
  caps: PlatformShellCapabilities,
  modId: string,
): boolean {
  const row = (caps.bridge_mods || []).find((b) => b.mod_id === modId)
  return Boolean(row?.installed)
}

export async function fetchDeliverableStatus(force = false): Promise<DeliverableStatus> {
  if (deliverableCached && !force) return deliverableCached
  const r = await apiFetch('/api/platform-shell/deliverable-status', {
    timeoutMs: DEFAULT_MOD_API_TIMEOUT_MS,
  })
  if (!r.ok) throw new Error(`deliverable-status HTTP ${r.status}`)
  const body = await r.json()
  const data = (body?.data || body) as DeliverableStatus
  deliverableCached = data
  return data
}

export function clearDeliverableStatusCache(): void {
  deliverableCached = null
  cached = null
}
