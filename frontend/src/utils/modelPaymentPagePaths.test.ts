import { describe, expect, it, vi } from 'vitest'
import { resolveModelPaymentPagePath } from './modelPaymentPagePaths'

describe('modelPaymentPagePaths', () => {
  it('maps model-payment page when facade on', () => {
    vi.stubGlobal('localStorage', { getItem: () => '1' })
    expect(resolveModelPaymentPagePath('/model-payment')).toBe(
      '/settings?section=model-payment',
    )
    expect(resolveModelPaymentPagePath('/kitten-finance')).toBe(
      '/mod/xcagi-model-payment-bridge/kitten-finance',
    )
  })
})
