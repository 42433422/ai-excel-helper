import { resolvePlannerChatStreamPath } from '@/utils/plannerChatPaths'

export type PlannerSseEvent =
  | { type: 'token'; text: string }
  | { type: 'done'; result?: unknown }
  | { type: 'error'; message?: string; status_code?: number }
  | { type: 'requires_token'; token_name?: string; token_description?: string }

function parseSseDataLine(line: string): PlannerSseEvent | null {
  const s = line.trim()
  if (!s.startsWith('data:')) return null
  const jsonStr = s.slice(5).trim()
  if (!jsonStr) return null
  try {
    return JSON.parse(jsonStr) as PlannerSseEvent
  } catch {
    return null
  }
}

/** 读取 ``fetch`` 得到的 SSE（``text/event-stream``）响应体并逐条回调事件 */
export async function readPlannerSseResponse(
  response: Response,
  onEvent: (ev: PlannerSseEvent) => void
): Promise<void> {
  if (!response.body) {
    throw new Error('响应体不可读（可能被代理缓冲或未返回流）')
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''
      for (const part of parts) {
        for (const line of part.split('\n')) {
          const ev = parseSseDataLine(line)
          if (ev) onEvent(ev)
        }
      }
    }
    if (buffer.trim()) {
      for (const line of buffer.split('\n')) {
        const ev = parseSseDataLine(line)
        if (ev) onEvent(ev)
      }
    }
  } finally {
    reader.releaseLock()
  }
}

export function resolveChatStreamPath(): string {
  return resolvePlannerChatStreamPath()
}

export function isChatStreamEnabled(): boolean {
  const v = String(import.meta.env.VITE_CHAT_STREAM ?? '').trim().toLowerCase()
  if (v === '0' || v === 'false' || v === 'off' || v === 'no') return false
  return true
}
