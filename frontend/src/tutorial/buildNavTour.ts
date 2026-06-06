import type { VisibleNavItem } from '@/composables/useVisibleNavItems'
import type { TutorialBuildContext, TutorialPageHighlight, TutorialStep } from './types'
import {
  advancedSidebarNavStep,
  createStep,
  fallbackPageObserveStep,
  pageHighlightToStep,
} from './stepFactory'
import { HOST_PAGE_HIGHLIGHTS, mergePageHighlights } from './pageHighlights'
import { collectModPageHighlights } from './buildModSteps'

const NAV_ENTRY_INTRO: Partial<Record<string, string>> = {
  chat: '主工作台：查价、发货单、任务与打印等多从这里开始；右侧常有「当前任务」，顶栏可开副窗。',
  'data-sources': '微信缓存、搜索、星标与列表维护；选中微信本地数据库适配器后可操作联系人。',
}

function navEntryDescription(item: VisibleNavItem): string {
  const hint = NAV_ENTRY_INTRO[item.routeName] || NAV_ENTRY_INTRO[item.key]
  if (hint) {
    return `【入口】${hint}请点击「${item.name}」进入（或点卡片「下一步」）。`
  }
  return `【入口】了解「${item.name}」模块。请点击侧栏「${item.name}」（或点卡片「下一步」）。`
}

export function buildAdvancedIntroStep(): TutorialStep {
  return createStep({
    id: 'advanced-sidebar-scan',
    title: '侧栏菜单 · 怎么用这条路线',
    description:
      '先点侧栏进入模块，再在同一页用多个高亮分区依次介绍顶栏、筛选、表格等（洞口落在对应区域，避免整块主区看起来像「还在讲侧栏」）。任一步可点卡片「下一步」略过。',
    targetSelector: '.sidebar .sidebar-menu',
    actionType: 'observe',
    routeName: 'chat',
    excludeInPro: false,
  })
}

export function buildAdvancedNavSteps(
  visibleNav: VisibleNavItem[],
  ctx: TutorialBuildContext,
): TutorialStep[] {
  const pageMap = mergePageHighlights(HOST_PAGE_HIGHLIGHTS, collectModPageHighlights(ctx))
  const steps: TutorialStep[] = [buildAdvancedIntroStep()]

  for (const item of visibleNav) {
    if (item.source === 'child') {
      steps.push(
        advancedSidebarNavStep(item.key, item.name, navEntryDescription(item)),
      )
      appendPageSteps(steps, item.routeName, item.name, pageMap)
      continue
    }
    if (item.key === 'settings') {
      steps.push(
        advancedSidebarNavStep(item.key, item.name, `【入口】行业、意图与其它系统项。请点击「${item.name}」。`),
      )
      appendPageSteps(steps, item.routeName, item.name, pageMap)
      continue
    }
    steps.push(advancedSidebarNavStep(item.key, item.name, navEntryDescription(item)))
    appendPageSteps(steps, item.routeName, item.name, pageMap)
  }

  return steps
}

function appendPageSteps(
  steps: TutorialStep[],
  routeName: string,
  menuLabel: string,
  pageMap: Record<string, TutorialPageHighlight[]>,
) {
  const route = String(routeName || '').trim()
  if (!route) return
  const highlights = pageMap[route]
  if (highlights?.length) {
    for (const h of highlights) {
      steps.push(pageHighlightToStep(route, h))
    }
    return
  }
  steps.push(fallbackPageObserveStep(route, menuLabel))
}
