import { defineStore } from 'pinia'
import { ref, computed, type Ref } from 'vue'
import { systemApi } from '@/api/system'

interface Industry {
  id: number | string;
  name: string;
  code: string;
  description?: string;
  config?: any;
  [key: string]: any;
}

interface IndustryState {
  industries: Industry[];
  currentIndustry: Industry | null;
  currentConfig: any;
  loading: boolean;
  error: string | null;
}

export const useIndustryStore = defineStore('industry', () => {
  const industries = ref<Industry[]>([])
  const currentIndustry = ref<Industry | null>(null)
  const currentConfig = ref<any>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const currentIndustryName = computed(() => {
    return currentIndustry.value?.name || '未知'
  })

  const currentIndustryId = computed(() => {
    return currentIndustry.value?.id?.toString() || '涂料'
  })

  const primaryUnit = computed(() => {
    return currentConfig.value?.units?.primary || '桶'
  })

  const primaryLabel = computed(() => {
    return currentConfig.value?.quantity_fields?.primary_label || '桶数'
  })

  const isLoaded = computed(() => {
    return currentIndustry.value !== null
  })

  async function loadIndustries() {
    loading.value = true
    error.value = null

    try {
      const response = await systemApi.getIndustries()
      if (response.success && response.data) {
        industries.value = (response.data as any).industries || []
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载行业列表失败'
      console.error('Failed to load industries:', err)
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
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载当前行业失败'
      console.error('Failed to load current industry:', err)
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

  async function initialize() {
    await loadIndustries()
    await loadCurrentIndustry()
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
