<template>
  <span class="drag-hold-progress" aria-hidden="true">
    <svg viewBox="0 0 36 36" class="drag-hold-progress-svg">
      <circle class="drag-hold-progress-track" cx="18" cy="18" r="14"></circle>
      <circle
        class="drag-hold-progress-indicator"
        cx="18"
        cy="18"
        r="14"
        :style="{
          strokeDasharray: `${circumference}px`,
          strokeDashoffset: `${dashoffset}px`,
        }"
      ></circle>
    </svg>
  </span>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  durationMs: {
    type: Number,
    default: 1000,
  },
})

const RADIUS = 14
const circumference = Math.PI * 2 * RADIUS
const progress = ref(0)
let rafId = 0
let startedAt = 0

const dashoffset = computed(() => circumference * (1 - progress.value / 100))

function tick() {
  const elapsed = Math.max(0, performance.now() - startedAt)
  progress.value = Math.min(100, (elapsed / props.durationMs) * 100)
  if (progress.value < 100) {
    rafId = window.requestAnimationFrame(tick)
  }
}

onMounted(() => {
  startedAt = performance.now()
  rafId = window.requestAnimationFrame(tick)
})

onBeforeUnmount(() => {
  if (rafId) window.cancelAnimationFrame(rafId)
})
</script>

<style scoped>
.drag-hold-progress {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.62);
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.25);
  pointer-events: none;
}

.drag-hold-progress-svg {
  width: 30px;
  height: 30px;
  transform: rotate(-90deg);
}

.drag-hold-progress-track,
.drag-hold-progress-indicator {
  fill: none;
  stroke-width: 4;
}

.drag-hold-progress-track {
  stroke: rgba(148, 163, 184, 0.35);
}

.drag-hold-progress-indicator {
  stroke: #38bdf8;
  stroke-linecap: round;
  transition: stroke-dashoffset 80ms linear;
}
</style>
