import { describe, expect, it, vi } from 'vitest'
import { resolveLanApiPath } from './lanPaths'

describe('lanPaths', () => {
  it('keeps host path when facade off', () => {
    vi.stubGlobal('localStorage', { getItem: () => '0' })
    expect(resolveLanApiPath('/api/lan/status')).toBe('/api/lan/status')
  })

  it('maps to mod facade when enabled', () => {
    vi.stubGlobal('localStorage', { getItem: () => '1' })
    expect(resolveLanApiPath('/api/lan/admin/keys')).toBe(
      '/api/mod/xcagi-lan-license-bridge/lan/admin/keys',
    )
  })
})
