import {
  isCoreWorkflowEmployeeId,
  type CoreWorkflowEmployeeId,
} from '@/constants/coreWorkflowMod'
import {
  formatWorkflowClock,
  formatWorkflowHintTime,
  isProIntentExperienceOn,
  isStarredChatAutoRefreshOn,
} from '@/workflow/coreWorkflowPrefs'
import {
  CORE_WORKFLOW_PAYLOAD_KEYS,
  type CoreWorkflowEmployeeCtx,
  type CoreWorkflowTimestampLine,
  type CoreWorkflowAuditLine,
  type WorkflowMonitorPayload,
  type WorkflowStepRow,
} from '@/workflow/coreWorkflowTypes'

export type { WorkflowMonitorPayload, WorkflowStepRow } from '@/workflow/coreWorkflowTypes'

export function computeWorkflowProgressFromSteps(steps: WorkflowStepRow[]): { pct: number; label: string } {
  if (!steps.length) return { pct: 0, label: '0 / 0 步' }
  const total = steps.length
  const done = steps.filter((s) => s.status === 'done').length
  const hasActive = steps.some((s) => s.status === 'active')
  const visual = done + (hasActive ? 0.5 : 0)
  const pct = Math.min(100, Math.round((visual / total) * 100))
  const label = `${done} / ${total} 步已完成${hasActive ? ' · 1 步进行中' : ''}`
  return { pct, label }
}

export function buildCoreWorkflowMonitorLine(
  empId: CoreWorkflowEmployeeId,
  monitor?: WorkflowMonitorPayload,
  ctx?: CoreWorkflowEmployeeCtx,
): string {
  const lastWechat = ctx?.lastWechat
  const lastLabelPrint = ctx?.lastLabelPrint
  const lastShipmentAudit = ctx?.lastShipmentAudit
  const lastReceiptFeedback = ctx?.lastReceiptFeedback

  if (empId === 'wechat_msg') {
    const refreshOn = isStarredChatAutoRefreshOn()
    if (!refreshOn) {
      return '监控已暂停：未开启「星标聊天自动刷新」，无法定时拉取星标会话。'
    }
    if (monitor?.lastPolledAt) {
      const t = formatWorkflowClock(monitor.lastPolledAt)
      const sec = Math.max(1, Math.round((monitor.pollIntervalMs || 60000) / 1000))
      const n = monitor.starredContactCount
      const cnt = typeof n === 'number' ? `星标联系人 ${n} 位` : '星标联系人'
      const ok = monitor.pollOk !== false ? '拉取通道正常' : '上次拉取失败，将重试'
      const tail = lastWechat
        ? ` · 最近预处理：${formatWorkflowHintTime(lastWechat.at)}`
        : ' · 持续监听新消息'
      return `${ok} · 上次检查 ${t} · 每 ${sec}s 轮询 · ${cnt}${tail}`
    }
    return '监控就绪：等待首次轮询（通常 1 分钟内）…'
  }
  if (empId === 'label_print') {
    const refreshOn = isStarredChatAutoRefreshOn()
    if (!refreshOn) {
      return '未开星标自动刷新：无法从微信侧接收标签/打印信号。'
    }
    if (lastLabelPrint) {
      const line = lastLabelPrint.line.slice(0, 100)
      return `已接收标签/打印类信号 · ${formatWorkflowHintTime(lastLabelPrint.at)} · ${line}${
        lastLabelPrint.line.length > 100 ? '…' : ''
      }`
    }
    return '星标轮询中：尚未命中标签/打印类意图；命中后本工作流才会推进。'
  }
  if (empId === 'shipment_mgmt') {
    if (lastShipmentAudit) {
      const line = lastShipmentAudit.line.slice(0, 100)
      return `打印后审计 · ${formatWorkflowHintTime(lastShipmentAudit.at)} · ${line}${
        lastShipmentAudit.line.length > 100 ? '…' : ''
      }`
    }
    return '等待「开始打印」成功：结束后将自动统计出货记录并提示保存/推送建议。'
  }
  if (empId === 'receipt_confirm') {
    const refreshOn = isStarredChatAutoRefreshOn()
    if (!refreshOn) {
      return '未开星标自动刷新：无法从微信侧接收客户收货/对账类反馈。'
    }
    if (lastReceiptFeedback) {
      const line = lastReceiptFeedback.line.slice(0, 100)
      return `客户业务进程 · ${formatWorkflowHintTime(lastReceiptFeedback.at)} · ${line}${
        lastReceiptFeedback.line.length > 100 ? '…' : ''
      }`
    }
    return '星标轮询中：尚未命中收货/对账类客户反馈；命中后将写入进程摘要。'
  }
  return ''
}

