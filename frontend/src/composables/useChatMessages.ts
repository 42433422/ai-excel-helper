import { ref, computed, watch, type Ref } from 'vue'
import { storeToRefs } from 'pinia'
import chatApi from '../api/chat'
import { speakText, stopSpeaking, cleanTextForSpeech } from '../utils/tts'
import { useModsStore } from '@/stores/mods'
import { useIndustryStore } from '@/stores/industry'
import { getIndustryWelcomeMarkdown } from '@/constants/industryPresets'
import {
  buildChatMessagesKey,
  buildChatSessionMetaKey,
} from '@/utils/chatStorageKeys'

const WELCOME_MESSAGE_PREFIX = '您好！我是您的'

// TTS 语音队列：按顺序播放，避免多条并发抢扬声器
const voiceQueue: string[] = []
let isPlayingVoice = false

async function playNextVoice() {
  if (voiceQueue.length === 0) {
    isPlayingVoice = false
    return
  }

  isPlayingVoice = true
  const text = voiceQueue.shift()
  if (!text) { playNextVoice(); return }

  try {
    await Promise.race([
      speakText(text),
      new Promise((_, reject) => setTimeout(() => reject(new Error('TTS timeout')), 8000))
    ])
  } catch {
    // swallow，继续播下一条
  }
  // 短间隔让句子之间有呼吸
  setTimeout(() => playNextVoice(), 350)
}

export function queueVoice(text: string) {
  // 去除 HTML 标签和标点符号，只保留纯文本用于语音
  const plainText = cleanTextForSpeech(
    String(text || '')
      .replace(/<br\s*\/?>/gi, ' ')
      .replace(/<[^>]*>/g, ' ')
      .replace(/&nbsp;/gi, ' ')
      .replace(/\s+/g, ' ')
      .trim()
  )

  if (!plainText) return

  voiceQueue.push(plainText)
  if (!isPlayingVoice) {
    void playNextVoice()
  }
}

export function clearVoiceQueue() {
  voiceQueue.length = 0
  isPlayingVoice = false
  stopSpeaking()
}

export interface ChatMessage {
  role: 'user' | 'ai' | 'task'
  content: string
  time: string
  thinkingSteps?: string
  todoSteps?: string[]
  workflowAction?: string
  nodeResults?: Array<{ node_id: string; success: boolean; tool_id: string; action: string; error?: string }>
  contextSummary?: string
  /** 发货单文档下载链接（与右侧任务卡一致，便于在对话内直接下载） */
  shipmentDownloadUrl?: string
}

export type ChatMessageExtras = Partial<Pick<ChatMessage, 'shipmentDownloadUrl'>>

