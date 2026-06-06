import { ref } from 'vue'
import { apiFetch, DEFAULT_MOD_API_TIMEOUT_MS } from '@/utils/apiBase'
import { fetchModRoutesPayloadShared } from '@/utils/modRoutesSharedFetch'

export function useModBootstrap() {
  const mods = ref<any[]>([])
  const modRoutes = ref<any[]>([])
  const isLoaded = ref(false)
  const loadError = ref<string | null>(null)

  async function fetchModsOnce() {
    try {
      const response = await apiFetch('/api/mods/', { timeoutMs: DEFAULT_MOD_API_TIMEOUT_MS })
      if (!response.ok) {
        loadError.value = `HTTP ${response.status}`
        return { ok: false }
      }
      const data = await response.json()
      if (!data.success) {
        loadError.value = typeof data.error === 'string' ? data.error : '列表失败'
        return { ok: false }
      }
      mods.value = Array.isArray(data.data) ? data.data : []
      isLoaded.value = mods.value.length > 0
      loadError.value = null
      return { ok: true }
    } catch (e) {
      loadError.value = '网络错误'
      return { ok: false }
    }
  }

  async function fetchModRoutes() {
    const data = await fetchModRoutesPayloadShared()
    if (data) modRoutes.value = data
  }

  return {
    mods,
    modRoutes,
    isLoaded,
    loadError,
    fetchModsOnce,
    fetchModRoutes,
  }
}

