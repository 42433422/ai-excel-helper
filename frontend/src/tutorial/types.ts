import type { ModForNavLabel } from '@/utils/coreNavLabel'
import type { VisibleNavItem } from '@/composables/useVisibleNavItems'

export type TutorialActionType = 'click' | 'observe'

export type TutorialTrackId = string

export interface TutorialStep {
  id: string
  title: string
  description: string
  targetSelector: string
  highlightSelector?: string
  actionType: TutorialActionType
  routeName?: string
  assistantTab?: string
  excludeInPro?: boolean
  allowCardNext?: boolean
  noAutoSkipWhenMissing?: boolean
  /** Mod 贡献：插入到某 nav key 之后 */
  afterNavKey?: string
  /** Mod 贡献：所属路线 */
  track?: string
}

export interface TutorialPageHighlight {
  idSuffix: string
  title: string
  description: string
  targetSelector: string
  highlightSelector?: string
}

export interface TutorialTrackMeta {
  id: TutorialTrackId
  title: string
  summary: string
  description: string
  kind: 'curated' | 'nav' | 'mod'
  recommended?: boolean
  modId?: string
}

export interface ModTutorialContribution {
  tracks?: Array<{
    id: string
    title: string
    summary?: string
    description?: string
    requires_mod_menu?: boolean
    recommended?: boolean
  }>
  steps?: Array<TutorialStep & { track?: string; after_nav_key?: string }>
  page_highlights?: Record<string, TutorialPageHighlight[]>
}

export interface TutorialBuildContext {
  industryId: string
  mods: ModForNavLabel[]
  visibleNav: VisibleNavItem[]
  isProMode: boolean
  modMenuKeys: Set<string>
}
