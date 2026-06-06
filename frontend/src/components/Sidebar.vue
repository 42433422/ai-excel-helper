<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-brand" aria-label="品牌与标题">
        <img
          class="sidebar-brand-logo"
          src="/brand-xc-logo.jpg"
          width="40"
          height="40"
          alt=""
          decoding="async"
        />
        <div class="sidebar-brand-text">
          <h4>{{ sidebarBrandTitle }}</h4>
          <small style="opacity: 0.7">{{ sidebarBrandSubtitle }}</small>
        </div>
      </div>
    </div>
    <nav
      ref="sidebarMenuRef"
      class="sidebar-menu"
      :class="{ 'reorder-enabled': sidebarLayoutStore.reorderEnabled, 'is-dragging': draggingKey }"
      aria-label="主导航"
    >
      <component
        :is="draggingKey ? TransitionGroup : 'div'"
        v-bind="draggingKey ? { name: 'sidebar-menu-shift', tag: 'div' } : {}"
        class="sidebar-menu-shift-wrap"
      >
        <SidebarMenuItem
          v-for="(item, navIndex) in displayMenuItems"
          :key="item.key"
          v-memo="[
            item.key,
            item.name,
            activeView === item.key || activeParentKeys.has(item.key),
            item.children?.length
              ? (item.children.find((child) => child.key === activeView)?.key ?? '')
              : '',
            expandedKeys.has(item.key),
            pressingKey === item.key,
            draggingKey === item.key,
            dragOverKey,
            navRevealPlaying,
            navIndex,
          ]"
          :item="item"
          :active-view="activeView"
          :is-active="activeView === item.key || activeParentKeys.has(item.key)"
          :has-active-child="activeParentKeys.has(item.key)"
          :is-expanded="expandedKeys.has(item.key)"
          :is-pressing="pressingKey === item.key"
          :is-dragging="draggingKey === item.key"
          :nav-reveal-active="Boolean(navRevealClass(navIndex)['nav-reveal-active'])"
          :nav-stagger-style="staggerStyle(navIndex)"
          :long-press-ms="LONG_PRESS_MS"
          @parent-click="onParentMenuClick(item)"
          @select-view="selectView"
          @reorder-pointer-down="onReorderPointerDown($event, item.key)"
          @keydown="onMenuItemKeydown($event, item.key)"
        />
      </component>
    </nav>
    <div class="sidebar-menu-bottom" role="navigation" aria-label="系统">
      <button
        class="menu-item"
        type="button"
        :class="{
          active: activeView === settingsMenuItem.key,
          ...navRevealClass(displayMenuItems.length),
        }"
        :style="staggerStyle(displayMenuItems.length)"
        :data-view="settingsMenuItem.key"
        :aria-label="settingsMenuItem.name"
        :aria-current="activeView === settingsMenuItem.key ? 'page' : undefined"
        :title="settingsMenuItem.name"
        @click="selectView(settingsMenuItem.key)"
      >
        <span class="menu-item-icon" aria-hidden="true">
          <i class="fa" :class="settingsMenuItem.iconClass"></i>
        </span>
        <span>{{ settingsMenuItem.name }}</span>
      </button>
    </div>
    <div class="sidebar-footer">
      <div class="sidebar-status-mods-row">
        <div class="status-indicator">
          <span class="status-dot online"></span>
          <span>系统正常</span>
        </div>
        <div
          v-if="primaryModChip"
          class="sidebar-mods-badges"
          :title="primaryModChip.fullName"
          aria-label="已加载扩展模块"
        >
          <span class="sidebar-mod-chip">{{ primaryModChip.shortLabel }}</span>
        </div>
      </div>
      <button
        v-if="!isSandboxMode"
        class="mode-switch"
        id="modeSwitch"
        type="button"
        aria-label="切换专业模式"
        @click="toggleProMode"
      >
        <span class="mode-label">
          {{ isProMode ? '切换到普通版' : '切换到专业版' }}
        </span>
        <div
          class="toggle-switch"
          id="proModeToggle"
          :class="{ active: isProMode }"
        >
          <div class="toggle-slider"></div>
        </div>
      </button>
      <div class="current-mode-text">
        当前：{{ currentModeText }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { TransitionGroup, computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useIndustryStore } from '@/stores/industry'
import { useSidebarLayoutStore } from '@/stores/sidebarLayout'
import { useModsStore } from '@/stores/mods'
import { DEFAULT_INDUSTRY_ID } from '@/constants/industryDefaults'
import { getIndustryPreset } from '@/constants/industryPresets'
import { useIndustryUiText } from '@/composables/useIndustryUiText'
import {
  isPlatformShellModeEnabled,
} from '@/constants/platformShellMode'
import { SETTINGS_MENU_ITEM, sidebarLayoutSeedKeys } from '@/constants/coreMenuCatalog'
import { useVisibleNavItems } from '@/composables/useVisibleNavItems'
import { useSidebarNavReveal } from '@/composables/useSidebarNavReveal'
import SidebarMenuItem from '@/components/SidebarMenuItem.vue'
import '@/styles/sidebar-reveal.css'

const props = defineProps({
  activeView: {
    type: String,
    required: true,
  },
  isProMode: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['change-view', 'toggle-pro-mode'])

const industryStore = useIndustryStore()
const sidebarLayoutStore = useSidebarLayoutStore()
const modsStore = useModsStore()
const { modsForUi } = storeToRefs(modsStore)
const { menuItems, visibleNavItems: _visibleNavItems } = useVisibleNavItems()
const { staggerStyle, navRevealClass, navRevealPlaying } = useSidebarNavReveal()
const { assistantSubtitle } = useIndustryUiText()

function shortModLabel(name) {
  const s = String(name || '').trim()
  if (!s) return 'Mod'
  return s.length > 8 ? `${s.slice(0, 7)}…` : s
}

const loadedModChips = computed(() =>
  (modsForUi.value || []).map((m) => ({
    id: m.id,
    shortLabel: shortModLabel((m.name && String(m.name).trim()) || m.id),
    fullName: (m.name && String(m.name).trim()) || m.id,
  })),
)

const primaryModChip = computed(() => {
  const chips = loadedModChips.value
  return chips.length > 0 ? chips[0] : null
})

const PRO_INTENT_EXPERIENCE_KEY = 'xcagi_pro_intent_experience'
const proIntentExperienceEnabled = ref(localStorage.getItem(PRO_INTENT_EXPERIENCE_KEY) === '1')
const LONG_PRESS_MS = 1000
const sidebarMenuRef = ref(null)
const pressingKey = ref('')
const draggingKey = ref('')
const dragOverKey = ref('')
const expandedKeys = ref(new Set())
let activeReorderPointerId = null
let pressTimer = null
let boundWindowPointerMove = null
let boundWindowPointerUp = null
let boundWindowPointerCancel = null
let dragMoveRaf = 0
let pendingDragPoint = null
/** @type {{ key: string, midY: number }[]} */
let menuHitCache = []

const isSandboxMode = new URLSearchParams(window.location.search).has('sandbox')
const isPlatformShellMode = isPlatformShellModeEnabled()
const sidebarSystemSubtitle = assistantSubtitle

const sidebarBrandTitle = computed(() => {
  if (isSandboxMode) return '沙箱测试'
  if (isPlatformShellMode) return 'XCAGI 平台壳'
  const id = String(industryStore.currentIndustryId || DEFAULT_INDUSTRY_ID).trim() || DEFAULT_INDUSTRY_ID
  const name = getIndustryPreset(id).name
  return name.includes('助手') ? name : `${name}助手`
})

const sidebarBrandSubtitle = computed(() => {
  if (isSandboxMode) return 'MODstore 在线测试'
  if (isPlatformShellMode) return '通用宿主 · 能力由 Mod 提供'
  return sidebarSystemSubtitle.value
})

const settingsMenuItem = computed(() => {
  const row = _visibleNavItems.value.find((n) => n.key === SETTINGS_MENU_ITEM.key)
  return {
    key: SETTINGS_MENU_ITEM.key,
    name: row?.name || SETTINGS_MENU_ITEM.name,
    iconClass: SETTINGS_MENU_ITEM.iconClass,
  }
})

const activeParentKeys = computed(() => {
  const view = props.activeView
  const parents = new Set()
  for (const item of menuItems.value) {
    if (item.children?.some((child) => child.key === view)) {
      parents.add(item.key)
    }
  }
  return parents
})

const displayMenuItems = computed(() => {
  const items = menuItems.value
  const drag = draggingKey.value
  const over = dragOverKey.value
  if (!drag || !over || drag === over) return items
  const keys = items.map((m) => m.key)
  const from = keys.indexOf(drag)
  const to = keys.indexOf(over)
  if (from < 0 || to < 0) return items
  const nextKeys = [...keys]
  const [lifted] = nextKeys.splice(from, 1)
  nextKeys.splice(to, 0, lifted)
  const byKey = new Map(items.map((m) => [m.key, m]))
  return nextKeys.map((k) => byKey.get(k)).filter(Boolean)
})

const currentModeText = computed(() => {
  if (props.isProMode) {
    return '专业版（增强执行）'
  }
  if (proIntentExperienceEnabled.value) {
    return '普通版（专业意图体验）'
  }
  return '普通版（标准对话）'
})

const syncProIntentExperience = () => {
  proIntentExperienceEnabled.value = localStorage.getItem(PRO_INTENT_EXPERIENCE_KEY) === '1'
}

const selectView = (key) => {
  if (draggingKey.value) return
  emit('change-view', key)
}

/** 有子菜单的父项：进入父路由（如 other-tools → 员工工作流管理）并展开子菜单 */
const onParentMenuClick = (item) => {
  if (!item.children?.length) {
    selectView(item.key)
    return
  }
  if (!expandedKeys.value.has(item.key)) {
    const next = new Set(expandedKeys.value)
    next.add(item.key)
    expandedKeys.value = next
  }
  selectView(item.key)
}

watch(() => props.activeView, (viewKey) => {
  if (!viewKey) return
  for (const item of menuItems.value) {
    if (item.children?.length && item.children.some((c) => c.key === viewKey)) {
      if (!expandedKeys.value.has(item.key)) {
        const next = new Set(expandedKeys.value)
        next.add(item.key)
        expandedKeys.value = next
      }
    }
  }
}, { immediate: true })

const toggleProMode = () => {
  emit('toggle-pro-mode')
}

function clearPressTimer() {
  if (pressTimer) {
    window.clearTimeout(pressTimer)
    pressTimer = null
  }
}

function focusMenuItemByKey(targetKey) {
  const root = sidebarMenuRef.value
  if (!root || !targetKey) return
  const btn = root.querySelector(`button.menu-item[data-view="${targetKey}"]`)
  if (btn instanceof HTMLElement) btn.focus()
}

function onMenuItemKeydown(event, key) {
  if (
    event.key !== 'ArrowDown' &&
    event.key !== 'ArrowUp' &&
    event.key !== 'Home' &&
    event.key !== 'End'
  ) {
    return
  }
  const keys = displayMenuItems.value.map((i) => i.key)
  const idx = keys.indexOf(key)
  if (idx < 0) return
  event.preventDefault()
  let nextIdx = idx
  if (event.key === 'ArrowDown') nextIdx = Math.min(keys.length - 1, idx + 1)
  else if (event.key === 'ArrowUp') nextIdx = Math.max(0, idx - 1)
  else if (event.key === 'Home') nextIdx = 0
  else if (event.key === 'End') nextIdx = keys.length - 1
  const nextKey = keys[nextIdx]
  if (nextKey) focusMenuItemByKey(nextKey)
}

function refreshMenuHitCache() {
  const root = sidebarMenuRef.value
  if (!root) {
    menuHitCache = []
    return
  }
  menuHitCache = Array.from(root.querySelectorAll('button.menu-item[data-view]'))
    .filter((btn) => btn.getAttribute('data-view') !== draggingKey.value)
    .map((btn) => {
      const rect = btn.getBoundingClientRect()
      return {
        key: String(btn.getAttribute('data-view') || ''),
        midY: rect.top + rect.height / 2,
      }
    })
}

function menuKeyUnderPoint(clientX, clientY) {
  const root = sidebarMenuRef.value
  if (!root) return ''
  const rect = root.getBoundingClientRect()
  if (
    clientX < rect.left ||
    clientX > rect.right ||
    clientY < rect.top ||
    clientY > rect.bottom
  ) {
    return ''
  }
  if (!menuHitCache.length) refreshMenuHitCache()
  let nearestKey = ''
  let nearestDistance = Number.POSITIVE_INFINITY
  for (const entry of menuHitCache) {
    const distance = Math.abs(entry.midY - clientY)
    if (distance < nearestDistance) {
      nearestDistance = distance
      nearestKey = entry.key
    }
  }
  return nearestKey
}

function clearDragMoveRaf() {
  if (dragMoveRaf) {
    window.cancelAnimationFrame(dragMoveRaf)
    dragMoveRaf = 0
  }
  pendingDragPoint = null
}

function detachReorderWindowListeners() {
  if (boundWindowPointerMove) {
    window.removeEventListener('pointermove', boundWindowPointerMove, true)
    boundWindowPointerMove = null
  }
  if (boundWindowPointerUp) {
    window.removeEventListener('pointerup', boundWindowPointerUp, true)
    boundWindowPointerUp = null
  }
  if (boundWindowPointerCancel) {
    window.removeEventListener('pointercancel', boundWindowPointerCancel, true)
    boundWindowPointerCancel = null
  }
}

function clearReorderGesture() {
  clearPressTimer()
  pressingKey.value = ''
  draggingKey.value = ''
  dragOverKey.value = ''
  activeReorderPointerId = null
  menuHitCache = []
  clearDragMoveRaf()
  detachReorderWindowListeners()
}

function flushDragMove() {
  dragMoveRaf = 0
  if (!pendingDragPoint || !draggingKey.value) {
    pendingDragPoint = null
    return
  }
  const { x, y } = pendingDragPoint
  pendingDragPoint = null
  const key = menuKeyUnderPoint(x, y)
  if (key && key !== dragOverKey.value) {
    dragOverKey.value = key
    refreshMenuHitCache()
  }
}

function onWindowPointerMove(event) {
  if (activeReorderPointerId !== null && event.pointerId !== activeReorderPointerId) return
  if (!draggingKey.value) return
  pendingDragPoint = { x: event.clientX, y: event.clientY }
  if (!dragMoveRaf) {
    dragMoveRaf = window.requestAnimationFrame(flushDragMove)
  }
}

function onWindowPointerUp(event) {
  if (activeReorderPointerId !== null && event.pointerId !== activeReorderPointerId) return
  if (draggingKey.value) {
    const from = draggingKey.value
    const to = dragOverKey.value
    if (to && to !== from) {
      sidebarLayoutStore.moveItem(from, to, menuItems.value.map((m) => m.key))
    }
  }
  clearReorderGesture()
}

function attachReorderWindowListeners() {
  detachReorderWindowListeners()
  boundWindowPointerMove = onWindowPointerMove
  boundWindowPointerUp = onWindowPointerUp
  boundWindowPointerCancel = clearReorderGesture
  window.addEventListener('pointermove', boundWindowPointerMove, true)
  window.addEventListener('pointerup', boundWindowPointerUp, true)
  window.addEventListener('pointercancel', boundWindowPointerCancel, true)
}

function onReorderPointerDown(event, key) {
  if (!sidebarLayoutStore.reorderEnabled) return
  if (event.button !== 2) return
  event.preventDefault()
  clearReorderGesture()
  activeReorderPointerId = event.pointerId
  pressingKey.value = key
  attachReorderWindowListeners()
  pressTimer = window.setTimeout(() => {
    if (activeReorderPointerId !== event.pointerId || pressingKey.value !== key) return
    pressingKey.value = ''
    draggingKey.value = key
    dragOverKey.value = key
    refreshMenuHitCache()
  }, LONG_PRESS_MS)
}

watch(draggingKey, (key) => {
  if (key) {
    window.requestAnimationFrame(() => refreshMenuHitCache())
  } else {
    menuHitCache = []
  }
})

onMounted(async () => {
  window.addEventListener('storage', syncProIntentExperience)
  window.addEventListener('xcagi:pro-intent-experience-changed', syncProIntentExperience)
  sidebarLayoutStore.initialize(sidebarLayoutSeedKeys())
  if (!industryStore.isLoaded) {
    try {
      await industryStore.initialize()
    } catch (_e) {
      // ignore initialize failures and keep fallback labels
    }
  }
  if (!modsStore.isLoaded) {
    void modsStore.initialize()
  }
})

onBeforeUnmount(() => {
  clearReorderGesture()
  window.removeEventListener('storage', syncProIntentExperience)
  window.removeEventListener('xcagi:pro-intent-experience-changed', syncProIntentExperience)
})
</script>

<style scoped>
.sidebar-status-mods-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 6px 8px;
  margin-bottom: 10px;
}

.sidebar-status-mods-row .status-indicator {
  margin-bottom: 0;
  flex-shrink: 0;
  min-width: 0;
}

.sidebar-mods-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: flex-end;
  flex: 1 1 auto;
  min-width: 0;
  max-width: 70%;
}

.sidebar-mod-chip {
  display: inline-block;
  max-width: 100%;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  line-height: 1.35;
  font-weight: 600;
  color: #3730a3;
  background: #e0e7ff;
  border: 1px solid #c7d2fe;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-menu-shift-wrap {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.sidebar-menu-bottom {
  flex-shrink: 0;
  width: 100%;
  padding: 8px 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  box-sizing: border-box;
}

.sidebar-menu.reorder-enabled :deep(.menu-item.pressing) {
  background: rgba(125, 211, 252, 0.1);
}

.sidebar-menu.reorder-enabled.is-dragging :deep(.menu-item.dragging) {
  opacity: 0.5;
}

.sidebar-menu.reorder-enabled.is-dragging .sidebar-menu-shift-move {
  transition: transform 0.26s cubic-bezier(0.22, 1, 0.36, 1) !important;
}
</style>
