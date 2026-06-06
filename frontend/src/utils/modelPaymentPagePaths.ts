import {
  MODEL_PAYMENT_BRIDGE_MOD_ID,
  readModelPaymentModFacadeEnabled,
} from '@/constants/modelPaymentMod'

const MOD_PREFIX = `/mod/${MODEL_PAYMENT_BRIDGE_MOD_ID}`

const HOST_PATH_TO_MOD: Record<string, string> = {
  '/model-payment': '/settings',
  '/kitten-finance': '/kitten-finance',
}

const HOST_ROUTE_NAME_TO_MOD: Record<string, string> = {
  'model-payment': '/settings',
  'kitten-finance': '/kitten-finance',
}

export function useModelPaymentModPages(): boolean {
  return readModelPaymentModFacadeEnabled()
}

export function resolveModelPaymentPagePath(hostPath: string): string {
  const raw = hostPath.startsWith('/') ? hostPath : `/${hostPath}`
  const pathOnly = raw.split('?')[0]?.split('#')[0] || raw
  if (pathOnly === '/model-payment') {
    const suffix = raw.slice(pathOnly.length)
    return `/settings${suffix || '?section=model-payment'}`
  }
  if (!useModelPaymentModPages()) return raw
  const seg = HOST_PATH_TO_MOD[pathOnly]
  if (!seg) return raw
  return `${MOD_PREFIX}${seg}${raw.slice(pathOnly.length)}`
}

export function resolveModelPaymentPageRedirectForRouteName(routeName: string): string | null {
  if (routeName === 'model-payment') {
    return '/settings?section=model-payment'
  }
  if (!useModelPaymentModPages()) return null
  const seg = HOST_ROUTE_NAME_TO_MOD[routeName]
  if (!seg) return null
  return `${MOD_PREFIX}${seg}`
}
