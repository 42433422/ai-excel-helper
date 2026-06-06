import { describe, expect, it } from 'vitest'
import { mergeSidebarMenuItems } from './mergeSidebarMenuItems'

describe('mergeSidebarMenuItems', () => {
  it('drops mod customer-service when trailing host keys exist', () => {
    const core = [{ key: 'products', name: '人员', iconClass: 'fa-cubes' }]
    const mod = [
      {
        key: 'mod-enterprise-customer-service',
        name: '外部客服',
        iconClass: 'fa-headphones',
        modId: 'xcagi-customer-service-bridge',
        path: '/mod/xcagi-customer-service-bridge/enterprise-customer-service',
      },
    ]
    const trailing = [
      { key: 'enterprise-customer-service', name: '外部客服', iconClass: 'fa-headphones' },
      { key: 'internal-customer-service', name: '内部客服', iconClass: 'fa-headphones' },
    ]
    const merged = mergeSidebarMenuItems(core, mod, [], trailing, ['taiyangniao-pro'])
    const keys = merged.map((m) => m.key)
    expect(keys).not.toContain('mod-enterprise-customer-service')
    expect(keys.filter((k) => k === 'enterprise-customer-service')).toHaveLength(1)
    expect(keys.filter((k) => k === 'internal-customer-service')).toHaveLength(1)
  })

  it('drops mod item when key uses erroneous mod-mod- prefix', () => {
    const trailing = [
      { key: 'internal-customer-service', name: '内部客服', iconClass: 'fa-headphones' },
    ]
    const mod = [
      {
        key: 'mod-mod-internal-customer-service',
        name: '内部客服',
        iconClass: 'fa-headphones',
        modId: 'xcagi-customer-service-bridge',
        path: '/mod/xcagi-customer-service-bridge/internal-customer-service',
      },
    ]
    const merged = mergeSidebarMenuItems([], mod, [], trailing, [])
    expect(merged.map((m) => m.key)).toEqual(['internal-customer-service'])
  })

  it('hides mod-workflow-visualization when client primary erp installed', () => {
    const core = [{ key: 'approval-hub', name: '审批中心', iconClass: 'fa-check-square-o' }]
    const mod = [
      {
        key: 'mod-workflow-visualization',
        name: '流程可视化',
        iconClass: 'fa-project-diagram',
        modId: 'xcagi-workflow-visualization-bridge',
        path: '/mod/xcagi-workflow-visualization-bridge/workflow-visualization',
      },
    ]
    const merged = mergeSidebarMenuItems(core, mod, [], [], ['taiyangniao-pro'])
    expect(merged.map((m) => m.key)).toEqual(['approval-hub'])
  })

  it('hides planner-brain when active extension is taiyangniao-pro (even without bridge list)', () => {
    const mod = [
      {
        key: 'mod-planner-brain',
        name: '智脑集成',
        iconClass: 'fa-brain',
        modId: 'xcagi-planner-bridge',
        path: '/mod/xcagi-planner-bridge/brain',
      },
      {
        key: 'mod-workflow-visualization',
        name: '流程可视化',
        iconClass: 'fa-project-diagram',
        modId: 'xcagi-workflow-visualization-bridge',
        path: '/mod/xcagi-workflow-visualization-bridge/workflow-visualization',
      },
    ]
    const merged = mergeSidebarMenuItems([], mod, [], [], [], 'taiyangniao-pro')
    expect(merged.map((m) => m.key)).toEqual([])
  })

  it('hides mod-kitten-finance in full host sidebar', () => {
    const mod = [
      {
        key: 'mod-kitten-finance',
        name: '财务分析',
        iconClass: 'fa-line-chart',
        modId: 'xcagi-model-payment-bridge',
        path: '/mod/xcagi-model-payment-bridge/kitten-finance',
      },
    ]
    const merged = mergeSidebarMenuItems([], mod, [], [], [])
    expect(merged.map((m) => m.key)).toEqual([])
  })

  it('hides workflow and planner brain in full host sidebar without client erp signals', () => {
    const core = [{ key: 'approval-hub', name: '审批中心', iconClass: 'fa-check-square-o' }]
    const mod = [
      {
        key: 'mod-workflow-visualization',
        name: '流程可视化',
        iconClass: 'fa-project-diagram',
        modId: 'xcagi-workflow-visualization-bridge',
        path: '/mod/xcagi-workflow-visualization-bridge/workflow-visualization',
      },
      {
        key: 'mod-planner-brain',
        name: '智脑集成',
        iconClass: 'fa-brain',
        modId: 'xcagi-planner-bridge',
        path: '/mod/xcagi-planner-bridge/brain',
      },
    ]
    const merged = mergeSidebarMenuItems(core, mod, [], [], [])
    expect(merged.map((m) => m.key)).toEqual(['approval-hub'])
  })

  it('drops erp bridge mod rows when host core slots already exist (client ERP)', () => {
    const core = [
      { key: 'products', name: '人员管理', iconClass: 'fa-cubes' },
      { key: 'orders', name: '考勤单管理', iconClass: 'fa-file-text-o' },
      { key: 'tools', name: '工具表', iconClass: 'fa-wrench' },
    ]
    const mod = [
      {
        key: 'mod-erp-products',
        name: '人员管理',
        iconClass: 'fa-cubes',
        modId: 'xcagi-erp-domain-bridge',
        path: '/mod/xcagi-erp-domain-bridge/products',
      },
      {
        key: 'mod-erp-orders',
        name: '考勤单管理',
        iconClass: 'fa-file-text-o',
        modId: 'xcagi-erp-domain-bridge',
        path: '/mod/xcagi-erp-domain-bridge/orders',
      },
      {
        key: 'mod-office-tools',
        name: '工具',
        iconClass: 'fa-wrench',
        modId: 'xcagi-office-employee-pack-bridge',
        path: '/mod/xcagi-office-employee-pack-bridge/tools',
      },
    ]
    const merged = mergeSidebarMenuItems(core, mod, [], [], ['taiyangniao-pro', 'xcagi-erp-domain-bridge'], 'taiyangniao-pro')
    const keys = merged.map((m) => m.key)
    expect(keys).toEqual(['products', 'orders', 'tools'])
    expect(new Set(keys).size).toBe(keys.length)
  })

  it('dedupes duplicate keys', () => {
    const mod = [
      { key: 'mod-approval-hub', name: '审批', iconClass: 'fa-check', modId: 'xcagi-approval-bridge' },
      { key: 'mod-approval-hub', name: '审批', iconClass: 'fa-check', modId: 'xcagi-approval-bridge' },
    ]
    const core = [{ key: 'approval-hub', name: '审批中心', iconClass: 'fa-check-square-o' }]
    const merged = mergeSidebarMenuItems(core, mod, [], [], [])
    expect(merged.map((m) => m.key)).toEqual(['approval-hub'])
  })
})
