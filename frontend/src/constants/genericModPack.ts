/** 通用宿主发行包：安装后建议自动进入平台壳模式 */
/** 客户 Mod 双轨策略优先 GET /api/system/host-profile → client_mod_policies */

import { clientModPolicies } from '@/stores/hostConfig'
import { getWorkflowEmployeeModIds } from '@/constants/workflowEmployeeMods'

/** 空壳发行（里程碑 Q）：对话 + NeuroBus + 办公 pack，无 ERP/审批等行业 Mod */
export const MINIMAL_HOST_MOD_IDS = [
  'xcagi-planner-bridge',
  'xcagi-neuro-bus-bridge',
  'xcagi-office-employee-pack-bridge',
] as const

/** 完整通用行业包（里程碑 I） */
export const GENERIC_HOST_MOD_IDS = [
  'xcagi-planner-bridge',
  'xcagi-erp-domain-bridge',
  'xcagi-workflow-visualization-bridge',
  'xcagi-approval-bridge',
  'xcagi-lan-license-bridge',
  'xcagi-model-payment-bridge',
  'xcagi-neuro-bus-bridge',
  'xcagi-office-employee-pack-bridge',
  'xcagi-customer-service-bridge',
] as const

/** 客户专属 Mod；存在时且未装通用 ERP 门面则保留完整 ERP 侧栏 */
export const CLIENT_PRIMARY_ERP_MOD_ID = 'taiyangniao-pro'

export type HostEdition = 'minimal' | 'generic' | 'full'

export function readBuildEdition(): HostEdition {
  const raw = String(import.meta.env.VITE_XCAGI_EDITION || '').trim().toLowerCase()
  if (raw === 'minimal') return 'minimal'
  if (raw === 'generic') return 'generic'
  return 'full'
}

function installedSet(installedModIds: string[]): Set<string> {
  return new Set(installedModIds.map((x) => String(x || '').trim()).filter(Boolean))
}

export function hasInstalledClientPrimaryErpMod(installedModIds: Iterable<string>): boolean {
  const ids = installedSet(Array.from(installedModIds))
  const pol = clientModPolicies.value
  const primary = String(pol?.client_primary_erp_mod_id || CLIENT_PRIMARY_ERP_MOD_ID).trim()
  return Boolean(primary && ids.has(primary))
}

/** 已装任一行业扩展包（非宿主 bridge） */
export function hasInstalledSelectableExtensionMod(installedModIds: Iterable<string>): boolean {
  return Array.from(installedModIds).some((id) => isSelectableExtensionModId(String(id || '').trim()))
}

/**
 * 客户 ERP / 考勤侧栏：隐藏与宿主重复的 bridge Mod 入口。
 * 除「已装主 ERP」外，当前选中行业扩展包或「扩展 + 无通用 ERP 门面」亦视为该场景。
 */
export function isClientErpSidebarContext(
  installedModIds: Iterable<string>,
  activeModId?: string | null,
): boolean {
  const ids = installedSet(Array.from(installedModIds))
  if (hasInstalledClientPrimaryErpMod(ids)) return true
  if (shouldRespectClientFullErp(ids)) return true
  const active = String(activeModId || '').trim()
  const pol = clientModPolicies.value
  const primary = String(pol?.client_primary_erp_mod_id || CLIENT_PRIMARY_ERP_MOD_ID).trim()
  if (primary && active === primary) return true
  if (isSelectableExtensionModId(active)) return true
  if (hasInstalledSelectableExtensionMod(ids) && !ids.has('xcagi-erp-domain-bridge')) return true
  return false
}

/** Planner bridge 侧栏项与宿主「智能对话 / 智能生态 / 智脑」重复，客户 ERP 场景不展示 */
export const REDUNDANT_PLANNER_BRIDGE_MENU_IDS = new Set([
  'mod-planner-chat',
  'mod-planner-ai-ecosystem',
  'mod-planner-brain',
])

/**
 * 已装客户主 ERP（太阳鸟等）时，宿主 bridge 的 Mod 侧栏入口与 core/trailing 重复，一律不展示。
 */
