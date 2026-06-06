import { PLANNER_FACADE_MOD_ID, readPlannerModFacadeEnabled } from '@/constants/plannerMod'

/** 里程碑 B：Planner 工具是否走 Mod 门面（与对话门面同开关） */
export function usePlannerModToolsFacade(): boolean {
  return readPlannerModFacadeEnabled()
}

/** 仅门面开启时返回 Mod 工具清单；否则前端继续用 /api/db-tools 的 planner_tools */
export function resolvePlannerToolsRegistryPath(): string | null {
  if (!usePlannerModToolsFacade()) return null
  return `/api/mod/${PLANNER_FACADE_MOD_ID}/tools/registry`
}

export function resolvePlannerToolsExecutePath(): string {
  if (usePlannerModToolsFacade()) {
    return `/api/mod/${PLANNER_FACADE_MOD_ID}/tools/execute`
  }
  return '/api/tools/execute'
}
