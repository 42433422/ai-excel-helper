import {
  ERP_DOMAIN_BRIDGE_MOD_ID,
  LEGACY_CLIENT_ERP_MOD_ID,
  readErpDomainModFacadeEnabled,
} from '@/constants/erpDomainMod'
import { CLIENT_PRIMARY_ERP_MOD_ID } from '@/constants/genericModPack'
import { isProtectedClientModId } from '@/constants/protectedMods'
import { clientModPolicies } from '@/stores/hostConfig'
import { useModsStore } from '@/stores/mods'
import { XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY } from '@/utils/xcagiStorageKeys'

const MOD_FACADE_BASE = `/api/mod/${ERP_DOMAIN_BRIDGE_MOD_ID}`

/**
 * 太阳鸟等客户 Mod 自管 API（见 mods/taiyangniao-pro/backend/blueprints.py）。
 * 订单/考勤记录等仍由 xcagi-erp-domain-bridge 提供；购买单位与客户同源走客户 Mod。
 */
const ERP_ON_CLIENT_MOD_PREFIXES: readonly string[] = [
  '/api/products',
  '/api/customers',
  '/api/purchase_units',
  '/api/shipment/shipment-records/units',
]

/** 选中客户 Mod 时仍走领域门面的路径（勿用 /api/shipment 整段前缀，否则会盖住 units 走客户库） */
const ERP_ON_BRIDGE_WHEN_CLIENT_ACTIVE: readonly string[] = [
  '/api/orders',
]

/**
 * 与 app.mod_sdk.erp_domain_compat.DOMAIN_SPECS 及 Mod blueprints 实际挂载路径对齐。
 * 按 host 前缀长度降序匹配（最长前缀优先）。
 */
const ERP_DOMAIN_PREFIX_SOURCE = [
    ['/api/shipment', `${MOD_FACADE_BASE}/shipment`],
    ['/api/wechat_contacts', `${MOD_FACADE_BASE}/wechat_contacts`],
    ['/api/products', `${MOD_FACADE_BASE}/products`],
    ['/api/customers', `${MOD_FACADE_BASE}/customers`],
    ['/api/purchase_units', `${MOD_FACADE_BASE}/purchase_units`],
    ['/api/orders', `${MOD_FACADE_BASE}/orders`],
    ['/api/wechat', `${MOD_FACADE_BASE}/wechat`],
  ] as const

const ERP_DOMAIN_PREFIX_MAP: ReadonlyArray<readonly [hostPrefix: string, facadePrefix: string]> =
  [...ERP_DOMAIN_PREFIX_SOURCE].sort((a, b) => b[0].length - a[0].length)

/** 门面开启时仍走宿主 /api 的路径（Mod 未提供门面或 materials/print 等扩展 API） */
/** 客户 Mod（太阳鸟等）未实现的 API，继续走宿主 /api */
const CLIENT_MOD_HOST_ONLY_API_PREFIXES: readonly string[] = [
  '/api/wechat_contacts',
  '/api/wechat',
]

const HOST_ONLY_API_PREFIXES: readonly string[] = [
  '/api/materials',
  '/api/print',
  '/api/printers',
  '/api/templates',
  '/api/template',
  '/api/generate',
  '/api/db-tools',
  '/api/traditional-mode',
  '/api/business-docking',
  '/api/data-sources',
  '/api/service-bridge',
  '/api/approval',
  '/api/market',
  '/api/employees',
  '/api/ai',
  '/api/tools',
  '/api/system',
  '/api/auth',
  '/api/mods',
  '/api/mod/',
  '/api/health',
  '/api/lan',
  '/api/xcmax',
  '/api/debug',
  '/api/preferences',
  '/api/desktop',
  '/api/tts',
  '/api/intent-packages',
]

function normalizeApiPath(path: string): string {
  const raw = path.startsWith('/') ? path : `/${path}`
  const q = raw.indexOf('?')
  const h = raw.indexOf('#')
  let end = raw.length
  if (q >= 0) end = Math.min(end, q)
  if (h >= 0) end = Math.min(end, h)
  return raw.slice(0, end) || raw
}

function pathSuffix(path: string): string {
  const raw = path.startsWith('/') ? path : `/${path}`
  const base = normalizeApiPath(raw)
  if (raw.length <= base.length) return ''
  return raw.slice(base.length)
}

export function readActiveExtensionModId(): string {
  try {
    return String(localStorage.getItem(XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY) || '').trim()
  } catch {
    return ''
  }
}

function readInstalledModIds(explicit?: string[]): string[] {
  if (explicit?.length) return explicit.map((id) => String(id || '').trim()).filter(Boolean)
  try {
    const store = useModsStore()
    return (store.mods || []).map((m) => String(m.id || '').trim()).filter(Boolean)
  } catch {
    return []
  }
}

