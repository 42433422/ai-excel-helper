/**
 * @deprecated 请改用 workflowEmployeeMods.ts
 * 保留 re-export 以免大范围 import 断裂。
 */
export {
  WORKFLOW_VIZ_BRIDGE_MOD_ID as CORE_WORKFLOW_MOD_ID,
  WORKFLOW_EMPLOYEE_IDS as CORE_WORKFLOW_EMPLOYEE_IDS,
  LS_WORKFLOW_VIZ_MOD_PAGES_ENABLED as LS_CORE_WORKFLOW_MOD_PAGES_ENABLED,
  readWorkflowVizModPagesEnabled as readCoreWorkflowModPagesEnabled,
  setWorkflowVizModPagesEnabled as setCoreWorkflowModPagesEnabled,
  isWorkflowEmployeeId as isCoreWorkflowEmployeeId,
  workflowVizModStatusPath as coreWorkflowModEmployeesPath,
  type WorkflowEmployeeId as CoreWorkflowEmployeeId,
  LEGACY_CORE_WORKFLOW_MOD_ID,
} from '@/constants/workflowEmployeeMods'

export function isCoreWorkflowModInstalled(
  mods: Array<{ id?: string }> | undefined | null,
): boolean {
  if (!mods?.length) return false
  return mods.some((m) => {
    const id = String(m?.id || '').trim()
    return id === 'xcagi-workflow-visualization-bridge' || id === 'xcagi-core-workflow-employees'
  })
}
