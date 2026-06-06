import type {
  WorkflowEmployeeRegistryEntry,
  WorkflowEmployeeRegistryV1,
  WorkflowEmployeeRegistryKind,
} from '@/types/workflow-employee'
import {
  buildModWorkflowPanelMeta,
  isNonWorkflowDeskEmployeeId,
  filterWorkflowRegistrySourceMods,
  type ModWithWorkflowEmployees,
} from '@/utils/modWorkflowEmployees'

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === 'object' && x !== null
}

function isValidV1(data: unknown): data is WorkflowEmployeeRegistryV1 {
  if (!isRecord(data)) return false
  if (data.schemaVersion !== 1) return false
  if (!Array.isArray(data.employees)) return false
  return data.employees.every(
    (e: unknown) =>
      isRecord(e) &&
      typeof e.id === 'string' &&
      typeof e.label === 'string' &&
      typeof e.kind === 'string' &&
      typeof e.order === 'number',
  )
}

function normalizeRegistry(d: WorkflowEmployeeRegistryV1): WorkflowEmployeeRegistryV1 {
  return {
    ...d,
    employees: d.employees.map((e) => ({
      ...e,
      kind: (e.kind as WorkflowEmployeeRegistryKind) || 'mod_extension',
      source: e.source || 'json',
    })),
  }
}

let cachedRegistry: Promise<WorkflowEmployeeRegistryV1> | null = null

/** 宿主不再内置员工行；注册表由已安装 Mod 的 manifest 注入。 */
export async function loadWorkflowEmployeeRegistry(): Promise<WorkflowEmployeeRegistryV1> {
  return { schemaVersion: 1, employees: [] }
}

export function invalidateWorkflowEmployeeRegistryCache(): void {
  cachedRegistry = null
}

export async function loadWorkflowEmployeeRegistryCached(): Promise<WorkflowEmployeeRegistryV1> {
  if (!cachedRegistry) {
    cachedRegistry = loadWorkflowEmployeeRegistry()
  }
  return cachedRegistry
}

export function mergeModManifestEntries(
  registry: WorkflowEmployeeRegistryV1,
  mods: ModWithWorkflowEmployees[],
): WorkflowEmployeeRegistryEntry[] {
  const baseMap = new Map(
    registry.employees
      .filter((e) => !isNonWorkflowDeskEmployeeId(e.id))
      .map((e) => [e.id, e]),
  )
  const modMeta = buildModWorkflowPanelMeta(filterWorkflowRegistrySourceMods(mods))

  for (const [id, meta] of Object.entries(modMeta)) {
    if (isNonWorkflowDeskEmployeeId(id)) continue
    if (baseMap.has(id)) continue
    const t = (meta.title || '').replace(/^工作流 ·\s*/, '').trim()
    baseMap.set(id, {
      id,
      label: t || id,
      kind: 'mod_extension',
      order: 100 + baseMap.size,
      source: 'mod_manifest',
    })
  }

  return Array.from(baseMap.values()).sort((a, b) => a.order - b.order)
}

export function resolveLabel(entry: WorkflowEmployeeRegistryEntry, i18nResolver?: (key: string) => string): string {
  if (entry.labelI18nKey && i18nResolver) {
    const resolved = i18nResolver(entry.labelI18nKey)
    if (resolved && resolved !== entry.labelI18nKey) return resolved
  }
  return entry.label
}

/** @deprecated 使用 loadWorkflowEmployeeRegistryCached + mergeModManifestEntries */
export async function loadRegistryFromJson(): Promise<WorkflowEmployeeRegistryV1> {
  return loadWorkflowEmployeeRegistry()
}