function pathMatchesPrefixes(pathOnly: string, prefixes: readonly string[]): boolean {
  return prefixes.some((prefix) => pathOnly === prefix || pathOnly.startsWith(`${prefix}/`))
}

function resolveErpBaseForClientMod(activeClient: string, installedModIds: string[]): string {
  const ids = installedModIds
  if (ids.includes(activeClient)) {
    return `/api/mod/${activeClient}`
  }
  if (ids.includes(ERP_DOMAIN_BRIDGE_MOD_ID)) {
    return MOD_FACADE_BASE
  }
  return `/api/mod/${activeClient}`
}

function isHostOnlyApiPath(pathOnly: string): boolean {
  if (!pathOnly.startsWith('/api/')) return true
  return HOST_ONLY_API_PREFIXES.some(
    (prefix) => pathOnly === prefix || pathOnly.startsWith(`${prefix}/`),
  )
}

/**
 * ERP 领域 API 根路径（不含尾部路径段）。
 * 优先级：当前选中的客户 Mod > 通用领域门面 Mod > 宿主 /api
 */
function readHostClientPrimaryErpModId(): string {
  const pol = clientModPolicies.value
  return String(pol?.client_primary_erp_mod_id || CLIENT_PRIMARY_ERP_MOD_ID).trim()
}

export function resolveErpApiBase(installedModIds?: string[]): string {
  const ids = readInstalledModIds(installedModIds)
  const activeClient = readActiveExtensionModId()
  if (activeClient && isProtectedClientModId(activeClient)) {
    return resolveErpBaseForClientMod(activeClient, ids)
  }
  const primary = readHostClientPrimaryErpModId()
  if (
    !activeClient &&
    primary &&
    isProtectedClientModId(primary) &&
    ids.includes(primary)
  ) {
    return resolveErpBaseForClientMod(primary, ids)
  }
  if (readErpDomainModFacadeEnabled()) {
    return MOD_FACADE_BASE
  }
  if (ids.includes(LEGACY_CLIENT_ERP_MOD_ID)) {
    return `/api/mod/${LEGACY_CLIENT_ERP_MOD_ID}`
  }
  return '/api'
}

/** 将宿主路径 /api/... 映射到 Mod 门面或保持宿主（与 DOMAIN_SPECS + blueprints 一致） */
export function resolveErpApiPath(hostPath: string, installedModIds?: string[]): string {
  const raw = hostPath.startsWith('/') ? hostPath : `/${hostPath}`
  const pathOnly = normalizeApiPath(raw)
  const suffix = pathSuffix(raw)
  const ids = readInstalledModIds(installedModIds)

  if (isHostOnlyApiPath(pathOnly)) {
    return raw
  }

  const activeClient = readActiveExtensionModId()
  if (activeClient && isProtectedClientModId(activeClient)) {
    if (
      CLIENT_MOD_HOST_ONLY_API_PREFIXES.some(
        (prefix) => pathOnly === prefix || pathOnly.startsWith(`${prefix}/`),
      )
    ) {
      return raw
    }
    let erpBase = resolveErpBaseForClientMod(activeClient, ids)
    if (pathMatchesPrefixes(pathOnly, ERP_ON_BRIDGE_WHEN_CLIENT_ACTIVE)) {
      erpBase = ids.includes(ERP_DOMAIN_BRIDGE_MOD_ID) ? MOD_FACADE_BASE : '/api'
    } else if (!pathMatchesPrefixes(pathOnly, ERP_ON_CLIENT_MOD_PREFIXES)) {
      erpBase = ids.includes(ERP_DOMAIN_BRIDGE_MOD_ID) ? MOD_FACADE_BASE : erpBase
    }
    if (erpBase === '/api') {
      return raw
    }
    if (pathOnly === '/api' || pathOnly.startsWith('/api/')) {
      return `${erpBase}${pathOnly.slice(4)}${suffix}`
    }
  }

  const erpBase = resolveErpApiBase(ids)
  if (erpBase === '/api') {
    return raw
  }

  if (pathOnly === '/api' || pathOnly.startsWith('/api/')) {
    return `${erpBase}${pathOnly.slice(4)}${suffix}`
  }

  for (const [hostPrefix] of ERP_DOMAIN_PREFIX_MAP) {
    if (pathOnly === hostPrefix || pathOnly.startsWith(`${hostPrefix}/`)) {
      return `${erpBase}${pathOnly.slice(4)}${suffix}`
    }
  }

  return raw
}

export function useErpDomainModFacade(): boolean {
  return readErpDomainModFacadeEnabled()
}

/** Mod 门面 HTTP 探针路径 */
export function erpDomainModStatusPath(): string {
  return `${MOD_FACADE_BASE}/status`
}
