<template>
  <div class="falling-text-container" ref="containerRef">
    <div 
      v-for="(char, index) in chars" 
      :key="index"
      class="falling-char"
      :style="charStyle(char)"
    >
      {{ char.char }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  isEntering: {
    type: Boolean,
    default: false
  },
  isExiting: {
    type: Boolean,
    default: false
  },
  isWorkMode: {
    type: Boolean,
    default: false
  },
  charCount: {
    type: Number,
    default: 30
  }
})

const containerRef = ref(null)
const chars = ref([])
const animationFrameId = ref(null)

const technicalChars = [
  '0', '1', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
  'α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ', 'λ', 'μ', 'ν', 'ξ', 'π', 'ρ', 'σ', 'τ', 'υ', 'φ', 'χ', 'ψ', 'ω'
]

function createChars() {
  chars.value = []
  
  for (let i = 0; i < props.charCount; i++) {
    const char = technicalChars[Math.floor(Math.random() * technicalChars.length)]
    const x = Math.random() * 100
    const y = Math.random() * 100
    const speed = 2 + Math.random() * 3
    const fontSize = 12 + Math.random() * 4
    const delay = Math.random() * 0.5
    const opacity = 0.6 + Math.random() * 0.4
    
    chars.value.push({
      char,
      x,
      y,
      speed,
      fontSize,
      delay,
      opacity,
      currentY: y
    })
  }
}

function charStyle(char) {
  return {
    left: `${char.x}%`,
    top: `${char.currentY}%`,
    fontSize: `${char.fontSize}px`,
    fontFamily: 'monospace',
    color: props.isWorkMode ? '#ff0000' : '#00ffff',
    opacity: char.opacity,
    textShadow: props.isWorkMode ? '0 0 5px #ff0000' : '0 0 5px #00ffff',
    animationDelay: `${char.delay}s`,
    animationDuration: `${3 + Math.random() * 2}s`
  }
}

function animate() {
  if (props.isEntering) {
    chars.value.forEach(char => {
      char.currentY = char.y + (100 - char.y) * Math.min(1, (performance.now() - startTime) / 1000)
    })
  } else if (props.isExiting) {
    chars.value.forEach(char => {
      char.currentY = char.y + (200 - char.y) * Math.min(1, (performance.now() - startTime) / 1000)
    })
  }
  
  animationFrameId.value = requestAnimationFrame(animate)
}

let startTime = 0

watch(() => props.isEntering, (newValue) => {
  if (newValue) {
    createChars()
    startTime = performance.now()
    animate()
  }
})

watch(() => props.isExiting, (newValue) => {
  if (newValue) {
    startTime = performance.now()
    animate()
  }
})

onMounted(() => {
  if (props.isEntering) {
    createChars()
    startTime = performance.now()
    animate()
  }
})

onUnmounted(() => {
  if (animationFrameId.value) {
    cancelAnimationFrame(animationFrameId.value)
  }
})
</script>

<style scoped>
.falling-text-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1000;
  overflow: hidden;
}

.falling-char {
  position: absolute;
  font-family: 'Courier New', monospace;
  font-weight: bold;
  white-space: nowrap;
  user-select: none;
  animation: charFallDown linear forwards;
}

@keyframes charFallDown {
  0% {
    transform: translateY(-100vh);
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  100% {
    transform: translateY(100vh);
    opacity: 0;
  }
}
</style>
