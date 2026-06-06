import { describe, expect, it, vi } from 'vitest'
import {
  GENERIC_HOST_MOD_IDS,
  isHostMountedModMenuPath,
  keepHostNavKeyVisibleWhenModSidebarFacetSuppressed,
  MINIMAL_HOST_MOD_IDS,
  shouldAutoEnableMinimalPlatformShell,
  shouldAutoEnablePlatformShell,
} from './genericModPack'

describe('genericModPack', () => {
  it('minimal pack is subset of generic', () => {
    for (const mid of MINIMAL_HOST_MOD_IDS) {
      expect(GENERIC_HOST_MOD_IDS).toContain(mid)
    }
  })

  it('shouldAutoEnableMinimalPlatformShell when minimal mods installed', () => {
    expect(shouldAutoEnableMinimalPlatformShell([...MINIMAL_HOST_MOD_IDS])).toBe(true)
    expect(shouldAutoEnableMinimalPlatformShell(['xcagi-planner-bridge'])).toBe(false)
  })

  it('respects client primary ERP without domain bridge', () => {
    expect(
      shouldAutoEnableMinimalPlatformShell(['taiyangniao-pro', ...MINIMAL_HOST_MOD_IDS]),
    ).toBe(false)
    const partialGeneric = GENERIC_HOST_MOD_IDS.filter((id) => id !== 'xcagi-erp-domain-bridge')
    expect(
      shouldAutoEnablePlatformShell(['taiyangniao-pro', ...partialGeneric]),
    ).toBe(false)
  })

  it('keeps host chat when planner mod facet is suppressed in client ERP', () => {
    const installed = ['taiyangniao-pro', 'xcagi-planner-bridge', ...MINIMAL_HOST_MOD_IDS]
    expect(
      keepHostNavKeyVisibleWhenModSidebarFacetSuppressed(
        'chat',
        installed,
        'taiyangniao-pro',
      ),
    ).toBe(true)
    expect(
      keepHostNavKeyVisibleWhenModSidebarFacetSuppressed(
        'ai-ecosystem',
        installed,
        'taiyangniao-pro',
      ),
    ).toBe(true)
    expect(
      keepHostNavKeyVisibleWhenModSidebarFacetSuppressed('kitten-finance', installed, 'taiyangniao-pro'),
    ).toBe(true)
  })

  it('isHostMountedModMenuPath accepts pro_entry_path and host keys', () => {
    expect(isHostMountedModMenuPath('/wechat-contacts', '/wechat-contacts')).toBe(true)
    expect(isHostMountedModMenuPath('/chat', null)).toBe(true)
    expect(isHostMountedModMenuPath('/mod/foo/bar', '/wechat-contacts')).toBe(false)
  })

  it('readBuildEdition from env', async () => {
    vi.stubEnv('VITE_XCAGI_EDITION', 'minimal')
    const { readBuildEdition } = await import('./genericModPack')
    expect(readBuildEdition()).toBe('minimal')
    vi.unstubAllEnvs()
  })
})
