/**
 * 宿主配置：从 /api/system/* 加载 industry presets、工作流员工目录与注册规则。
 */
import { ref } from 'vue'
import { apiFetch } from '@/utils/apiBase'
import type { IndustryPreset } from '@/constants/industryPresets'

export type EmployeeRegistryRules = {
  workflow_employee_id_prefixes?: string[]
  exclude_id_suffixes?: string[]
  exclude_artifact_types?: string[]
  exclude_mod_ids?: string[]
  non_workflow_desk_employee_patterns?: string[]
}

export type WorkflowCatalogEntry = {
  mod_id: string
  employee_id: string
  label?: string
  panel_title?: string
  panel_summary?: string
}

const loaded = ref(false)
const loadError = ref<string | null>(null)
let bootstrapInFlight: Promise<void> | null = null
export const industryPresets = ref<Record<string, IndustryPreset>>({})
export const industryPresetIds = ref<string[]>([])
export const workflowEmployeeModIds = ref<string[]>([])
export const workflowEmployeeIds = ref<string[]>([])
export const employeeRegistryRules = ref<EmployeeRegistryRules | null>(null)
export const clientModPolicies = ref<{
  client_primary_erp_mod_id?: string
  suppress_generic_shell_mod_ids?: string[]
  protected_ids?: string[]
} | null>(null)
const workflowDelivery = ref<string>('monolith')

function unwrapData<T>(body: unknown): T | null {
  if (!body || typeof body !== 'object') return null
  const o = body as Record<string, unknown>
  if (o.data !== undefined) return o.data as T
  return body as T
}

async function fetchSystemJson<T>(path: string): Promise<T | null> {
  try {
    const res = await apiFetch(path)
    if (!res.ok) return null
    const body = await res.json()
    return unwrapData<T>(body)
  } catch {
    return null
  }
}

export async function bootstrapHostConfig(): Promise<void> {
  if (loaded.value) return
  if (bootstrapInFlight) return bootstrapInFlight
  bootstrapInFlight = (async () => {
  try {
    const [presetsData, catalogWrap, rulesData, profileWrap] = await Promise.all([
      fetchSystemJson<{
        preset_ids?: string[]
        presets?: Record<string, IndustryPreset>
      }>('/api/system/industry-presets'),
      fetchSystemJson<{
        catalog?: {
          default_mod_ids?: string[]
          default_employee_ids?: string[]
          split_mod_entries?: WorkflowCatalogEntry[]
        }
        workflow_delivery?: string
      }>('/api/system/workflow-employee-catalog'),
      fetchSystemJson<EmployeeRegistryRules>('/api/system/employee-registry-rules'),
      fetchSystemJson<{ profile?: Record<string, unknown> }>('/api/system/host-profile'),
    ])

    if (presetsData?.presets && typeof presetsData.presets === 'object') {
      industryPresets.value = { ...presetsData.presets }
      industryPresetIds.value = Array.isArray(presetsData.preset_ids)
        ? [...presetsData.preset_ids]
        : Object.keys(presetsData.presets)
    }

    if (catalogWrap) {
      const data = catalogWrap
      const cat = data?.catalog
      if (cat?.default_mod_ids?.length) {
        workflowEmployeeModIds.value = [...cat.default_mod_ids]
      }
      if (cat?.default_employee_ids?.length) {
        workflowEmployeeIds.value = [...cat.default_employee_ids]
      }
      if (data?.workflow_delivery) {
        workflowDelivery.value = String(data.workflow_delivery)
      }
    }

    if (rulesData && typeof rulesData === 'object') {
      employeeRegistryRules.value = rulesData
    }

    if (profileWrap) {
      const data = profileWrap
      const pol = data?.profile?.client_mod_policies
      if (pol && typeof pol === 'object') {
        clientModPolicies.value = pol as typeof clientModPolicies.value
      }
      const delivery = data?.profile?.workflow_delivery
      if (delivery) workflowDelivery.value = String(delivery)
    }

    loaded.value = true
    loadError.value = null
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e)
  }
  })()
  try {
    await bootstrapInFlight
  } finally {
    bootstrapInFlight = null
  }
}

export function useHostConfigStore() {
  return {
    loaded,
    loadError,
    industryPresets,
    industryPresetIds,
    workflowEmployeeModIds,
    workflowEmployeeIds,
    employeeRegistryRules,
    clientModPolicies,
    workflowDelivery,
    bootstrapHostConfig,
  }
}
