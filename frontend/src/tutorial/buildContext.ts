import type { VisibleNavItem } from '@/composables/useVisibleNavItems'
import type { ModForNavLabel } from '@/utils/coreNavLabel'
import type { TutorialBuildContext } from './types'

export function createTutorialBuildContext(options: {
  industryId: string
  mods: ModForNavLabel[]
  visibleNav: VisibleNavItem[]
  isProMode: boolean
}): TutorialBuildContext {
  const modMenuKeys = new Set<string>()
  for (const item of options.visibleNav) {
    if (item.source === 'mod' && item.key) {
      modMenuKeys.add(item.key)
    }
  }
  return {
    industryId: options.industryId,
    mods: options.mods,
    visibleNav: options.visibleNav,
    isProMode: options.isProMode,
    modMenuKeys,
  }
}
