/**
 * Mod manifest workflow_employees 与副窗/聊天任务面板的对接（避免在业务代码里硬编码某 Mod 的员工 id）。
 */

export interface WorkflowEmployeeManifestEntry {
  id: string
  label: string
  /** 任务面板标题，缺省为「工作流 · {label}」 */
  panel_title?: string
  /** 任务面板摘要 */
  panel_summary?: string
  /**
   * 相对本 Mod 的 API 路径前缀（不含 /api/mod/{id}/），如 phone-agent。
   * 解析为 /api/mod/{modId}/phone-agent，与 phone_agent_api_base 二选一。
   */
  phone_agent_base_path?: string
  /** 该 Mod 电话业务员 HTTP 根路径，如 /api/mod/sz-qsm-pro/phone-agent（不要尾斜杠） */
  phone_agent_api_base?: string
  /** 为 true 时启用副窗 start/stop 与聊天页状态轮询；未写且已配置电话 API 时默认轮询 */
  phone_agent_status_poll?: boolean
  /** 占位员工：仅展示说明步骤，无后端自动化 */
  workflow_placeholder?: boolean
  /** manifest 常用：与 workflow_placeholder 等价 */
  workflow_ui_kind?: 'placeholder'
}

/** 由 manifest 字段得到电话 HTTP 根（无则 null） */
export function resolvePhoneAgentApiBase(
  e: WorkflowEmployeeManifestEntry | undefined,
  modId: string
): string | null {
  if (!e) return null
  const full = e.phone_agent_api_base?.trim()
  if (full) return full.replace(/\/+$/, '')
  const rel = e.phone_agent_base_path?.trim()
  if (rel && modId) {
    const p = rel.replace(/^\/+|\/+$/g, '')
    return `/api/mod/${modId}/${p}`
  }
  return null
}

export type ModWithWorkflowEmployees = {
  id: string
  name?: string
  workflow_employees?: WorkflowEmployeeManifestEntry[]
}

/**
 * 当前已加载 Mod 中 manifest 声明的工作流员工行数（跨包按 id 去重，与副窗 buildModWorkflowPanelMeta 一致）。
 */
export function countManifestWorkflowEmployeeRows(mods: ModWithWorkflowEmployees[] | undefined): number {
  const seen = new Set<string>()
  let n = 0
  for (const m of mods || []) {
    for (const e of m.workflow_employees || []) {
      const id = String(e?.id || '').trim()
      if (!id || seen.has(id)) continue
      seen.add(id)
      n += 1
    }
  }
  return n
}

export function findWorkflowEmployeeEntry(
  mods: ModWithWorkflowEmployees[] | undefined,
  empId: string
): (WorkflowEmployeeManifestEntry & { modId: string; modName: string }) | null {
  const id = String(empId || '').trim()
  if (!id) return null
  for (const m of mods || []) {
    for (const e of m.workflow_employees || []) {
      if (e?.id === id) {
        return {
          ...e,
          modId: String(m.id || ''),
          modName: String(m.name || m.id || ''),
        }
      }
    }
  }
  return null
}

/** 副窗开关：该员工是否配置了电话 API 根路径（用于 start/stop） */
export function getPhoneAgentApiBaseForEmployeeId(
  mods: ModWithWorkflowEmployees[] | undefined,
  empId: string
): string | null {
  const e = findWorkflowEmployeeEntry(mods, empId)
  if (!e) return null
  return resolvePhoneAgentApiBase(e, e.modId)
}

export function isPhoneAgentStatusEmployee(
  mods: ModWithWorkflowEmployees[] | undefined,
  empId: string
): boolean {
  const e = findWorkflowEmployeeEntry(mods, empId)
  if (!e) return false
  const base = resolvePhoneAgentApiBase(e, e.modId)
  if (!base) return false
  if (e.phone_agent_status_poll === false) return false
  return true
}

export function isWorkflowPlaceholderEmployee(
  mods: ModWithWorkflowEmployees[] | undefined,
  empId: string
): boolean {
  const e = findWorkflowEmployeeEntry(mods, empId)
  if (!e) return false
  if (e.workflow_ui_kind === 'placeholder') return true
  return !!e.workflow_placeholder
}

/**
 * 取当前应轮询 phone-agent 的员工与 API：任一启用且声明了 poll + api_base 的员工（通常每个 Mod 一个）。
 */
export function getActivePhoneAgentPollTarget(
  mods: ModWithWorkflowEmployees[] | undefined,
  enabled: Record<string, boolean>
): { empId: string; apiBase: string } | null {
  for (const m of mods || []) {
    const modId = String(m.id || '').trim()
    for (const e of m.workflow_employees || []) {
      const id = e?.id
      if (!id || !enabled[id]) continue
      if (e.phone_agent_status_poll === false) continue
      const base = resolvePhoneAgentApiBase(e, modId)
      if (base) {
        return { empId: id, apiBase: base }
      }
    }
  }
  return null
}

/** 由已加载 Mod 生成任务面板 meta（不含内置四条，仅 Mod 声明的员工） */
export function buildModWorkflowPanelMeta(
  mods: ModWithWorkflowEmployees[] | undefined
): Record<string, { title: string; summary: string }> {
  const out: Record<string, { title: string; summary: string }> = {}
  for (const m of mods || []) {
    const modName = String(m.name || m.id || '扩展')
    for (const e of m.workflow_employees || []) {
      const id = String(e?.id || '').trim()
      if (!id || out[id]) continue
      const label = String(e.label || id).trim() || id
      out[id] = {
        title: e.panel_title?.trim() || `工作流 · ${label}`,
        summary:
          e.panel_summary?.trim() ||
          `由扩展「${modName}」在 manifest 中声明的工作流员工「${label}」。`,
      }
    }
  }
  return out
}
