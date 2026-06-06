export type RoleMenuKind = 'enterprise-user' | 'local-admin' | 'personal-user'

export type RoleMenuProfile = {
  role: RoleMenuKind
  canSeeAdminMenus: boolean
  canSeeDeveloperMenus: boolean
  visibleCoreKeys: Set<string> | null
}

export type AccountRoleSource = {
  accountKind?: string
  marketIsAdmin?: boolean
  marketIsEnterprise?: boolean
  isAdminAccount?: boolean
}

const ENTERPRISE_GENERIC_CORE_KEYS = new Set([
  'chat',
  'ai-ecosystem',
  'mod-store',
  'data-sources',
  'printer-list',
  'template-preview',
  'tools',
  'other-tools',
  'workflow-employee-space',
])

const ENTERPRISE_BUSINESS_CORE_KEYS = new Set([
  'products',
  'materials',
  'materials-list',
  'traditional-mode',
  'orders',
  'orders-create',
  'shipment-records',
  'customers',
  'print',
  'approval-hub',
  'enterprise-customer-service',
])

export function buildRoleMenuProfile(
  source: AccountRoleSource,
  hasIndustryBusinessMod = false,
): RoleMenuProfile {
  const isAdmin =
    source.isAdminAccount === true ||
    (source.accountKind === 'admin' && source.marketIsAdmin === true)
  if (isAdmin) {
    return {
      role: 'local-admin',
      canSeeAdminMenus: true,
      canSeeDeveloperMenus: true,
      visibleCoreKeys: null,
    }
  }

  const isEnterprise =
    source.accountKind === 'enterprise' || source.marketIsEnterprise === true
  if (!isEnterprise) {
    return {
      role: 'personal-user',
      canSeeAdminMenus: false,
      canSeeDeveloperMenus: false,
      visibleCoreKeys: null,
    }
  }

  const visibleCoreKeys = new Set(ENTERPRISE_GENERIC_CORE_KEYS)
  if (hasIndustryBusinessMod) {
    for (const key of ENTERPRISE_BUSINESS_CORE_KEYS) visibleCoreKeys.add(key)
  }
  return {
    role: 'enterprise-user',
    canSeeAdminMenus: false,
    canSeeDeveloperMenus: false,
    visibleCoreKeys,
  }
}

export function canShowCoreMenuKey(profile: RoleMenuProfile, key: string): boolean {
  const allowed = profile.visibleCoreKeys
  if (!allowed) return true
  return allowed.has(String(key || '').trim())
}
