import { computed, type ComputedRef } from 'vue'
import { storeToRefs } from 'pinia'
import { useIndustryStore } from '@/stores/industry'
import { useModsStore } from '@/stores/mods'
import { DEFAULT_INDUSTRY_ID } from '@/constants/industryDefaults'
import { resolveCoreNavLabel } from '@/utils/coreNavLabel'

/** 与侧栏、Mod `menu_overrides` 一致的菜单展示名（用于页内 h2、说明文案等） */
export function useCoreNavLabel(menuKey: string): ComputedRef<string> {
  const industryStore = useIndustryStore()
  const modsStore = useModsStore()
  const { modsForUi } = storeToRefs(modsStore)
  return computed(() =>
    resolveCoreNavLabel(
      menuKey,
      String(industryStore.currentIndustryId || DEFAULT_INDUSTRY_ID),
      modsForUi.value,
    ),
  )
}
