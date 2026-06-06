import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { CoreWorkflowEmployeeId } from '@/constants/coreWorkflowMod'
import { shortNameFromPanelTitle } from '@/utils/workflowEmployeeDisplayName'
import { useWorkflowAiEmployeesStore } from '@/stores/workflowAiEmployees'

export const WORKFLOW_EMPLOYEE_SPACE_STORAGE_KEY = 'xcagi_workflow_employee_space_v1'
export const WORKFLOW_EMPLOYEE_SESSIONS_STORAGE_KEY = 'xcagi_workflow_employee_sessions_v1'

export type WorkflowEmployeeSpaceSnapshot = {
  empId: string
  panelTitle: string
  shortName: string
  stage: string
  progressPct: number
  progressLabel: string
  hintLine: string
  /** 与任务面板 workflowProgressIdle 一致 */
  idle: boolean
  /** 用于像素工位：是否在「干活」视觉态 */
  visuallyBusy: boolean
  lastActivityAt: number
}

/**
 * 员工的「工时与产能」量化数据，用于工位卡片头顶的状态条 / 工位特写。
 *
 * - `enabledAt`: 当前一次「副窗一键托管」打开的时间戳；关闭时清空，再开则刷新。
 * - `firstActivityAt`: 首次实际处理活动的时间戳（跨会话累计，仅记录第一次）。
 * - `lastActivityAt`: 最近一次活动；用于「最近 5 分钟无新活动 → 视觉态淡化」类判断。
 * - `processedCount`: 累计处理任务数（仅 applyFromWorkflowPayload 的非心跳调用，
 *    心跳轮询如 wechat_star_feed_polled 不计数）。
 * - `sessionMs`: 本次启用累计时长；关闭时把 `now - enabledAt` 累加进 `lifetimeMs` 后清零。
 * - `lifetimeMs`: 历史累计工时（已下班的所有 session 之和）。当前 session 的实时时长在外层渲染时按 `now - enabledAt` 计算后叠加。
 */
export type WorkflowEmployeeSession = {
  empId: string
  enabledAt: number | null
  firstActivityAt: number | null
  lastActivityAt: number | null
  processedCount: number
  lifetimeMs: number
}

type PersistedV1 = {
  schemaVersion: 1
  snapshots: Record<string, WorkflowEmployeeSpaceSnapshot>
}

type PersistedSessionsV1 = {
  schemaVersion: 1
  sessions: Record<string, WorkflowEmployeeSession>
}

function safeParsePersisted(raw: string | null): PersistedV1 | null {
  if (!raw) return null
  try {
    const p = JSON.parse(raw) as unknown
    if (!p || typeof p !== 'object') return null
    const o = p as Record<string, unknown>
    if (o.schemaVersion !== 1) return null
    const snaps = o.snapshots
    if (!snaps || typeof snaps !== 'object') return null
    return { schemaVersion: 1, snapshots: snaps as Record<string, WorkflowEmployeeSpaceSnapshot> }
  } catch {
    return null
  }
}

function safeParseSessions(raw: string | null): PersistedSessionsV1 | null {
  if (!raw) return null
  try {
    const p = JSON.parse(raw) as unknown
    if (!p || typeof p !== 'object') return null
    const o = p as Record<string, unknown>
    if (o.schemaVersion !== 1) return null
    const sess = o.sessions
    if (!sess || typeof sess !== 'object') return null
    return { schemaVersion: 1, sessions: sess as Record<string, WorkflowEmployeeSession> }
  } catch {
    return null
  }
}

function emptySession(empId: string): WorkflowEmployeeSession {
  return {
    empId,
    enabledAt: null,
    firstActivityAt: null,
    lastActivityAt: null,
    processedCount: 0,
    lifetimeMs: 0,
  }
}

function snapshotVisuallyBusy(payload: Record<string, unknown>): boolean {
  const idle = payload.workflowProgressIdle === true
  const started = payload.workflowProgressStarted === true
  const pct = Number(payload.workflowProgressPct ?? 0)
  if (idle) return false
  if (started) return true
  return pct > 0
}

let persistTimer: number | null = null
let sessionsPersistTimer: number | null = null