export function buildCoreWorkflowStepsForEmployee(
  empId: CoreWorkflowEmployeeId,
  ctx?: CoreWorkflowEmployeeCtx,
): WorkflowStepRow[] {
  if (empId === 'wechat_msg') {
    const refreshOn = isStarredChatAutoRefreshOn()
    const proIntent = isProIntentExperienceOn()
    const last = ctx?.lastWechat
    const preface = proIntent ? '调用 POST /api/ai/intent/test' : '本地关键词规则（inferWechatCustomerIntent）'
    return [
      { id: 'wx1', label: '① 副窗「一键托管」启用「微信消息处理 AI 员工」', status: 'done' },
      { id: 'wx2', label: '② 智能对话勾选「星标聊天自动刷新（1分钟）」', status: refreshOn ? 'done' : 'active' },
      {
        id: 'wx3',
        label: '③ 定时拉取星标联系人最新消息，并同步副窗「推送」提醒',
        status: refreshOn ? 'active' : 'pending',
      },
      {
        id: 'wx4',
        label: `④ 新消息到达 → 意图预处理（${preface}）`,
        status: last ? 'done' : 'pending',
      },
      {
        id: 'wx5',
        label: '⑤ 预处理结果写入本列表（「微信消息处理 · 联系人」类条目）',
        status: last ? 'done' : 'pending',
      },
    ]
  }
  if (empId === 'label_print') {
    const sig = ctx?.lastLabelPrint
    const refreshOn = isStarredChatAutoRefreshOn()
    return [
      { id: 'lp1', label: '① 副窗启用「标签打印 AI 员工」', status: 'done' },
      {
        id: 'lp2',
        label: refreshOn
          ? '② 星标新消息 → 意图预处理（与微信消息员工同源）'
          : '② 请开启「星标聊天自动刷新」以接收微信侧信号',
        status: refreshOn ? (sig ? 'done' : 'active') : 'active',
      },
      {
        id: 'lp3',
        label: sig
          ? '③ 在智能对话补充型号/张数并触发打印链路'
          : '③ 命中标签/打印意图后，在对话中执行打印',
        status: sig ? 'active' : 'pending',
      },
    ]
  }
  if (empId === 'shipment_mgmt') {
    const audit = ctx?.lastShipmentAudit
    return [
      { id: 'sm1', label: '① 副窗启用「出货管理 AI 员工」', status: 'done' },
      {
        id: 'sm2',
        label: '② 对话完成发货单生成并在确认后执行「开始打印」',
        status: audit ? 'done' : 'active',
      },
      {
        id: 'sm3',
        label: audit
          ? '③ 已输出打印后审计：请到出货记录核对，按需导出/推送'
          : '③ 打印后将自动统计本单位出货记录并给出保存/推送建议',
        status: audit ? 'active' : 'pending',
      },
    ]
  }
  if (empId === 'receipt_confirm') {
    const sig = ctx?.lastReceiptFeedback
    const refreshOn = isStarredChatAutoRefreshOn()
    return [
      { id: 'rc1', label: '① 副窗启用「收货确认 AI 员工」', status: 'done' },
      {
        id: 'rc2',
        label: refreshOn
          ? '② 星标微信 → 意图预处理（与微信消息员工同源），捕捉收货/对账类客户反馈'
          : '② 请开启「星标聊天自动刷新」以接收客户侧业务进程',
        status: refreshOn ? (sig ? 'done' : 'active') : 'active',
      },
      {
        id: 'rc3',
        label: sig
          ? '③ 已展示客户业务进程摘要，请在智能对话中跟进确认'
          : '③ 命中收货/对账类意图后写入进程信息',
        status: sig ? 'active' : 'pending',
      },
    ]
  }
  return []
}

