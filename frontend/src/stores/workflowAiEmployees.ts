import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ModWithWorkflowEmployees } from '@/utils/modWorkflowEmployees'
import type { WorkflowEmployeeRegistryEntry } from '@/types/workflow-employee'
import {
  filterWorkflowRegistrySourceMods,
  isNonWorkflowDeskEmployeeId,
} from '@/utils/modWorkflowEmployees'
import {
  loadWorkflowEmployeeRegistry,
  mergeModManifestEntries,
  resolveLabel,
  invalidateWorkflowEmployeeRegistryCache,
} from '@/utils/workflowEmployeeRegistry'

function collectManifestWorkflowEmployeeIds(mods: ModWithWorkflowEmployees[] | undefined): Set<string> {
  const ids = new Set<string>()
  for (const m of filterWorkflowRegistrySourceMods(mods)) {
    for (const e of m.workflow_employees || []) {
      const id = String(e?.id || '').trim()
      if (id && !isNonWorkflowDeskEmployeeId(id)) ids.add(id)
    }
  }
  return ids
}

export const WORKFLOW_AI_EMPLOYEES_STORAGE_KEY = 'xcagi_workflow_ai_employees'

export function defaultWorkflowBuiltinEnabled(): Record<string, boolean> {
  return {}
}

export function coreWorkflowEmployeeIdSet(): Set<string> {
  return new Set()
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
  mods: ModWithWorkflowEmployees[] | undefined,
): Record<string, boolean> {
  const next = { ...cur }
  for (const m of filterWorkflowRegistrySourceMods(mods)) {
    for (const e of m.workflow_employees || []) {
      const id = String(e?.id || '').trim()
      if (!id || isNonWorkflowDeskEmployeeId(id) || id in next) continue
      next[id] = false
    }
  }
  return next
}

export const useWorkflowAiEmployeesStore = defineStore('workflowAiEmployees', () => {
  const enabled = ref<Record<string, boolean>>(readWorkflowEnabledFromLocalStorage())
  const registryEntries = ref<WorkflowEmployeeRegistryEntry[]>([])
  const registryLoaded = ref(false)

  const registeredIds = computed(() => new Set(registryEntries.value.map((e) => e.id)))

  function persistAndNotify() {
    try {
      localStorage.setItem(WORKFLOW_AI_EMPLOYEES_STORAGE_KEY, JSON.stringify(enabled.value))
    } catch {
      /* quota / private mode */
    }
    window.dispatchEvent(
      new CustomEvent('xcagi:workflow-ai-employees-changed', {
        detail: { enabled: { ...enabled.value } },
      }),
    )
  }

  async function loadRegistry(mods?: ModWithWorkflowEmployees[]) {
    try {
      const registry = await loadWorkflowEmployeeRegistry()
      const merged = mods ? mergeModManifestEntries(registry, mods) : registry.employees
      registryEntries.value = merged
      registryLoaded.value = true
      ensureEnabledKeys()
    } catch (e) {
      console.warn('[workflowAiEmployees] loadRegistry failed:', e)
    }
  }

  function registerEmployee(entry: WorkflowEmployeeRegistryEntry) {
    const idx = registryEntries.value.findIndex((e) => e.id === entry.id)
    if (idx >= 0) {
      registryEntries.value[idx] = entry
    } else {
      registryEntries.value.push(entry)
      registryEntries.value.sort((a, b) => a.order - b.order)
    }
    if (!(entry.id in enabled.value)) {
      enabled.value = { ...enabled.value, [entry.id]: false }
      persistAndNotify()
    }
  }

  function unregisterEmployee(id: string) {
    const idx = registryEntries.value.findIndex((e) => e.id === id)
    if (idx >= 0) {
      registryEntries.value.splice(idx, 1)
    }
    const next = { ...enabled.value }
    delete next[id]
    if (JSON.stringify(next) !== JSON.stringify(enabled.value)) {
      enabled.value = next
      persistAndNotify()
    }
  }

  function ensureEnabledKeys() {
    const next = { ...enabled.value }
    let changed = false
    for (const entry of registryEntries.value) {
      if (!(entry.id in next)) {
        next[entry.id] = false
        changed = true
      }
    }
    if (changed) {
      enabled.value = next
      persistAndNotify()
    }
  }

  function hydrateFromMods(mods: ModWithWorkflowEmployees[] | undefined) {
    const merged = mergeModWorkflowIds({ ...enabled.value }, mods)
    if (JSON.stringify(merged) !== JSON.stringify(enabled.value)) {
      enabled.value = merged
    }
  }

  function stripModWorkflowEmployeeKeys() {
    const registryIds = registeredIds.value
    const next: Record<string, boolean> = {}
    for (const k of Object.keys(enabled.value)) {
      if (registryIds.has(k)) next[k] = enabled.value[k]
    }
    if (JSON.stringify(next) !== JSON.stringify(enabled.value)) {
      enabled.value = next
      persistAndNotify()
    }
  }

  function pruneOrphanWorkflowEmployeeToggles(mods: ModWithWorkflowEmployees[] | undefined) {
    const manifestIds = collectManifestWorkflowEmployeeIds(mods)
    const registryIds = registeredIds.value
    const next: Record<string, boolean> = { ...enabled.value }
    for (const k of Object.keys(next)) {
      if (registryIds.has(k)) continue
      if (!manifestIds.has(k)) delete next[k]
    }
    if (JSON.stringify(next) !== JSON.stringify(enabled.value)) {
      enabled.value = next
      persistAndNotify()
    }
  }

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

  function getEmployeeLabel(id: string, i18nResolver?: (key: string) => string): string {
    const entry = registryEntries.value.find((e) => e.id === id)
    if (entry) return resolveLabel(entry, i18nResolver)
    return id
  }

  async function refreshRegistry(mods?: ModWithWorkflowEmployees[]) {
    invalidateWorkflowEmployeeRegistryCache()
    registryLoaded.value = false
    await loadRegistry(mods)
  }

  return {
    enabled,
    registryEntries,
    registryLoaded,
    registeredIds,
    loadRegistry,
    registerEmployee,
    unregisterEmployee,
    ensureEnabledKeys,
    hydrateFromMods,
    stripModWorkflowEmployeeKeys,
    pruneOrphanWorkflowEmployeeToggles,
    reloadFromLocalStorage,
    setAll,
    toggle,
    enableAllOn,
    persistAndNotify,
    getEmployeeLabel,
    refreshRegistry,
  }
})
