import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  bootstrapEditionDefaults,
  bootstrapGenericEditionDefaults,
  bootstrapMinimalEditionDefaults,
  isGenericEditionBuild,
  isHostBusinessMenuKey,
  isMinimalEditionBuild,
  isPlatformShellModeEnabled,
  LS_PLATFORM_SHELL_MODE,
  SHELL_CORE_MENU_KEYS,
} from './platformShellMode'

describe('platformShellMode', () => {
  it('shell core includes chat and mod-store', () => {
    expect(SHELL_CORE_MENU_KEYS.has('chat')).toBe(true)
    expect(SHELL_CORE_MENU_KEYS.has('mod-store')).toBe(true)
  })

  it('host business keys are not shell core', () => {
    expect(isHostBusinessMenuKey('products')).toBe(true)
    expect(isHostBusinessMenuKey('shipment-records')).toBe(true)
    expect(SHELL_CORE_MENU_KEYS.has('products')).toBe(false)
  })

  describe('generic edition (milestone I)', () => {
    afterEach(() => {
      vi.unstubAllEnvs()
      localStorage.clear()
    })

    it('isGenericEditionBuild reads VITE_XCAGI_DEFAULT_PLATFORM_SHELL', () => {
      vi.stubEnv('VITE_XCAGI_EDITION', 'generic')
      vi.stubEnv('VITE_XCAGI_DEFAULT_PLATFORM_SHELL', '1')
      expect(isGenericEditionBuild()).toBe(true)
    })

    it('bootstrap sets shell mode in localStorage', () => {
      vi.stubEnv('VITE_XCAGI_EDITION', 'generic')
      vi.stubEnv('VITE_XCAGI_DEFAULT_PLATFORM_SHELL', '1')
      vi.stubEnv('VITE_XCAGI_PRODUCT_SKU', '')
      bootstrapGenericEditionDefaults()
      expect(localStorage.getItem(LS_PLATFORM_SHELL_MODE)).toBe('1')
      expect(isPlatformShellModeEnabled()).toBe(true)
    })

    it('bootstrap respects user opt-out', () => {
      vi.stubEnv('VITE_XCAGI_DEFAULT_PLATFORM_SHELL', '1')
      localStorage.setItem(LS_PLATFORM_SHELL_MODE, '0')
      bootstrapEditionDefaults()
      expect(localStorage.getItem(LS_PLATFORM_SHELL_MODE)).toBe('0')
      expect(isPlatformShellModeEnabled()).toBe(false)
    })
  })

  describe('minimal edition (milestone Q)', () => {
    afterEach(() => {
      vi.unstubAllEnvs()
      localStorage.clear()
    })

    it('isMinimalEditionBuild reads VITE_XCAGI_EDITION', () => {
      vi.stubEnv('VITE_XCAGI_EDITION', 'minimal')
      vi.stubEnv('VITE_XCAGI_DEFAULT_PLATFORM_SHELL', '1')
      vi.stubEnv('VITE_XCAGI_PRODUCT_SKU', '')
      expect(isMinimalEditionBuild()).toBe(true)
      expect(isPlatformShellModeEnabled()).toBe(true)
    })

    it('bootstrapMinimal sets shell mode', () => {
      vi.stubEnv('VITE_XCAGI_EDITION', 'minimal')
      vi.stubEnv('VITE_XCAGI_DEFAULT_PLATFORM_SHELL', '1')
      bootstrapMinimalEditionDefaults()
      expect(localStorage.getItem(LS_PLATFORM_SHELL_MODE)).toBe('1')
    })
  })
})
