export type SafeJsonResult<T = unknown> = {
  ok: boolean
  status: number
  data: T | null
  message: string
}

/**
 * fetch + JSON 解析，非 JSON 或解析失败时返回结构化错误（供生态页、小猫分析等复用）。
 */
export async function safeJsonRequest<T = unknown>(
  url: string,
  options: RequestInit = {}
): Promise<SafeJsonResult<T>> {
  const resp = await fetch(url, options)
  const contentType = String(resp.headers.get('content-type') || '').toLowerCase()
  const text = await resp.text()
  if (!contentType.includes('application/json')) {
    const trimmed = (text || '').trim().slice(0, 180)
    return {
      ok: false,
      status: resp.status,
      data: null,
      message: `接口未返回JSON（${resp.status}）。可能服务未重启或路由未生效。${trimmed ? ` 响应片段：${trimmed}` : ''}`
    }
  }
  try {
    const data = (text ? JSON.parse(text) : {}) as T
    if (!resp.ok) {
      const msg =
        typeof (data as { message?: string })?.message === 'string'
          ? (data as { message: string }).message
          : `请求失败（${resp.status}）`
      return {
        ok: false,
        status: resp.status,
        data,
        message: msg
      }
    }
    return { ok: true, status: resp.status, data, message: '' }
  } catch {
    return {
      ok: false,
      status: resp.status,
      data: null,
      message: `JSON解析失败（${resp.status}）`
    }
  }
}
