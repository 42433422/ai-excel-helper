<template>
  <div class="jarvis-chat-panel" :class="{ 'hidden': !showPanel }">
    <div class="chat-messages" ref="messagesRef">
      <div 
        v-for="message in messages" 
        :key="message.id"
        class="jarvis-message"
        :class="message.type"
      >
        <div v-if="message.type === 'ai'" class="message-header">
          <span class="message-role">JARVIS</span>
          <span class="message-time">{{ formatTime(message.timestamp) }}</span>
        </div>
        <div v-else-if="message.type === 'user'" class="message-header">
          <span class="message-role">用户</span>
          <span class="message-time">{{ formatTime(message.timestamp) }}</span>
        </div>
        <div v-else-if="message.type === 'task'" class="message-header">
          <span class="message-role">任务</span>
        </div>
        
        <div class="message-content">{{ message.content }}</div>
        
        <div v-if="message.type === 'task' && message.taskData" class="jarvis-task-card">
          <h4 class="task-title">{{ message.taskData.title || '任务确认' }}</h4>
          <p class="task-description">{{ message.taskData.description || message.content }}</p>
          <div class="task-actions">
            <button 
              v-if="message.taskData.confirmAction"
              class="task-button confirm"
              @click="handleTaskConfirm(message.taskData)"
            >
              确认
            </button>
            <button 
              v-if="message.taskData.ignoreAction"
              class="task-button ignore"
              @click="handleTaskIgnore(message.taskData)"
            >
              忽略
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="showInput" class="chat-input-container">
      <input
        ref="inputRef"
        v-model="inputText"
        type="text"
        class="chat-input"
        placeholder="输入消息..."
        @keyup.enter="handleSend"
        @focus="handleFocus"
        @blur="handleBlur"
      />
      <button 
        class="send-button"
        @click="handleSend"
        :disabled="!inputText.trim()"
      >
        发送
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  isWorkMode: {
    type: Boolean,
    default: false
  },
  showInput: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['messageSend', 'taskConfirm', 'taskIgnore'])

const messagesRef = ref(null)
const inputRef = ref(null)
const inputText = ref('')
const showPanel = ref(true)

const hasMessages = computed(() => props.messages.length > 0)

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) {
    return '刚刚'
  } else if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  } else if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  } else {
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
}

function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  
  emit('messageSend', text)
  inputText.value = ''
  
  nextTick(() => {
    scrollToBottom()
  })
}

function handleTaskConfirm(taskData) {
  emit('taskConfirm', taskData)
}

function handleTaskIgnore(taskData) {
  emit('taskIgnore', taskData)
}

function handleFocus() {
  showPanel.value = true
}

function handleBlur() {
  setTimeout(() => {
    if (!inputRef.value || document.activeElement !== inputRef.value) {
      showPanel.value = false
    }
  }, 200)
}

function scrollToBottom() {
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

watch(() => props.messages, () => {
  nextTick(() => {
    scrollToBottom()
  })
}, { deep: true })

onMounted(() => {
  scrollToBottom()
})

onUnmounted(() => {
  showPanel.value = false
})
</script>

<style scoped>
.jarvis-chat-panel {
  position: absolute;
  bottom: 140px;
  left: 50%;
  transform: translateX(-50%);
  width: 400px;
  max-height: 300px;
  background: rgba(10, 14, 39, 0.9);
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 12px;
  padding: 16px;
  overflow-y: auto;
  backdrop-filter: blur(10px);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.2);
}

.jarvis-chat-panel.hidden {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
  pointer-events: none;
}

.work-mode .jarvis-chat-panel {
  border-color: rgba(255, 0, 0, 0.5);
  box-shadow: 0 0 20px rgba(255, 0, 0, 0.3);
}

.chat-messages {
  max-height: 200px;
  overflow-y: auto;
  margin-bottom: 12px;
}

.jarvis-message {
  margin-bottom: 12px;
  padding: 12px;
  border-radius: 8px;
  animation: slideInUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.jarvis-message.ai {
  background: rgba(0, 255, 255, 0.1);
  border-left: 3px solid rgba(0, 255, 255, 0.5);
}

.jarvis-message.user {
  background: rgba(255, 255, 255, 0.1);
  border-right: 3px solid rgba(0, 255, 255, 0.5);
  text-align: right;
}

.jarvis-message.task {
  background: rgba(255, 204, 0, 0.1);
  border: 1px solid rgba(255, 204, 0, 0.3);
}

.work-mode .jarvis-message.ai {
  background: rgba(255, 0, 0, 0.1);
  border-left-color: rgba(255, 0, 0, 0.5);
}

.work-mode .jarvis-message.user {
  border-right-color: rgba(255, 0, 0, 0.5);
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 12px;
}

.message-role {
  font-weight: bold;
  color: rgba(0, 255, 255, 0.8);
}

.work-mode .message-role {
  color: rgba(255, 0, 0, 0.8);
}

.message-time {
  color: rgba(0, 255, 255, 0.6);
  font-size: 11px;
}

.message-content {
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.5;
  word-wrap: break-word;
}

.jarvis-task-card {
  background: rgba(255, 204, 0, 0.15);
  border: 1px solid rgba(255, 204, 0, 0.4);
  border-radius: 8px;
  padding: 12px;
  margin-top: 8px;
}

.task-title {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: bold;
  color: rgba(255, 204, 0, 0.9);
}

.task-description {
  margin: 0 0 12px 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.4;
}

.task-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.task-button {
  flex: 1;
  padding: 8px 16px;
  border: 1px solid rgba(255, 204, 0, 0.5);
  border-radius: 6px;
  background: rgba(255, 204, 0, 0.2);
  color: rgba(255, 255, 255, 0.9);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.task-button:hover {
  background: rgba(255, 204, 0, 0.3);
  transform: scale(1.05);
}

.task-button.confirm {
  border-color: rgba(0, 255, 0, 0.5);
}

.task-button.ignore {
  border-color: rgba(255, 0, 0, 0.5);
}

.chat-input-container {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 255, 255, 0.2);
}

.chat-input {
  flex: 1;
  padding: 10px 14px;
  background: rgba(0, 255, 255, 0.1);
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  outline: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.chat-input:focus {
  border-color: rgba(0, 255, 255, 0.6);
  background: rgba(0, 255, 255, 0.15);
  box-shadow: 0 0 10px rgba(0, 255, 255, 0.2);
}

.work-mode .chat-input {
  border-color: rgba(255, 0, 0, 0.3);
}

.work-mode .chat-input:focus {
  border-color: rgba(255, 0, 0, 0.6);
  box-shadow: 0 0 10px rgba(255, 0, 0, 0.2);
}

.send-button {
  padding: 10px 20px;
  background: rgba(0, 255, 255, 0.2);
  border: 1px solid rgba(0, 255, 255, 0.5);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.send-button:hover:not(:disabled) {
  background: rgba(0, 255, 255, 0.3);
  transform: scale(1.05);
}

.send-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.work-mode .send-button {
  background: rgba(255, 0, 0, 0.2);
  border-color: rgba(255, 0, 0, 0.5);
}

.work-mode .send-button:hover:not(:disabled) {
  background: rgba(255, 0, 0, 0.3);
}

@keyframes slideInUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}
</style>
