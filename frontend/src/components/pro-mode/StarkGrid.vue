<template>
  <div class="stark-grid" ref="gridRef">
    <div class="grid-lines">
      <div 
        v-for="i in 20" 
        :key="'h-' + i"
        class="grid-line horizontal"
        :style="{ top: (i * 5) + '%' }"
      ></div>
      <div 
        v-for="i in 20" 
        :key="'v-' + i"
        class="grid-line vertical"
        :style="{ left: (i * 5) + '%' }"
      ></div>
    </div>
    <div class="grid-dots">
      <div 
        v-for="(dot, index) in dots" 
        :key="index"
        class="grid-dot"
        :style="{ left: dot.x + '%', top: dot.y + '%' }"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  isWorkMode: {
    type: Boolean,
    default: false
  },
  dotCount: {
    type: Number,
    default: 50
  }
})

const gridRef = ref(null)
const dots = ref([])
const animationFrameId = ref(null)
const offset = ref(0)

function createDots() {
  dots.value = []
  
  for (let i = 0; i < props.dotCount; i++) {
    dots.value.push({
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: 1 + Math.random() * 2,
      opacity: 0.3 + Math.random() * 0.5
    })
  }
}

function animate() {
  offset.value = (offset.value + 0.5) % 50
  animationFrameId.value = requestAnimationFrame(animate)
}

onMounted(() => {
  createDots()
  animate()
})

onUnmounted(() => {
  if (animationFrameId.value) {
    cancelAnimationFrame(animationFrameId.value)
  }
})
</script>

<style scoped>
.stark-grid {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1000;
  pointer-events: none;
  perspective: 1000px;
  overflow: hidden;
  background: rgba(10, 14, 39, 0.3);
}

.grid-lines {
  position: absolute;
  width: 100%;
  height: 100%;
  transform: perspective(1000px) rotateX(60deg) translateY(var(--offset, 0px));
  transform-style: preserve-3d;
  animation: gridMove 10s linear infinite;
}

.grid-line {
  position: absolute;
  background: rgba(0, 255, 255, 0.2);
  transition: background 0.3s ease;
}

.grid-line.horizontal {
  width: 100%;
  height: 1px;
}

.grid-line.vertical {
  width: 1px;
  height: 100%;
}

.grid-dots {
  position: absolute;
  width: 100%;
  height: 100%;
  transform: perspective(1000px) rotateX(60deg) translateY(var(--offset, 0px));
  transform-style: preserve-3d;
  animation: gridMove 10s linear infinite;
}

.grid-dot {
  position: absolute;
  border-radius: 50%;
  background: rgba(0, 255, 255, 0.5);
  transition: background 0.3s ease;
  box-shadow: 0 0 5px rgba(0, 255, 255, 0.3);
}

.work-mode .grid-line {
  background: rgba(255, 0, 0, 0.2);
}

.work-mode .grid-dot {
  background: rgba(255, 0, 0, 0.5);
  box-shadow: 0 0 5px rgba(255, 0, 0, 0.3);
}

@keyframes gridMove {
  0% {
    --offset: 0px;
  }
  100% {
    --offset: -50px;
  }
}
</style>
