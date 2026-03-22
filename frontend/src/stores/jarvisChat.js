import { defineStore } from 'pinia'
import { useProModeStore } from './proMode'

export const useJarvisChatStore = defineStore('jarvisChat', {
  state: () => ({
    messages: [],
    isRecording: false,
    isPlaying: false,
    voiceQueue: [],
    currentTask: null,
    statusText: '准备就绪',
    isCoreSpeaking: false
  }),

  getters: {
    lastMessage: (state) => state.messages[state.messages.length - 1],
    hasPendingVoice: (state) => state.voiceQueue.length > 0
  },

  actions: {
    addMessage(content, type = 'ai') {
      this.messages.push({
        id: Date.now(),
        content,
        type,
        timestamp: new Date().toISOString()
      })
    },

    addTaskMessage(content, taskData) {
      this.messages.push({
        id: Date.now(),
        content,
        type: 'task',
        taskData,
        timestamp: new Date().toISOString()
      })
    },

    sendMessage(message) {
      const lowerMessage = message.toLowerCase()
      if (lowerMessage.includes('监控模式')) {
        const proModeStore = useProModeStore()
        proModeStore.enterMonitorMode()
        this.addMessage(message, 'user')
        this.addMessage('正在切换到监控模式...', 'ai')
        return Promise.resolve('正在切换到监控模式...')
      }

      this.addMessage(message, 'user')
      
      return new Promise((resolve) => {
        setTimeout(() => {
          const response = this.generateResponse(message)
          this.addMessage(response, 'ai')
          this.queueVoice(response)
          resolve(response)
        }, 1000)
      })
    },

    generateResponse(message) {
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
    },

    queueVoice(text) {
      this.voiceQueue.push(text)
      if (!this.isPlaying) {
        this.playNextVoice()
      }
    },

    playNextVoice() {
      if (this.voiceQueue.length === 0) {
        this.isPlaying = false
        this.isCoreSpeaking = false
        return
      }

      this.isPlaying = true
      this.isCoreSpeaking = true
      const text = this.voiceQueue.shift()
      
      this.speak(text)
    },

    speak(text) {
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text)
        utterance.lang = 'zh-CN'
        utterance.rate = 1
        utterance.pitch = 1
        
        utterance.onend = () => {
          setTimeout(() => {
            this.playNextVoice()
          }, 500)
        }
        
        utterance.onerror = () => {
          this.playNextVoice()
        }
        
        window.speechSynthesis.speak(utterance)
      } else {
        this.playNextVoice()
      }
    },

    startRecording() {
      this.isRecording = true
      this.statusText = '正在录音...'
    },

    stopRecording() {
      this.isRecording = false
      this.statusText = '处理中...'
      
      setTimeout(() => {
        this.statusText = '准备就绪'
      }, 1000)
    },

    setStatus(text) {
      this.statusText = text
    },

    setCoreSpeaking(speaking) {
      this.isCoreSpeaking = speaking
    },

    setCurrentTask(task) {
      this.currentTask = task
    },

    clearMessages() {
      this.messages = []
    },

    clearVoiceQueue() {
      this.voiceQueue = []
      this.isPlaying = false
      this.isCoreSpeaking = false
      
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel()
      }
    }
  }
})
