import {
  CUSTOMER_SERVICE_BRIDGE_MOD_ID,
  readCustomerServiceModPagesEnabled,
} from '@/constants/customerServiceMod'

const MOD_PREFIX = `/mod/${CUSTOMER_SERVICE_BRIDGE_MOD_ID}`

const HOST_PATH_TO_MOD: Record<string, string> = {
  '/enterprise-customer-service': '/enterprise-customer-service',
  '/internal-customer-service': '/internal-customer-service',
}

const HOST_ROUTE_NAME_TO_MOD: Record<string, string> = {
  'enterprise-customer-service': '/enterprise-customer-service',
  'internal-customer-service': '/internal-customer-service',
}

export function useCustomerServiceModPages(): boolean {
  return readCustomerServiceModPagesEnabled()
}

export function resolveCustomerServicePagePath(hostPath: string): string {
  const raw = hostPath.startsWith('/') ? hostPath : `/${hostPath}`
  const pathOnly = raw.split('?')[0]?.split('#')[0] || raw
  if (!useCustomerServiceModPages()) return raw
  const seg = HOST_PATH_TO_MOD[pathOnly]
  if (!seg) return raw
  return `${MOD_PREFIX}${seg}${raw.slice(pathOnly.length)}`
}

export function resolveCustomerServicePageRedirectForRouteName(routeName: string): string | null {
  if (!useCustomerServiceModPages()) return null
  const seg = HOST_ROUTE_NAME_TO_MOD[routeName]
  if (!seg) return null
  return `${MOD_PREFIX}${seg}`
}

/** Mod 客服路径 → 宿主路径（路由尚未注册时的回退） */
export function customerServiceHostPathFromModPath(modPath: string): string | null {
  const pathOnly = String(modPath || '').split('?')[0]?.split('#')[0] || ''
  if (pathOnly.startsWith(`${MOD_PREFIX}/enterprise-customer-service`)) {
    return '/enterprise-customer-service'
  }
  if (pathOnly.startsWith(`${MOD_PREFIX}/internal-customer-service`)) {
    return '/internal-customer-service'
  }
  return null
}
