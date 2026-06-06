/** 里程碑 C：通用 ERP 领域门面 Mod */

export const ERP_DOMAIN_BRIDGE_MOD_ID = 'xcagi-erp-domain-bridge'

export const LS_ERP_DOMAIN_MOD_FACADE_ENABLED = 'xcagi_erp_domain_mod_facade_enabled'

/** 受保护客户 Mod：门面未启用时产品/客户 API 可回退到此 Mod */
export const LEGACY_CLIENT_ERP_MOD_ID = 'taiyangniao-pro'

export function readErpDomainModFacadeEnabled(): boolean {
  if (typeof localStorage === 'undefined') return false
  try {
    return localStorage.getItem(LS_ERP_DOMAIN_MOD_FACADE_ENABLED) === '1'
  } catch {
    return false
  }
}

export function setErpDomainModFacadeEnabled(on: boolean): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(LS_ERP_DOMAIN_MOD_FACADE_ENABLED, on ? '1' : '0')
  } catch {
    /* ignore */
  }
}
