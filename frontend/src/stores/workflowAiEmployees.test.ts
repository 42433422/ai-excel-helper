import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import {
  useWorkflowAiEmployeesStore,
  WORKFLOW_AI_EMPLOYEES_STORAGE_KEY,
  defaultWorkflowBuiltinEnabled,
} from './workflowAiEmployees'

describe('workflowAiEmployees store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.spyOn(window, 'dispatchEvent').mockImplementation(() => true)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('reads keys from localStorage without builtin defaults', () => {
    localStorage.setItem(
      WORKFLOW_AI_EMPLOYEES_STORAGE_KEY,
      JSON.stringify({
        label_print: true,
        custom_mod_emp: false,
      }),
    )
    const store = useWorkflowAiEmployeesStore()
    expect(store.enabled.label_print).toBe(true)
    expect(store.enabled.shipment_mgmt).toBeUndefined()
    expect(store.enabled.custom_mod_emp).toBe(false)
  })

  it('falls back to empty defaults on invalid JSON', () => {
    localStorage.setItem(WORKFLOW_AI_EMPLOYEES_STORAGE_KEY, '{not json')
    const store = useWorkflowAiEmployeesStore()
    expect(store.enabled).toEqual(defaultWorkflowBuiltinEnabled())
  })

  it('hydrateFromMods adds dynamic ids with default false', () => {
    const store = useWorkflowAiEmployeesStore()
    store.hydrateFromMods([
      {
        id: 'm',
        workflow_employees: [{ id: 'from_manifest', label: 'X' }],
      },
    ])
    expect(store.enabled.from_manifest).toBe(false)
  })

  it('stripModWorkflowEmployeeKeys keeps only registry keys', async () => {
    const store = useWorkflowAiEmployeesStore()
    await store.loadRegistry([
      { id: 'm', workflow_employees: [{ id: 'label_print', label: 'L' }] },
    ])
    store.setAll({
      ...store.enabled,
      extra: true,
      label_print: true,
    })
    vi.mocked(window.dispatchEvent).mockClear()
    store.stripModWorkflowEmployeeKeys()
    expect('extra' in store.enabled).toBe(false)
    expect(store.enabled.label_print).toBe(true)
    expect(window.dispatchEvent).toHaveBeenCalled()
  })

  it('pruneOrphanWorkflowEmployeeToggles removes keys not in manifest', () => {
    const store = useWorkflowAiEmployeesStore()
    store.hydrateFromMods([
      { id: 'm', workflow_employees: [{ id: 'still_here', label: 'S' }] },
    ])
    store.setAll({
      ...store.enabled,
      orphan: true,
      still_here: true,
      label_print: true,
    })
    vi.mocked(window.dispatchEvent).mockClear()
    store.pruneOrphanWorkflowEmployeeToggles([
      { id: 'm', workflow_employees: [{ id: 'still_here', label: 'S' }] },
    ])
    expect(store.enabled.orphan).toBeUndefined()
    expect(store.enabled.still_here).toBe(true)
    expect(store.enabled.label_print).toBeUndefined()
    expect(window.dispatchEvent).toHaveBeenCalled()
  })

  it('toggle flips and dispatches xcagi:workflow-ai-employees-changed', () => {
    const store = useWorkflowAiEmployeesStore()
    vi.mocked(window.dispatchEvent).mockClear()
    store.toggle('label_print')
    expect(store.enabled.label_print).toBe(true)
    const evt = vi.mocked(window.dispatchEvent).mock.calls.find(
      (c) => (c[0] as CustomEvent).type === 'xcagi:workflow-ai-employees-changed',
    )?.[0] as CustomEvent
    expect(evt).toBeDefined()
    expect(evt.detail.enabled.label_print).toBe(true)
  })

  it('enableAllOn sets every known key to true', () => {
    const store = useWorkflowAiEmployeesStore()
    store.hydrateFromMods([
      { id: 'm', workflow_employees: [{ id: 'dyn', label: 'D' }] },
    ])
    store.enableAllOn()
    for (const k of Object.keys(store.enabled)) {
      expect(store.enabled[k]).toBe(true)
    }
  })

  it('reloadFromLocalStorage picks up external storage writes', () => {
    const store = useWorkflowAiEmployeesStore()
    localStorage.setItem(
      WORKFLOW_AI_EMPLOYEES_STORAGE_KEY,
      JSON.stringify({ label_print: true }),
    )
    store.reloadFromLocalStorage()
    expect(store.enabled.label_print).toBe(true)
  })
})
