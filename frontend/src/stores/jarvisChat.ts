import { defineStore } from 'pinia'
import { ref, type Ref } from 'vue'
import { useProModeStore } from './proMode'

interface ChatMessage {
  id: number;
  content: string;
  type: 'user' | 'ai' | 'task';
  timestamp: string;
  taskData?: any;
}

interface JarvisChatState {
  messages: ChatMessage[];
  isRecording: boolean;
  isPlaying: boolean;
  voiceQueue: string[];
  currentTask: any | null;
  statusText: string;
  isCoreSpeaking: boolean;
}

export const useJarvisChatStore = defineStore('jarvisChat', () => {
  const messages = ref<ChatMessage[]>([]) as Ref<ChatMessage[]>
  const isRecording = ref(false)
  const isPlaying = ref(false)
  const voiceQueue = ref<string[]>([])
  const currentTask = ref<any | null>(null)
  const statusText = ref('准备就绪')
  const isCoreSpeaking = ref(false)

  const lastMessage = ref<ChatMessage | undefined>(undefined)
  const hasPendingVoice = ref(false)

  function updateLastMessage() {
    lastMessage.value = messages.value[messages.value.length - 1]
    hasPendingVoice.value = voiceQueue.value.length > 0
  }

  function addMessage(content: string, type: 'user' | 'ai' | 'task' = 'ai') {
    messages.value.push({
      id: Date.now(),
      content,
      type,
      timestamp: new Date().toISOString()
    })
    updateLastMessage()
  }

  function addTaskMessage(content: string, taskData: any) {
    messages.value.push({
      id: Date.now(),
      content,
      type: 'task',
      taskData,
      timestamp: new Date().toISOString()
    })
    updateLastMessage()
  }

  function syncLegacyMonitorMode(): boolean {
    const monitorToggle = (window as any).setMonitorModeFromChat
    if (typeof monitorToggle !== 'function') return false

    // Keep legacy runtime as source of truth for overlay mode classes.
    monitorToggle(true)
    if (typeof (window as any).refreshWorkModeMonitorList === 'function') {
      ;(window as any).refreshWorkModeMonitorList()
    }
    return true
  }

  function syncLegacyWorkMode(): boolean {
    const workToggle = (window as any).setWorkModeFromChat
    if (typeof workToggle !== 'function') return false

    // Keep legacy runtime as source of truth for overlay mode classes.
    workToggle(true)
    if (typeof (window as any).refreshWorkModeMonitorList === 'function') {
      ;(window as any).refreshWorkModeMonitorList()
    }
    return true
  }

  async function sendMessage(message: string): Promise<string> {
    const lowerMessage = message.toLowerCase()
    if (lowerMessage.includes('监控模式')) {
      const proModeStore = useProModeStore()
      const switchedByLegacy = syncLegacyMonitorMode()
      if (!switchedByLegacy) {
        proModeStore.enterMonitorMode()
      } else {
        // Mirror store state so Vue-only consumers remain consistent.
        proModeStore.enterMonitorMode()
        proModeStore.exitWorkMode()
      }
      addMessage(message, 'user')
      addMessage('正在切换到监控模式...', 'ai')
      return '正在切换到监控模式...'
    }

    if (lowerMessage.includes('工作模式') || lowerMessage.includes('work mode')) {
      const proModeStore = useProModeStore()
      const switchedByLegacy = syncLegacyWorkMode()
      if (!switchedByLegacy) {
        proModeStore.enterWorkMode()
      } else {
        // Mirror store state so Vue-only consumers remain consistent.
        proModeStore.enterWorkMode()
        proModeStore.exitMonitorMode()
      }
      addMessage(message, 'user')
      addMessage('正在切换到工作模式...', 'ai')
      return '正在切换到工作模式...'
    }

    addMessage(message, 'user')
    
    return new Promise((resolve) => {
      setTimeout(() => {
        const response = generateResponse(message)
        addMessage(response, 'ai')
        queueVoice(response)
        resolve(response)
      }, 1000)
    })
  }

  function generateResponse(message: string): string {
    const lowerMessage = message.toLowerCase()
    
    if (lowerMessage.includes('产品') || lowerMessage.includes('product')) {
      return '正在为您查询产品信息...'
    } else if (lowerMessage.includes('客户') || lowerMessage.includes('customer')) {
      return '正在为您查询客户信息...'
    } else if (lowerMessage.includes('订单') || lowerMessage.includes('order')) {
      return '正在为您查询订单信息...'
    } else if (lowerMessage.includes('工作模式') || lowerMessage.includes('work mode')) {
      return '正在进入工作模式...'
    } else {
      return '我已收到您的消息，正在处理中...'
    }
  }

  function queueVoice(text: string) {
    voiceQueue.value.push(text)
    if (!isPlaying.value) {
      playNextVoice()
    }
  }

  function playNextVoice() {
    if (voiceQueue.value.length === 0) {
      isPlaying.value = false
      isCoreSpeaking.value = false
      return
    }

    isPlaying.value = true
    isCoreSpeaking.value = true
    const text = voiceQueue.value.shift()
    
    if (text) {
      speak(text)
    }
  }

  function speak(text: string) {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = 'zh-CN'
      utterance.rate = 1
      utterance.pitch = 1
      
      utterance.onend = () => {
        setTimeout(() => {
          playNextVoice()
        }, 500)
      }
      
      utterance.onerror = () => {
        playNextVoice()
      }
      
      window.speechSynthesis.speak(utterance)
    } else {
      playNextVoice()
    }
  }

  function startRecording() {
    isRecording.value = true
    statusText.value = '正在录音...'
  }

  function stopRecording() {
    isRecording.value = false
    statusText.value = '处理中...'
    
    setTimeout(() => {
      statusText.value = '准备就绪'
    }, 1000)
  }

  function setStatus(text: string) {
    statusText.value = text
  }

  function setCoreSpeaking(speaking: boolean) {
    isCoreSpeaking.value = speaking
  }

  function setCurrentTask(task: any) {
    currentTask.value = task
  }

  function clearMessages() {
    messages.value = []
    updateLastMessage()
  }

  function clearVoiceQueue() {
    voiceQueue.value = []
    isPlaying.value = false
    isCoreSpeaking.value = false
    
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
  }

  return {
    messages,
    isRecording,
    isPlaying,
    voiceQueue,
    currentTask,
    statusText,
    isCoreSpeaking,
    lastMessage,
    hasPendingVoice,
    addMessage,
    addTaskMessage,
    sendMessage,
    generateResponse,
    queueVoice,
    playNextVoice,
    speak,
    startRecording,
    stopRecording,
    setStatus,
    setCoreSpeaking,
    setCurrentTask,
    clearMessages,
    clearVoiceQueue
  }
})
