import type { CoreWorkflowEmployeeId } from '@/constants/coreWorkflowMod'

export type WorkflowStepRow = { id: string; label: string; status: 'done' | 'active' | 'pending' }

export type WorkflowMonitorPayload = {
  lastPolledAt: number
  pollIntervalMs: number
  starredContactCount?: number
  pollOk?: boolean
}

export type CoreWorkflowTimestampLine = { at: number; line: string }
export type CoreWorkflowAuditLine = { at: number; line: string; detail?: string }

export type CoreWorkflowEmployeeCtx = {
  lastWechat?: CoreWorkflowTimestampLine
  lastLabelPrint?: CoreWorkflowTimestampLine
  lastShipmentAudit?: CoreWorkflowAuditLine
  lastReceiptFeedback?: CoreWorkflowAuditLine
}

export type CoreWorkflowUpsertOpts = CoreWorkflowEmployeeCtx & {
  monitor?: WorkflowMonitorPayload | null
}

export const CORE_WORKFLOW_PAYLOAD_KEYS: Record<
  CoreWorkflowEmployeeId,
  keyof CoreWorkflowEmployeeCtx
> = {
  wechat_msg: 'lastWechat',
  label_print: 'lastLabelPrint',
  shipment_mgmt: 'lastShipmentAudit',
  receipt_confirm: 'lastReceiptFeedback',
  wechat_phone: 'lastWechat',
  real_phone: 'lastWechat',
}
