/**
 * 流程全景 / workflow-employee-docs 用的员工 id 分类。
 * 副窗内「微信电话 / 真实电话」两行仅当已加载 Mod 在 manifest 中声明对应 id 时才会出现，
 * 但文档里仍可能包含 wechat_phone / real_phone，故此处保留固定 id 分类。
 */
export const WORKFLOW_DOC_CORE_EMPLOYEE_IDS = [
  'label_print',
  'shipment_mgmt',
  'receipt_confirm',
  'wechat_msg',
] as const

/** 前端写死的 Mod 服务相关行（非 manifest 动态追加），id 与副窗代码一致 */
export const WORKFLOW_DOC_FIXED_MOD_SERVICE_IDS = ['wechat_phone', 'real_phone'] as const

export type WorkflowDocCoreId = (typeof WORKFLOW_DOC_CORE_EMPLOYEE_IDS)[number]
export type WorkflowDocFixedModId = (typeof WORKFLOW_DOC_FIXED_MOD_SERVICE_IDS)[number]

export function isWorkflowDocCoreEmployeeId(id: string): boolean {
  return (WORKFLOW_DOC_CORE_EMPLOYEE_IDS as readonly string[]).includes(id)
}

export function isWorkflowDocFixedModServiceId(id: string): boolean {
  return (WORKFLOW_DOC_FIXED_MOD_SERVICE_IDS as readonly string[]).includes(id)
}
