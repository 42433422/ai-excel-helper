import {
  OFFICE_EMPLOYEE_PACK_BRIDGE_MOD_ID,
  readOfficeEmployeePackModPagesEnabled,
} from '@/constants/officeEmployeePackMod'

const MOD_PREFIX = `/mod/${OFFICE_EMPLOYEE_PACK_BRIDGE_MOD_ID}`

const HOST_PATH_TO_MOD: Record<string, string> = {
  '/tools': '/tools',
  '/other-tools': '/other-tools',
}

const HOST_ROUTE_NAME_TO_MOD: Record<string, string> = {
  tools: '/tools',
  'other-tools': '/other-tools',
}

export function useOfficeEmployeePackModPages(): boolean {
  return readOfficeEmployeePackModPagesEnabled()
}

export function resolveOfficeEmployeePagePath(hostPath: string): string {
  const raw = hostPath.startsWith('/') ? hostPath : `/${hostPath}`
  const pathOnly = raw.split('?')[0]?.split('#')[0] || raw
  if (!useOfficeEmployeePackModPages()) return raw
  const seg = HOST_PATH_TO_MOD[pathOnly]
  if (!seg) return raw
  return `${MOD_PREFIX}${seg}${raw.slice(pathOnly.length)}`
}

export function resolveOfficeEmployeePageRedirectForRouteName(routeName: string): string | null {
  if (!useOfficeEmployeePackModPages()) return null
  const seg = HOST_ROUTE_NAME_TO_MOD[routeName]
  if (!seg) return null
  return `${MOD_PREFIX}${seg}`
}
