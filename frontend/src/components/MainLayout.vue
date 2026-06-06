<template>
  <div class="main-container">
    <div
      class="sidebar-shell"
      :class="{ collapsed: sidebarCollapsed }"
      :style="sidebarShellStyle"
      @mouseenter="onSidebarMouseEnter"
    >
      <Sidebar
        :active-view="currentRouteName"
        :is-pro-mode="isProMode"
        @change-view="handleViewChange"
        @toggle-pro-mode="$emit('toggle-pro-mode')"
      />
      <PaneResizeHandle
        v-if="isSidebarFeatureEnabled && !sidebarCollapsed"
        orientation="vertical"
        label="调整侧边栏宽度"
        @resize-start="onSidebarResizeStart"
        @reset="resetSidebarWidth"
      />
    </div>
    <div
      v-if="isSidebarFeatureEnabled && sidebarCollapsed"
      class="sidebar-hover-trigger"
      @mouseenter="onHoverTriggerEnter"
      @mouseleave="onHoverTriggerLeave"
    >
      <button
        class="sidebar-peek-button"
        type="button"
        aria-label="展开侧边栏"
        title="展开侧边栏"
        @click="onHoverTriggerClick"
      >
        ▶
      </button>
    </div>
    <div class="main-content">
      <div
        v-if="isImpersonating"
        class="impersonate-bar"
        role="status"
      >
        <span class="impersonate-bar__text">
          正在代管：<strong>{{ impersonationLabel }}</strong>
        </span>
        <button
          type="button"
          class="impersonate-bar__end"
          :disabled="endingImpersonation"
          @click="endImpersonation"
        >
          {{ endingImpersonation ? '结束中…' : '结束代管' }}
        </button>
      </div>
      <div class="top-bar">
        <div class="page-title-wrap">
          <div class="page-kicker">{{ topKickerText }}</div>
          <div class="page-title">{{ currentViewTitle }}</div>
          <div v-if="accountUsername && displayBrand" class="page-account-sub muted">
            {{ accountUsername }}
          </div>
        </div>
        <div
          class="mode-badge"
          :class="[props.isProMode ? 'pro' : 'normal', { 'with-mod': hasModsForUi }]"
        >
          {{ modeBadgeText }}
        </div>
        <button
          type="button"
          class="top-bar-settings-btn"
          :class="{ active: currentRouteName === 'settings' }"
          aria-label="系统设置"
          title="系统设置"
          data-tutorial-id="top-bar-settings"
          @click="openSettings"
        >
          <i class="fa fa-cog" aria-hidden="true"></i>
        </button>
        <TopAssistantFloat />
      </div>
      <slot></slot>
    </div>
    <FloatingChatAssistant :visible="shouldShowFloatingChatAssistant" />
    <TutorialOverlay />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute, useRouter } from 'vue-router'
import { useIndustryStore } from '@/stores/industry'
import { useModsStore } from '@/stores/mods'
import { useAccountProfileStore } from '@/stores/accountProfile'
import { xcmaxAdminApi } from '@/api/xcmaxAdmin'
import { LS_MARKET_USER_JSON } from '@/api/marketAccount'
import { appAlert } from '@/utils/appDialog'
import { useResizablePane } from '@/composables/useResizablePane'
import { DEFAULT_INDUSTRY_ID } from '@/constants/industryDefaults'
import { getIndustryPreset } from '@/constants/industryPresets'
import { resolveCoreNavLabel, INDUSTRY_MENU_LABELS } from '@/utils/coreNavLabel'
import { resolveHostBusinessPageRedirect } from '@/utils/hostBusinessPageRedirect'
import { customerServiceHostPathFromModPath } from '@/utils/customerServicePagePaths'
import { isChatSidebarActive, normalizeSidebarActiveKey } from '@/utils/sidebarActiveKey'
import { useModRoutes } from '@/composables/useModRoutes'
import FloatingChatAssistant from './FloatingChatAssistant.vue'
import PaneResizeHandle from './PaneResizeHandle.vue'
import Sidebar from './Sidebar.vue'
import TopAssistantFloat from './TopAssistantFloat.vue'
import TutorialOverlay from './TutorialOverlay.vue'
import { setTutorialBuildContextFactory } from '@/stores/tutorial'
import { useTutorialCatalog } from '@/composables/useTutorialCatalog'

