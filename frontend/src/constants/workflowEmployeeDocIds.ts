/**
 * 流程全景文案中的员工 id 分类（角标展示）。
 * 静态 JSON 已清空；合并 manifest 时由 buildSynthetic* 标为 mod_extension。
 */
import { WORKFLOW_EMPLOYEE_IDS } from '@/constants/workflowEmployeeMods'

export const WORKFLOW_DOC_CORE_EMPLOYEE_IDS = WORKFLOW_EMPLOYEE_IDS.slice(0, 4)

export const WORKFLOW_DOC_FIXED_MOD_SERVICE_IDS = WORKFLOW_EMPLOYEE_IDS.slice(4)

export type WorkflowDocCoreId = (typeof WORKFLOW_DOC_CORE_EMPLOYEE_IDS)[number]
export type WorkflowDocFixedModId = (typeof WORKFLOW_DOC_FIXED_MOD_SERVICE_IDS)[number]

export function isWorkflowDocCoreEmployeeId(id: string): boolean {
  return (WORKFLOW_DOC_CORE_EMPLOYEE_IDS as readonly string[]).includes(id)
}

export function isWorkflowDocFixedModServiceId(id: string): boolean {
  return (WORKFLOW_DOC_FIXED_MOD_SERVICE_IDS as readonly string[]).includes(id)
}
