import type { TutorialPageHighlight, TutorialStep } from './types'

export const createStep = (step: TutorialStep): TutorialStep => ({
  ...step,
  excludeInPro: step.excludeInPro ?? true,
})

export const advancedSidebarNavStep = (
  viewKey: string,
  title: string,
  description: string,
): TutorialStep =>
  createStep({
    id: `nav-${viewKey.replace(/[^a-z0-9-]/gi, '-')}`,
    title,
    description,
    targetSelector: `.sidebar .menu-item[data-view="${viewKey}"]`,
    actionType: 'click',
    allowCardNext: true,
    excludeInPro: false,
  })

export const advancedPageFeaturesStep = (
  idSuffix: string,
  routeName: string,
  title: string,
  description: string,
  targetSelector: string,
  highlightSelector?: string,
): TutorialStep =>
  createStep({
    id: `page-${routeName}-${idSuffix}`,
    title,
    description,
    targetSelector,
    highlightSelector: highlightSelector || targetSelector,
    actionType: 'observe',
    routeName,
    excludeInPro: false,
    allowCardNext: true,
    noAutoSkipWhenMissing: true,
  })

export function pageHighlightToStep(
  routeName: string,
  highlight: TutorialPageHighlight,
): TutorialStep {
  return advancedPageFeaturesStep(
    highlight.idSuffix,
    routeName,
    highlight.title,
    highlight.description,
    highlight.targetSelector,
    highlight.highlightSelector,
  )
}

export const fallbackPageObserveStep = (
  routeName: string,
  menuLabel: string,
): TutorialStep =>
  createStep({
    id: `page-${routeName}-overview`,
    title: `${menuLabel} · 页面概览`,
    description: `已进入「${menuLabel}」。请浏览本页主要区域；不熟悉时可点卡片「下一步」继续。`,
    targetSelector: `#view-${routeName} .page-content, #view-${routeName} .page-header`,
    highlightSelector: `#view-${routeName} .page-content`,
    actionType: 'observe',
    routeName,
    excludeInPro: false,
    allowCardNext: true,
    noAutoSkipWhenMissing: true,
  })