export function computeCoreWorkflowCurrentHint(
  empId: CoreWorkflowEmployeeId,
  ctx?: CoreWorkflowEmployeeCtx,
  monitor?: WorkflowMonitorPayload,
): string {
  const lastWechat = ctx?.lastWechat
  const lastLabelPrint = ctx?.lastLabelPrint
  const lastShipmentAudit = ctx?.lastShipmentAudit
  const lastReceiptFeedback = ctx?.lastReceiptFeedback

  if (empId === 'wechat_msg') {
    const refreshOn = isStarredChatAutoRefreshOn()
    if (!refreshOn) {
      return '请先勾选「星标聊天自动刷新」以启动监控轮询。'
    }
    if (lastWechat) {
      return `最近一条客户消息已预处理并写入列表：${lastWechat.line.slice(0, 120)}${lastWechat.line.length > 120 ? '…' : ''}`
    }
    if (monitor?.lastPolledAt) {
      return '尚未捕获到新消息签名变化；监控轮询在运行，有新聊天时会自动执行意图预处理。'
    }
    return '工作流已就绪；首次轮询完成后，上方「工作状态」将显示上次检查时间。'
  }
  if (empId === 'label_print') {
    const refreshOn = isStarredChatAutoRefreshOn()
    if (!refreshOn) {
      return '请先勾选「星标聊天自动刷新」；标签打印员工仅从星标微信链路接收「标签/打印」类信号。'
    }
    if (lastLabelPrint) {
      return `最近命中标签/打印意图：${lastLabelPrint.line.slice(0, 120)}${lastLabelPrint.line.length > 120 ? '…' : ''}`
    }
    return '等待星标会话中出现标签/打印类消息；未命中前本工作流不执行后续步骤。'
  }
  if (empId === 'shipment_mgmt') {
    if (lastShipmentAudit) {
      const d = String(lastShipmentAudit.detail || lastShipmentAudit.line || '').trim()
      return d.length > 220 ? `${d.slice(0, 220)}…` : d || lastShipmentAudit.line
    }
    return '「开始打印」成功后，将自动拉取出货记录、汇总条数并提示是否导出存档或推送同事。'
  }
  if (empId === 'receipt_confirm') {
    const refreshOn = isStarredChatAutoRefreshOn()
    if (!refreshOn) {
      return '请先勾选「星标聊天自动刷新」；收货确认员工依赖微信消息员工同源链路获取客户反馈。'
    }
    if (lastReceiptFeedback) {
      const d = String(lastReceiptFeedback.detail || lastReceiptFeedback.line || '').trim()
      return d.length > 220 ? `${d.slice(0, 220)}…` : d || lastReceiptFeedback.line
    }
    return '等待星标客户发送收货、到货、签收、对账等消息；命中后在此展示对应业务进程摘要。'
  }
  return ''
}

export function computeCoreWorkflowStageLine(
  empId: CoreWorkflowEmployeeId,
  ctx?: CoreWorkflowEmployeeCtx,
): string {
  if (empId === 'wechat_msg') {
    if (!isStarredChatAutoRefreshOn()) return '等待开启星标自动刷新'
    return ctx?.lastWechat ? '监控中 · 最近已处理' : '监控中 · 等待新消息'
  }
  if (empId === 'label_print') {
    if (!isStarredChatAutoRefreshOn()) return '等待开启星标自动刷新'
    return ctx?.lastLabelPrint ? '已收微信侧标签/打印信号' : '等待微信侧标签/打印信号'
  }
  if (empId === 'shipment_mgmt') {
    return ctx?.lastShipmentAudit ? '已审计 · 建议核对出货记录' : '待命 · 等待打印完成后审计'
  }
  if (empId === 'receipt_confirm') {
    if (!isStarredChatAutoRefreshOn()) return '等待开启星标自动刷新'
    return ctx?.lastReceiptFeedback ? '已收客户侧业务进程反馈' : '等待微信侧收货/对账类反馈'
  }
  return ''
}

