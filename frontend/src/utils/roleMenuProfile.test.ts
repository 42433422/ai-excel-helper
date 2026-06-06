import { describe, expect, it } from 'vitest'
import { buildRoleMenuProfile, canShowCoreMenuKey } from '@/utils/roleMenuProfile'

describe('roleMenuProfile', () => {
  it('keeps enterprise users on the generic host menu without an industry mod', () => {
    const profile = buildRoleMenuProfile({ accountKind: 'enterprise', marketIsEnterprise: true })

    expect(profile.role).toBe('enterprise-user')
    expect(canShowCoreMenuKey(profile, 'chat')).toBe(true)
    expect(canShowCoreMenuKey(profile, 'mod-store')).toBe(true)
    expect(canShowCoreMenuKey(profile, 'products')).toBe(false)
    expect(canShowCoreMenuKey(profile, 'orders')).toBe(false)
  })

  it('allows industry business slots only when an industry mod is active', () => {
    const profile = buildRoleMenuProfile(
      { accountKind: 'enterprise', marketIsEnterprise: true },
      true,
    )

    expect(canShowCoreMenuKey(profile, 'products')).toBe(true)
    expect(canShowCoreMenuKey(profile, 'orders')).toBe(true)
  })

  it('does not restrict local admin menus', () => {
    const profile = buildRoleMenuProfile({ accountKind: 'admin', marketIsAdmin: true })

    expect(profile.canSeeAdminMenus).toBe(true)
    expect(canShowCoreMenuKey(profile, 'products')).toBe(true)
    expect(canShowCoreMenuKey(profile, 'orders')).toBe(true)
  })
})
