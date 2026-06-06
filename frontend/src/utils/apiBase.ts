import { XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY } from './xcagiStorageKeys'
import { readCsrfTokenFromCookie, shouldAttachCsrfHeader } from './csrfCookie'

/**
 * Mod 列表、loading-status、routes 等读请求上限。
 * 冷启动时 lifespan 中 load_all_mods + 数据库初始化可能超过 1min；并行启动后仍可能偶发较慢，故与路由预取对齐放宽。
 */
/** 冷启动后台 load_all_mods 期间列表接口可能较慢，但不应无限挂起 */
export const DEFAULT_MOD_API_TIMEOUT_MS = 90_000

/** Mod 门面 HTTP 探针（status/employees）用较短超时，避免拖住 initialize */
export const MOD_PROBE_API_TIMEOUT_MS = 8_000

export type ApiFetchInit = RequestInit & { timeoutMs?: number }

/** 是否为 ``apiFetch`` 的限时中止（便于友好提示，避免控制台刷屏成「失败」） */
export function isApiFetchTimeoutError(e: unknown): boolean {
  if (e instanceof DOMException && e.name === 'AbortError') {
    return e.message.includes('apiFetch timeout')
  }
  if (e instanceof Error && e.name === 'AbortError') {
    return e.message.includes('apiFetch timeout')
  }
  return false
}

function mergeAbortSignals(a: AbortSignal, b: AbortSignal): AbortSignal {
  if (a.aborted) return a
  if (b.aborted) return b
  const c = new AbortController()
  const kick = (src: AbortSignal) => {
    if (!c.signal.aborted) {
      try {
        c.abort(src.reason)
      } catch {
        c.abort()
      }
    }
  }
  a.addEventListener('abort', () => kick(a), { once: true })
  b.addEventListener('abort', () => kick(b), { once: true })
  return c.signal
}

/**
 * Mod 等 API 的基址。
 * - **持久与线上一致（推荐）**：在 ``index.html`` 或 Nginx 子请求中先于 bundle 执行
 *   ``window.__XCMAX_API_BASE__ = '/fhd-api'``（或与站点一致的完整源），使登录 ``/api/auth/login``
 *   实际请求 ``/fhd-api/api/...``，即与服务器 PostgreSQL 账号库同源反代，无需改构建产物。
 * - 未设置且未配置 Vite 变量时：用相对路径（与页面同源）。Vite dev（如 :5001）下走 ``/api`` 代理。
 * - 开发联调可设 ``VITE_API_BASE`` / ``VITE_API_BASE_URL`` 为远端完整 API 源（由 Vite 代理转发）。
 *
 * Loopback 基址特例：构建或环境里常写 ``http://127.0.0.1:5000``。若用户用局域网 IP 打开页面
 * （如 ``http://192.168.*.*:5001`` 或 FastAPI 托管的 ``:5000``），浏览器仍请求 127.0.0.1 会构成跨域，
 * ``credentials: 'include'`` 下 CORS 须精确匹配 Origin，易整页 ``Failed to fetch``。
 * 故对 **纯 loopback/localhost** 的 API 基址一律改走相对路径 ``/api``（与当前页面同源）。
 */
function readInjectedApiBase(): string {
  if (typeof window === 'undefined') return ''
  const inj = (window as unknown as { __XCMAX_API_BASE__?: unknown }).__XCMAX_API_BASE__
  if (typeof inj !== 'string') return ''
  return inj.trim().replace(/\/$/, '')
}

function shouldPreferRelativeApiBase(): boolean {
  if (import.meta.env.DEV) return true
  if (import.meta.env.VITE_API_RELATIVE === '1') return true
  if (typeof window === 'undefined') return false
  const h = window.location.hostname || ''
  if (h === 'localhost' || h === '127.0.0.1') return true
  if (/^192\.168\.\d{1,3}\.\d{1,3}$/.test(h)) return true
  if (/^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(h)) return true
  if (/^172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}$/.test(h)) return true
  return false
}

export function getApiBase(): string {
  const injected = readInjectedApiBase()
  if (injected) {
    if (/^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/i.test(injected)) {
      return ''
    }
    return injected
  }

  const a = import.meta.env.VITE_API_BASE as string | undefined
  const b = import.meta.env.VITE_API_BASE_URL as string | undefined
  const raw = (typeof a === 'string' && a.trim() ? a : b) as string | undefined
  if (typeof raw === 'string' && raw.trim()) {
    const base = raw.trim().replace(/\/$/, '')
    if (/^https?:\/\/(127\.0\.0\.1|localhost)(:\d+)?$/i.test(base)) {
      return ''
    }
    // 开发 / 私网访问：与当前页不同源时走相对 /api，由 Vite 代理（避免直连公网 API 基址 CORS）
    if (shouldPreferRelativeApiBase() && typeof window !== 'undefined' && window.location?.origin) {
      try {
        const apiOrigin = new URL(base.includes('://') ? base : `http://${base}`).origin
        if (apiOrigin !== window.location.origin) {
          return ''
        }
      } catch {
        /* keep base */
      }
    }
    return base
  }
  return ''
}

