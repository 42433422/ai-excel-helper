import { ref, computed, watch, type Ref } from 'vue'
import chatApi from '../api/chat'

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
  const storageKey = computed(() => `xcagi_chat_messages_${String(sessionId.value || 'default')}`)

  function getDefaultWelcome(): ChatMessage[] {
    return [
      {
        role: 'ai',
        content: '您好！我是您的 AI 智能助手。<div style="margin-top: 8px;">我可以帮您：</div><ul style="margin: 8px 0 0 20px;"><li>查询产品信息和价格</li><li>管理出货单和订单</li><li>查看原材料库存</li><li>打印产品标签</li></ul><div style="margin-top: 8px;">请直接输入您的需求</div>',
        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      }
    ]
  }

  function readCachedMessages(): ChatMessage[] {
    try {
      const raw = localStorage.getItem(storageKey.value)
      if (!raw) return getDefaultWelcome()
      const parsed = JSON.parse(raw)
      if (!Array.isArray(parsed) || !parsed.length) return getDefaultWelcome()
      return parsed
    } catch (_e) {
      return getDefaultWelcome()
    }
  }

  function persistMessagesCache(): void {
    try {
      localStorage.setItem(storageKey.value, JSON.stringify(messages.value))
    } catch (_e) {
      // ignore storage errors
    }
  }

  const messages = ref<ChatMessage[]>(readCachedMessages())

  const lastMessage = computed(() => messages.value[messages.value.length - 1])

  function escapeHtml(text: string): string {
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML
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
    extras?: ChatMessageExtras
  ) {
    const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    const safeContent = escapeHtml(content).replace(/\n/g, '<br>')
    messages.value.push({
      role,
      content: safeContent,
      time,
      ...(extras || {})
    })
    persistMessagesCache()
  }

  async function saveMessage(role: 'user' | 'ai' | 'task', content: string): Promise<void> {
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
    extras?: ChatMessageExtras
  ): Promise<void> {
    addMessage(content, role, extras)
    await saveMessage(role, content)
  }

  function clearMessages() {
    messages.value = []
    persistMessagesCache()
  }

  function loadMessages(newMessages: ChatMessage[]) {
    messages.value = newMessages
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
      loadMessages(mapped)
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

  return {
    messages,
    lastMessage,
    addMessage,
    saveMessage,
    addAndSaveMessage,
    clearMessages,
    loadMessages,
    syncFromServer
  }
}
