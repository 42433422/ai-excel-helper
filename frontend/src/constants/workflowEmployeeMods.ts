/** 商店安装的 6 个独立工作流员工 Mod（与 manifest.workflow_employees[0].id 一致） */
/** 运行时列表优先 GET /api/system/workflow-employee-catalog */

import { workflowEmployeeIds, workflowEmployeeModIds } from '@/stores/hostConfig'

export const WORKFLOW_VIZ_BRIDGE_MOD_ID = 'xcagi-workflow-visualization-bridge'

export const LS_WORKFLOW_VIZ_MOD_PAGES_ENABLED = 'xcagi_workflow_viz_mod_pages_enabled'

/** @deprecated 旧单体包 id，仅迁移提示 */
export const LEGACY_CORE_WORKFLOW_MOD_ID = 'xcagi-core-workflow-employees'

export const WORKFLOW_EMPLOYEE_MOD_IDS = [
  'xcagi-workflow-employee-label-print',
  'xcagi-workflow-employee-shipment-mgmt',
  'xcagi-workflow-employee-receipt-confirm',
  'xcagi-workflow-employee-wechat-msg',
  'xcagi-workflow-employee-wechat-phone',
  'xcagi-workflow-employee-real-phone',
] as const

/** 宿主事件链仍识别的员工 id（与各 Mod manifest 中 id 对齐） */
export const WORKFLOW_EMPLOYEE_IDS = [
  'label_print',
  'shipment_mgmt',
  'receipt_confirm',
  'wechat_msg',
  'wechat_phone',
  'real_phone',
] as const

export type WorkflowEmployeeId = (typeof WORKFLOW_EMPLOYEE_IDS)[number]

export function workflowVizModStatusPath(): string {
  return `/api/mod/${WORKFLOW_VIZ_BRIDGE_MOD_ID}/status`
}

export function readWorkflowVizModPagesEnabled(): boolean {
  if (typeof localStorage === 'undefined') return false
  try {
    return localStorage.getItem(LS_WORKFLOW_VIZ_MOD_PAGES_ENABLED) === '1'
  } catch {
    return false
  }
}

export function setWorkflowVizModPagesEnabled(on: boolean): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(LS_WORKFLOW_VIZ_MOD_PAGES_ENABLED, on ? '1' : '0')
  } catch {
    /* ignore */
  }
}

export function getWorkflowEmployeeModIds(): readonly string[] {
  const api = workflowEmployeeModIds.value
  if (api.length > 0) return api
  return WORKFLOW_EMPLOYEE_MOD_IDS
}

export function getWorkflowEmployeeIds(): readonly string[] {
  const api = workflowEmployeeIds.value
  if (api.length > 0) return api
  return WORKFLOW_EMPLOYEE_IDS
}

export function isWorkflowEmployeeId(id: string): id is WorkflowEmployeeId {
  return (getWorkflowEmployeeIds() as readonly string[]).includes(id)
}