function schedulePersist(snapshots: Record<string, WorkflowEmployeeSpaceSnapshot>) {
  if (typeof window === 'undefined') return
  if (persistTimer != null) window.clearTimeout(persistTimer)
  persistTimer = window.setTimeout(() => {
    persistTimer = null
    try {
      const out: PersistedV1 = { schemaVersion: 1, snapshots: { ...snapshots } }
      sessionStorage.setItem(WORKFLOW_EMPLOYEE_SPACE_STORAGE_KEY, JSON.stringify(out))
    } catch {
      /* quota / private mode */
    }
  }, 280)
}

function scheduleSessionsPersist(sessions: Record<string, WorkflowEmployeeSession>) {
  if (typeof window === 'undefined') return
  if (sessionsPersistTimer != null) window.clearTimeout(sessionsPersistTimer)
  sessionsPersistTimer = window.setTimeout(() => {
    sessionsPersistTimer = null
    try {
      const out: PersistedSessionsV1 = { schemaVersion: 1, sessions: { ...sessions } }
      /** 工时累计跨页要存活，用 localStorage（与 xcagi_workflow_ai_employees 持久层一致） */
      localStorage.setItem(WORKFLOW_EMPLOYEE_SESSIONS_STORAGE_KEY, JSON.stringify(out))
    } catch {
      /* quota / private mode */
    }
  }, 280)
}

