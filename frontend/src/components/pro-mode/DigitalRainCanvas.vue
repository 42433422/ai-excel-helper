<template>
  <canvas 
    ref="canvasRef"
    class="digital-rain"
    :class="{ 'work-mode': isWorkMode }"
    :style="{ display: isActive ? 'block' : 'none' }"
  ></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useDigitalRain } from '@/composables/useDigitalRain'

const props = defineProps({
  isWorkMode: {
    type: Boolean,
    default: false
  },
  isActive: {
    type: Boolean,
    default: false
  },
  autoStart: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['ready'])

const canvasRef = ref(null)
const { isRunning, start, stop, setWorkMode, resize, clear } = useDigitalRain(canvasRef, {
  chars: ['0', '1'],
  fontSize: 14
})

watch(() => props.isWorkMode, (newValue) => {
  setWorkMode(newValue)
})

watch(() => props.isActive, (newValue) => {
  if (newValue) {
    if (!isRunning.value) {
      start()
    }
  } else {
    if (isRunning.value) {
      stop()
    }
  }
})

onMounted(() => {
  window.addEventListener('resize', handleResize)
  
  if (props.autoStart && props.isActive) {
    start()
  }
  
  emit('ready')
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  stop()
})

function handleResize() {
  resize()
}
</script>

<style scoped>
.digital-rain {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
  pointer-events: none;
  opacity: 0.3;
}

.digital-rain.work-mode {
  opacity: 0.5;
}
</style>
