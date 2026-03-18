<template>
  <div 
    class="pro-core-reset-hotspot"
    @click="handleClick"
    :style="{ transform: `translate(-50%, -50%) scale(${scale})` }"
  >
    <div class="hotspot-inner">
      <div class="hotspot-icon">↻</div>
      <div class="hotspot-label">重置</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  scale: {
    type: Number,
    default: 1
  }
})

const emit = defineEmits(['click'])

const hotspotScale = computed(() => {
  const baseScale = 0.15
  return baseScale * props.scale
})

function handleClick() {
  emit('click')
}
</script>

<style scoped>
.pro-core-reset-hotspot {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 80px;
  height: 80px;
  cursor: pointer;
  pointer-events: auto;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.pro-core-reset-hotspot:hover {
  transform: translate(-50%, -50%) scale(1.2) !important;
}

.hotspot-inner {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0, 255, 255, 0.1);
  border-radius: 50%;
  border: 2px solid rgba(0, 255, 255, 0.3);
  backdrop-filter: blur(5px);
  box-shadow: 0 0 15px rgba(0, 255, 255, 0.2);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.hotspot-icon {
  font-size: 32px;
  color: rgba(0, 255, 255, 0.9);
  margin-bottom: 4px;
  font-weight: bold;
  text-shadow: 0 0 5px rgba(0, 255, 255, 0.5);
}

.hotspot-label {
  font-size: 12px;
  color: rgba(0, 255, 255, 0.8);
  font-weight: 500;
  text-shadow: 0 0 3px rgba(0, 255, 255, 0.3);
}
</style>
