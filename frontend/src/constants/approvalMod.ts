/** 里程碑 E：审批门面 Mod */

export const APPROVAL_BRIDGE_MOD_ID = 'xcagi-approval-bridge'

export const LS_APPROVAL_MOD_FACADE_ENABLED = 'xcagi_approval_mod_facade_enabled'

export function readApprovalModFacadeEnabled(): boolean {
  if (typeof localStorage === 'undefined') return false
  try {
    return localStorage.getItem(LS_APPROVAL_MOD_FACADE_ENABLED) === '1'
  } catch {
    return false
  }
}

export function setApprovalModFacadeEnabled(on: boolean): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(LS_APPROVAL_MOD_FACADE_ENABLED, on ? '1' : '0')
  } catch {
    /* ignore */
  }
}
