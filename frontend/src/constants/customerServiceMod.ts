/** K（客服）：外部/内部客服页桥接 Mod */

export const CUSTOMER_SERVICE_BRIDGE_MOD_ID = 'xcagi-customer-service-bridge'

export const LS_CUSTOMER_SERVICE_MOD_PAGES_ENABLED = 'xcagi_customer_service_mod_pages_enabled'

export function readCustomerServiceModPagesEnabled(): boolean {
  if (typeof localStorage === 'undefined') return false
  try {
    return localStorage.getItem(LS_CUSTOMER_SERVICE_MOD_PAGES_ENABLED) === '1'
  } catch {
    return false
  }
}

export function setCustomerServiceModPagesEnabled(on: boolean): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(LS_CUSTOMER_SERVICE_MOD_PAGES_ENABLED, on ? '1' : '0')
  } catch {
    /* ignore */
  }
}
