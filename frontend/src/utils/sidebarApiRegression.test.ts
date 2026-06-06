/**
 * 侧栏主导航 API 回归：门面路径与 Mod 路由约定（手工 Network 清单见计划阶段 7）。
 */
import { describe, expect, it, afterEach } from 'vitest'
import { resolveErpApiPath } from './erpDomainPaths'
import { resolveApprovalApiPath } from './approvalPaths'
import { resolveErpPageRedirectForRouteName } from './erpPagePaths'
import { resolveWorkflowPageRedirectForRouteName } from './workflowPagePaths'

const ERP_LS = 'xcagi_erp_domain_mod_facade_enabled'
const APPROVAL_LS = 'xcagi_approval_mod_facade_enabled'
const WORKFLOW_LS = 'xcagi_workflow_viz_mod_pages_enabled'

describe('sidebarApiRegression', () => {
  afterEach(() => {
    localStorage.removeItem(ERP_LS)
    localStorage.removeItem(APPROVAL_LS)
    localStorage.removeItem(WORKFLOW_LS)
  })

  it('core ERP menu APIs map to domain-bridge when facade on', () => {
    localStorage.setItem(ERP_LS, '1')
    const cases: Array<[host: string, expected: string]> = [
      ['/api/products/list', '/api/mod/xcagi-erp-domain-bridge/products/list'],
      ['/api/purchase_units', '/api/mod/xcagi-erp-domain-bridge/purchase_units'],
      ['/api/orders?limit=100', '/api/mod/xcagi-erp-domain-bridge/orders?limit=100'],
      [
        '/api/wechat_contacts/ensure_contact_cache',
        '/api/mod/xcagi-erp-domain-bridge/wechat_contacts/ensure_contact_cache',
      ],
      ['/api/materials', '/api/materials'],
      ['/api/print/templates', '/api/print/templates'],
    ]
    for (const [host, expected] of cases) {
      expect(resolveErpApiPath(host)).toBe(expected)
    }
  })

  it('approval menu uses approval-bridge when facade on', () => {
    localStorage.setItem(APPROVAL_LS, '1')
    expect(resolveApprovalApiPath('/api/approval/requests')).toBe(
      '/api/mod/xcagi-approval-bridge/requests',
    )
  })

  it('host business routes redirect to mod pages when ERP facade on', () => {
    localStorage.setItem(ERP_LS, '1')
    expect(resolveErpPageRedirectForRouteName('products')).toBe(
      '/mod/xcagi-erp-domain-bridge/products',
    )
    expect(resolveErpPageRedirectForRouteName('wechat-contacts')).toBe(
      '/mod/xcagi-erp-domain-bridge/data-sources?source=wechat_local_db',
    )
  })

  it('workflow visualization redirects to visualization-bridge mod when facade on', () => {
    localStorage.setItem(WORKFLOW_LS, '1')
    expect(resolveWorkflowPageRedirectForRouteName('workflow-visualization')).toBe(
      '/mod/xcagi-workflow-visualization-bridge/workflow-visualization',
    )
  })
})
