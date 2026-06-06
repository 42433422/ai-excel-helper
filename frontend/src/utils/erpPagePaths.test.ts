import { describe, expect, it, vi } from 'vitest'
import { resolveErpPagePath, resolveErpPageRedirectForRouteName } from './erpPagePaths'

describe('erpPagePaths', () => {
  it('keeps host path when facade off', () => {
    vi.stubGlobal('localStorage', { getItem: () => '0' })
    expect(resolveErpPagePath('/products')).toBe('/products')
  })

  it('maps to mod page when facade on', () => {
    vi.stubGlobal('localStorage', { getItem: () => '1' })
    expect(resolveErpPagePath('/products')).toBe('/mod/xcagi-erp-domain-bridge/products')
    expect(resolveErpPagePath('/print')).toBe('/mod/xcagi-erp-domain-bridge/print')
    expect(resolveErpPageRedirectForRouteName('customers')).toBe(
      '/mod/xcagi-erp-domain-bridge/customers',
    )
    expect(resolveErpPageRedirectForRouteName('materials-list')).toBe(
      '/mod/xcagi-erp-domain-bridge/materials',
    )
  })
})
