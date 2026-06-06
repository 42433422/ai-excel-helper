import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface PaneSizeOptions {
  defaultSize: number
  minSize: number
  maxSize: number
}

const PANE_LAYOUT_STORAGE_KEY = 'xcagi.layout.paneSizes'

function clampPaneSize(value: number, options: PaneSizeOptions): number {
  const fallback = Number(options.defaultSize) || 0
  const min = Math.min(Number(options.minSize) || fallback, Number(options.maxSize) || fallback)
  const max = Math.max(Number(options.minSize) || fallback, Number(options.maxSize) || fallback)
  const raw = Number.isFinite(value) ? value : fallback
  return Math.min(max, Math.max(min, Math.round(raw)))
}

export const usePaneLayoutStore = defineStore('paneLayout', () => {
  const paneSizes = ref<Record<string, number>>({})
  const loaded = ref(false)

  function loadFromStorage() {
    try {
      const raw = localStorage.getItem(PANE_LAYOUT_STORAGE_KEY)
      const parsed = raw ? JSON.parse(raw) : {}
      paneSizes.value = parsed && typeof parsed === 'object' ? parsed : {}
    } catch (_e) {
      paneSizes.value = {}
    }
    loaded.value = true
  }

  function ensureLoaded() {
    if (!loaded.value) loadFromStorage()
  }

  function persistPaneSizes() {
    try {
      localStorage.setItem(PANE_LAYOUT_STORAGE_KEY, JSON.stringify(paneSizes.value))
    } catch (_e) {
      // ignore storage errors
    }
  }

  function initializePane(key: string, options: PaneSizeOptions): number {
    ensureLoaded()
    const nextSize = clampPaneSize(paneSizes.value[key], options)
    if (paneSizes.value[key] !== nextSize) {
      paneSizes.value = {
        ...paneSizes.value,
        [key]: nextSize,
      }
      persistPaneSizes()
    }
    return nextSize
  }

  function getPaneSize(key: string, options: PaneSizeOptions): number {
    return initializePane(key, options)
  }

  function setPaneSize(key: string, value: number, options: PaneSizeOptions): number {
    ensureLoaded()
    const nextSize = clampPaneSize(value, options)
    if (paneSizes.value[key] === nextSize) return nextSize
    paneSizes.value = {
      ...paneSizes.value,
      [key]: nextSize,
    }
    persistPaneSizes()
    return nextSize
  }

  function resetPaneSize(key: string, options: PaneSizeOptions): number {
    return setPaneSize(key, options.defaultSize, options)
  }

  return {
    paneSizes,
    initializePane,
    getPaneSize,
    setPaneSize,
    resetPaneSize,
  }
})
