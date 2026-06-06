/** 里程碑 J：LAN 授权门面 Mod */

export const LAN_BRIDGE_MOD_ID = 'xcagi-lan-license-bridge'

export const LS_LAN_MOD_FACADE_ENABLED = 'xcagi_lan_mod_facade_enabled'

export function readLanModFacadeEnabled(): boolean {
  if (typeof localStorage === 'undefined') return false
  try {
    return localStorage.getItem(LS_LAN_MOD_FACADE_ENABLED) === '1'
  } catch {
    return false
  }
}

export function setLanModFacadeEnabled(on: boolean): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(LS_LAN_MOD_FACADE_ENABLED, on ? '1' : '0')
  } catch {
    /* ignore */
  }
}
