import { MODEL_PAYMENT_BRIDGE_MOD_ID, readModelPaymentModFacadeEnabled } from '@/constants/modelPaymentMod'

export function useModelPaymentModFacade(): boolean {
  return readModelPaymentModFacadeEnabled()
}

/** 将 /api/model-payment/... 映射到 Mod 门面或宿主 */
export function resolveModelPaymentApiPath(hostPath: string): string {
  const p = hostPath.startsWith('/') ? hostPath : `/${hostPath}`
  if (!useModelPaymentModFacade()) return p
  const prefix = '/api/model-payment'
  if (p === prefix) return `/api/mod/${MODEL_PAYMENT_BRIDGE_MOD_ID}/model-payment`
  if (p.startsWith(`${prefix}/`)) {
    return `/api/mod/${MODEL_PAYMENT_BRIDGE_MOD_ID}/model-payment${p.slice(prefix.length)}`
  }
  return p
}
