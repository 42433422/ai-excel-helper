<template>
  <div class="wire-rings-container" :class="{ 'breathing': isBreathing }">
    <div 
      v-for="i in 8" 
      :key="'ring-' + i"
      class="wire-ring"
      :class="'ring-' + i"
      :style="{ animationDuration: ringDuration(i) }"
    ></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  isBreathing: {
    type: Boolean,
    default: false
  },
  isWorkMode: {
    type: Boolean,
    default: false
  }
})

const ringDurations = computed(() => [
    '30s',
    '25s',
    '20s',
    '15s',
    '12s',
    '10s',
    '8s',
    '6s'
  ])

const ringDirections = computed(() => [
    'spin',
    'spinReverse',
    'spin',
    'spinReverse',
    'spin',
    'spinReverse',
    'spin'
  ])

function ringDuration(index) {
  return ringDurations.value[index]
}

function ringDirection(index) {
  return ringDirections.value[index]
}
</script>

<style scoped>
.wire-rings-container {
  position: absolute;
  width: 100%;
  height: 100%;
  pointer-events: none;
  top: 0;
  left: 0;
}

.wire-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 1px solid rgba(0, 255, 255, 0.5);
  box-shadow: 0 0 5px rgba(0, 255, 255, 0.3);
  transition: border-color 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.wire-ring.ring-0 {
  width: 220px;
  height: 220px;
  animation: spin 30s linear infinite;
}

.wire-ring.ring-1 {
  width: 240px;
  height: 240px;
  animation: spinReverse 25s linear infinite;
}

.wire-ring.ring-2 {
  width: 260px;
  height: 260px;
  animation: spin 20s linear infinite;
}

.wire-ring.ring-3 {
  width: 280px;
  height: 280px;
  animation: spinReverse 15s linear infinite;
}

.wire-ring.ring-4 {
  width: 300px;
  height: 300px;
  animation: spin 12s linear infinite;
}

.wire-ring.ring-5 {
  width: 320px;
  height: 320px;
  animation: spinReverse 10s linear infinite;
}

.wire-ring.ring-6 {
  width: 340px;
  height: 340px;
  animation: spin 8s linear infinite;
}

.wire-ring.ring-7 {
  width: 360px;
  height: 360px;
  animation: spinReverse 6s linear infinite;
}

.wire-rings-container.breathing .wire-ring {
  animation: ringPulse 2s ease-in-out infinite;
}

.work-mode .wire-ring {
  border-color: rgba(255, 0, 0, 0.5);
  box-shadow: 0 0 5px rgba(255, 0, 0, 0.3);
}

@keyframes spin {
  from {
    transform: translate(-50%, -50%) rotateZ(0deg);
  }
  to {
    transform: translate(-50%, -50%) rotateZ(360deg);
  }
}

@keyframes spinReverse {
  from {
    transform: translate(-50%, -50%) rotateZ(360deg);
  }
  to {
    transform: translate(-50%, -50%) rotateZ(0deg);
  }
}

@keyframes ringPulse {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.8;
  }
  50% {
    transform: translate(-50%, -50%) scale(1.05);
    opacity: 1;
  }
}
</style>
