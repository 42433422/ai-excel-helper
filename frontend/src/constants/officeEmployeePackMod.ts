/** 办公 employee_pack 桥接 Mod 业务页 */

export const OFFICE_EMPLOYEE_PACK_BRIDGE_MOD_ID = 'xcagi-office-employee-pack-bridge'

export const LS_OFFICE_EMPLOYEE_PACK_MOD_PAGES_ENABLED = 'xcagi_office_employee_pack_mod_pages_enabled'

export function readOfficeEmployeePackModPagesEnabled(): boolean {
  if (typeof localStorage === 'undefined') return false
  try {
    return localStorage.getItem(LS_OFFICE_EMPLOYEE_PACK_MOD_PAGES_ENABLED) === '1'
  } catch {
    return false
  }
}

export function setOfficeEmployeePackModPagesEnabled(on: boolean): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(LS_OFFICE_EMPLOYEE_PACK_MOD_PAGES_ENABLED, on ? '1' : '0')
  } catch {
    /* ignore */
  }
}
