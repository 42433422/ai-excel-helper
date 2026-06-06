import { describe, expect, it, vi } from 'vitest'
import { resolveModelPaymentApiPath } from './modelPaymentPaths'

describe('modelPaymentPaths', () => {
  it('keeps host path when facade off', () => {
    vi.stubGlobal('localStorage', { getItem: () => '0' })
    expect(resolveModelPaymentApiPath('/api/model-payment/plans')).toBe('/api/model-payment/plans')
  })

  it('maps to mod facade when enabled', () => {
    vi.stubGlobal('localStorage', { getItem: () => '1' })
    expect(resolveModelPaymentApiPath('/api/model-payment/checkout')).toBe(
      '/api/mod/xcagi-model-payment-bridge/model-payment/checkout',
    )
  })
})