export function useChatMessages(sessionId: Ref<string>) {
  const modsStore = useModsStore()
  const industryStore = useIndustryStore()
  const { activeModId } = storeToRefs(modsStore)
  const storageKey = computed(() =>
    buildChatMessagesKey(String(sessionId.value || 'default'), String(activeModId.value || ''))
  )
  const sessionMetaKey = computed(() =>
    buildChatSessionMetaKey(String(sessionId.value || 'default'), String(activeModId.value || ''))
  )

  function getDefaultWelcome(): ChatMessage[] {
    const industryId = String(industryStore.currentIndustryId || '').trim() || '通用'
    return [
      {
        role: 'ai',
        content: getIndustryWelcomeMarkdown(industryId),
        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      },
    ]
  }

  function readCachedMessages(): ChatMessage[] {
    try {
      const raw = localStorage.getItem(storageKey.value)
      if (!raw) return getDefaultWelcome()
      const parsed = JSON.parse(raw)
      if (!Array.isArray(parsed) || !parsed.length) return getDefaultWelcome()
      const sanitized = sanitizeMessagesList(parsed)
      if (!sanitized.length) return getDefaultWelcome()
      if (isWelcomeMessage(sanitized[0]) && /<[a-z]+[\s>]/i.test(sanitized[0].content)) {
        sanitized[0] = getDefaultWelcome()[0]
      }
      return sanitized
    } catch (_e) {
      return getDefaultWelcome()
    }
  }

  function persistMessagesCache(): void {
    try {
      const sanitized = sanitizeMessagesList(messages.value)
      if (sanitized.length !== messages.value.length) {
        messages.value = sanitized
      }
      localStorage.setItem(storageKey.value, JSON.stringify(messages.value))
      persistSessionMeta(messages.value)
    } catch (_e) {
      // ignore storage errors
    }
  }

  const messages = ref<ChatMessage[]>(readCachedMessages())
  const bootSanitized = sanitizeMessagesList(messages.value)
  if (bootSanitized.length !== messages.value.length) {
    messages.value = bootSanitized.length ? bootSanitized : getDefaultWelcome()
    try {
      localStorage.setItem(storageKey.value, JSON.stringify(messages.value))
      persistSessionMeta(messages.value)
    } catch {
      // ignore storage errors
    }
  }

  const lastMessage = computed(() => messages.value[messages.value.length - 1])

  function escapeHtml(text: string): string {
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML
  }

  function hasMeaningfulContent(raw: unknown): boolean {
    const html = String(raw || '')
    if (!html) return false
    const text = html
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<[^>]*>/g, '')
      .replace(/&nbsp;/gi, ' ')
      .trim()
    return text.length > 0
  }

  function toPlainText(raw: unknown): string {
    return String(raw || '')
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<[^>]*>/g, '')
      .replace(/&nbsp;/gi, ' ')
      .trim()
  }

  function isWelcomeMessage(msg: Pick<ChatMessage, 'role' | 'content'>): boolean {
    if (msg.role !== 'ai') return false
    return toPlainText(msg.content).startsWith(WELCOME_MESSAGE_PREFIX)
  }

  function deriveSessionTitle(list: ChatMessage[]): string {
    const meaningful = list.filter((msg) => hasMeaningfulContent(msg.content) && !isWelcomeMessage(msg))
    const preferred = meaningful.find((msg) => msg.role === 'user') || meaningful[0]
    const plain = toPlainText(preferred?.content || '').replace(/\s+/g, ' ').trim()
    if (!plain) return '新会话'
    return plain.length > 32 ? `${plain.slice(0, 32)}...` : plain
  }

  function persistSessionMeta(list: ChatMessage[]): void {
    try {
      const meaningful = list.filter((msg) => hasMeaningfulContent(msg.content) && !isWelcomeMessage(msg))
      if (!meaningful.length) {
        localStorage.removeItem(sessionMetaKey.value)
        return
      }
      localStorage.setItem(
        sessionMetaKey.value,
        JSON.stringify({
          session_id: String(sessionId.value || 'default'),
          title: deriveSessionTitle(list),
          message_count: meaningful.length,
          updated_at: new Date().toISOString()
        })
      )
    } catch {
      // ignore storage errors
    }
  }

  function sanitizeMessagesList(rawList: unknown[]): ChatMessage[] {
    return (Array.isArray(rawList) ? rawList : [])
      .map((msg: any) => {
        const role = (msg?.role === 'user' || msg?.role === 'task') ? msg.role : 'ai'
        const content = String(msg?.content || '')
        if (!hasMeaningfulContent(content)) return null
        return {
          role,
          content,
          time: String(msg?.time || '').trim()
            || new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
        } as ChatMessage
      })
      .filter((m): m is ChatMessage => !!m)
  }

  function normalizeServerContentToHtml(raw: unknown): string {
    const text = String(raw || '')
    // 如果已经是 HTML（常见：<br>/<div>/<ul>），按原样展示，避免二次转义
    if (/<[a-z][\s\S]*>/i.test(text)) return text
    return escapeHtml(text).replace(/\n/g, '<br>')
  }

  function addMessage(
    content: string,
    role: 'user' | 'ai' | 'task' = 'ai',
    extras?: ChatMessageExtras,
    options?: { speak?: boolean }
  ) {
    if (!hasMeaningfulContent(content)) return
    const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    const safeContent = escapeHtml(content).replace(/\n/g, '<br>')
    messages.value.push({
      role,
      content: safeContent,
      time,
      ...(extras || {})
    })
    persistMessagesCache()

    // TTS 语音播报（仅 AI 消息且非欢迎消息）
    if (options?.speak && role === 'ai' && !isWelcomeMessage({ role, content: safeContent })) {
      queueVoice(safeContent)
    }
  }

  async function saveMessage(role: 'user' | 'ai' | 'task', content: string): Promise<void> {
    if (!hasMeaningfulContent(content)) return
    try {
      await chatApi.saveMessage({
        session_id: sessionId.value,
        user_id: 'default',
        role,
        content
      })
    } catch (e) {
      console.error('保存消息失败:', e)
    }
  }

  async function addAndSaveMessage(
    content: string,
    role: 'user' | 'ai' | 'task' = 'ai',
    extras?: ChatMessageExtras,
    options?: { speak?: boolean }
  ): Promise<void> {
    if (!hasMeaningfulContent(content)) return
    addMessage(content, role, extras, options)
    await saveMessage(role, content)
  }

  /** 流式回复：先占位一条 AI 消息，返回其在 messages 中的下标 */
  function pushStreamingAiShell(): number {
    const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    messages.value.push({
      role: 'ai',
      content: '...',
      time
    })
    persistMessagesCache()
    return messages.value.length - 1
  }

  /** 将纯文本安全转为气泡 HTML 并写入指定下标（用于 SSE token 追加） */
  function applyPlainTextToMessageIndex(index: number, plain: string) {
    const safe = escapeHtml(plain).replace(/\n/g, '<br>')
    const row = messages.value[index]
    if (!row) return
    row.content = safe || '...'
    persistMessagesCache()
  }

  function clearMessages() {
    messages.value = []
    persistMessagesCache()
  }

  function loadMessages(newMessages: ChatMessage[]) {
    messages.value = sanitizeMessagesList(newMessages)
    persistMessagesCache()
  }

  async function syncFromServer(): Promise<boolean> {
    try {
      const sid = String(sessionId.value || '').trim()
      if (!sid) return false
      const data = await chatApi.getConversation(sid)
      const serverMessages = Array.isArray((data as any)?.messages) ? (data as any).messages : []
      if (!serverMessages.length) return false

      const mapped: ChatMessage[] = serverMessages.map((msg: any) => ({
        role: (msg?.role === 'user' || msg?.role === 'task') ? msg.role : 'ai',
        content: normalizeServerContentToHtml(msg?.content),
        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      }))
      const sanitized = sanitizeMessagesList(mapped)
      if (!sanitized.length) return false
      loadMessages(sanitized)
      return true
    } catch (_e) {
      return false
    }
  }

  watch(
    () => sessionId.value,
    () => {
      messages.value = readCachedMessages()
    }
  )

  // 切换当前扩展（Mod）时：同一会话 ID 下不同 Mod 的消息缓存相互隔离，
  // 切换后应重新读取当前 Mod 对应的本地消息（若无缓存则展示欢迎语）。
  watch(
    () => String(activeModId.value || ''),
    () => {
      messages.value = readCachedMessages()
    }
  )

  return {
    messages,
    lastMessage,
    addMessage,
    saveMessage,
    addAndSaveMessage,
    pushStreamingAiShell,
    applyPlainTextToMessageIndex,
    clearMessages,
    loadMessages,
    syncFromServer,
    queueVoice,
    clearVoiceQueue
  }
}
