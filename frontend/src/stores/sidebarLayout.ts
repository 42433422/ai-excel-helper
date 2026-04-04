import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const SIDEBAR_ORDER_KEY = 'xcagi.sidebar.menuOrder'
const SIDEBAR_REORDER_ENABLED_KEY = 'xcagi.sidebar.reorderEnabled'

export const useSidebarLayoutStore = defineStore('sidebarLayout', () => {
  const menuOrder = ref<string[]>([])
  const reorderEnabled = ref(false)

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
      reorderEnabled.value = localStorage.getItem(SIDEBAR_REORDER_ENABLED_KEY) === '1'
    } catch (_e) {
      reorderEnabled.value = false
    }
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

  function initialize(defaultKeys: string[]) {
    if (!menuOrder.value.length && !reorderEnabled.value) {
      loadFromStorage()
    }
    normalizeOrder(defaultKeys)
  }

  function normalizeOrder(defaultKeys: string[]) {
    const valid = new Set(defaultKeys.map((k) => String(k)))
    const kept = menuOrder.value.filter((k) => valid.has(k))
    const missing = defaultKeys.filter((k) => !kept.includes(k))
    const normalized = [...kept, ...missing]

    // 业务固定顺序：原材料仓库紧跟在原材料列表后。
    const materialsListIdx = normalized.indexOf('materials-list')
    const materialsIdx = normalized.indexOf('materials')
    if (materialsListIdx >= 0 && materialsIdx >= 0 && materialsIdx !== materialsListIdx + 1) {
      normalized.splice(materialsIdx, 1)
      normalized.splice(materialsListIdx + 1, 0, 'materials')
    }

    menuOrder.value = normalized
    persistOrder()
  }

  function setReorderEnabled(enabled: boolean) {
    reorderEnabled.value = Boolean(enabled)
    persistReorderEnabled()
  }

  function applyOrder<T extends { key: string }>(items: T[]): T[] {
    if (!Array.isArray(items) || items.length === 0) return []
    initialize(items.map((item) => String(item.key)))
    const rank = new Map(menuOrder.value.map((k, idx) => [k, idx]))
    return [...items].sort((a, b) => {
      const ra = rank.get(String(a.key))
      const rb = rank.get(String(b.key))
      return (ra ?? Number.MAX_SAFE_INTEGER) - (rb ?? Number.MAX_SAFE_INTEGER)
    })
  }

  function moveItem(dragKey: string, targetKey: string, defaultKeys: string[]) {
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
    hasCustomOrder,
    initialize,
    setReorderEnabled,
    applyOrder,
    moveItem,
    resetOrder,
  }
})
