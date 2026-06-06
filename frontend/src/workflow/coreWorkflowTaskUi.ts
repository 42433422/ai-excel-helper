import { isCoreWorkflowEmployeeId } from '@/constants/coreWorkflowMod'
import { STAR_REFRESH_STORAGE_KEY } from '@/workflow/coreWorkflowPrefs'

function starredRefreshOnFromStorage(): boolean {
  try {
    return localStorage.getItem(STAR_REFRESH_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function workflowProgressIsIdle(payload: Record<string, unknown>): boolean {
  if (typeof payload.workflowProgressIdle === 'boolean') return payload.workflowProgressIdle
  if (typeof payload.workflowProgressStarted === 'boolean') return !payload.workflowProgressStarted
  return false
}

/** 任务列表圆点：四名核心工作流员工 */
export function coreWorkflowTaskDotStatusClass(
  empId: string,
  payload: Record<string, unknown>,
): string | null {
  if (!isCoreWorkflowEmployeeId(empId)) return null
  const mon = payload.monitor as { pollOk?: boolean } | undefined
  if (mon && mon.pollOk === false) return 'failed'

  const started = payload.workflowProgressStarted === true
  if (!started) {
    if (empId === 'shipment_mgmt') return 'queued'
    return starredRefreshOnFromStorage() ? 'queued' : 'workflow-warn'
  }
  const pct = Number(payload.workflowProgressPct)
  if (pct >= 100) return 'success'
  return 'running'
}

export function coreWorkflowTaskDotTitle(empId: string, payload: Record<string, unknown>): string | null {
  if (!isCoreWorkflowEmployeeId(empId)) return null
  const mon = payload.monitor as { pollOk?: boolean } | undefined
  if (mon && mon.pollOk === false) return '状态：上次星标会话拉取失败（红）'

  if (empId === 'wechat_msg') {
    if (workflowProgressIsIdle(payload)) {
      return starredRefreshOnFromStorage()
        ? '状态：待命，等待新消息后再计进度（灰）'
        : '状态：未开星标自动刷新，监控未就绪（橙）'
    }
    const pct = Number(payload.workflowProgressPct)
    if (pct >= 100) return '状态：本轮流程已跑通，仍持续监控（绿）'
    return '状态：已处理消息，流程推进中（蓝）'
  }
  if (empId === 'label_print') {
    if (workflowProgressIsIdle(payload)) {
      return starredRefreshOnFromStorage()
        ? '状态：等待微信侧标签/打印信号，未计进度（灰）'
        : '状态：未开星标自动刷新，无法收微信信号（橙）'
    }
    const pctLp = Number(payload.workflowProgressPct)
    if (pctLp >= 100) return '状态：流程已推进，可在对话中完成打印（绿）'
    return '状态：已收到标签/打印信号，待对话执行打印（蓝）'
  }
  if (empId === 'shipment_mgmt') {
    if (workflowProgressIsIdle(payload)) return '状态：等待打印完成后出货审计（灰）'
    const pctSm = Number(payload.workflowProgressPct)
    if (pctSm >= 100) return '状态：已输出审计建议，可核对出货记录（绿）'
    return '状态：审计已生成，建议核对并导出（蓝）'
  }
  if (empId === 'receipt_confirm') {
    if (workflowProgressIsIdle(payload)) {
      return starredRefreshOnFromStorage()
        ? '状态：等待微信侧收货/对账类客户反馈（灰）'
        : '状态：未开星标自动刷新，无法收客户进程（橙）'
    }
    const pctRc = Number(payload.workflowProgressPct)
    if (pctRc >= 100) return '状态：已捕获客户业务进程，可对话跟进（绿）'
    return '状态：已收到客户反馈摘要（蓝）'
  }
  return null
}