const props = defineProps({
  isProMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['toggle-pro-mode'])

const route = useRoute()
const router = useRouter()
const industryStore = useIndustryStore()
const modsStore = useModsStore()
const accountProfileStore = useAccountProfileStore()
const { modsForUi } = storeToRefs(modsStore)
const {
  displayBrand,
  isImpersonating,
  impersonatingUsername,
  companyBrand,
} = storeToRefs(accountProfileStore)
const endingImpersonation = ref(false)
const { modMenuItems } = useModRoutes()
const SIDEBAR_INACTIVITY_MS = 15000
const SIDEBAR_HOVER_OPEN_MS = 1000
const SIDEBAR_DISABLE_MQ = '(max-width: 767px)'
const SIDEBAR_PANE_KEY = 'main-layout.sidebar'
const ACTIVITY_EVENTS = ['mousemove', 'mousedown', 'keydown', 'wheel', 'touchstart']
const sidebarCollapsed = ref(false)
const isSidebarFeatureEnabled = ref(true)
let sidebarCollapseTimer = null
let sidebarHoverTimer = null
let sidebarViewportMedia = null

const isSandboxMode = new URLSearchParams(window.location.search).has('sandbox')

/** 原版模式或未加载扩展时为空，与侧栏 Mod 菜单一致 */
const hasModsForUi = computed(() => modsForUi.value.length > 0)

const { buildContext: tutorialBuildContext } = useTutorialCatalog()
setTutorialBuildContextFactory(() => tutorialBuildContext.value)

const workbenchKicker = computed(() => {
  const id = String(industryStore.currentIndustryId || DEFAULT_INDUSTRY_ID).trim() || DEFAULT_INDUSTRY_ID
  const name = getIndustryPreset(id).name
  return `${name}工作台`
})

const topKickerText = computed(() => {
  const brand = String(displayBrand.value || '').trim()
  if (brand) return brand
  return workbenchKicker.value
})

const accountUsername = computed(() => {
  try {
    const raw = window.localStorage.getItem(LS_MARKET_USER_JSON)
    if (!raw) return ''
    const u = JSON.parse(raw)
    return String(u?.username || '').trim()
  } catch {
    return ''
  }
})

const impersonationLabel = computed(() => {
  const brand = String(companyBrand.value || '').trim()
  if (brand) return brand
  const user = String(impersonatingUsername.value || '').trim()
  return user || '目标用户'
})

async function endImpersonation() {
  endingImpersonation.value = true
  try {
    await xcmaxAdminApi.endImpersonate()
    await accountProfileStore.refreshFromServer()
    try {
      await modsStore.initialize(true)
    } catch {
      /* ignore */
    }
    window.location.reload()
  } catch (e) {
    await appAlert(`结束代管失败：${e instanceof Error ? e.message : String(e)}`)
  } finally {
    endingImpersonation.value = false
  }
}

/** 顶栏角标：普通/专业 + 已加载 Mod 时追加简写（如 ·Pro） */
function resolveModBadgeSuffix() {
  const list = modsForUi.value
  if (!list.length) return ''
  const lead = list.find((m) => m.primary) || list[0]
  const name = String(lead?.name || lead?.id || 'Mod').trim()
  if (!name) return 'Mod'
  return name.length <= 8 ? name : `${name.slice(0, 7)}…`
}

const modeBadgeText = computed(() => {
  if (isSandboxMode) return '沙箱模式'
  const base = props.isProMode ? '专业版' : '普通版'
  if (!hasModsForUi.value) return base
  return `${base}·${resolveModBadgeSuffix()}`
})

const modPathToSidebarKey = computed(() => {
  const m = {}
  for (const item of modMenuItems.value) {
    if (item.path) m[item.path] = item.key
  }
  return m
})

const viewTitlesBase = {
  chat: '智能对话',
  'ai-ecosystem': '智能生态',
  brain: '智脑集成',
  'model-payment': '模型服务',
  'kitten-finance': '财务分析',
  'mod-store': '能力库',
  products: '业务对象',
  'materials-list': '资源列表',
  materials: '资源库',
  'traditional-mode': '表格模式',
  'business-docking': '业务对接',
  orders: '业务单据',
  'orders-create': '新建业务单据',
  'shipment-records': '业务记录',
  customers: '组织管理',
  'data-sources': '数据来源',
  'wechat-contacts': '企业微信联系人',
  print: '模板与打印',
  'printer-list': '打印机列表',
  'template-preview': '模板库',
  console: '模板库',
  settings: '系统设置',
  tools: '工具表',
  'other-tools': '员工工作流',
  'workflow-employee-space': '员工空间',
  'workflow-visualization': '流程可视化',
  purchase: '耗材申领',
  'label-editor': '模板编辑器',
  'batch-analyze': '批量分析',
  'chat-debug': '对话调试',
  'enterprise-customer-service': '外部客服',
  'internal-customer-service': '内部客服',
  'admin-entitlements': '用户 Mod 管理',
}

const routeNameMap = {
  '/': 'chat',
  '/ai-ecosystem': 'ai-ecosystem',
  '/brain': 'brain',
  '/model-payment': 'model-payment',
  '/kitten-finance': 'kitten-finance',
  '/mod-store': 'mod-store',
  '/products': 'products',
  '/materials-list': 'materials-list',
  '/materials': 'materials',
  '/traditional-mode': 'traditional-mode',
  '/business-docking': 'business-docking',
  '/orders': 'orders',
  '/orders/create': 'orders-create',
  '/shipment-records': 'shipment-records',
  '/customers': 'customers',
  '/data-sources': 'data-sources',
  '/wechat-contacts': 'wechat-contacts',
  '/print': 'print',
  '/printer-list': 'printer-list',
  '/template-preview': 'template-preview',
  '/console': 'console',
  '/settings': 'settings',
  '/tools': 'tools',
  '/other-tools': 'other-tools',
  '/workflow-employee-space': 'workflow-employee-space',
  '/workflow-visualization': 'workflow-visualization',
  '/purchase': 'purchase',
  '/label-editor': 'label-editor',
  '/batch-analyze': 'batch-analyze',
  '/chat-debug': 'chat-debug',
  '/enterprise-customer-service': 'enterprise-customer-service',
  '/internal-customer-service': 'internal-customer-service',
  '/approval-hub': 'approval-hub',
  '/approval-hub/workspace': 'approval-hub',
  '/approval-hub/flows': 'approval-hub',
  '/approval-hub/rules': 'approval-hub',
  '/inventory': 'inventory'
}

const currentRouteName = computed(() => {
  const modKey = modPathToSidebarKey.value[route.path]
  let raw = modKey || routeNameMap[route.path] || ''
  if (!raw) {
    for (const matched of [...route.matched].reverse()) {
      if (matched.path && routeNameMap[matched.path]) {
        raw = routeNameMap[matched.path]
        break
      }
    }
  }
  if (!raw) raw = String(route.name || '') || 'chat'
  return normalizeSidebarActiveKey(raw, route)
})

/** 侧栏选中「智能对话」时隐藏悬浮入口（含 Mod 门面 /mod/.../chat） */
const shouldShowFloatingChatAssistant = computed(
  () => !isChatSidebarActive(currentRouteName.value, route),
)

const {
  paneStyle: sidebarShellStyle,
  resetSize: resetSidebarWidth,
  startResize: onSidebarResizeStart,
  stopResize: stopSidebarResize,
} = useResizablePane({
  paneKey: SIDEBAR_PANE_KEY,
  cssVarName: '--sidebar-width',
  orientation: 'vertical',
  defaultSize: 236,
  minSize: 220,
  maxSize: 360,
  enabled: () => isSidebarFeatureEnabled.value && !sidebarCollapsed.value,
  onResizeStart: () => {
    clearSidebarCollapseTimer()
    clearSidebarHoverTimer()
  },
  onResizeEnd: () => {
    if (isSidebarFeatureEnabled.value && !sidebarCollapsed.value) {
      scheduleSidebarAutoCollapse()
    }
  },
})

/** 顶栏与页面标题：仅核心 + 行业（与侧栏 resolveCoreNavLabel / INDUSTRY_MENU_LABELS 同源），不含 Mod menu_overrides */
const viewTitles = computed(() => {
  const industryId = String(industryStore.currentIndustryId || DEFAULT_INDUSTRY_ID)
  const byIndustry =
    INDUSTRY_MENU_LABELS[industryId] || INDUSTRY_MENU_LABELS[DEFAULT_INDUSTRY_ID]
  return {
    ...viewTitlesBase,
    ...byIndustry,
  }
})

const currentViewTitle = computed(() => {
  const key = currentRouteName.value
  const industryId = String(industryStore.currentIndustryId || DEFAULT_INDUSTRY_ID)
  const fromNav = resolveCoreNavLabel(key, industryId, modsForUi.value)
  if (fromNav) return fromNav
  const fromMap = viewTitles.value[key]
  if (typeof fromMap === 'string' && fromMap.trim()) return fromMap
  const metaTitle = route.meta?.title
  if (typeof metaTitle === 'string' && metaTitle.trim()) return metaTitle
  return '未知页面'
})

/** 侧栏 key → 实际叶子路由，避免父级 redirect 触发连续两次导航 */
const SIDEBAR_ROUTE_ALIASES = {
  'approval-hub': 'approval-workspace',
  'mod-approval-hub': 'approval-workspace',
}

function resolveLegacyRouteFromModPath(modPath) {
  const pathOnly = String(modPath || '').split('?')[0]?.split('#')[0] || ''
  if (!pathOnly) return null
  if (pathOnly.includes('/approval-hub/workspace') && router.hasRoute('approval-workspace')) {
    return { name: 'approval-workspace' }
  }
  if (pathOnly.endsWith('/approval-hub') && router.hasRoute('approval-hub')) {
    return { name: 'approval-hub' }
  }
  const lastSeg = pathOnly.split('/').filter(Boolean).pop()
  if (lastSeg && router.hasRoute(lastSeg)) {
    return { name: lastSeg }
  }
  return null
}

async function navigateToView(viewKey) {
  const routeName =
    typeof viewKey === 'string' ? SIDEBAR_ROUTE_ALIASES[viewKey] || viewKey : viewKey

  const modItem = modMenuItems.value.find((m) => m.key === viewKey)
  if (modItem?.path) {
    if (router.resolve(modItem.path).matched.length === 0) {
      try {
        const { registerAllModRoutesFromGlob, registerModRoutes } = await import(
          '@/router/registerModRoutes'
        )
        await registerAllModRoutesFromGlob(router)
        if (modsStore.modRoutes?.length) {
          await registerModRoutes(router, modsStore.modRoutes)
        }
      } catch (e) {
        console.warn('[MainLayout] 补注册 Mod 路由失败:', e)
      }
    }
    if (router.resolve(modItem.path).matched.length > 0) {
      await router.push(modItem.path)
      return
    }
    const legacy = resolveLegacyRouteFromModPath(modItem.path)
    if (legacy) {
      await router.push(legacy)
      return
    }
    const csHost = customerServiceHostPathFromModPath(modItem.path)
    if (csHost) {
      await router.push(csHost)
      return
    }
    console.warn('[MainLayout] Mod 路由未注册，路径无效:', modItem.path)
  }
  // ERP/审批等 Mod 业务页：优先于宿主 route name（企业版与壳模式一致）
  if (typeof routeName === 'string') {
    const stripped = routeName.replace(/^mod-/, '')
    const modBusinessPath = resolveHostBusinessPageRedirect(stripped) || resolveHostBusinessPageRedirect(routeName)
    if (modBusinessPath) {
      if (router.resolve(modBusinessPath).matched.length === 0) {
        const { registerAllModRoutesFromGlob } = await import('@/router/registerModRoutes')
        await registerAllModRoutesFromGlob(router)
      }
      if (router.resolve(modBusinessPath).matched.length > 0) {
        await router.push(modBusinessPath)
        return
      }
      const legacy = resolveLegacyRouteFromModPath(modBusinessPath)
      if (legacy) {
        await router.push(legacy)
        return
      }
      const csHost = customerServiceHostPathFromModPath(modBusinessPath)
      if (csHost) {
        await router.push(csHost)
        return
      }
    }
  }
  // 侧栏 key 与核心路由 name 一致，优先按名称跳转，避免 routeNameMap 漏配或反查顺序问题
  const nameCandidate =
    typeof routeName === 'string' ? routeName.replace(/^mod-/, '') : routeName
  if (typeof nameCandidate === 'string' && router.hasRoute(nameCandidate)) {
    await router.push({ name: nameCandidate })
    return
  }
  if (typeof routeName === 'string' && router.hasRoute(routeName)) {
    await router.push({ name: routeName })
    return
  }
  const routePath = Object.entries(routeNameMap).find(
    ([, name]) => name === viewKey
  )?.[0]
  if (routePath) {
    await router.push(routePath)
    return
  }
  console.warn('[MainLayout] 侧栏无对应路由:', viewKey)
}

const handleViewChange = (viewKey) => {
  void navigateToView(viewKey)
}

function openSettings() {
  void router.push({ name: 'settings' })
}

const clearSidebarCollapseTimer = () => {
  if (sidebarCollapseTimer) {
    window.clearTimeout(sidebarCollapseTimer)
    sidebarCollapseTimer = null
  }
}

const clearSidebarHoverTimer = () => {
  if (sidebarHoverTimer) {
    window.clearTimeout(sidebarHoverTimer)
    sidebarHoverTimer = null
  }
}

const scheduleSidebarAutoCollapse = () => {
  if (!isSidebarFeatureEnabled.value || sidebarCollapsed.value) return
  clearSidebarCollapseTimer()
  sidebarCollapseTimer = window.setTimeout(() => {
    sidebarCollapsed.value = true
  }, SIDEBAR_INACTIVITY_MS)
}

const handleGlobalActivity = () => {
  if (!isSidebarFeatureEnabled.value) return
  if (sidebarCollapsed.value) return
  scheduleSidebarAutoCollapse()
}

const onSidebarMouseEnter = () => {
  handleGlobalActivity()
}

const onHoverTriggerEnter = () => {
  if (!isSidebarFeatureEnabled.value || !sidebarCollapsed.value) return
  clearSidebarHoverTimer()
  sidebarHoverTimer = window.setTimeout(() => {
    sidebarCollapsed.value = false
    scheduleSidebarAutoCollapse()
  }, SIDEBAR_HOVER_OPEN_MS)
}

const onHoverTriggerLeave = () => {
  clearSidebarHoverTimer()
}

const onHoverTriggerClick = () => {
  clearSidebarHoverTimer()
  sidebarCollapsed.value = false
  scheduleSidebarAutoCollapse()
}

const onViewportChange = (event) => {
  isSidebarFeatureEnabled.value = !event.matches
  clearSidebarHoverTimer()
  clearSidebarCollapseTimer()
  if (!isSidebarFeatureEnabled.value) {
    sidebarCollapsed.value = false
    stopSidebarResize()
    return
  }
  scheduleSidebarAutoCollapse()
}

onMounted(async () => {
  if (!accountProfileStore.loaded) {
    try {
      await accountProfileStore.refreshFromServer()
    } catch {
      /* ignore */
    }
  }
  try {
    const { authApi } = await import('@/api/auth')
    const {
      augmentEntitledModIdsForAccount,
      isSunbirdAccountUsername,
      SUNBIRD_CLIENT_MOD_ID,
    } = await import('@/constants/accountModBinding')
    const me = await authApi.getCurrentUser()
    const uname = String(me?.data?.user?.username || accountUsername.value || '').trim()
    if (
      isSunbirdAccountUsername(uname) &&
      String(modsStore.activeModId || '').trim() !== SUNBIRD_CLIENT_MOD_ID
    ) {
      await modsStore.initialize(true, {
        entitledModIds: augmentEntitledModIdsForAccount(uname, []),
        forceFromEntitlements: true,
        accountUsername: uname,
      })
    }
  } catch {
    /* ignore */
  }
  if (!industryStore.isLoaded) {
    try {
      await industryStore.initialize()
    } catch (_e) {
      // 行业信息加载失败时，顶部标题保持默认文案
    }
  }
  sidebarViewportMedia = window.matchMedia(SIDEBAR_DISABLE_MQ)
  onViewportChange(sidebarViewportMedia)
  if (typeof sidebarViewportMedia.addEventListener === 'function') {
    sidebarViewportMedia.addEventListener('change', onViewportChange)
  } else if (typeof sidebarViewportMedia.addListener === 'function') {
    sidebarViewportMedia.addListener(onViewportChange)
  }
  ACTIVITY_EVENTS.forEach((eventName) => {
    window.addEventListener(eventName, handleGlobalActivity, { passive: true })
  })
})

onBeforeUnmount(() => {
  stopSidebarResize()
  clearSidebarHoverTimer()
  clearSidebarCollapseTimer()
  ACTIVITY_EVENTS.forEach((eventName) => {
    window.removeEventListener(eventName, handleGlobalActivity)
  })
  if (!sidebarViewportMedia) return
  if (typeof sidebarViewportMedia.removeEventListener === 'function') {
    sidebarViewportMedia.removeEventListener('change', onViewportChange)
  } else if (typeof sidebarViewportMedia.removeListener === 'function') {
    sidebarViewportMedia.removeListener(onViewportChange)
  }
})
</script>

<style scoped>
.main-container {
  position: relative;
}

.sidebar-shell {
  position: relative;
  width: var(--sidebar-width, 236px);
  flex: 0 0 var(--sidebar-width, 236px);
  height: 100vh;
  min-width: 0;
  overflow: visible;
  transition:
    width 260ms cubic-bezier(0.2, 0.8, 0.2, 1),
    flex-basis 260ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

.sidebar-shell :deep(.sidebar) {
  width: var(--sidebar-width, 236px);
  height: 100%;
  transition:
    transform 260ms cubic-bezier(0.2, 0.8, 0.2, 1),
    opacity 220ms ease;
  transform: translateX(0);
  opacity: 1;
}

.sidebar-shell.collapsed {
  width: 0;
  flex-basis: 0;
}

.sidebar-shell.collapsed :deep(.sidebar) {
  transform: translateX(100%);
  opacity: 0;
  pointer-events: none;
}

.sidebar-hover-trigger {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 18px;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar-peek-button {
  width: 16px;
  height: 52px;
  border: 1px solid rgba(74, 144, 217, 0.45);
  border-left: none;
  border-radius: 0 10px 10px 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(231, 240, 251, 0.95));
  color: #2563eb;
  font-size: 10px;
  line-height: 1;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.16);
  transition:
    transform 160ms ease,
    box-shadow 160ms ease,
    background 160ms ease;
}

.sidebar-peek-button:hover {
  transform: translateX(1px);
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.2);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(219, 234, 254, 0.96));
}