/** 与当前站点同源的 API 路径，或 dev 下拼到后端根 */
export function apiUrl(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`
  const base = getApiBase()
  return base ? `${base}${p}` : p
}

export function getClientModsUiOffHeader(): Record<string, string> {
  try {
    const off = localStorage.getItem('xcagi_client_mods_ui_off') === '1';
    return off ? { 'X-Client-Mods-Off': '1' } : {};
  } catch {
    return {};
  }
}

function shouldAttachActiveModHeader(rawUrl = ''): boolean {
  const value = String(rawUrl || '').trim();
  if (!value) return true;
  try {
    const pathname = /^https?:\/\//i.test(value) ? new URL(value).pathname : value.split('?')[0] || '';
    return !pathname.startsWith('/api/auth/');
  } catch {
    return true;
  }
}

/** 与 ``installFetchDbReadToken`` / 业务库按 Mod 分表一致；签名由服务端 dev 模式放宽校验。 */
export function getActiveExtensionModHeaders(rawUrl = ''): Record<string, string> {
  if (!shouldAttachActiveModHeader(rawUrl)) return {};
  try {
    const id = String(localStorage.getItem(XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY) || '').trim();
    if (!id) return {};
    return { 'X-XCAGI-Active-Mod-Id': id };
  } catch {
    return {};
  }
}

/** 与 ``vite.config.js`` 中 /api 代理 target 一致；仅作 DEV 下网络失败时的单次回退。 */
const DEV_API_LOOPBACK_FALLBACK = 'http://127.0.0.1:5000'

function canRetryApiOnDevLoopback(originalInput: string): boolean {
  if (!import.meta.env.DEV) return false
  if (getApiBase() !== '') return false
  if (typeof window === 'undefined') return false
  const h = window.location.hostname
  if (h !== '127.0.0.1' && h !== 'localhost') return false
  if (/^https?:\/\//i.test(originalInput)) return false
  const path = originalInput.startsWith('/') ? originalInput : `/${originalInput}`
  return path.startsWith('/api/')
}

/** 与 ``pushClientModsOffState`` 一致：原版模式开关涉及 UI 回滚，不宜过短；后台同步与之对齐。 */
const CLIENT_MODS_OFF_SYNC_TIMEOUT_MS = 25_000

export function apiFetch(input: string, init?: ApiFetchInit): Promise<Response> {
  const url = input.startsWith('http') ? input : apiUrl(input)
  const {
    timeoutMs,
    signal: userSignal,
    headers: userHeaders,
    ...rest
  } = init || {}

  const modsOffHeaders = getClientModsUiOffHeader()
  const modScopeHeaders = getActiveExtensionModHeaders(url)
  const headers: Record<string, string> = {
    ...modsOffHeaders,
    ...modScopeHeaders,
    ...(typeof userHeaders === 'object' &&
    userHeaders !== null &&
    typeof (userHeaders as Headers).forEach === 'function'
      ? Object.fromEntries((userHeaders as Headers).entries())
      : ((userHeaders || {}) as Record<string, string>)),
  }
  const method = String((rest as { method?: string }).method || 'GET')
  if (shouldAttachCsrfHeader(method, headers)) {
    const tok = readCsrfTokenFromCookie()
    if (tok) headers['X-CSRF-Token'] = tok
  }

  let timeoutId: number | undefined
  let signal = userSignal

  if (typeof timeoutMs === 'number' && timeoutMs > 0) {
    const to = new AbortController()
    timeoutId = window.setTimeout(() => {
      to.abort(new DOMException(`apiFetch timeout after ${timeoutMs}ms`, 'AbortError'))
    }, timeoutMs)
    signal = userSignal ? mergeAbortSignals(userSignal, to.signal) : to.signal
  }

  const fetchInit: RequestInit = { ...rest, headers, signal, credentials: 'include' }

  const perform = async (): Promise<Response> => {
    try {
      return await fetch(url, fetchInit)
    } catch (e) {
      if (canRetryApiOnDevLoopback(input)) {
        const path = input.startsWith('/') ? input : `/${input}`
        return fetch(`${DEV_API_LOOPBACK_FALLBACK}${path}`, fetchInit)
      }
      throw e
    }
  }

  const p = perform()

  if (timeoutId != null) {
    return p.finally(() => {
      window.clearTimeout(timeoutId!)
    })
  }
  return p
}

const STATE_KEY = 'xcagi_client_mods_ui_off'

/** 设置页切换「原版模式」时使用：失败则抛错以便回滚 UI，不静默 reload */
export async function pushClientModsOffState(clientModsOff: boolean): Promise<void> {
  const res = await apiFetch('/api/state/client-mods-off', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_mods_off: clientModsOff }),
    timeoutMs: CLIENT_MODS_OFF_SYNC_TIMEOUT_MS,
  })
  if (!res.ok) {
    const err = new Error(`同步原版模式失败（HTTP ${res.status}）`)
    console.warn('[apiBase]', err.message)
    throw err
  }
}

export function syncClientModsStateToBackend(): Promise<void> {
  const isOff = localStorage.getItem(STATE_KEY) === '1'
  return apiFetch('/api/state/client-mods-off', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_mods_off: isOff }),
    timeoutMs: CLIENT_MODS_OFF_SYNC_TIMEOUT_MS,
  }).then(res => {
    if (!res.ok) {
      console.warn('[apiBase] 同步原版模式状态到后端失败:', res.status)
    }
  }).catch(err => {
    // 启动阶段后端 / 代理未就绪时易触发限时中止；此为后台同步，避免 console.warn 刷屏并经 clientDebugLog 镜像到服务端
    if (isApiFetchTimeoutError(err)) {
      if (import.meta.env.DEV) {
        console.debug(
          '[apiBase] 同步原版模式状态超时（后端或代理可能仍在启动）；可刷新页面或在设置中再次切换原版模式',
          err
        )
      }
      return
    }
    console.warn('[apiBase] 同步原版模式状态到后端失败:', err)
  })
}

export function readClientModsOffState(): boolean {
  return localStorage.getItem(STATE_KEY) === '1'
}
