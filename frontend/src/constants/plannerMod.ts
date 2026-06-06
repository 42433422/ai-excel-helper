/** 3d：Planner 对话门面 Mod（房子） */

export const PLANNER_FACADE_MOD_ID = 'xcagi-planner-bridge'

export const LS_PLANNER_MOD_FACADE_ENABLED = 'xcagi_planner_mod_facade_enabled'

export function readPlannerModFacadeEnabled(): boolean {
  if (typeof localStorage === 'undefined') return false
  try {
    return localStorage.getItem(LS_PLANNER_MOD_FACADE_ENABLED) === '1'
  } catch {
    return false
  }
}

export function setPlannerModFacadeEnabled(on: boolean): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(LS_PLANNER_MOD_FACADE_ENABLED, on ? '1' : '0')
  } catch {
    /* ignore */
  }
}
