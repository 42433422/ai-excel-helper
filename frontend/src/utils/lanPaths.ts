import { LAN_BRIDGE_MOD_ID, readLanModFacadeEnabled } from '@/constants/lanMod'

export function useLanModFacade(): boolean {
  return readLanModFacadeEnabled()
}

/** 将 /api/lan/... 映射到 Mod 门面或宿主 */
export function resolveLanApiPath(hostPath: string): string {
  const p = hostPath.startsWith('/') ? hostPath : `/${hostPath}`
  if (!useLanModFacade()) return p
  const prefix = '/api/lan'
  if (p === prefix) return `/api/mod/${LAN_BRIDGE_MOD_ID}/lan`
  if (p.startsWith(`${prefix}/`)) {
    return `/api/mod/${LAN_BRIDGE_MOD_ID}/lan${p.slice(prefix.length)}`
  }
  return p
}
