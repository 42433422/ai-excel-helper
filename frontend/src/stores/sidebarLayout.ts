import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const SIDEBAR_ORDER_KEY = 'xcagi.sidebar.menuOrder'
const SIDEBAR_REORDER_ENABLED_KEY = 'xcagi.sidebar.reorderEnabled'
const SIDEBAR_WIDTH_KEY = 'xcagi.sidebar.width'
export const DEFAULT_SIDEBAR_WIDTH = 236
export const MIN_SIDEBAR_WIDTH = 220
export const MAX_SIDEBAR_WIDTH = 360

export const useSidebarLayoutStore = defineStore('sidebarLayout', () => {
  const menuOrder = ref<string[]>([])
  /** 默认开启侧栏排序；仅当 localStorage 为 `'0'` 时关闭（与历史「未持久化标志也允许排序」行为一致） */
  const reorderEnabled = ref(true)
  const sidebarWidth = ref(DEFAULT_SIDEBAR_WIDTH)
  const widthLoaded = ref(false)

  const hasCustomOrder = computed(() => Array.isArray(menuOrder.value) && menuOrder.value.length > 0)

  function loadFromStorage() {
    try {
      const rawOrder = localStorage.getItem(SIDEBAR_ORDER_KEY)
      const parsed = rawOrder ? JSON.parse(rawOrder) : []
      menuOrder.value = Array.isArray(parsed) ? parsed.map((v) => String(v)) : []
    } catch (_e) {
      menuOrder.value = []
    }

    try {
      const raw = localStorage.getItem(SIDEBAR_REORDER_ENABLED_KEY)
      reorderEnabled.value = raw !== '0'
    } catch (_e) {
      reorderEnabled.value = true
    }

    try {
      const rawWidth = Number(localStorage.getItem(SIDEBAR_WIDTH_KEY))
      if (Number.isFinite(rawWidth) && rawWidth > 0) {
        sidebarWidth.value = Math.min(MAX_SIDEBAR_WIDTH, Math.max(MIN_SIDEBAR_WIDTH, Math.round(rawWidth)))
      } else {
        sidebarWidth.value = DEFAULT_SIDEBAR_WIDTH
      }
    } catch (_e) {
      sidebarWidth.value = DEFAULT_SIDEBAR_WIDTH
    }
    widthLoaded.value = true
  }

  function persistOrder() {
    try {
      localStorage.setItem(SIDEBAR_ORDER_KEY, JSON.stringify(menuOrder.value))
    } catch (_e) {
      // ignore storage errors
    }
  }

  function persistReorderEnabled() {
    try {
      localStorage.setItem(SIDEBAR_REORDER_ENABLED_KEY, reorderEnabled.value ? '1' : '0')
    } catch (_e) {
      // ignore storage errors
    }
  }

  function persistSidebarWidth() {
    try {
      localStorage.setItem(SIDEBAR_WIDTH_KEY, String(sidebarWidth.value))
    } catch (_e) {
      // ignore storage errors
    }
  }

  function initialize(defaultKeys: string[]) {
    if (!menuOrder.value.length) {
      loadFromStorage()
    }
    normalizeOrder(defaultKeys)
  }

  function normalizeOrder(defaultKeys: string[]) {
    const valid = new Set(defaultKeys.map((k) => String(k)))
    const seen = new Set<string>()
    const kept = menuOrder.value.filter((k) => {
      const key = String(k)
      if (!valid.has(key) || seen.has(key)) return false
      seen.add(key)
      return true
    })
    const missing = defaultKeys.filter((k) => !kept.includes(k))
    const normalized = [...kept, ...missing]

    const prev = menuOrder.value.join('\0')
    const next = normalized.join('\0')
    menuOrder.value = normalized
    if (prev !== next) persistOrder()
  }

  function setReorderEnabled(enabled: boolean) {
    reorderEnabled.value = Boolean(enabled)
    persistReorderEnabled()
  }

  function initializeWidth() {
    if (!widthLoaded.value) loadFromStorage()
    try {
      const rawWidth = localStorage.getItem(SIDEBAR_WIDTH_KEY)
      if (rawWidth === null) {
        persistSidebarWidth()
      }
    } catch (_e) {
      // ignore storage errors
    }
  }

  function setSidebarWidth(width: number) {
    const nextWidth = Math.min(MAX_SIDEBAR_WIDTH, Math.max(MIN_SIDEBAR_WIDTH, Math.round(Number(width) || DEFAULT_SIDEBAR_WIDTH)))
    sidebarWidth.value = nextWidth
    persistSidebarWidth()
  }

  let lastApplyOrderKeysSig = ''

  function applyOrder<T extends { key: string }>(items: T[]): T[] {
    if (!Array.isArray(items) || items.length === 0) return []
    const keys = items.map((item) => String(item.key))
    const sig = keys.join('\0')
    if (!menuOrder.value.length) loadFromStorage()
    if (sig !== lastApplyOrderKeysSig) {
      normalizeOrder(keys)
      lastApplyOrderKeysSig = sig
    }
    const rank = new Map(menuOrder.value.map((k, idx) => [k, idx]))
    return [...items].sort((a, b) => {
      const ra = rank.get(String(a.key))
      const rb = rank.get(String(b.key))
      return (ra ?? Number.MAX_SAFE_INTEGER) - (rb ?? Number.MAX_SAFE_INTEGER)
    })
  }

  function moveItem(dragKey: string, targetKey: string, defaultKeys: string[]) {
    if (!reorderEnabled.value) return
    initialize(defaultKeys)
    if (!dragKey || !targetKey || dragKey === targetKey) return
    const order = [...menuOrder.value]
    const from = order.indexOf(dragKey)
    const to = order.indexOf(targetKey)
    if (from < 0 || to < 0) return
    const [item] = order.splice(from, 1)
    order.splice(to, 0, item)
    menuOrder.value = order
    persistOrder()
  }

  function resetOrder(defaultKeys: string[]) {
    menuOrder.value = [...defaultKeys]
    persistOrder()
  }

  return {
    menuOrder,
    reorderEnabled,
    sidebarWidth,
    hasCustomOrder,
    initialize,
    initializeWidth,
    setReorderEnabled,
    setSidebarWidth,
    applyOrder,
    moveItem,
    resetOrder,
  }
})
