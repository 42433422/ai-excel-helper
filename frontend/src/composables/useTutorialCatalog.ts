import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useIndustryStore } from '@/stores/industry'
import { useModsStore } from '@/stores/mods'
import { DEFAULT_INDUSTRY_ID } from '@/constants/industryDefaults'
import { useVisibleNavItems } from '@/composables/useVisibleNavItems'
import { createTutorialBuildContext } from '@/tutorial/buildContext'
import { formatAdvancedTrackHint, getTrackMetas } from '@/tutorial/catalog'

export function useTutorialCatalog() {
  const industryStore = useIndustryStore()
  const modsStore = useModsStore()
  const { modsForUi } = storeToRefs(modsStore)
  const { visibleNavItems } = useVisibleNavItems()

  const buildContext = computed(() =>
    createTutorialBuildContext({
      industryId: String(industryStore.currentIndustryId || DEFAULT_INDUSTRY_ID),
      mods: modsForUi.value || [],
      visibleNav: visibleNavItems.value,
      isProMode: !!window.__XCAGI_IS_PRO_MODE,
    }),
  )

  const tutorialTracks = computed(() => getTrackMetas(buildContext.value))

  const advancedNavPreviewNames = computed(() =>
    visibleNavItems.value
      .filter((n) => n.key !== 'settings')
      .map((n) => n.name),
  )

  const advancedTrackHint = computed(() =>
    formatAdvancedTrackHint(advancedNavPreviewNames.value),
  )

  return {
    buildContext,
    tutorialTracks,
    advancedTrackHint,
    visibleNavItems,
  }
}
