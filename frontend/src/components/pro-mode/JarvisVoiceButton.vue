<template>
  <button 
    class="jarvis-voice-button"
    :class="{ 
      'recording': isRecording,
      'listening': isListening,
      'work-mode': isWorkMode
    }"
    @mousedown="handleMouseDown"
    @mouseup="handleMouseUp"
    @mouseleave="handleMouseLeave"
    @touchstart="handleTouchStart"
    @touchend="handleTouchEnd"
    @click="handleClick"
  >
    <svg viewBox="0 0 24 24" fill="none">
      <path 
        v-if="!isRecording"
        d="M12 14c1.66 0 3-1.34 3-3s0 6.69 0 12 2.5 0 17.31 0 19 2.5 0 21.31 0 22 6.69 0 22 13.5 0 12 15c-1.66 0-3 1.34-3 3-6.69 0-12-2.5 0-17.31-2.5-19-6.69-0-21.31-0-22-6.69-0-22-13.5-0-12-15zm-2 0h-1v-1h1v1zm1 0h1v1h1v-1h-1v1zm1 0h1v1h1v-1h-1v1z"
        fill="currentColor"
      />
      <path 
        v-else
        d="M12 14c1.66 0 3-1.34 3-3s0 6.69 0 12 2.5 0 17.31 0 19 2.5 0 21.31 0 22 6.69 0 22 13.5 0 12 15c-1.66 0-3 1.34-3 3-6.69 0-12-2.5 0-17.31-2.5-19-6.69-0-21.31-0-22-6.69-0-22-13.5-0-12-15zm-2 0h-1v-1h1v1zm1 0h1v1h1v-1h-1v1zm1 0h1v1h1v-1h-1v1z"
        fill="currentColor"
      />
      <circle 
        v-if="isRecording"
        cx="12"
        cy="12"
        r="3"
        fill="currentColor"
        class="recording-dot"
      />
    </svg>
  </button>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  isRecording: {
    type: Boolean,
    default: false
  },
  isListening: {
    type: Boolean,
    default: false
  },
  isWorkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click', 'longPress'])

const isLongPress = ref(false)
const longPressTimer = ref(null)
const longPressThreshold = 500

function handleMouseDown() {
  isLongPress.value = false
  longPressTimer.value = setTimeout(() => {
    isLongPress.value = true
    emit('longPress')
  }, longPressThreshold)
}

function handleMouseUp() {
  clearTimeout(longPressTimer.value)
  if (!isLongPress.value) {
    emit('click')
  }
  isLongPress.value = false
}

function handleMouseLeave() {
  clearTimeout(longPressTimer.value)
  isLongPress.value = false
}

function handleTouchStart(event) {
  event.preventDefault()
  isLongPress.value = false
  longPressTimer.value = setTimeout(() => {
    isLongPress.value = true
    emit('longPress')
  }, longPressThreshold)
}

function handleTouchEnd(event) {
  event.preventDefault()
  clearTimeout(longPressTimer.value)
  if (!isLongPress.value) {
    emit('click')
  }
  isLongPress.value = false
}

function handleClick() {
  if (!isLongPress.value) {
    emit('click')
  }
}

onUnmounted(() => {
  if (longPressTimer.value) {
    clearTimeout(longPressTimer.value)
  }
})
</script>

<style scoped>
.jarvis-voice-button {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(0, 255, 255, 0.2);
  border: 2px solid rgba(0, 255, 255, 0.5);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
  backdrop-filter: blur(10px);
}

.jarvis-voice-button:hover {
  background: rgba(0, 255, 255, 0.3);
  transform: translateX(-50%) scale(1.1);
  box-shadow: 0 0 30px rgba(0, 255, 255, 0.5);
}

.jarvis-voice-button.recording {
  background: rgba(255, 0, 0, 0.3);
  border-color: rgba(255, 0, 0, 0.5);
  box-shadow: 0 0 20px rgba(255, 0, 0, 0.5);
  animation: pulse 1s ease-in-out infinite;
}

.jarvis-voice-button.listening {
  background: rgba(0, 255, 255, 0.4);
  border-color: rgba(0, 255, 255, 0.8);
}

.work-mode .jarvis-voice-button {
  background: rgba(255, 0, 0, 0.2);
  border-color: rgba(255, 0, 0, 0.5);
  box-shadow: 0 0 20px rgba(255, 0, 0, 0.3);
}

.work-mode .jarvis-voice-button:hover {
  background: rgba(255, 0, 0, 0.3);
  box-shadow: 0 0 30px rgba(255, 0, 0, 0.5);
}

.work-mode .jarvis-voice-button.recording {
  background: rgba(255, 0, 0, 0.4);
  border-color: rgba(255, 0, 0, 0.8);
  box-shadow: 0 0 20px rgba(255, 0, 0, 0.5);
}

.jarvis-voice-button svg {
  width: 40px;
  height: 40px;
  fill: rgba(0, 255, 255, 0.8);
  transition: fill 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.work-mode .jarvis-voice-button svg {
  fill: rgba(255, 0, 0, 0.8);
}

.recording-dot {
  animation: recordingPulse 1s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 30px rgba(0, 255, 255, 0.5);
  }
}

.work-mode @keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 20px rgba(255, 0, 0, 0.3);
  }
  50% {
    box-shadow: 0 0 30px rgba(255, 0, 0, 0.5);
  }
}

@keyframes recordingPulse {
  0%, 100% {
    opacity: 1;
    r: 4;
  }
  50% {
    opacity: 0.5;
    r: 3;
  }
}
</style>
