import { describe, expect, it, vi } from 'vitest'
import { resolveApprovalPagePath, resolveApprovalPageRedirectForRouteName } from './approvalPagePaths'

describe('approvalPagePaths', () => {
  it('maps approval hub when facade on', () => {
    vi.stubGlobal('localStorage', { getItem: () => '1' })
    expect(resolveApprovalPagePath('/approval-hub/workspace')).toBe(
      '/mod/xcagi-approval-bridge/approval-hub/workspace',
    )
    expect(resolveApprovalPageRedirectForRouteName('approval-workspace')).toBe(
      '/mod/xcagi-approval-bridge/approval-hub/workspace',
    )
  })
})
