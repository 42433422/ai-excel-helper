import { describe, expect, it, vi } from 'vitest'
import {
  customerServiceHostPathFromModPath,
  resolveCustomerServicePagePath,
} from './customerServicePagePaths'

describe('customerServicePagePaths', () => {
  it('maps customer service pages when mod pages enabled', () => {
    vi.stubGlobal('localStorage', { getItem: () => '1' })
    expect(resolveCustomerServicePagePath('/enterprise-customer-service')).toBe(
      '/mod/xcagi-customer-service-bridge/enterprise-customer-service',
    )
  })

  it('maps mod customer service paths back to host paths', () => {
    expect(
      customerServiceHostPathFromModPath(
        '/mod/xcagi-customer-service-bridge/enterprise-customer-service',
      ),
    ).toBe('/enterprise-customer-service')
    expect(
      customerServiceHostPathFromModPath(
        '/mod/xcagi-customer-service-bridge/internal-customer-service',
      ),
    ).toBe('/internal-customer-service')
  })
})
