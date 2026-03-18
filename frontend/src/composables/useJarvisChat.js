import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useJarvisChatStore } from '@/stores/jarvisChat'

export function useJarvisChat() {
  const store = useJarvisChatStore()
  
  const isListening = ref(false)
  const recognition = ref(null)
  
  const messages = computed(() => store.messages)
  const isRecording = computed(() => store.isRecording)
  const isPlaying = computed(() => store.isPlaying)
  const statusText = computed(() => store.statusText)
  const isCoreSpeaking = computed(() => store.isCoreSpeaking)
  
  const sendMessage = async (message) => {
    return await store.sendMessage(message)
  }
  
  const addMessage = (content, type = 'ai') => {
    store.addMessage(content, type)
  }
  
  const addTaskMessage = (content, taskData) => {
    store.addTaskMessage(content, taskData)
  }
  
  const startRecording = () => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      recognition.value = new SpeechRecognition()
      recognition.value.lang = 'zh-CN'
      recognition.value.continuous = false
      recognition.value.interimResults = false
      
      recognition.value.onstart = () => {
        isListening.value = true
        store.startRecording()
      }
      
      recognition.value.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        store.stopRecording()
        sendMessage(transcript)
      }
      
      recognition.value.onerror = (event) => {
        console.error('Speech recognition error:', event.error)
        store.stopRecording()
        isListening.value = false
      }
      
      recognition.value.onend = () => {
        isListening.value = false
        if (store.isRecording) {
          store.stopRecording()
        }
      }
      
      recognition.value.start()
    } else {
      console.warn('Speech recognition not supported')
    }
  }
  
  const stopRecording = () => {
    if (recognition.value) {
      recognition.value.stop()
      recognition.value = null
    }
    isListening.value = false
    store.stopRecording()
  }
  
  const queueVoice = (text) => {
    store.queueVoice(text)
  }
  
  const speak = (text) => {
    store.queueVoice(text)
  }
  
  const setStatus = (text) => {
    store.setStatus(text)
  }
  
  const setCoreSpeaking = (speaking) => {
    store.setCoreSpeaking(speaking)
  }
  
  const clearMessages = () => {
    store.clearMessages()
  }
  
  const clearVoiceQueue = () => {
    store.clearVoiceQueue()
  }
  
  onUnmounted(() => {
    stopRecording()
  })
  
  return {
    messages,
    isRecording,
    isPlaying,
    isListening,
    statusText,
    isCoreSpeaking,
    sendMessage,
    addMessage,
    addTaskMessage,
    startRecording,
    stopRecording,
    queueVoice,
    speak,
    setStatus,
    setCoreSpeaking,
    clearMessages,
    clearVoiceQueue
  }
}
