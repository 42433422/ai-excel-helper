<template>
  <div class="jarvis-status">
    <div 
      class="status-dot"
      :class="{ 
        'animating': isAnimating,
        'recording': isRecording,
        'speaking': isSpeaking
      }"
    ></div>
    <span class="status-text">{{ statusText }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  statusText: {
    type: String,
    default: '准备就绪'
  },
  isRecording: {
    type: Boolean,
    default: false
  },
  isSpeaking: {
    type: Boolean,
    default: false
  },
  isAnimating: {
    type: Boolean,
    default: false
  },
  isWorkMode: {
    type: Boolean,
    default: false
  }
})

const isAnimating = computed(() => props.isRecording || props.isSpeaking || props.isAnimating)
</script>

<style scoped>
.jarvis-status {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(10, 14, 39, 0.9);
  border: 1px solid rgba(0, 255, 255, 0.3);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.2);
}

.work-mode .jarvis-status {
  border-color: rgba(255, 0, 0, 0.5);
  box-shadow: 0 0 20px rgba(255, 0, 0, 0.3);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: rgba(0, 255, 255, 0.8);
  box-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.status-dot.animating {
  animation: statusBlink 1s ease-in-out infinite;
}

.status-dot.recording {
  background: rgba(255, 0, 0, 0.8);
  box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
  animation: recordingPulse 1s ease-in-out infinite;
}

.status-dot.speaking {
  animation: speakingPulse 1s ease-in-out infinite;
}

.work-mode .status-dot {
  background: rgba(255, 0, 0, 0.8);
  box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
}

.work-mode .status-dot.recording {
  background: rgba(255, 0, 0, 0.8);
  box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
}

.work-mode .status-dot.speaking {
  background: rgba(255, 0, 0, 0.8);
  box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
}

.status-text {
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  white-space: nowrap;
  transition: color 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.work-mode .status-text {
  color: rgba(255, 255, 255, 0.9);
}

@keyframes statusBlink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

@keyframes recordingPulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.2);
    opacity: 0.8;
  }
}

@keyframes speakingPulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.8;
  }
}
</style>
