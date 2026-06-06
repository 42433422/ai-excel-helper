import { ref, computed } from 'vue'
import { apiFetch, isApiFetchTimeoutError } from '@/utils/apiBase'
import { summarizeModLoadingData } from '@/utils/modLoadingStatus'
import { CLIENT_MODS_UI_OFF_KEY } from '@/stores/mods'

const STARTUP_SPLASH_MS = 1800
const STARTUP_LOADING_STATUS_TIMEOUT_MS = 12_000

export function useStartupSplash() {
  const startupVisible = ref(true)
  const appReady = ref(false)
  const startupProgressPct = ref(0)
  const startupModPreview = ref<any[]>([])
  const modsLoading = ref(false)
  const modsLoadError = ref<string | null>(null)

  function extractModNames(list: any[]) {
    const rows = Array.isArray(list) ? list : []
    const names = rows
      .map((m) => {
        const name = String(m?.name || '').trim()
        const id = String(m?.id || '').trim()
        return name || id
      })
      .filter(Boolean)
    return Array.from(new Set(names))
  }

  const startupPreviewModNames = computed(() => extractModNames(startupModPreview.value))

  async function loadModsForStartup() {
    if (typeof localStorage !== 'undefined' && localStorage.getItem(CLIENT_MODS_UI_OFF_KEY) === '1') {
      startupModPreview.value = []
      modsLoading.value = false
      return
    }
    modsLoading.value = true
    modsLoadError.value = null
    try {
      const response = await apiFetch('/api/mods/loading-status', {
        timeoutMs: STARTUP_LOADING_STATUS_TIMEOUT_MS,
      })
      if (!response.ok) {
        startupModPreview.value = []
        return
      }
      const data = await response.json()
      if (data.success) {
        const d = data.data || {}
        const raw = d.mods
        startupModPreview.value = Array.isArray(raw) ? raw : []
        const hint = summarizeModLoadingData(d)
        if (hint) modsLoadError.value = hint
      } else {
        startupModPreview.value = []
        modsLoadError.value = typeof data.error === 'string' ? data.error : 'Mod 加载失败'
      }
    } catch (error) {
      startupModPreview.value = []
      if (isApiFetchTimeoutError(error)) {
        // no-op
      } else {
        console.warn('[useStartupSplash] Mod loading-status error:', error)
      }
    } finally {
      modsLoading.value = false
      if (startupVisible.value) startupProgressPct.value = Math.max(startupProgressPct.value, 72)
    }
  }

  return {
    startupVisible,
    appReady,
    startupProgressPct,
    startupModPreview,
    startupPreviewModNames,
    modsLoading,
    modsLoadError,
    loadModsForStartup,
  }
}