.sidebar-peek-button:active {
  transform: translateX(0);
}

.page-title-wrap {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.page-kicker {
  font-size: 11px;
  line-height: 1;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(71, 85, 105, 0.72);
}

.page-account-sub {
  font-size: 12px;
  line-height: 1.2;
  color: rgba(100, 116, 139, 0.9);
}

.impersonate-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 8px 16px;
  background: linear-gradient(90deg, #fff7ed, #ffedd5);
  border-bottom: 1px solid #fdba74;
  color: #9a3412;
  font-size: 13px;
}

.impersonate-bar__end {
  border: 1px solid #fb923c;
  background: #fff;
  color: #c2410c;
  border-radius: 8px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.impersonate-bar__end:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.top-bar-settings-btn {
  margin-left: 10px;
  width: 36px;
  height: 36px;
  border: 1px solid rgba(203, 213, 225, 0.85);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.88);
  color: #475569;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    color 0.15s ease;
}

.top-bar-settings-btn:hover,
.top-bar-settings-btn.active {
  color: #0b72d9;
  border-color: rgba(11, 114, 217, 0.35);
  background: rgba(239, 246, 255, 0.96);
}

.mode-badge {
  margin-left: auto;
  padding: 7px 12px;
  border-radius: 999px;
  font-size: var(--app-font-size-caption, 12px);
  line-height: 1;
  font-weight: 800;
  letter-spacing: 0.01em;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.mode-badge.normal {
  color: #1e3a8a;
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.96), rgba(219, 234, 254, 0.92));
  border: 1px solid rgba(147, 197, 253, 0.62);
}

.mode-badge.pro {
  color: #7dd3fc;
  background: linear-gradient(135deg, rgba(14, 116, 144, 0.3), rgba(15, 23, 42, 0.78));
  border: 1px solid rgba(125, 211, 252, 0.35);
}

/* 已加载 Mod：在普通/专业底子上略强调「扩展环境」 */
.mode-badge.with-mod.normal {
  background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%);
  border-color: #a5b4fc;
  color: #3730a3;
}

.mode-badge.with-mod.pro {
  box-shadow: 0 0 0 1px rgba(125, 211, 252, 0.2);
}

</style>
