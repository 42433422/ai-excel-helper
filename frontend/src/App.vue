<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useModsStore, CLIENT_MODS_UI_OFF_KEY } from '@/stores/mods'
import { useWorkflowAiEmployeesStore } from '@/stores/workflowAiEmployees'
import { authApi } from '@/api/auth'
import { fetchSessionMarketHandoff, persistMarketTokensFromHandoff } from '@/api/marketAccount'
import { apiFetch, isApiFetchTimeoutError } from '@/utils/apiBase'
import { fetchModLoadingStatusShared } from '@/utils/modLoadingStatusShared'
import { summarizeModLoadingData } from '@/utils/modLoadingStatus'
import MainLayout from './components/MainLayout.vue'
import GlobalReadTokenPrompt from './fhd/GlobalReadTokenPrompt.vue'
import GlobalWriteTokenPrompt from './fhd/GlobalWriteTokenPrompt.vue'
import AppDialogHost from './components/AppDialogHost.vue'
import GlobalLanGateModal from './components/lan/GlobalLanGateModal.vue'
import { isPlatformShellModeEnabled } from '@/constants/platformShellMode'
import { fetchProductSku, isEnterpriseEdition } from '@/utils/productSku'
import { useStartupRevealStore } from '@/stores/startupReveal'
import StartupGiftReveal from '@/components/startup/StartupGiftReveal.vue'

const route = useRoute()
const router = useRouter()
const modsStore = useModsStore()
const startupReveal = useStartupRevealStore()
const isProMode = ref(false)
const appReady = ref(false)
const startupVisible = ref(true)
const hideChrome = computed(() => route.meta?.hideChrome === true)

const isSandboxMode = new URLSearchParams(window.location.search).has('sandbox')
const skipSplashByUrl = new URLSearchParams(window.location.search).has('nosplash')

function isPublicEntryRoute(r = route) {
  const name = String(r?.name || '')
  return (
    name === 'login' ||
    name === 'lan-gate' ||
    name === 'product-onboarding' ||
    r?.meta?.hideChrome === true
  )
}

/** 过长的启动遮罩会拖慢「可交互」时间；略长于 logo 文案渐显（约 1.65s）即可 */
const STARTUP_SPLASH_MS = 1200
/** 为在关屏前展示 Mod 摘要，最多额外等待 loading-status（避免后端极慢时无限停留） */
const STARTUP_MOD_FETCH_CAP_MS = 2500
/** 无论开屏逻辑是否异常，超时后强制显示主界面，避免永久 opacity:0 白屏 */
const STARTUP_FAILSAFE_MS = 6000
const STARTUP_AUTH_TIMEOUT_MS = 8_000
/** 开屏仅拉 loading-status：勿用 180s Mod 超时，后端未起时尽快结束请求并交给开屏 cap / failsafe */
const STARTUP_LOADING_STATUS_TIMEOUT_MS = 12_000

const modsLoading = ref(false)
const modsLoadError = ref(null)
/** 启动页 logo 下方：来自 /api/mods/loading-status */
const startupModPreview = ref([])