export const CLIENT_ERP_SUPPRESSED_MOD_MENU_IDS = new Set([
  ...REDUNDANT_PLANNER_BRIDGE_MENU_IDS,
  'mod-workflow-visualization',
  'mod-approval-hub',
  'mod-enterprise-customer-service',
  'mod-internal-customer-service',
  'mod-erp-products',
  'mod-erp-customers',
  'mod-erp-orders',
  'mod-erp-shipment-records',
  'mod-erp-materials',
  'mod-erp-traditional-mode',
  'mod-erp-data-sources',
  'mod-erp-printer-list',
  'mod-erp-template-preview',
  'mod-office-tools',
  'mod-office-other-tools',
  'mod-kitten-finance',
  'mod-lan-gate',
])

/** 完整宿主 ERP 侧栏（非平台壳）下与 core/bridge 重复的 Mod 入口，始终不展示 */
export const FULL_HOST_SIDEBAR_SUPPRESSED_MOD_MENU_IDS = new Set([
  ...REDUNDANT_PLANNER_BRIDGE_MENU_IDS,
  'mod-workflow-visualization',
  'mod-kitten-finance',
  'mod-lan-gate',
  /** 员工包上架项：仅商店安装，不进主侧栏（与 bridge mod-lan-gate 一致） */
  'mod-lan-gate-ai-employee-entry',
  'lan-gate-ai-employee-entry',
])

function isSandboxSidebarMode(): boolean {
  if (typeof window === 'undefined') return false
  try {
    return new URLSearchParams(window.location.search).has('sandbox')
  } catch {
    return false
  }
}

function isPlatformShellSidebarMode(): boolean {
  const sku = String(import.meta.env.VITE_XCAGI_PRODUCT_SKU || '').trim().toLowerCase()
  if (sku === 'enterprise') return false
  if (typeof window !== 'undefined') {
    try {
      const q = new URLSearchParams(window.location.search)
      if (q.has('shell')) return true
      if (q.has('full')) return false
    } catch {
      /* ignore */
    }
  }
  if (typeof localStorage !== 'undefined') {
    try {
      const stored = localStorage.getItem('xcagi_platform_shell_mode')
      if (stored === '0') return false
      if (stored === '1') return true
    } catch {
      /* ignore */
    }
  }
  const env = String(import.meta.env.VITE_XCAGI_PLATFORM_SHELL || '').trim().toLowerCase()
  if (env === '1' || env === 'true' || env === 'yes') return true
  const edition = readBuildEdition()
  if (edition === 'minimal' || edition === 'generic') return true
  const def = String(import.meta.env.VITE_XCAGI_DEFAULT_PLATFORM_SHELL || '').trim().toLowerCase()
  return def === '1' || def === 'true' || def === 'yes'
}

/** 企业完整侧栏：流程可视化 / 智脑集成等由宿主页承担，不重复挂 Mod 入口 */
export function shouldSuppressRedundantModMenuInFullHostSidebar(menuId: string): boolean {
  if (isPlatformShellSidebarMode() || isSandboxSidebarMode()) return false
  const id = normalizeModSidebarNavKey(String(menuId || '').trim())
  return FULL_HOST_SIDEBAR_SUPPRESSED_MOD_MENU_IDS.has(id)
}

export function shouldSuppressClientErpModMenuId(
  menuId: string,
  installedModIds: Iterable<string>,
  activeModId?: string | null,
): boolean {
  if (shouldSuppressRedundantModMenuInFullHostSidebar(menuId)) return true
  if (!isClientErpSidebarContext(installedModIds, activeModId)) return false
  const id = normalizeModSidebarNavKey(String(menuId || '').trim())
  return CLIENT_ERP_SUPPRESSED_MOD_MENU_IDS.has(id)
}

/**
 * bridge 的 menu_overrides 会隐藏宿主槽位（如 chat），以便改由 Mod 路由展示。
 * 当对应 Mod 侧栏项已被抑制时，应保留宿主入口，避免「智能对话」等完全消失。
 */
export function keepHostNavKeyVisibleWhenModSidebarFacetSuppressed(
  hostNavKey: string,
  installedModIds: Iterable<string>,
  activeModId?: string | null,
): boolean {
  const key = String(hostNavKey || '').trim()
  if (!key) return false
  for (const [modMenuId, mappedKey] of Object.entries(MOD_MENU_ID_TO_HOST_NAV_KEY)) {
    if (mappedKey !== key) continue
    if (
      shouldSuppressClientErpModMenuId(modMenuId, installedModIds, activeModId) ||
      shouldSuppressRedundantModMenuInFullHostSidebar(modMenuId)
    ) {
      return true
    }
  }
  return false
}

