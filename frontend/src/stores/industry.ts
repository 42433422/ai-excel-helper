import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { systemApi } from '@/api/system'
import { useModsStore } from '@/stores/mods'
import { DEFAULT_INDUSTRY_ID } from '@/constants/industryDefaults'

interface Industry {
  id: number | string;
  name: string;
  code: string;
  description?: string;
  config?: any;
  [key: string]: any;
}

/**
 * 把当前 modsStore.mods 中已声明的 manifest.industry 合并进 industries.value。
 * server 来源的优先（按 id 去重时 server 先到不被覆盖），mod 仅作为兜底，
 * 修复"后端 _mod_industries_dict 返回空、/api/system/industries 落到 YAML 兜底
 * 但前端能从 /api/mods/ 看到 mod 行业"造成的下拉缺项问题。
 */
function mergeModIndustriesInto(
  base: Industry[],
  modList: ReadonlyArray<Record<string, any>>,
): Industry[] {
  const out: Industry[] = Array.isArray(base) ? [...base] : []
  const seen = new Set(out.map((ind) => String(ind.id ?? '').trim()).filter(Boolean))
  for (const mod of modList) {
    const ind = mod && typeof mod === 'object' ? (mod as any).industry : null
    if (!ind || typeof ind !== 'object') continue
    const id = String(ind.id ?? '').trim()
    if (!id || seen.has(id)) continue
    seen.add(id)
    out.push({
      id,
      name: String(ind.name ?? id),
      code: id,
      description: typeof ind.description === 'string' ? ind.description : '',
      config: {
        units: ind.units ?? {},
        quantity_fields: ind.quantity_fields ?? {},
        product_fields: ind.product_fields ?? {},
        order_types: ind.order_types ?? {},
        intent_keywords: ind.intent_keywords ?? {},
        print_config: ind.print_config ?? {},
      },
      // 同时把原始 manifest.industry 放在顶层，方便 useIndustryUiText 复用
      units: ind.units ?? {},
      quantity_fields: ind.quantity_fields ?? {},
      product_fields: ind.product_fields ?? {},
      order_types: ind.order_types ?? {},
      intent_keywords: ind.intent_keywords ?? {},
      print_config: ind.print_config ?? {},
    })
  }
  return out
}

export const useIndustryStore = defineStore('industry', () => {
  const industries = ref<Industry[]>([])
  const currentIndustry = ref<Industry | null>(null)
  const currentConfig = ref<any>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  let initInFlight: Promise<void> | null = null

  const currentIndustryName = computed(() => {
    return currentIndustry.value?.name || '未知'
  })

  const currentIndustryId = computed(() => {
    return currentIndustry.value?.id?.toString() || DEFAULT_INDUSTRY_ID
  })

  const primaryUnit = computed(() => {
    return currentConfig.value?.units?.primary || '天'
  })

  const primaryLabel = computed(() => {
    return currentConfig.value?.quantity_fields?.primary_label || '出勤天数'
  })

  const isLoaded = computed(() => {
    return currentIndustry.value !== null
  })

  /** 从 modsStore 当前选中的 mod 取 manifest.industry，找不到时返回 null */
  function activeModIndustryConfig(): any | null {
    try {
      const modsStore = useModsStore()
      const activeId = String(modsStore.activeModId || '').trim()
      const list = Array.isArray(modsStore.mods) ? modsStore.mods : []
      const exact = activeId
        ? list.find((m: any) => String(m?.id || '').trim() === activeId)
        : null
      const candidate = exact || list[0] || null
      const ind = candidate && (candidate as any).industry
      return ind && typeof ind === 'object' ? ind : null
    } catch {
      return null
    }
  }

  async function loadIndustries() {
    loading.value = true
    error.value = null

    try {
      const response = await systemApi.getIndustries()
      let serverIndustries: Industry[] = []
      if (response.success && response.data) {
        serverIndustries = (response.data as any).industries || []
      }
      let modList: ReadonlyArray<Record<string, any>> = []
      try {
        const modsStore = useModsStore()
        modList = Array.isArray(modsStore.mods) ? modsStore.mods : []
      } catch {
        modList = []
      }
      industries.value = mergeModIndustriesInto(serverIndustries, modList)
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载行业列表失败'
      console.error('Failed to load industries:', err)
      // server 列表失败时，至少把 mod manifest 行业暴露出来
      try {
        const modsStore = useModsStore()
        const modList = Array.isArray(modsStore.mods) ? modsStore.mods : []
        industries.value = mergeModIndustriesInto([], modList)
      } catch {
        // ignore
      }
    } finally {
      loading.value = false
    }
  }

  async function loadCurrentIndustry() {
    loading.value = true
    error.value = null

    try {
      const response = await systemApi.getCurrentIndustry()
      if (response.success && response.data) {
        currentIndustry.value = response.data as Industry
        currentConfig.value = response.data
      } else {
        // server 没给当前行业时，用当前 active mod 的 manifest.industry 兜底，
        // 让 primaryUnit / intent_keywords 至少能跟着 mod 选择走。
        const modInd = activeModIndustryConfig()
        if (modInd) {
          const id = String(modInd.id || '').trim()
          if (id) {
            const fallback: Industry = {
              id,
              name: String(modInd.name || id),
              code: id,
              description: typeof modInd.description === 'string' ? modInd.description : '',
              config: modInd,
              ...modInd,
            }
            currentIndustry.value = fallback
            currentConfig.value = fallback
          }
        }
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载当前行业失败'
      console.error('Failed to load current industry:', err)
      const modInd = activeModIndustryConfig()
      if (modInd) {
        const id = String(modInd.id || '').trim()
        if (id) {
          const fallback: Industry = {
            id,
            name: String(modInd.name || id),
            code: id,
            description: typeof modInd.description === 'string' ? modInd.description : '',
            config: modInd,
            ...modInd,
          }
          currentIndustry.value = fallback
          currentConfig.value = fallback
        }
      }
    } finally {
      loading.value = false
    }
  }

  async function switchIndustry(industryId: number | string): Promise<boolean> {
    loading.value = true
    error.value = null

    try {
      const response = await systemApi.setIndustry(industryId)
      if (response.success) {
        await loadCurrentIndustry()
        return true
      } else {
        error.value = response.message || '切换行业失败'
        return false
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : '切换行业失败'
      console.error('Failed to switch industry:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  async function initialize(force = false) {
    if (isLoaded.value && !force) {
      return
    }
    if (initInFlight) {
      await initInFlight
      return
    }
    initInFlight = (async () => {
      await loadIndustries()
      await loadCurrentIndustry()
    })()
    try {
      await initInFlight
    } finally {
      initInFlight = null
    }
  }

  function getIndustryById(id: number | string): Industry | null {
    return industries.value.find(ind => ind.id === id) || null
  }

  return {
    industries,
    currentIndustry,
    currentConfig,
    loading,
    error,
    currentIndustryName,
    currentIndustryId,
    primaryUnit,
    primaryLabel,
    isLoaded,
    loadIndustries,
    loadCurrentIndustry,
    switchIndustry,
    initialize,
    getIndustryById
  }
})

export default useIndustryStore