function extractModNames(list) {
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
const startupStoreModNames = computed(() => extractModNames(modsStore.modsForUi))

const startupModNames = computed(() => {
  if (startupPreviewModNames.value.length > 0) return startupPreviewModNames.value
  return startupStoreModNames.value
})

const primaryModName = computed(() => startupModNames.value[0] || '')

let splashFinishOnce = false
/** 开屏进度条（主界面 opacity:0 时左下角 progress-panel 不可见，需在遮罩内单独展示） */
const startupProgressPct = ref(0)
let startupProgressRaf = null

function stopStartupProgressLoop() {
  if (startupProgressRaf != null) {
    cancelAnimationFrame(startupProgressRaf)
    startupProgressRaf = null
  }
}

function runStartupProgressLoop() {
  const t0 = performance.now()
  const tick = () => {
    if (!startupVisible.value) {
      stopStartupProgressLoop()
      return
    }
    const elapsed = performance.now() - t0
    const linear = Math.min(1, elapsed / STARTUP_SPLASH_MS)
    const eased = 1 - (1 - linear) ** 2
    const pct = Math.min(88, Math.round(eased * 88))
    if (pct > startupProgressPct.value) {
      startupProgressPct.value = pct
    }
    startupProgressRaf = requestAnimationFrame(tick)
  }
  startupProgressRaf = requestAnimationFrame(tick)
}

/** 点击跳过时提前结束「最短开屏」等待，避免 Promise 挂死 */
let resolveStartupMinWait = null
let switchViewEvent = null
let startupRevealTimer = null
let startupFailsafeTimer = null
let startupAudio = null
let startupAudioFallbackPlayed = false
let startupAudioUserGestureHandler = null

function finishStartupUi() {
  startupVisible.value = false
  appReady.value = true
  startupReveal.notifyAppReady()
}

const isDesktopShell = () => {
  if (typeof window === 'undefined') return false
  if (window.xcagiDesktop) return true
  // 旧版 Electron 壳可能未注入 preload，用 UA 识别桌面 WebView
  return typeof navigator !== 'undefined' && /Electron/i.test(navigator.userAgent)
}

/** 仅跳过开屏动画（桌面仍需走企业版登录校验，见 runEnterpriseStartupAuth） */
const shouldSkipSplashVisual = () =>
  isSandboxMode ||
  skipSplashByUrl ||
  isDesktopShell() ||
  isPlatformShellModeEnabled() ||
  isPublicEntryRoute()

/** @deprecated 使用 shouldSkipSplashVisual；保留别名避免遗漏引用 */
const shouldSkipStartupSplash = shouldSkipSplashVisual

/** 登录/授权等页必须立刻收起开屏，否则会挡住表单（z-index 10000） */
function dismissStartupSplashImmediate() {
  startupReveal.disableGiftFlow()
  finishStartupUi()
  stopStartupProgressLoop()
  startupProgressPct.value = 100
  if (splashFinishOnce) return
  splashFinishOnce = true
  if (startupFailsafeTimer != null) {
    window.clearTimeout(startupFailsafeTimer)
    startupFailsafeTimer = null
  }
  if (startupRevealTimer) {
    window.clearTimeout(startupRevealTimer)
    startupRevealTimer = null
  }
  if (resolveStartupMinWait) {
    resolveStartupMinWait()
    resolveStartupMinWait = null
  }
}

if (shouldSkipSplashVisual()) {
  startupReveal.disableGiftFlow()
  dismissStartupSplashImmediate()
}

async function runEnterpriseStartupAuth() {
  if (isPublicEntryRoute()) return true
  let sku = 'generic'
  try {
    sku = await fetchProductSku()
  } catch {
    /* ignore */
  }
  const authResult = await ensureStartupAuthenticated()
  if (!authResult.ok) return false
  let sunbirdAccount = false
  try {
    const { isSunbirdAccountUsername } = await import('@/constants/accountModBinding')
    sunbirdAccount = isSunbirdAccountUsername(authResult.accountUsername)
  } catch {
    /* ignore */
  }
  if (!isEnterpriseEdition(sku) && !sunbirdAccount) return true
  try {
    await modsStore.initialize(true, {
      entitledModIds: authResult.entitledModIds,
      forceFromEntitlements: sunbirdAccount || authResult.entitledModIds.length > 0,
      accountUsername: authResult.accountUsername,
    })
  } catch (e) {
    console.warn('[App] mods initialize after auth:', e)
  }
  return true
}

/**
 * 构造登录回跳路径：严禁把「当前已在 /login?redirect=…」整串再次嵌套进 redirect（会产生无限 ?redirect=/login?redirect=…）。
 */
function safeRedirectFromLocation() {
  const path = window.location.pathname || '/'
  const search = window.location.search || ''
  const hash = window.location.hash || ''

  if (path !== '/login' && !path.endsWith('/login')) {
    return `${path}${search}${hash}`
  }

  try {
    const params = new URLSearchParams(search.startsWith('?') ? search.slice(1) : '')
    let inner = params.get('redirect')
    if (!inner || typeof inner !== 'string') return '/'
    inner = decodeURIComponent(inner.trim())
    // 剥洋葱：内层仍是 /login?redirect=… 时继续取内层 redirect，最多 5 层防循环
    for (let i = 0; i < 5 && inner.startsWith('/login'); i++) {
      const q = inner.indexOf('?')
      if (q < 0) {
        inner = '/'
        break
      }
      const nested = new URLSearchParams(inner.slice(q + 1)).get('redirect')
      inner = nested ? decodeURIComponent(nested.trim()) : '/'
    }
    const cleanPath = inner.split('?')[0].split('#')[0]
    if (cleanPath.startsWith('/') && !cleanPath.startsWith('//') && !cleanPath.startsWith('/login')) {
      return cleanPath
    }
  } catch {
    /* ignore */
  }
  return '/'
}

function buildLoginLocation() {
  let redirect = safeRedirectFromLocation()
  if (!redirect.startsWith('/') || redirect.startsWith('//') || redirect.startsWith('/login')) {
    redirect = '/'
  }
  return {
    name: 'login',
    query: {
      redirect,
    },
  }
}

async function syncMarketTokensFromSession() {
  try {
    const handoff = await fetchSessionMarketHandoff()
    persistMarketTokensFromHandoff(handoff)
  } catch (error) {
    console.debug(
      '[App] session-handoff skipped:',
      error instanceof Error ? error.message : error
    )
  }
}

async function ensureStartupAuthenticated() {
  try {
    const res = await authApi.validateSession()
    if (res?.success === true || res?.valid === true || res?.data?.valid === true) {
      await syncMarketTokensFromSession()
      try {
        const { useAccountProfileStore } = await import('@/stores/accountProfile')
        await useAccountProfileStore().refreshFromServer()
      } catch {
        /* ignore */
      }
      let entitledModIds = []
      let accountUsername = ''
      try {
        const { readEntitledModIdsFromAuthPayload } = await import('@/stores/mods')
        entitledModIds = readEntitledModIdsFromAuthPayload(res)
        const data =
          res?.data && typeof res.data === 'object' && !Array.isArray(res.data)
            ? res.data
            : res
        accountUsername = String(data?.username || data?.user?.username || '').trim()
      } catch {
        /* ignore */
      }
      return { ok: true, entitledModIds, accountUsername }
    }
  } catch {
    // Fall through to the local login page.
  }
  dismissStartupSplashImmediate()
  void router.replace(buildLoginLocation())
  return { ok: false, entitledModIds: [] }
}

const loadModsForStartup = async () => {
  if (typeof localStorage !== 'undefined' && localStorage.getItem(CLIENT_MODS_UI_OFF_KEY) === '1') {
    startupModPreview.value = []
    modsLoading.value = false
    return
  }
  modsLoading.value = true
  modsLoadError.value = null
  try {
    const d = await fetchModLoadingStatusShared()
    if (!d) {
      startupModPreview.value = []
      return
    }
    const raw = d.mods
    startupModPreview.value = Array.isArray(raw) ? raw : []
    const hint = summarizeModLoadingData(d)
    if (hint) {
      modsLoadError.value = hint
    }
  } catch (error) {
    startupModPreview.value = []
    if (isApiFetchTimeoutError(error)) {
      console.debug(
        '[App] Mod loading-status 超时（后端可能仍在启动），开屏结束后将再试。',
        error
      )
    } else {
      console.warn('[App] Mod loading-status error:', error instanceof Error ? error.message : error)
    }
  } finally {
    modsLoading.value = false
    if (startupVisible.value) {
      startupProgressPct.value = Math.max(startupProgressPct.value, 72)
    }
  }
}

function completeStartupSplash() {
  const firstRun = !splashFinishOnce
  if (firstRun) {
    splashFinishOnce = true
    if (startupFailsafeTimer != null) {
      window.clearTimeout(startupFailsafeTimer)
      startupFailsafeTimer = null
    }
    stopStartupProgressLoop()
    startupProgressPct.value = 100
    if (startupRevealTimer) {
      window.clearTimeout(startupRevealTimer)
      startupRevealTimer = null
    }
    if (resolveStartupMinWait) {
      resolveStartupMinWait()
      resolveStartupMinWait = null
    }
  } else {
    // 兜底/跳过时可能已标记 finish 但遮罩未关，必须强制收起（避免永久卡在开屏）
    finishStartupUi()
    return
  }
  // 无论会进入主界面还是被重定向到登录页，都必须先收起启动遮罩，避免“看起来卡住”。
  const authTimeout = new Promise((resolve) => {
    window.setTimeout(() => resolve({ ok: false, entitledModIds: [] }), STARTUP_AUTH_TIMEOUT_MS)
  })
  void Promise.race([ensureStartupAuthenticated(), authTimeout])
    .catch(() => ({ ok: false, entitledModIds: [] }))
    .finally(finishStartupUi)
  startupAudioFallbackPlayed = true
  if (startupAudio) {
    startupAudio.pause()
    startupAudio.currentTime = 0
  }
  if (startupAudioUserGestureHandler) {
    document.removeEventListener('pointerdown', startupAudioUserGestureHandler)
    document.removeEventListener('keydown', startupAudioUserGestureHandler)
    startupAudioUserGestureHandler = null
  }
}

const tryPlayStartupAudio = () => {
  if (!startupAudio || startupAudioFallbackPlayed) return
  startupAudio.play().catch(() => {
    // Autoplay may be blocked; wait for first user gesture.
  })
}

const bindStartupAudioFallback = () => {
  startupAudioUserGestureHandler = () => {
    if (!startupAudio || startupAudioFallbackPlayed) return
    startupAudioFallbackPlayed = true
    startupAudio.play().catch(() => {
      // Ignore playback failure if the environment blocks audio.
    })
    document.removeEventListener('pointerdown', startupAudioUserGestureHandler)
    document.removeEventListener('keydown', startupAudioUserGestureHandler)
  }
  document.addEventListener('pointerdown', startupAudioUserGestureHandler, { once: true })
  document.addEventListener('keydown', startupAudioUserGestureHandler, { once: true })
}

const skipStartupSplash = () => {
  if (!startupVisible.value) return
  startupReveal.skipToDone()
  completeStartupSplash()
}

watch(
  () => route.name,
  () => {
    if (isPublicEntryRoute()) {
      dismissStartupSplashImmediate()
    }
  },
  { immediate: true },
)

const hasLegacyProModeRuntime = () => {
  const legacyToggle = window.__legacyToggleProMode || window.toggleProMode
  return typeof legacyToggle === 'function'
}

const readProModeStateFromDom = () => {
  const overlay = document.getElementById('proModeOverlay')
  if (!overlay && typeof window.__XCAGI_IS_PRO_MODE === 'boolean') {
    return !!window.__XCAGI_IS_PRO_MODE
  }
  const bodyActive = document.body.classList.contains('pro-mode-active')
  const overlayActive = !!overlay?.classList.contains('active')
  const overlayVisible = !!overlay && overlay.style.display !== 'none'
  // Toggle class can lag animation/legacy lifecycle; use overlay/body as single source of truth.
  return bodyActive || (overlayActive && overlayVisible)
}

const syncProModeStateSoon = () => {
  requestAnimationFrame(() => {
    isProMode.value = readProModeStateFromDom()
  })
  setTimeout(() => {
    isProMode.value = readProModeStateFromDom()
  }, 350)
}

const resolveModProEntryPath = () => {
  const mods = Array.isArray(modsStore.modsForUi) ? modsStore.modsForUi : []
  for (const mod of mods) {
    const frontend = mod?.frontend && typeof mod.frontend === 'object' ? mod.frontend : {}
    const explicit = typeof frontend.pro_entry_path === 'string' ? frontend.pro_entry_path.trim() : ''
    if (explicit) return explicit
    const menu = Array.isArray(mod?.menu) ? mod.menu : []
    const firstPath = typeof menu[0]?.path === 'string' ? menu[0].path.trim() : ''
    if (firstPath) return firstPath
  }
  return ''
}

const enterModProMode = async () => {
  if (!Array.isArray(modsStore.modsForUi) || modsStore.modsForUi.length === 0) {
    try {
      await modsStore.initialize()
    } catch (error) {
      console.warn('加载 Mod 菜单失败，无法解析专业版入口:', error)
    }
  }
  const targetPath = resolveModProEntryPath()
  isProMode.value = true
  if (targetPath && route.path !== targetPath) {
    await router.push(targetPath).catch((error) => {
      console.warn('跳转 Mod 专业版入口失败:', error)
    })
  }
}

const exitModProMode = async () => {
  isProMode.value = false
  if (route.name !== 'chat') {
    await router.push({ name: 'chat' }).catch(() => undefined)
  }
}

const handleToggleProMode = () => {
  const legacyToggle = window.__legacyToggleProMode || window.toggleProMode
  if (!resolveModProEntryPath() && typeof legacyToggle === 'function') {
    legacyToggle()
    syncProModeStateSoon()
    return
  }
  if (isProMode.value) {
    void exitModProMode()
  } else {
    void enterModProMode()
  }
}

const syncGlobalProMode = () => {
  const active = !!isProMode.value
  window.__XCAGI_IS_PRO_MODE = active
  window.dispatchEvent(new CustomEvent('xcagi:pro-mode-changed', {
    detail: { isProMode: active }
  }))
}

let proModeObserver = null
let onToggleProModeEvent = null
let onModsVisibilityRetry = null
let onPageShowBfCache = null

onMounted(async () => {
  if (isPublicEntryRoute()) {
    dismissStartupSplashImmediate()
  }

  try {
    if (new URLSearchParams(window.location.search).has('replayNav')) {
      sessionStorage.removeItem('xcagi.navReveal.done')
    }
  } catch {
    /* ignore */
  }

  if (shouldSkipSplashVisual()) {
    dismissStartupSplashImmediate()
    // 桌面壳：须等待路由就绪再校验，否则 replace('/login') 可能无效
    void router.isReady().then(() => runEnterpriseStartupAuth())
  }

  // 非开屏场景（如桌面 shell）尽早拉 Mod；开屏流程内会 initialize(true)，避免重复 force
  if (shouldSkipSplashVisual()) {
    void modsStore.initialize()
  }
  onModsVisibilityRetry = () => {
    if (document.visibilityState !== 'visible') return
    if (!modsStore.isLoaded) void modsStore.initialize()
  }
  document.addEventListener('visibilitychange', onModsVisibilityRetry)

  onPageShowBfCache = (e) => {
    if (!e.persisted) return
    if (modsStore.clientModsUiOff) return
    void modsStore.initialize(true)
  }
  window.addEventListener('pageshow', onPageShowBfCache)

  // 开机动画与主界面就绪不等待 Mod API（后端慢或未启动时仍可进入应用）
  // 注意：preload='metadata' 而非 'auto'，避免大文件下载阻塞首屏渲染
  startupAudio = new Audio('/startup/startup-enter.mp3')
  startupAudio.preload = 'metadata'
  startupAudio.volume = 0.9
  tryPlayStartupAudio()
  bindStartupAudioFallback()
  startupProgressPct.value = 0
  runStartupProgressLoop()

  const minSplashElapsed = new Promise((resolve) => {
    resolveStartupMinWait = () => {
      resolveStartupMinWait = null
      resolve()
    }
    startupRevealTimer = window.setTimeout(() => {
      startupRevealTimer = null
      resolveStartupMinWait = null
      resolve()
    }, STARTUP_SPLASH_MS)
  })
  const loadStartupMods = loadModsForStartup().catch((e) => {
    console.warn('[App] loadModsForStartup:', e)
  })
  const modWaitOrCap = Promise.race([
    loadStartupMods,
    new Promise((r) => {
      window.setTimeout(r, STARTUP_MOD_FETCH_CAP_MS)
    }),
  ])

  void loadStartupMods.finally(() => {
    modsStore.applyLoadingStatusPreview(startupModPreview.value)
  })

  startupFailsafeTimer = window.setTimeout(() => {
    if (!appReady.value) {
      console.warn(
        '[App] 开屏超时兜底：强制结束启动遮罩（若仍白屏请看控制台其它报错）。'
      )
      startupReveal.skipToDone()
      completeStartupSplash()
    }
  }, STARTUP_FAILSAFE_MS)

  void (async () => {
    if (shouldSkipSplashVisual()) {
      return
    }
    startupReveal.begin()
    try {
      const authResult = await ensureStartupAuthenticated().catch(() => ({
        ok: false,
        entitledModIds: [],
      }))
      await minSplashElapsed
      startupReveal.completeStep1()

      await modWaitOrCap
      try {
        modsStore.applyLoadingStatusPreview(startupModPreview.value)
      } catch (e) {
        console.warn('[App] applyLoadingStatusPreview:', e)
      }
      startupReveal.completeStep2()

      try {
        const { isSunbirdAccountUsername } = await import('@/constants/accountModBinding')
        await modsStore.initialize(true, {
          entitledModIds: authResult.entitledModIds,
          forceFromEntitlements:
            authResult.ok &&
            (isSunbirdAccountUsername(authResult.accountUsername) ||
              authResult.entitledModIds.length > 0),
          accountUsername: authResult.accountUsername,
        })
        if (modsStore.clientModsUiOff) {
          useWorkflowAiEmployeesStore().stripModWorkflowEmployeeKeys()
        }
      } catch (e) {
        console.warn('[App] Mod initialize（开屏）:', e)
      }

      await startupReveal.startUnboxing()
      startupReveal.markDone()
    } catch (e) {
      console.error('[App] 开屏等待阶段异常:', e)
      startupReveal.skipToDone()
    } finally {
      if (startupFailsafeTimer != null) {
        window.clearTimeout(startupFailsafeTimer)
        startupFailsafeTimer = null
      }
      completeStartupSplash()
    }
  })()

  const syncProModeFromDom = () => {
    isProMode.value = readProModeStateFromDom()
  }

  window.setProModeEnabled = (enabled) => {
    const shouldEnable = !!enabled
    const active = isProMode.value || readProModeStateFromDom()
    if (shouldEnable === active) {
      isProMode.value = active
      return
    }
    if (!resolveModProEntryPath() && hasLegacyProModeRuntime()) {
      const legacyToggle = window.__legacyToggleProMode || window.toggleProMode
      legacyToggle()
      syncProModeStateSoon()
    } else if (shouldEnable) {
      void enterModProMode()
    } else {
      void exitModProMode()
    }
  }

  onToggleProModeEvent = () => {
    handleToggleProMode()
  }

  window.addEventListener('xcagi:toggle-pro-mode', onToggleProModeEvent)

  if (hasLegacyProModeRuntime()) {
    let scheduled = false
    const scheduleSync = () => {
      if (scheduled) return
      scheduled = true
      requestAnimationFrame(() => {
        scheduled = false
        syncProModeFromDom()
      })
    }
    proModeObserver = new MutationObserver(() => {
      scheduleSync()
    })
    proModeObserver.observe(document.body, { attributes: true, attributeFilter: ['class'] })
    const overlay = document.getElementById('proModeOverlay')
    if (overlay) {
      proModeObserver.observe(overlay, { attributes: true, attributeFilter: ['class', 'style'] })
    }
  }
  syncProModeFromDom()
  syncGlobalProMode()

  const bindOnce = (id, eventName, handler) => {
    const el = document.getElementById(id)
    if (!el) return
    if (el.getAttribute('data-xcagi-bound') === '1') return
    el.setAttribute('data-xcagi-bound', '1')
    el.addEventListener(eventName, handler)
  }

  const routeName = String(route.name || '')
  const shouldBindLegacyUploadHooks = routeName === 'chat' || routeName === ''
  if (shouldBindLegacyUploadHooks) {
    bindOnce('fileUploadEntry', 'click', () => {
      try {
        if (typeof window.openImportWindow === 'function') {
          console.log('[xcagi] click fileUploadEntry -> openImportWindow()')
          window.openImportWindow()
        } else {
          console.warn('[xcagi] openImportWindow not found on window')
        }
      } catch (err) {
        console.warn('[xcagi] fileUploadEntry click failed:', err)
      }
    })

    bindOnce('chooseFileBtn', 'click', () => {
      const fileInput = document.getElementById('fileInput')
      if (fileInput) fileInput.click()
    })
  }

  switchViewEvent = (event) => {
    const view = event.detail?.view
    if (view) {
      console.log('[App] xcagi:switch-view received, navigating to:', view)
      router.push({ name: view })
    }
  }
  window.addEventListener('xcagi:switch-view', switchViewEvent)

  if (isSandboxMode) {
    window.addEventListener('message', (e) => {
      if (e.data?.type === 'sandbox:navigate' && typeof e.data.path === 'string') {
        router.push(e.data.path)
      }
    })
    window.parent.postMessage({ type: 'sandbox:ready' }, '*')
  }
})

watch(isProMode, () => {
  syncGlobalProMode()
})

onBeforeUnmount(() => {
  if (onModsVisibilityRetry) {
    document.removeEventListener('visibilitychange', onModsVisibilityRetry)
    onModsVisibilityRetry = null
  }
  if (onPageShowBfCache) {
    window.removeEventListener('pageshow', onPageShowBfCache)
    onPageShowBfCache = null
  }
  if (proModeObserver) {
    proModeObserver.disconnect()
    proModeObserver = null
  }
  if (onToggleProModeEvent) {
    window.removeEventListener('xcagi:toggle-pro-mode', onToggleProModeEvent)
    onToggleProModeEvent = null
  }
  if (switchViewEvent) {
    window.removeEventListener('xcagi:switch-view', switchViewEvent)
    switchViewEvent = null
  }
  if (startupRevealTimer) {
    window.clearTimeout(startupRevealTimer)
    startupRevealTimer = null
  }
  if (startupFailsafeTimer != null) {
    window.clearTimeout(startupFailsafeTimer)
    startupFailsafeTimer = null
  }
  stopStartupProgressLoop()
  if (startupAudioUserGestureHandler) {
    document.removeEventListener('pointerdown', startupAudioUserGestureHandler)
    document.removeEventListener('keydown', startupAudioUserGestureHandler)
    startupAudioUserGestureHandler = null
  }
  if (startupAudio) {
    startupAudio.pause()
    startupAudio.currentTime = 0
    startupAudio = null
  }
  if (window.setProModeEnabled) {
    delete window.setProModeEnabled
  }
  if (typeof window.__XCAGI_IS_PRO_MODE !== 'undefined') {
    delete window.__XCAGI_IS_PRO_MODE
  }
})
</script>

<template>
  <div
    v-if="startupVisible && !hideChrome"
    class="startup-splash"
    aria-label="初始化动画，点击跳过"
    title="点击屏幕快速进入"
    @pointerdown.stop="skipStartupSplash"
  >
    <div class="startup-splash-inner">
      <div class="startup-logo-wrap">
        <img class="startup-logo-base" src="/startup/xc-logo-base.jpg" alt="XC logo" />
        <img class="startup-logo-text" src="/startup/xc-logo-text.jpg" alt="XC logo with text" />
      </div>
      <div v-if="primaryModName" class="startup-mod-title">
        {{ primaryModName }}
      </div>
      <div v-if="startupVisible" class="startup-mod-chips-wrap">
        <template v-if="startupModNames.length > 1">
          <div class="startup-mod-chips-hint">已加载扩展包</div>
          <div class="startup-mod-chips">
            <span
              v-for="modName in startupModNames"
              :key="modName"
              class="startup-mod-chip"
            >
              {{ modName }}
            </span>
          </div>
        </template>
        <div v-else class="startup-mod-status">
          <div v-if="primaryModName" class="mod-loaded">
            <i class="fa fa-check-circle" aria-hidden="true"></i>
            <span>当前扩展包：{{ primaryModName }}</span>
          </div>
          <div v-else-if="modsLoading" class="mod-loading">
            <i class="fa fa-spinner fa-spin" aria-hidden="true"></i>
            <span>正在加载扩展包...</span>
          </div>
          <div v-else-if="modsLoadError" class="mod-error">
            <i class="fa fa-exclamation-circle" aria-hidden="true"></i>
            <span>扩展包加载异常</span>
          </div>
          <div v-else class="mod-loading">
            <i class="fa fa-circle-o-notch fa-spin" aria-hidden="true"></i>
            <span>正在初始化...</span>
          </div>
        </div>
      </div>
      <StartupGiftReveal
        v-if="!startupReveal.giftFlowDisabled"
        :primary-mod-name="primaryModName"
        :mod-names="startupModNames"
      />
      <div v-if="startupVisible" class="startup-progress-wrap" aria-hidden="true">
        <div class="startup-progress-track">
          <div
            class="startup-progress-fill"
            :style="{ width: `${startupProgressPct}%` }"
          ></div>
        </div>
      </div>
    </div>
    <div class="startup-version" aria-label="当前版本">v8.0.0</div>
  </div>

  <div class="app-shell" :class="{ 'is-ready': appReady || hideChrome }">
    <div class="transition-overlay" id="transitionOverlay"></div>

    <div class="preview-float-window" id="previewFloatWindow">
    <div class="preview-header">
      <h4><i class="fa fa-television" aria-hidden="true"></i> 媒体预览</h4>
      <button class="preview-close" id="previewCloseBtn" data-close-action="closePreviewWindow">&times;</button>
    </div>
    <div class="preview-content">
      <div class="preview-media" id="previewMedia">
        <div class="preview-placeholder">暂无预览内容</div>
      </div>
    </div>
  </div>

    <div class="progress-panel" id="progressPanel">
    <div class="progress-panel-header">
      <div class="progress-title">任务进度</div>
      <button class="progress-close" id="progressCloseBtn" data-close-action="hideProgress">&times;</button>
    </div>
    <div class="progress-info">
      <span class="progress-status">处理中...</span>
      <span class="progress-percent" id="progressPercent">0%</span>
    </div>
    <div class="progress-bar-wrapper">
      <div class="progress-bar-fill" id="progressBarFill" style="width: 0%;"></div>
    </div>
    <div class="progress-task" id="progressTask">正在初始化任务...</div>
  </div>

    <div class="file-upload-entry" id="fileUploadEntry">
    <span class="entry-icon" aria-hidden="true"><i class="fa fa-folder-open-o"></i></span>
    <span class="entry-text">上传文件</span>
  </div>

    <div class="import-float-window" id="importFloatWindow">
    <div class="import-header">
      <h4><i class="fa fa-folder-open-o" aria-hidden="true"></i> 导入文件</h4>
      <button class="import-close" id="importCloseBtn" data-close-action="closeImportWindow">&times;</button>
    </div>
    <div class="import-content">
      <div class="drop-zone" id="dropZone">
        <div class="drop-zone-icon" aria-hidden="true"><i class="fa fa-folder-open"></i></div>
        <div class="drop-zone-text">拖拽文件到此处或点击选择</div>
        <div class="drop-zone-hint">支持 Excel、CSV、图片等文件</div>
      </div>
      <input type="file" class="file-input" id="fileInput" multiple accept="*/*">
      <div class="import-actions">
        <button class="btn btn-primary" id="chooseFileBtn">选择文件</button>
        <button class="btn btn-success" id="openCameraBtn"><i class="fa fa-camera" aria-hidden="true"></i> 拍照识别</button>
        <button class="btn btn-secondary" id="cancelImportBtn" data-close-action="closeImportWindow">取消</button>
      </div>
      <div class="camera-panel" id="cameraPanel" style="display: none;">
        <video id="cameraVideo" autoplay playsinline></video>
        <canvas id="cameraCanvas" style="display: none;"></canvas>
        <div class="camera-buttons">
          <button class="btn btn-primary" id="capturePhotoBtn">拍照</button>
          <button class="btn btn-secondary" id="closeCameraBtn" data-close-action="closeCamera">关闭</button>
        </div>
      </div>
      <div class="import-progress" id="importProgress">
        <div class="progress-bar-container">
          <div class="progress-bar" id="progressBar"></div>
        </div>
        <div class="progress-text">
          <span id="progressText">读取中...</span>
          <span id="importProgressPercent">0%</span>
        </div>
      </div>
      <div class="import-status" id="importStatus"></div>
    </div>
  </div>

    <div class="import-float-window" id="labelsExportWindow">
    <div class="import-header">
      <h4><i class="fa fa-tag" aria-hidden="true"></i> 商标导出</h4>
      <button class="import-close" id="labelsExportCloseBtn" type="button" title="关闭">&times;</button>
    </div>
    <div class="import-content">
      <div id="labelsExportList" class="labels-export-list">
        <p class="labels-export-hint">加载中...</p>
      </div>
      <div class="import-actions" style="margin-top: 12px;">
        <button class="btn btn-secondary" id="labelsExportCloseBtn2" type="button">关闭</button>
      </div>
    </div>
  </div>

    <div class="import-float-window" id="printPanelWindow">
    <div class="import-header">
      <h4><i class="fa fa-print" aria-hidden="true"></i> 标签打印</h4>
      <button class="import-close" id="printPanelCloseBtn" type="button" title="关闭">&times;</button>
    </div>
    <div class="import-content">
      <div id="printPanelStatus" class="labels-export-hint">正在连接打印机...</div>
      <div id="printPanelProgress" class="print-panel-progress" style="display:none; margin:10px 0;"></div>
      <div id="printPanelResults" class="print-panel-results" style="margin:10px 0; max-height:240px; overflow-y:auto;"></div>
      <div class="import-actions" style="margin-top: 12px;">
        <button class="btn btn-primary" id="printPanelStartBtn" type="button">开始打印</button>
        <button class="btn btn-secondary" id="printPanelCloseBtn2" type="button">关闭</button>
      </div>
    </div>
  </div>

    <div id="labelFloatPreviews" class="label-float-previews hidden" aria-hidden="true"></div>

    <div id="labelPreviewModal" class="label-preview-modal hidden" aria-hidden="true">
    <div class="label-preview-modal-backdrop"></div>
    <div class="label-preview-modal-content">
      <img id="labelPreviewModalImg" src="" alt="标签预览" />
      <div class="label-preview-modal-actions">
        <a id="labelPreviewModalDownload" href="" download="" class="btn btn-primary">下载标签</a>
        <button type="button" class="btn btn-secondary label-preview-modal-close">关闭</button>
      </div>
    </div>
  </div>

    <GlobalReadTokenPrompt api-base="" />
    <GlobalWriteTokenPrompt />
    <AppDialogHost />
    <GlobalLanGateModal />

    <router-view v-if="hideChrome" />
    <MainLayout
      v-else
      :is-pro-mode="isProMode"
      @toggle-pro-mode="handleToggleProMode"
    >
      <router-view v-slot="{ Component, route }">
        <keep-alive :max="12">
          <component :is="Component" :key="route.name || route.path" />
        </keep-alive>
      </router-view>
    </MainLayout>
  </div>
</template>

<style>
.app-shell {
  /* 不用 opacity:0 藏整页（开屏遮罩已 z-index 盖住）；否则 appReady 未置位时会长期白屏 */
  opacity: 1;
  transition: opacity 320ms ease;
  background:
    radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.88), transparent 42%),
    linear-gradient(135deg, #edf5fb 0%, #e7eef6 48%, #eef3f8 100%);
}

