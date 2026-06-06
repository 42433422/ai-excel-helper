import { describe, expect, it } from 'vitest'
import { resolveApprovalApiPath } from './approvalPaths'

describe('approvalPaths', () => {
  it('keeps host path when facade off', () => {
    localStorage.removeItem('xcagi_approval_mod_facade_enabled')
    expect(resolveApprovalApiPath('/api/approval/requests')).toBe('/api/approval/requests')
  })

  it('maps to mod facade when enabled', () => {
    localStorage.setItem('xcagi_approval_mod_facade_enabled', '1')
    expect(resolveApprovalApiPath('/api/approval/requests')).toBe(
      '/api/mod/xcagi-approval-bridge/requests'
    )
    localStorage.removeItem('xcagi_approval_mod_facade_enabled')
  })
})
