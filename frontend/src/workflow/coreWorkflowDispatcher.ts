import type { CoreWorkflowEmployeeId } from '@/constants/coreWorkflowMod'
import { tryPostCoreWorkflowEmployeeRun } from '@/utils/coreWorkflowEmployeeApi'
import type { CoreWorkflowAuditLine, CoreWorkflowTimestampLine } from '@/workflow/coreWorkflowTypes'

export const CORE_WORKFLOW_HOST_EVENTS = {
  labelPrintSignal: 'xcagi:workflow-label-print-signal',
  receiptFeedbackSignal: 'xcagi:workflow-receipt-feedback-signal',
  wechatEnqueue: 'xcagi:wechat-ai-task-enqueue',
  wechatStarPolled: 'xcagi:wechat-star-feed-polled',
} as const

export type CoreWorkflowModRunAction =
  | 'status'
  | 'signal_ack'
  | 'audit_summary'
  | 'feedback_ack'
  | 'enqueue_ack'

/** Mod 已安装时向员工 run 端点投递；失败不阻断宿主事件链 */
export function dispatchCoreWorkflowModRun(
  modInstalled: boolean,
  employeeId: CoreWorkflowEmployeeId,
  payload: Record<string, unknown>,
): void {
  if (!modInstalled) return
  void tryPostCoreWorkflowEmployeeRun(employeeId, payload)
}

export type LabelPrintSignalDetail = {
  at?: number
  line?: string
  model_number?: string
  modelNumber?: string
  quantity?: number
  contactName?: string
}

export type ReceiptFeedbackSignalDetail = {
  at?: number
  line?: string
  contactName?: string
  messageText?: string
  intentLabel?: string
  intentDetail?: string
}

export type WechatStarPolledDetail = {
  at?: number
  intervalMs?: number
  contactCount?: number
  ok?: boolean
}

export function buildLabelPrintHostUpdate(
  detail: LabelPrintSignalDetail,
): { lastLabelPrint: CoreWorkflowTimestampLine } {
  const line = String(detail.line || '').trim() || '标签/打印类消息'
  return { lastLabelPrint: { at: Number(detail.at) || Date.now(), line } }
}

export function buildReceiptFeedbackHostUpdate(detail: ReceiptFeedbackSignalDetail): {
  lastReceiptFeedback: CoreWorkflowAuditLine
  pushTitle: string
  pushDescription: string
} {
  const contact = String(detail.contactName || '星标联系人').trim()
  const msg = String(detail.messageText || '').trim().slice(0, 400)
  const il = String(detail.intentLabel || '').trim()
  const idetail = String(detail.intentDetail || '').trim().slice(0, 240)
  const line = String(detail.line || '').trim() || `${contact}：${msg.slice(0, 80)}`
  const detailParts = [
    `【客户反馈 · 业务进程】联系人：${contact}`,
    il ? `预处理意图：${il}` : '',
    idetail ? `说明：${idetail}` : '',
    msg ? `原文摘要：${msg}` : '',
  ].filter(Boolean)
  return {
    lastReceiptFeedback: {
      at: Number(detail.at) || Date.now(),
      line,
      detail: detailParts.join('\n'),
    },
    pushTitle: '收货确认 · 客户业务进程',
    pushDescription: line.length > 100 ? `${line.slice(0, 100)}…` : line,
  }
}

export function buildWechatMonitorUpdate(detail: WechatStarPolledDetail): {
  monitor: {
    lastPolledAt: number
    pollIntervalMs: number
    starredContactCount?: number
    pollOk?: boolean
  }
} {
  return {
    monitor: {
      lastPolledAt: Number(detail.at) || Date.now(),
      pollIntervalMs: Number(detail.intervalMs) || 60000,
      starredContactCount: typeof detail.contactCount === 'number' ? detail.contactCount : undefined,
      pollOk: detail.ok !== false,
    },
  }
}

export async function runLabelPrintSideEffect(detail: LabelPrintSignalDetail): Promise<void> {
  const modelNumber = String(detail.model_number || detail.modelNumber || '').trim()
  const quantity = Number(detail.quantity) || 1
  if (!modelNumber) return
  try {
    const { printApi } = await import('@/api')
    const res = await printApi.printSingleLabel({ model_number: modelNumber, quantity })
    if (!res?.success) {
      console.warn('[workflow:label_print] 打印返回失败:', res?.message)
    }
  } catch (err) {
    console.warn('[workflow:label_print] 打印异常:', err)
  }
}