.startup-splash {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at 28% 20%, rgba(255, 255, 255, 0.9), transparent 30%),
    linear-gradient(135deg, #edf5fb 0%, #e7eef6 48%, #eef3f8 100%);
  opacity: 1;
  visibility: visible;
  transition: opacity 360ms ease, visibility 0s linear 360ms;
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
  overflow: hidden;
}

.startup-splash::before,
.startup-splash::after {
  content: "";
  position: absolute;
  pointer-events: none;
  display: none;
}

.startup-splash::before {
  width: min(760px, 74vw);
  aspect-ratio: 1;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(24, 144, 255, 0.13) 0%, rgba(34, 211, 238, 0.08) 34%, transparent 68%);
  filter: blur(10px);
  animation: startupAuraPulse 3600ms ease-in-out infinite;
}

.startup-splash::after {
  inset: 0;
  background:
    linear-gradient(115deg, transparent 0%, rgba(255, 255, 255, 0.26) 42%, transparent 58%),
    radial-gradient(circle at 70% 72%, rgba(34, 211, 238, 0.09), transparent 24%);
  transform: translateX(-18%);
  animation: startupBackdropSheen 5200ms ease-in-out infinite;
}

.startup-splash.hide {
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
}

.startup-splash-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  max-width: min(480px, 92vw);
  padding: 0 var(--app-space-md);
  position: relative;
  z-index: 1;
  animation: startupContentEnter 520ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
}