export const useWorkflowEmployeeSpaceStore = defineStore('workflowEmployeeSpace', () => {
  const snapshots = ref<Record<string, WorkflowEmployeeSpaceSnapshot>>({})
  const sessions = ref<Record<string, WorkflowEmployeeSession>>({})

  function hydrateFromSessionStorage() {
    if (typeof sessionStorage === 'undefined') return
    try {
      const parsed = safeParsePersisted(sessionStorage.getItem(WORKFLOW_EMPLOYEE_SPACE_STORAGE_KEY))
      if (parsed?.snapshots) {
        snapshots.value = { ...parsed.snapshots }
      }
    } catch {
      /* ignore */
    }
  }

  function hydrateSessionsFromLocalStorage() {
    if (typeof localStorage === 'undefined') return
    try {
      const parsed = safeParseSessions(localStorage.getItem(WORKFLOW_EMPLOYEE_SESSIONS_STORAGE_KEY))
      if (parsed?.sessions) {
        sessions.value = { ...parsed.sessions }
      }
    } catch {
      /* ignore */
    }
  }

  hydrateFromSessionStorage()
  hydrateSessionsFromLocalStorage()

  function ensureSession(empId: string): WorkflowEmployeeSession {
    const cur = sessions.value[empId]
    if (cur) return cur
    const fresh = emptySession(empId)
    sessions.value = { ...sessions.value, [empId]: fresh }
    return fresh
  }

  /** 副窗一键托管开 → 记录上工时间 */
  function markEnabled(empId: string) {
    if (!empId) return
    const cur = ensureSession(empId)
    if (cur.enabledAt) return
    sessions.value = {
      ...sessions.value,
      [empId]: { ...cur, enabledAt: Date.now() },
    }
    scheduleSessionsPersist(sessions.value)
  }

  /** 副窗一键托管关 → 把当前 session 时长累加进 lifetime */
  function markDisabled(empId: string) {
    if (!empId) return
    const cur = sessions.value[empId]
    if (!cur || !cur.enabledAt) return
    const elapsed = Math.max(0, Date.now() - cur.enabledAt)
    sessions.value = {
      ...sessions.value,
      [empId]: {
        ...cur,
        enabledAt: null,
        lifetimeMs: cur.lifetimeMs + elapsed,
      },
    }
    scheduleSessionsPersist(sessions.value)
  }

  function bumpProcessed(empId: string) {
    if (!empId) return
    const cur = ensureSession(empId)
    const now = Date.now()
    sessions.value = {
      ...sessions.value,
      [empId]: {
        ...cur,
        processedCount: cur.processedCount + 1,
        firstActivityAt: cur.firstActivityAt ?? now,
        lastActivityAt: now,
      },
    }
    scheduleSessionsPersist(sessions.value)
  }

  function applyFromWorkflowPayload(
    panelTitle: string,
    payload: Record<string, unknown> | null | undefined,
    options: { isHeartbeat?: boolean } = {}
  ) {
    const empId = String(payload?.employeeId ?? '').trim()
    if (!empId) return
    const stage = String(payload?.workflowStageLine ?? '').trim()
    const progressPct = Math.max(0, Math.min(100, Number(payload?.workflowProgressPct ?? 0) || 0))
    const progressLabel = String(payload?.workflowProgressLabel ?? '').trim()
    const hintLine = String(payload?.workflowCurrentHint ?? '').trim()
    const idle = payload?.workflowProgressIdle === true
    const visuallyBusy = snapshotVisuallyBusy(payload || {})

    const next: WorkflowEmployeeSpaceSnapshot = {
      empId,
      panelTitle: String(panelTitle || '').trim() || `工作流 · ${empId}`,
      shortName: shortNameFromPanelTitle(panelTitle),
      stage: stage || '—',
      progressPct,
      progressLabel,
      hintLine,
      idle,
      visuallyBusy,
      lastActivityAt: Date.now(),
    }

    const prev = snapshots.value[empId]
    const sameSnapshot =
      prev &&
      prev.stage === next.stage &&
      prev.progressPct === next.progressPct &&
      prev.progressLabel === next.progressLabel &&
      prev.hintLine === next.hintLine &&
      prev.idle === next.idle &&
      prev.visuallyBusy === next.visuallyBusy &&
      prev.panelTitle === next.panelTitle

    /**
     * 心跳（如星标轮询）即便相同也写一次 lastActivityAt 以保留「在线」感，
     * 但不计入「已处理任务数」；真实活动且状态变化时才递增 processedCount。
     */
    if (!options.isHeartbeat && !sameSnapshot) {
      bumpProcessed(empId)
    }

    if (sameSnapshot) return

    snapshots.value = { ...snapshots.value, [empId]: next }
    schedulePersist(snapshots.value)
  }

  /** 副窗事件桥：仅更新标签打印工作流快照（不操作任务列表） */
  function applyLabelPrintBridge(detail: { at?: number; line?: string }) {
    const wf = useWorkflowAiEmployeesStore()
    if (!wf.enabled.label_print) return
    const line = String(detail?.line || '').trim() || '标签/打印类消息'
    const at = Number(detail?.at) || Date.now()
    applyFromWorkflowPayload('工作流 · 标签打印 AI 员工', {
      employeeId: 'label_print' as CoreWorkflowEmployeeId,
      workflowStageLine: '已收微信侧标签/打印信号',
      workflowProgressPct: 55,
      workflowProgressLabel: '进行中',
      workflowCurrentHint: `最近命中标签/打印意图：${line.slice(0, 160)}${line.length > 160 ? '…' : ''}`,
      workflowProgressIdle: false,
      workflowProgressStarted: true,
      lastLabelPrint: { at, line },
    })
  }

  /** 副窗事件桥：收货确认 */
  function applyReceiptBridge(detail: {
    at?: number
    line?: string
    intentLabel?: string
    messageText?: string
    contactName?: string
  }) {
    const wf = useWorkflowAiEmployeesStore()
    if (!wf.enabled.receipt_confirm) return
    const line = String(detail?.line || '').trim() || '客户反馈'
    const at = Number(detail?.at) || Date.now()
    const hint = [
      detail?.contactName ? `联系人：${detail.contactName}` : '',
      detail?.intentLabel ? `意图：${detail.intentLabel}` : '',
      detail?.messageText ? `摘要：${String(detail.messageText).slice(0, 120)}` : '',
    ]
      .filter(Boolean)
      .join(' · ')
    applyFromWorkflowPayload('工作流 · 收货确认 AI 员工', {
      employeeId: 'receipt_confirm' as CoreWorkflowEmployeeId,
      workflowStageLine: '已收客户侧业务进程反馈',
      workflowProgressPct: 55,
      workflowProgressLabel: '进行中',
      workflowCurrentHint: hint || line,
      workflowProgressIdle: false,
      workflowProgressStarted: true,
      lastReceiptFeedback: { at, line, detail: hint },
    })
  }

  /** 副窗事件桥：微信消息处理（与 onWechatAiTaskEnqueue 写入的 lastWechat 对齐） */
  function applyWechatMsgBridge(detail: { messageText?: string; contactName?: string }) {
    const wf = useWorkflowAiEmployeesStore()
    if (!wf.enabled.wechat_msg) return
    const name = String(detail?.contactName || '星标联系人').trim()
    const msg = String(detail?.messageText || '').trim()
    const line = `${name}：${msg.replace(/\s+/g, ' ').slice(0, 120)}`
    const at = Date.now()
    applyFromWorkflowPayload('工作流 · 微信消息处理 AI 员工', {
      employeeId: 'wechat_msg' as CoreWorkflowEmployeeId,
      workflowStageLine: '监控中 · 最近已处理',
      workflowProgressPct: 100,
      workflowProgressLabel: '处理中',
      workflowCurrentHint: `最近一条客户消息已预处理：${line.slice(0, 120)}${line.length > 120 ? '…' : ''}`,
      workflowProgressIdle: false,
      workflowProgressStarted: true,
      lastWechat: { at, line },
    })
  }

  /**
   * 星标轮询心跳：在无聊天页 upsert 时仍刷新「监控」提示（与任务面板 monitor 行语义接近）。
   */
  function applyWechatStarFeedPolledBridge(detail: { at?: number; intervalMs?: number; contactCount?: number; ok?: boolean }) {
    const wf = useWorkflowAiEmployeesStore()
    if (!wf.enabled.wechat_msg) return
    const prev = snapshots.value.wechat_msg
    const pollOk = detail?.ok !== false
    const t = Number(detail?.at) || Date.now()
    const sec = Math.max(1, Math.round((Number(detail?.intervalMs) || 60000) / 1000))
    const n = detail?.contactCount
    const cnt = typeof n === 'number' ? `星标联系人 ${n} 位` : '星标联系人'
    const clock = new Date(t).toLocaleTimeString('zh-CN', { hour12: false })
    const monitorLine = `${pollOk ? '拉取通道正常' : '上次拉取失败，将重试'} · 上次检查 ${clock} · 每 ${sec}s 轮询 · ${cnt}`
    applyFromWorkflowPayload(
      prev?.panelTitle || '工作流 · 微信消息处理 AI 员工',
      {
        employeeId: 'wechat_msg' as CoreWorkflowEmployeeId,
        workflowStageLine: prev?.stage && prev.stage.includes('已处理') ? prev.stage : '监控中 · 等待新消息',
        workflowProgressPct: prev?.progressPct ?? 30,
        workflowProgressLabel: prev?.progressLabel || '轮询中',
        workflowCurrentHint: prev?.hintLine ? `${prev.hintLine}\n${monitorLine}` : monitorLine,
        workflowProgressIdle: prev ? prev.idle : true,
        workflowProgressStarted: prev ? prev.visuallyBusy : false,
      },
      { isHeartbeat: true }
    )
  }

  function removeEmployee(empId: string) {
    if (!snapshots.value[empId]) return
    const next = { ...snapshots.value }
    delete next[empId]
    snapshots.value = next
    schedulePersist(snapshots.value)
  }

  /**
   * 跟踪副窗一键托管开关：开 → markEnabled，关 → markDisabled。
   * 通过 pinia $subscribe 与开关 store 解耦——卡片 UI 只调 wfEmp.toggle，
   * 工时累计在这里集中处理，避免分散到每个调用点。
   */
  const wfEmp = useWorkflowAiEmployeesStore()
  let lastEnabled: Record<string, boolean> = { ...wfEmp.enabled }
  /** 初始化阶段：已经处于开启的员工，把 enabledAt 设为「现在」（从启动那一刻算起） */
  for (const id of Object.keys(lastEnabled)) {
    if (lastEnabled[id]) markEnabled(id)
  }
  wfEmp.$subscribe((_mutation, state) => {
    const cur = state.enabled as Record<string, boolean>
    const allIds = new Set([...Object.keys(lastEnabled), ...Object.keys(cur)])
    for (const id of allIds) {
      const wasOn = lastEnabled[id] === true
      const isOn = cur[id] === true
      if (!wasOn && isOn) markEnabled(id)
      else if (wasOn && !isOn) markDisabled(id)
    }
    lastEnabled = { ...cur }
  })

  return {
    snapshots,
    sessions,
    hydrateFromSessionStorage,
    hydrateSessionsFromLocalStorage,
    applyFromWorkflowPayload,
    applyLabelPrintBridge,
    applyReceiptBridge,
    applyWechatMsgBridge,
    applyWechatStarFeedPolledBridge,
    removeEmployee,
    markEnabled,
    markDisabled,
  }
})
