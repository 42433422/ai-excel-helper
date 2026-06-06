/** 通用化宿主壳（阶段 4）— 与 GET /api/platform-shell/capabilities 对齐 */

export const BRIDGE_MOD_IDS = [
  'xcagi-approval-bridge',
  'xcagi-lan-license-bridge',
  'xcagi-model-payment-bridge',
  'xcagi-planner-bridge',
] as const

export type BridgeModId = (typeof BRIDGE_MOD_IDS)[number]

export const PLATFORM_SHELL_POLICY =
  '新业务应做成 Mod（房子）或 employee_pack（家具），勿再写入宿主 workflow-employees.json'

export interface PlatformShellCapabilities {
  schema_version?: number
  edition?: 'minimal' | 'generic' | 'full'
  core_workflow_mod_id?: string
  protected_client_mod_ids?: string[]
  minimal_pack_installed?: boolean
  generic_pack_installed?: boolean
  platform_shell_mode?: boolean
  shell_api_prefixes?: string[]
  bridge_mods?: Array<{
    mod_id: string
    role: string
    host_api_prefixes: string[]
    installed: boolean
  }>
  policy?: string
}

export interface DeliverableStatus {
  schema_version?: number
  deliverable?: boolean
  edition?: 'minimal' | 'generic' | 'full'
  edition_ready?: boolean
  minimal_pack_installed?: boolean
  generic_pack_installed?: boolean
  missing_mod_ids?: string[]
  host_foundation_employee_installed?: boolean
  host_foundation_bridges_ready?: boolean
  host_foundation_materialize?: Record<string, unknown> | null
  blockers?: Array<{ code: string; message: string; missing_mod_ids?: string[] }>
  next_actions?: string[]
}