.startup-version {
  position: absolute;
  left: 24px;
  bottom: 20px;
  z-index: 1;
  padding: 7px 11px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: rgba(23, 32, 51, 0.56);
  background: rgba(255, 255, 255, 0.46);
  border: 1px solid rgba(255, 255, 255, 0.64);
  box-shadow:
    0 8px 20px rgba(15, 76, 129, 0.07),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(12px);
  pointer-events: none;
  user-select: none;
  -webkit-user-select: none;
}

.startup-logo-wrap {
  width: min(380px, 68vw);
  aspect-ratio: 1 / 1;
  position: relative;
  display: grid;
  place-items: center;
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 251, 255, 0.76) 100%);
  border: 1px solid rgba(255, 255, 255, 0.78);
  box-shadow:
    0 20px 50px rgba(15, 76, 129, 0.12),
    0 8px 18px rgba(15, 76, 129, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.95);
  overflow: hidden;
  animation: none;
}

.startup-logo-wrap::before,
.startup-logo-wrap::after {
  content: "";
  position: absolute;
  pointer-events: none;
  display: none;
}

.startup-logo-wrap::before {
  inset: 10%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(34, 211, 238, 0.22) 0%, rgba(24, 144, 255, 0.1) 42%, transparent 70%);
  filter: blur(8px);
}