/** Mod 菜单 id → 宿主 core/trailing 槽位（已占用则不再插入 Mod 项，避免「外部客服」等出现两次） */
export const MOD_MENU_ID_TO_HOST_NAV_KEY: Readonly<Record<string, string>> = {
  'mod-enterprise-customer-service': 'enterprise-customer-service',
  'mod-internal-customer-service': 'internal-customer-service',
  'mod-approval-hub': 'approval-hub',
  'mod-workflow-visualization': 'workflow-visualization',
  'mod-planner-chat': 'chat',
  'mod-planner-ai-ecosystem': 'ai-ecosystem',
  'mod-planner-brain': 'brain',
  'mod-erp-products': 'products',
  'mod-erp-customers': 'customers',
  'mod-erp-orders': 'orders',
  'mod-erp-shipment-records': 'shipment-records',
  'mod-erp-materials': 'materials',
  'mod-erp-traditional-mode': 'traditional-mode',
  'mod-erp-data-sources': 'data-sources',
  'mod-erp-printer-list': 'printer-list',
  'mod-erp-template-preview': 'template-preview',
  'mod-office-tools': 'tools',
  'mod-office-other-tools': 'other-tools',
  'mod-kitten-finance': 'kitten-finance',
  'mod-lan-gate': 'lan-gate',
}

/** 归一化侧栏 key（兼容历史错误的 mod-mod- 双前缀） */
export function normalizeModSidebarNavKey(key: string): string {
  const k = String(key || '').trim();
  return k.replace(/^mod-mod-/, 'mod-');
}

/**
 * 员工包 / bridge 复用宿主路由的 menu.path（如 /wechat-contacts、/chat），非 /mod/{id}/ 前缀。
 */
export function isHostMountedModMenuPath(
  path: string,
  proEntryPath?: string | null,
): boolean {
  const p = String(path || '').trim();
  if (!p) return false;
  const pro = String(proEntryPath || '').trim();
  if (pro && (p === pro || p.startsWith(`${pro}/`))) return true;
  for (const hostKey of Object.values(MOD_MENU_ID_TO_HOST_NAV_KEY)) {
    if (p === `/${hostKey}` || p.startsWith(`/${hostKey}/`)) return true;
  }
  return false;
}

export function shouldRespectClientFullErp(ids: Set<string>): boolean {
  const pol = clientModPolicies.value
  const primary = String(pol?.client_primary_erp_mod_id || CLIENT_PRIMARY_ERP_MOD_ID).trim()
  const suppress = pol?.suppress_generic_shell_mod_ids || [CLIENT_PRIMARY_ERP_MOD_ID]
  if (!ids.has(primary)) return false
  if (suppress.some((mid) => ids.has(String(mid).trim()) && !ids.has('xcagi-erp-domain-bridge'))) {
    return ids.has(primary) && !ids.has('xcagi-erp-domain-bridge')
  }
  return ids.has(primary) && !ids.has('xcagi-erp-domain-bridge')
}

export function shouldAutoEnableMinimalPlatformShell(installedModIds: string[]): boolean {
  const ids = installedSet(installedModIds)
  if (shouldRespectClientFullErp(ids)) return false
  return MINIMAL_HOST_MOD_IDS.every((mid) => ids.has(mid))
}

export function shouldAutoEnablePlatformShell(installedModIds: string[]): boolean {
  const ids = installedSet(installedModIds)
  if (shouldRespectClientFullErp(ids)) return false
  return GENERIC_HOST_MOD_IDS.every((mid) => ids.has(mid))
}

export function shouldAutoEnableEditionPlatformShell(installedModIds: string[]): boolean {
  const edition = readBuildEdition()
  if (edition === 'minimal') return shouldAutoEnableMinimalPlatformShell(installedModIds)
  if (edition === 'generic') return shouldAutoEnablePlatformShell(installedModIds)
  return shouldAutoEnableMinimalPlatformShell(installedModIds) || shouldAutoEnablePlatformShell(installedModIds)
}

