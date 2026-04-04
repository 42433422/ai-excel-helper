/**
 * Mod 等 API 的基址。
 * - 未设置 VITE_API_BASE：用相对路径（与页面同源）。Vite dev（如 :5001）下走 vite.config 里 /api 代理，与主站一致。
 * - 需要直连后端时设 VITE_API_BASE，例如 http://127.0.0.1:5000
 */
export function getApiBase(): string {
  const raw = import.meta.env.VITE_API_BASE as string | undefined
  if (typeof raw === 'string' && raw.trim()) {
    return raw.trim().replace(/\/$/, '')
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

export function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  const url = input.startsWith('http') ? input : apiUrl(input)
  const modsOffHeaders = getClientModsUiOffHeader()
  const headers = {
    ...modsOffHeaders,
    ...init?.headers,
  }
  return fetch(url, { ...init, headers })
}

const STATE_KEY = 'xcagi_client_mods_ui_off'

export function syncClientModsStateToBackend(): Promise<void> {
  const isOff = localStorage.getItem(STATE_KEY) === '1'
  return apiFetch('/api/state/client-mods-off', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_mods_off: isOff }),
  }).then(res => {
    if (!res.ok) {
      console.warn('[apiBase] 同步原版模式状态到后端失败:', res.status)
    }
  }).catch(err => {
    console.warn('[apiBase] 同步原版模式状态到后端失败:', err)
  })
}

export function readClientModsOffState(): boolean {
  return localStorage.getItem(STATE_KEY) === '1'
}
