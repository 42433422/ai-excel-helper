import { apiFetch, DEFAULT_MOD_API_TIMEOUT_MS } from '@/utils/apiBase'
import {
  isWorkflowEmployeeId,
  type WorkflowEmployeeId,
} from '@/constants/workflowEmployeeMods'
import type { ModWithWorkflowEmployees } from '@/utils/modWorkflowEmployees'
import { findWorkflowEmployeeEntry } from '@/utils/modWorkflowEmployees'

export type CoreWorkflowRunPayload = {
  action?: string
  [key: string]: unknown
}

function modIdForWorkflowEmployee(
  mods: ModWithWorkflowEmployees[] | undefined,
  employeeId: string,
): string | null {
  const entry = findWorkflowEmployeeEntry(mods, employeeId)
  return entry?.modId?.trim() || null
}

/** 调用已安装工作流员工 Mod 内该员工的 run 端点 */
export async function postCoreWorkflowEmployeeRun(
  employeeId: WorkflowEmployeeId,
  payload: CoreWorkflowRunPayload = { action: 'status' },
  mods?: ModWithWorkflowEmployees[],
): Promise<{ success?: boolean; data?: { ok?: boolean; summary?: string; error?: string } }> {
  const modId = modIdForWorkflowEmployee(mods, employeeId)
  if (!modId) {
    throw new Error(`workflow employee mod not installed: ${employeeId}`)
  }
  const path = `/api/mod/${modId}/employees/${encodeURIComponent(employeeId)}/run`
  const r = await apiFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    timeoutMs: DEFAULT_MOD_API_TIMEOUT_MS,
  })
  if (!r.ok) {
    throw new Error(`workflow employee run ${employeeId}: HTTP ${r.status}`)
  }
  return r.json()
}

export function tryPostCoreWorkflowEmployeeRun(
  employeeId: string,
  payload: CoreWorkflowRunPayload = { action: 'status' },
  mods?: ModWithWorkflowEmployees[],
): Promise<{ success?: boolean; data?: { ok?: boolean } }> | null {
  if (!isWorkflowEmployeeId(employeeId)) return null
  return postCoreWorkflowEmployeeRun(employeeId, payload, mods).catch((e) => {
    console.warn('[coreWorkflowEmployeeApi]', employeeId, e)
    return { success: false, data: { ok: false } }
  })
}