export type CoreWorkflowProgressState = {
  progressPct: number
  progressLabel: string
  workflowProgressStarted: boolean
}

export function computeCoreWorkflowProgressState(
  empId: CoreWorkflowEmployeeId,
  steps: WorkflowStepRow[],
  ctx?: CoreWorkflowEmployeeCtx,
): CoreWorkflowProgressState {
  const hasSignal =
    empId === 'wechat_msg'
      ? !!ctx?.lastWechat
      : empId === 'label_print'
        ? !!ctx?.lastLabelPrint
        : empId === 'shipment_mgmt'
          ? !!ctx?.lastShipmentAudit
          : !!ctx?.lastReceiptFeedback

  if (!hasSignal) {
    if (empId === 'wechat_msg') {
      return {
        progressPct: 0,
        progressLabel: isStarredChatAutoRefreshOn()
          ? '尚未进入处理：等待新消息'
          : '尚未进入处理：请先开启星标自动刷新',
        workflowProgressStarted: false,
      }
    }
    if (empId === 'label_print') {
      return {
        progressPct: 0,
        progressLabel: isStarredChatAutoRefreshOn()
          ? '尚未进入执行：等待微信侧标签/打印类消息'
          : '尚未进入执行：请先开启星标自动刷新',
        workflowProgressStarted: false,
      }
    }
    if (empId === 'shipment_mgmt') {
      return {
        progressPct: 0,
        progressLabel: '尚未完成打印后审计：请先完成发货单打印',
        workflowProgressStarted: false,
      }
    }
    return {
      progressPct: 0,
      progressLabel: isStarredChatAutoRefreshOn()
        ? '尚未收到客户侧收货/对账类反馈'
        : '尚未进入：请先开启星标自动刷新',
      workflowProgressStarted: false,
    }
  }
  const p = computeWorkflowProgressFromSteps(steps)
  return {
    progressPct: p.pct,
    progressLabel: p.label,
    workflowProgressStarted: true,
  }
}

export function mergeCorePayloadFromExisting(
  empId: string,
  opts: CoreWorkflowEmployeeCtx | undefined,
  existingPayload: Record<string, unknown> | undefined,
): CoreWorkflowEmployeeCtx {
  const out: CoreWorkflowEmployeeCtx = {}
  if (!isCoreWorkflowEmployeeId(empId)) return out
  const key = CORE_WORKFLOW_PAYLOAD_KEYS[empId]
  for (const k of Object.keys(CORE_WORKFLOW_PAYLOAD_KEYS) as CoreWorkflowEmployeeId[]) {
    const payloadKey = CORE_WORKFLOW_PAYLOAD_KEYS[k]
    if (opts && payloadKey in opts && opts[payloadKey] !== undefined) {
      out[payloadKey] = opts[payloadKey]
      continue
    }
    if (k === empId && existingPayload?.[payloadKey]) {
      out[payloadKey] = existingPayload[payloadKey] as CoreWorkflowTimestampLine & CoreWorkflowAuditLine
    }
  }
  return out
}

export function appendCoreWorkflowSummaryParts(
  empId: string,
  parts: string[],
  ctx?: CoreWorkflowEmployeeCtx,
): void {
  if (!isCoreWorkflowEmployeeId(empId)) return
  const t = formatWorkflowHintTime
  if (empId === 'wechat_msg' && ctx?.lastWechat) {
    parts.push(`最近处理 ${t(ctx.lastWechat.at)}：${ctx.lastWechat.line}`)
  }
  if (empId === 'label_print' && ctx?.lastLabelPrint) {
    parts.push(`最近标签/打印信号 ${t(ctx.lastLabelPrint.at)}：${ctx.lastLabelPrint.line}`)
  }
  if (empId === 'shipment_mgmt' && ctx?.lastShipmentAudit) {
    parts.push(`最近打印后审计 ${t(ctx.lastShipmentAudit.at)}：${ctx.lastShipmentAudit.line}`)
  }
  if (empId === 'receipt_confirm' && ctx?.lastReceiptFeedback) {
    parts.push(`最近客户反馈 ${t(ctx.lastReceiptFeedback.at)}：${ctx.lastReceiptFeedback.line}`)
  }
}
