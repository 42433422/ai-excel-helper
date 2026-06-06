/**
 * 与 FastAPI ``CSRFMiddleware`` 双提交 Cookie 对齐：变更方法需带 ``X-CSRF-Token``，
 * 且与可读 Cookie ``csrf_token`` 一致（非 HttpOnly，供 JS 读取）。
 */
export function readCsrfTokenFromCookie(): string | null {
  if (typeof document === 'undefined') return null
  for (const part of document.cookie.split(';')) {
    const s = part.trim()
    if (s.startsWith('csrf_token=')) {
      try {
        return decodeURIComponent(s.slice('csrf_token='.length))
      } catch {
        return s.slice('csrf_token='.length)
      }
    }
  }
  return null
}

/** 非安全方法且未显式带 Bearer 时，应附加 CSRF 头（与后端 ``authorization`` 豁免分支一致）。 */
export function shouldAttachCsrfHeader(
  method: string | undefined,
  headers: Record<string, string | undefined>,
): boolean {
  const m = (method || 'GET').toUpperCase()
  if (m === 'GET' || m === 'HEAD' || m === 'OPTIONS') return false
  for (const k of Object.keys(headers)) {
    if (k.toLowerCase() === 'x-csrf-token' && String(headers[k] || '').trim()) return false
    if (k.toLowerCase() === 'authorization' && String(headers[k] || '').toLowerCase().startsWith('bearer ')) {
      return false
    }
  }
  return true
}
