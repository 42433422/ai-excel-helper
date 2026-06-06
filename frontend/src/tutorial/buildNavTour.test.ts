import { describe, expect, it } from 'vitest'
import { buildAdvancedNavSteps } from './buildNavTour'
import { createTutorialBuildContext } from './buildContext'
import type { VisibleNavItem } from '@/composables/useVisibleNavItems'

const nav = (rows: Array<{ key: string; name: string; routeName: string }>): VisibleNavItem[] =>
  rows.map((r) => ({
    key: r.key,
    name: r.name,
    routeName: r.routeName,
    source: 'core',
  }))

describe('buildAdvancedNavSteps', () => {
  it('starts with sidebar scan and generates nav steps in visible order', () => {
    const visibleNav = nav([
      { key: 'chat', name: '智能对话', routeName: 'chat' },
      { key: 'products', name: '人员管理', routeName: 'products' },
    ])
    const ctx = createTutorialBuildContext({
      industryId: '考勤',
      mods: [],
      visibleNav,
      isProMode: false,
    })
    const steps = buildAdvancedNavSteps(visibleNav, ctx)
    expect(steps[0]?.id).toBe('advanced-sidebar-scan')
    expect(steps.some((s) => s.id === 'nav-chat')).toBe(true)
    expect(steps.some((s) => s.id === 'nav-products')).toBe(true)
    expect(steps.some((s) => s.id === 'page-chat-quick')).toBe(true)
    const chatIdx = steps.findIndex((s) => s.id === 'nav-chat')
    const productsIdx = steps.findIndex((s) => s.id === 'nav-products')
    expect(chatIdx).toBeGreaterThan(0)
    expect(productsIdx).toBeGreaterThan(chatIdx)
  })

  it('does not include print route when not in visible nav', () => {
    const visibleNav = nav([{ key: 'printer-list', name: '打印机列表', routeName: 'printer-list' }])
    const ctx = createTutorialBuildContext({
      industryId: '考勤',
      mods: [],
      visibleNav,
      isProMode: false,
    })
    const steps = buildAdvancedNavSteps(visibleNav, ctx)
    expect(steps.some((s) => s.routeName === 'print')).toBe(false)
    expect(steps.some((s) => /#view-print(\s|\.|$)/.test(String(s.targetSelector || '')))).toBe(false)
  })
})
