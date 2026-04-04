import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ModWithWorkflowEmployees } from '@/utils/modWorkflowEmployees'

/** 当前 Mod 列表下仍合法的动态员工 id；用于去掉「已无 manifest 条目」的本地开关（如关 Mod 界面后） */
function collectManifestWorkflowEmployeeIds(mods: ModWithWorkflowEmployees[] | undefined): Set<string> {
  const ids = new Set<string>()
  for (const m of mods || []) {
    for (const e of m.workflow_employees || []) {
      const id = String(e?.id || '').trim()
      if (id) ids.add(id)
    }
  }
  return ids
}

export const WORKFLOW_AI_EMPLOYEES_STORAGE_KEY = 'xcagi_workflow_ai_employees'

/** 与副窗、useChatView 一致的内置 key（含固定扩展） */
export function defaultWorkflowBuiltinEnabled(): Record<string, boolean> {
  return {
    label_print: false,
    shipment_mgmt: false,
    receipt_confirm: false,
    wechat_msg: false,
    // wechat_phone / real_phone 仅由各 Mod manifest 的 workflow_employees 声明（如 sz-qsm-pro），勿在此硬编码
  }
}

function readWorkflowEnabledFromLocalStorage(): Record<string, boolean> {
  const base = defaultWorkflowBuiltinEnabled()
  try {
    const raw = localStorage.getItem(WORKFLOW_AI_EMPLOYEES_STORAGE_KEY)
    if (!raw) return base
    const p = JSON.parse(raw) as Record<string, unknown>
    if (!p || typeof p !== 'object') return base
    for (const k of Object.keys(base)) {
      if (typeof p[k] === 'boolean') base[k] = p[k]
    }
    for (const k of Object.keys(p)) {
      if (!(k in base) && typeof p[k] === 'boolean') base[k] = p[k] as boolean
    }
    return base
  } catch {
    return base
  }
}

function mergeModWorkflowIds(
  cur: Record<string, boolean>,
  mods: ModWithWorkflowEmployees[] | undefined
): Record<string, boolean> {
  const builtin = new Set(Object.keys(defaultWorkflowBuiltinEnabled()))
  const next = { ...cur }
  for (const m of mods || []) {
    for (const e of m.workflow_employees || []) {
      const id = String(e?.id || '').trim()
      if (id && !builtin.has(id) && !(id in next)) next[id] = false
    }
  }
  return next
}

/**
 * 副窗「一键托管」工作流员工开关：单一数据源，供聊天页任务面板 watch 同步，
 * 避免仅依赖 window 事件导致漏更新。
 */
export const useWorkflowAiEmployeesStore = defineStore('workflowAiEmployees', () => {
  const enabled = ref<Record<string, boolean>>(readWorkflowEnabledFromLocalStorage())

  function persistAndNotify() {
    try {
      localStorage.setItem(WORKFLOW_AI_EMPLOYEES_STORAGE_KEY, JSON.stringify(enabled.value))
    } catch {
      /* quota / private mode */
    }
    window.dispatchEvent(
      new CustomEvent('xcagi:workflow-ai-employees-changed', {
        detail: { enabled: { ...enabled.value } },
      })
    )
  }

  function hydrateFromMods(mods: ModWithWorkflowEmployees[] | undefined) {
    const merged = mergeModWorkflowIds({ ...enabled.value }, mods)
    if (JSON.stringify(merged) !== JSON.stringify(enabled.value)) {
      enabled.value = merged
    }
  }

  /** 关闭前端 Mod 显示时调用：去掉 manifest 动态员工 id，仅保留内置键的开关状态 */
  function stripModWorkflowEmployeeKeys() {
    const builtins = defaultWorkflowBuiltinEnabled()
    const next: Record<string, boolean> = { ...builtins }
    for (const k of Object.keys(builtins)) {
      if (k in enabled.value) next[k] = enabled.value[k]
    }
    enabled.value = next
    persistAndNotify()
  }

  /** 删除本地存储里已不存在于当前 Mod manifest 的员工键（核心四条保留） */
  function pruneOrphanWorkflowEmployeeToggles(mods: ModWithWorkflowEmployees[] | undefined) {
    const builtins = defaultWorkflowBuiltinEnabled()
    const manifestIds = collectManifestWorkflowEmployeeIds(mods)
    const next: Record<string, boolean> = { ...enabled.value }
    for (const k of Object.keys(next)) {
      if (k in builtins) continue
      if (!manifestIds.has(k)) delete next[k]
    }
    if (JSON.stringify(next) !== JSON.stringify(enabled.value)) {
      enabled.value = next
      persistAndNotify()
    }
  }

  /** 从其它标签页 / 外部写入的 localStorage 同步回内存 */
  function reloadFromLocalStorage() {
    enabled.value = readWorkflowEnabledFromLocalStorage()
  }

  function setAll(next: Record<string, boolean>) {
    enabled.value = { ...next }
    persistAndNotify()
  }

  function toggle(id: string) {
    if (!(id in enabled.value)) {
      enabled.value = { ...enabled.value, [id]: true }
    } else {
      enabled.value = { ...enabled.value, [id]: !enabled.value[id] }
    }
    persistAndNotify()
  }

  function enableAllOn() {
    const next = { ...enabled.value }
    for (const k of Object.keys(next)) next[k] = true
    setAll(next)
  }

  return {
    enabled,
    hydrateFromMods,
    stripModWorkflowEmployeeKeys,
    pruneOrphanWorkflowEmployeeToggles,
    reloadFromLocalStorage,
    setAll,
    toggle,
    enableAllOn,
    persistAndNotify,
  }
})
