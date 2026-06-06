/** 里程碑 J：模型付费门面 Mod */

export const MODEL_PAYMENT_BRIDGE_MOD_ID = 'xcagi-model-payment-bridge'

export const LS_MODEL_PAYMENT_MOD_FACADE_ENABLED = 'xcagi_model_payment_mod_facade_enabled'

export function readModelPaymentModFacadeEnabled(): boolean {
  if (typeof localStorage === 'undefined') return false
  try {
    return localStorage.getItem(LS_MODEL_PAYMENT_MOD_FACADE_ENABLED) === '1'
  } catch {
    return false
  }
}

export function setModelPaymentModFacadeEnabled(on: boolean): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(LS_MODEL_PAYMENT_MOD_FACADE_ENABLED, on ? '1' : '0')
  } catch {
    /* ignore */
  }
}