.startup-logo-wrap::after {
  inset: -35%;
  background: linear-gradient(115deg, transparent 34%, rgba(255, 255, 255, 0.58) 48%, transparent 62%);
  transform: translateX(-42%) rotate(8deg);
  animation: startupLogoSheen 2200ms ease-out 260ms both;
}

.startup-logo-wrap img {
  position: absolute;
  inset: 8%;
  width: 84%;
  height: 84%;
  object-fit: contain;
  user-select: none;
  -webkit-user-drag: none;
  z-index: 1;
}

.startup-logo-base {
  opacity: 1;
}

.startup-logo-text {
  opacity: 0;
  animation: startupTextFadeIn 1200ms ease 450ms forwards;
}

@keyframes startupTextFadeIn {
  from {
    opacity: 0;
    transform: translateY(6px) scale(0.985);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.startup-mod-title {
  font-size: 24px;
  font-weight: 700;
  color: #172033;
  text-align: center;
  margin-top: 10px;
  letter-spacing: -0.02em;
  animation: startupSoftEnter 800ms ease 600ms forwards;
  opacity: 0;
}

.startup-progress-wrap {
  width: 100%;
  max-width: min(420px, 84vw);
  margin-top: 10px;
  animation: startupSoftEnter 500ms ease 200ms forwards;
  opacity: 0;
}

.startup-progress-track {
  height: 5px;
  border-radius: 999px;
  background: rgba(15, 76, 129, 0.1);
  overflow: hidden;
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.08);
}

.startup-progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #0b63ce 0%, #12bde6 62%, #62d9ff 100%);
  transition: width 120ms ease-out;
  animation: none;
  box-shadow: none;
}