const HOST_BRIDGE_ID_SET = new Set<string>([
  ...MINIMAL_HOST_MOD_IDS,
  ...GENERIC_HOST_MOD_IDS,
  'xcagi-core-workflow-employees',
  'xcagi-planner-excel-tools',
  'wechat-contacts-ai-employee',
])

/** 宿主基础设施 bridge：应作为「基础预装包」整体管理，不参与设置页「当前扩展包」单选。 */
export function isHostBridgeModId(modId: string): boolean {
  const id = String(modId || '').trim()
  if (!id) return false
  if (HOST_BRIDGE_ID_SET.has(id)) return true
  return id.startsWith('xcagi-') && id.endsWith('-bridge')
}

/** 工作流单员工 Mod：由商店按需安装，不在「行业扩展包」单选里展示。 */
export function isWorkflowEmployeeModId(modId: string): boolean {
  const id = String(modId || '').trim()
  if (/^xcagi-workflow-employee-/.test(id)) return true
  return (getWorkflowEmployeeModIds() as readonly string[]).includes(id)
}

/** 商店「AI 员工」上架的触点/授权类扩展（非 workflow-employee 前缀） */
export const AUX_EMPLOYEE_PACK_MOD_IDS = [
  'wechat-contacts-ai-employee',
  'lan-gate-ai-employee',
] as const

export function isAuxEmployeePackModId(modId: string): boolean {
  const id = String(modId || '').trim()
  return (AUX_EMPLOYEE_PACK_MOD_IDS as readonly string[]).includes(id)
}

export function isEmployeePackListingModId(modId: string): boolean {
  const id = String(modId || '').trim()
  if (!id) return false
  if (id === HOST_FOUNDATION_EMPLOYEE_PACK_ID) return true
  if (isAuxEmployeePackModId(id)) return true
  if (/-(?:generate|full-read)-employee$/.test(id)) return true
  if (/^(csv|excel|pdf|ppt|word)-/.test(id) && id.endsWith('-employee')) return true
  return false
}

export function isSelectableExtensionModId(modId: string): boolean {
  const id = String(modId || '').trim()
  if (!id) return false
  if (isHostBridgeModId(id)) return false
  if (isWorkflowEmployeeModId(id)) return false
  if (isEmployeePackListingModId(id)) return false
  return true
}

export function expectedHostBridgeModIds(): readonly string[] {
  const edition = readBuildEdition()
  if (edition === 'minimal') return MINIMAL_HOST_MOD_IDS
  return GENERIC_HOST_MOD_IDS
}

/** 商店/设置：宿主基础设施以员工包交付，不按逐项 bridge Mod 上架。 */
export const HOST_FOUNDATION_EMPLOYEE_PACK_ID = 'xcagi-host-foundation-employee'

export const STORE_COLLECTION_HOST_FOUNDATION = 'host_foundation'
export const STORE_COLLECTION_WORKFLOW_EMPLOYEE = 'workflow_employee'
export const STORE_COLLECTION_INDUSTRY_MOD = 'industry_mod'

export function isHostFoundationEmployeePackId(modId: string): boolean {
  return String(modId || '').trim() === HOST_FOUNDATION_EMPLOYEE_PACK_ID
}

export function catalogStoreCollection(row: {
  store_collection?: string
  artifact?: string
  id?: string
  pkg_id?: string
  config?: { host_foundation_pack?: boolean }
}): string {
  const sc = String(row?.store_collection || '').trim()
  if (sc) return sc
  const art = String(row?.artifact || '').trim().toLowerCase()
  if (art === 'employee_pack') {
    if (row?.config?.host_foundation_pack) return STORE_COLLECTION_HOST_FOUNDATION
    return STORE_COLLECTION_WORKFLOW_EMPLOYEE
  }
  const id = String(row?.id || row?.pkg_id || '').trim()
  if (isHostFoundationEmployeePackId(id)) return STORE_COLLECTION_HOST_FOUNDATION
  if (isWorkflowEmployeeModId(id)) return STORE_COLLECTION_WORKFLOW_EMPLOYEE
  if (isHostBridgeModId(id)) return ''
  return STORE_COLLECTION_INDUSTRY_MOD
}
