<template>
  <div class="energy-particles-container">
    <div 
      v-for="(particle, index) in particles" 
      :key="'particle-' + index"
      class="energy-particle"
      :class="{ 
        'exploding': isExploding,
        'imploding': isImploding
      }"
      :style="particleStyle(particle, index)"
    ></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  isExploding: {
    type: Boolean,
    default: false
  },
  isImploding: {
    type: Boolean,
    default: false
  },
  isWorkMode: {
    type: Boolean,
    default: false
  },
  particleCount: {
    type: Number,
    default: 40
  }
})

const particles = ref([])
const animationFrameId = ref(null)

function createParticles() {
  particles.value = []
  
  for (let i = 0; i < props.particleCount; i++) {
    const angle = (i / props.particleCount) * Math.PI * 2
    const distance = 150 + Math.random() * 250
    const size = 3 + Math.random() * 3
    const opacity = 0.8 + Math.random() * 0.2
    const delay = Math.random() * 0.3
    
    particles.value.push({
      angle,
      distance,
      size,
      opacity,
      delay,
      currentX: 0,
      currentY: 0,
      currentOpacity: 0,
      currentScale: 1
    })
  }
}

function particleStyle(particle, index) {
  const x = particle.currentX
  const y = particle.currentY
  const scale = particle.currentScale
  const opacity = particle.currentOpacity
  const r = props.isWorkMode ? 255 : 0
  const g = props.isWorkMode ? 0 : 255
  const b = props.isWorkMode ? 0 : 255
  
  return {
    left: `calc(50% + ${x}px)`,
    top: `calc(50% + ${y}px)`,
    width: `${particle.size * scale}px`,
    height: `${particle.size * scale}px`,
    borderRadius: '50%',
    background: `rgba(${r}, ${g}, ${b}, ${opacity})`,
    boxShadow: `0 0 10px rgba(${r}, ${g}, ${b}, ${opacity * 0.5})`,
    animationDelay: `${particle.delay}s`,
    animationDuration: '0.5s'
  }
}

function animate() {
  if (props.isExploding) {
    particles.value.forEach((particle, index) => {
      const targetX = Math.cos(particle.angle) * particle.distance
      const targetY = Math.sin(particle.angle) * particle.distance
      
      particle.currentX += (targetX - particle.currentX) * 0.1
      particle.currentY += (targetY - particle.currentY) * 0.1
      particle.currentOpacity -= 0.02
      particle.currentScale -= 0.02
    })
  } else if (props.isImploding) {
    particles.value.forEach((particle, index) => {
      particle.currentX += (0 - particle.currentX) * 0.1
      particle.currentY += (0 - particle.currentY) * 0.1
      particle.currentOpacity -= 0.02
      particle.currentScale -= 0.02
    })
  }
  
  particles.value = particles.value.filter(p => p.currentOpacity > 0)
  
  if (particles.value.length > 0) {
    if (animationFrameId.value) {
      cancelAnimationFrame(animationFrameId.value)
      animationFrameId.value = null
    }
    return
  }
  
  animationFrameId.value = requestAnimationFrame(animate)
}

watch(() => props.isExploding, (newValue) => {
  if (newValue) {
    createParticles()
    animate()
  }
})

watch(() => props.isImploding, (newValue) => {
  if (newValue) {
    particles.value.forEach(p => {
      p.currentX = Math.cos(p.angle) * p.distance
      p.currentY = Math.sin(p.angle) * p.distance
    })
    animate()
  }
})

onMounted(() => {
  if (props.isExploding) {
    createParticles()
    animate()
  }
})
</script>

<style scoped>
.energy-particles-container {
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  pointer-events: none;
}

.energy-particle {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  transition: background 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.energy-particle.exploding {
  animation: particleExplode 0.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.energy-particle.imploding {
  animation: particleImplode 0.5s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

@keyframes particleExplode {
  0% {
    transform: translate(-50%, -50%) translate(0px, 0px) scale(1);
    opacity: 1;
  }
  100% {
    transform: translate(-50%, -50%) translate(var(--tx, 0px), var(--ty, 0px)) scale(0);
    opacity: 0;
  }
}

@keyframes particleImplode {
  0% {
    transform: translate(-50%, -50%) translate(var(--tx, 0px), var(--ty, 0px)) scale(0);
    opacity: 0;
  }
  100% {
    transform: translate(-50%, -50%) translate(0px, 0px) scale(1);
    opacity: 1;
  }
}
</style>