.startup-mod-chips-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  width: 100%;
  max-width: min(420px, 92vw);
  animation: startupSoftEnter 600ms ease 420ms both;
}

.startup-mod-chips-hint {
  font-size: var(--app-font-size-caption);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(23, 32, 51, 0.55);
}

.startup-mod-chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.startup-mod-chip {
  padding: var(--app-space-sm) var(--app-space-md);
  border-radius: 999px;
  font-size: 13px;
  color: #172033;
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid rgba(255, 255, 255, 0.78);
  box-shadow:
    0 8px 20px rgba(15, 76, 129, 0.09),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.startup-mod-status {
  text-align: center;
  font-size: var(--app-font-size-body);
  color: rgba(23, 32, 51, 0.66);
  min-height: 28px;
}

.mod-loading,
.mod-loaded,
.mod-error {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.54);
  border: 1px solid rgba(255, 255, 255, 0.72);
  box-shadow: 0 8px 20px rgba(15, 76, 129, 0.07);
  backdrop-filter: blur(12px);
  animation: fadeIn 300ms ease;
}

.mod-loading i {
  color: var(--app-accent, #1890ff);
}

.mod-loaded i {
  color: #36b35f;
}

.mod-error i {
  color: #ff4d4f;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes startupContentEnter {
  from {
    opacity: 0;
    transform: translateY(14px) scale(0.985);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes startupSoftEnter {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes startupLogoFloat {
  0%,
  100% {
    transform: translateY(0);
    box-shadow:
      0 28px 80px rgba(15, 76, 129, 0.18),
      0 12px 26px rgba(15, 76, 129, 0.08),
      inset 0 1px 0 rgba(255, 255, 255, 0.95);
  }
  50% {
    transform: translateY(-6px);
    box-shadow:
      0 34px 92px rgba(15, 76, 129, 0.2),
      0 16px 30px rgba(15, 76, 129, 0.1),
      inset 0 1px 0 rgba(255, 255, 255, 0.95);
  }
}

@keyframes startupLogoSheen {
  from {
    transform: translateX(-42%) rotate(8deg);
  }
  to {
    transform: translateX(42%) rotate(8deg);
  }
}

@keyframes startupAuraPulse {
  0%,
  100% {
    opacity: 0.72;
    transform: scale(0.96);
  }
  50% {
    opacity: 1;
    transform: scale(1.04);
  }
}

@keyframes startupBackdropSheen {
  0%,
  100% {
    opacity: 0.52;
    transform: translateX(-18%);
  }
  50% {
    opacity: 0.85;
    transform: translateX(8%);
  }
}

@keyframes startupProgressSheen {
  from {
    background-position: -120px 0, 0 0;
  }
  to {
    background-position: 120px 0, 0 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .startup-splash,
  .app-shell {
    transition-duration: 1ms;
  }

  .startup-splash::before,
  .startup-splash::after,
  .startup-logo-wrap,
  .startup-logo-wrap::after,
  .startup-logo-text,
  .startup-mod-title,
  .startup-progress-wrap,
  .startup-progress-fill,
  .startup-mod-chips-wrap,
  .mod-loading,
  .mod-loaded,
  .mod-error {
    animation: none;
  }

  .startup-logo-text,
  .startup-mod-title,
  .startup-progress-wrap {
    opacity: 1;
    transform: none;
  }
}
</style>
