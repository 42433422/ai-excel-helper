import { LAN_BRIDGE_MOD_ID, readLanModFacadeEnabled } from '@/constants/lanMod'

const MOD_PREFIX = `/mod/${LAN_BRIDGE_MOD_ID}`

const HOST_PATH_TO_MOD: Record<string, string> = {
  '/lan-gate': '/lan-gate',
}

const HOST_ROUTE_NAME_TO_MOD: Record<string, string> = {
  'lan-gate': '/lan-gate',
}

export function useLanModPages(): boolean {
  return readLanModFacadeEnabled()
}

export function resolveLanPagePath(hostPath: string): string {
  const raw = hostPath.startsWith('/') ? hostPath : `/${hostPath}`
  const pathOnly = raw.split('?')[0]?.split('#')[0] || raw
  if (!useLanModPages()) return raw
  const seg = HOST_PATH_TO_MOD[pathOnly]
  if (!seg) return raw
  return `${MOD_PREFIX}${seg}${raw.slice(pathOnly.length)}`
}

export function resolveLanPageRedirectForRouteName(routeName: string): string | null {
  if (!useLanModPages()) return null
  const seg = HOST_ROUTE_NAME_TO_MOD[routeName]
  if (!seg) return null
  return `${MOD_PREFIX}${seg}`
}
