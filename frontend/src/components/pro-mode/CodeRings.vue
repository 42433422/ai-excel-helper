<template>
  <div class="code-rings-container" :class="{ 'work-mode': isWorkMode }">
    <div 
      v-for="(ring, index) in rings" 
      :key="'code-ring-' + index"
      class="code-ring"
      :style="{ 
        transform: `rotateX(${ring.tilt}deg) rotateY(${index * 15}deg)`,
        animationDelay: `${index * 0.2}s`
      }"
    >
      <svg 
        :width="svgWidth" 
        :height="svgHeight" 
        :viewBox="`0 0 ${svgWidth} ${svgHeight}`"
        class="code-ring-svg"
      >
        <defs>
          <path 
            :id="'toolRingPath-' + index"
            :d="ringPathD(index)"
            fill="none"
          />
        </defs>
        <text class="tool-name-text">
          <textPath 
            :href="'#toolRingPath-' + index"
            startOffset="0%"
          >
            {{ ringToolText(index) }}
          </textPath>
        </text>
      </svg>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  tools: {
    type: Array,
    default: () => []
  },
  isWorkMode: {
    type: Boolean,
    default: false
  },
  frozenRing: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['toolSelect'])

const svgWidth = computed(() => 600)
const svgHeight = computed(() => 600)
const centerX = computed(() => svgWidth.value / 2)
const centerY = computed(() => svgHeight.value / 2)

const rings = computed(() => {
  return props.tools.map((tool, index) => ({
    tool,
    index,
    radius: 200 + index * 30,
    tilt: index * 5,
    isFrozen: props.frozenRing === index
  }))
})

function ringPathD(index) {
  const ring = rings.value[index]
  const r = ring.radius
  
  return `M ${centerX.value}, ${centerY.value - r} 
           A ${r} ${r} 0 1 1 ${centerX.value}, ${centerY.value + r}`
}

function ringToolText(index) {
  const ring = rings.value[index]
  const toolNames = ring.tool.map(t => t.name).join('    ')
  
  return toolNames + '    '
}

function handleRingClick(ring) {
  if (!ring.isFrozen) {
    emit('toolSelect', ring.tool)
  }
}
</script>

<style scoped>
.code-rings-container {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 600px;
  height: 600px;
  pointer-events: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.code-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  cursor: pointer;
  pointer-events: auto;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.code-ring:hover {
  transform: translate(-50%, -50%) scale(1.05);
}

.code-ring.frozen {
  opacity: 0.3;
  cursor: not-allowed;
}

.code-ring-svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.tool-name-text {
  font-family: 'Courier New', monospace;
  font-size: 14px;
  font-weight: bold;
  fill: rgba(0, 255, 255, 0.8);
  letter-spacing: 4px;
  text-shadow: 0 0 5px rgba(0, 255, 255, 0.5);
  transition: fill 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.work-mode .tool-name-text {
  fill: rgba(255, 0, 0, 0.8);
  text-shadow: 0 0 5px rgba(255, 0, 0, 0.5);
}

@keyframes codeCharFlicker {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}
</style>
