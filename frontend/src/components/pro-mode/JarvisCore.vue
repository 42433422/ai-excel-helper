<template>
  <div 
    class="jarvis-core"
    :class="{ 'speaking': isSpeaking, 'work-mode': isWorkMode, 'monitor-mode': isMonitorMode }"
    :style="{ transform: coreTransform }"
    @click="handleClick"
  >
    <div class="jarvis-sphere"></div>
    
    <div class="polyhedron icosa" :style="{ transform: icosaTransform }">
      <div 
        v-for="(face, index) in icosaFaces" 
        :key="'icosa-' + index"
        class="poly-face"
        :style="{ transform: face.transform, opacity: face.opacity }"
      ></div>
    </div>
    
    <div class="polyhedron octa" :style="{ transform: octaTransform }">
      <div 
        v-for="(face, index) in octaFaces" 
        :key="'octa-' + index"
        class="poly-face"
        :style="{ transform: face.transform, opacity: face.opacity }"
      ></div>
    </div>
    
    <div class="polyhedron tetra" :style="{ transform: tetraTransform }">
      <div 
        v-for="(face, index) in tetraFaces" 
        :key="'tetra-' + index"
        class="poly-face"
        :style="{ transform: face.transform, opacity: face.opacity }"
      ></div>
    </div>
    
    <div class="polyhedron dodeca" :style="{ transform: dodecaTransform }">
      <div 
        v-for="(face, index) in dodecaFaces" 
        :key="'dodeca-' + index"
        class="poly-face"
        :style="{ transform: face.transform, opacity: face.opacity }"
      ></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { createIcosahedron, createOctahedron, createTetrahedron, createDodecahedron } from '@/utils/geometry-real'

const props = defineProps({
  isSpeaking: {
    type: Boolean,
    default: false
  },
  isWorkMode: {
    type: Boolean,
    default: false
  },
  isMonitorMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click'])

const rotation = ref({ x: 0, y: 0, z: 0 })
const animationId = ref(null)

const icosaFaces = ref([])
const octaFaces = ref([])
const tetraFaces = ref([])
const dodecaFaces = ref([])

const icosaTransform = computed(() => 
  `rotateX(${rotation.value.x}deg) rotateY(${rotation.value.y}deg) rotateZ(${rotation.value.z}deg)`
)

const octaTransform = computed(() => 
  `rotateX(${rotation.value.x * 1.2}deg) rotateY(${rotation.value.y * 1.2}deg) rotateZ(${rotation.value.z * 1.2}deg)`
)

const tetraTransform = computed(() => 
  `rotateX(${rotation.value.x * 1.5}deg) rotateY(${rotation.value.y * 1.5}deg) rotateZ(${rotation.value.z * 1.5}deg)`
)

const dodecaTransform = computed(() => 
  `rotateX(${rotation.value.x * 0.8}deg) rotateY(${rotation.value.y * 0.8}deg) rotateZ(${rotation.value.z * 0.8}deg)`
)

const coreTransform = computed(() => 
  `scale(${props.isSpeaking ? 1.1 : 1})`
)

function createPolyhedronFaces() {
  const icosa = createIcosahedron(100)
  const octa = createOctahedron(100)
  const tetra = createTetrahedron(100)
  const dodeca = createDodecahedron(100)
  
  icosaFaces.value = icosa.faces.map((face, index) => ({
    transform: faceTransform(face, index, icosa.faces.length),
    opacity: 0.3
  }))
  
  octaFaces.value = octa.faces.map((face, index) => ({
    transform: faceTransform(face, index, octa.faces.length),
    opacity: 0.25
  }))
  
  tetraFaces.value = tetra.faces.map((face, index) => ({
    transform: faceTransform(face, index, tetra.faces.length),
    opacity: 0.2
  }))
  
  dodecaFaces.value = dodeca.faces.map((face, index) => ({
    transform: faceTransform(face, index, dodeca.faces.length),
    opacity: 0.35
  }))
}

function faceTransform(face, index, totalFaces) {
  if (face?.normal) {
    const [nx, ny, nz] = face.normal
    const rotateY = Math.atan2(nx, nz) * (180 / Math.PI)
    const rotateX = -Math.atan2(ny, Math.hypot(nx, nz)) * (180 / Math.PI)

    // 基于面的中心点半径动态设置深度，让不同几何体层次更自然。
    let translateZ = 140
    if (Array.isArray(face.vertices) && face.vertices.length > 0) {
      const center = face.vertices.reduce(
        (acc, v) => [acc[0] + v[0], acc[1] + v[1], acc[2] + v[2]],
        [0, 0, 0]
      ).map((n) => n / face.vertices.length)

      const radius = Math.hypot(center[0], center[1], center[2])
      translateZ = Math.max(110, Math.min(165, radius * 1.25))
    }

    return `rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(${translateZ}px)`
  }

  const transforms = [
    'rotateX(0deg) rotateY(0deg) translateZ(140px)',
    'rotateX(60deg) rotateY(0deg) translateZ(140px)',
    'rotateX(-60deg) rotateY(0deg) translateZ(140px)',
    'rotateX(0deg) rotateY(60deg) translateZ(140px)',
    'rotateX(0deg) rotateY(-60deg) translateZ(140px)',
    'rotateX(60deg) rotateY(60deg) translateZ(140px)',
    'rotateX(60deg) rotateY(-60deg) translateZ(140px)',
    'rotateX(-60deg) rotateY(60deg) translateZ(140px)',
    'rotateX(-60deg) rotateY(-60deg) translateZ(140px)',
    'rotateX(0deg) rotateY(120deg) translateZ(140px)',
    'rotateX(0deg) rotateY(-120deg) translateZ(140px)',
    'rotateX(120deg) rotateY(0deg) translateZ(140px)',
    'rotateX(-120deg) rotateY(0deg) translateZ(140px)',
    'rotateX(120deg) rotateY(60deg) translateZ(140px)',
    'rotateX(120deg) rotateY(-60deg) translateZ(140px)',
    'rotateX(-120deg) rotateY(60deg) translateZ(140px)',
    'rotateX(-120deg) rotateY(-60deg) translateZ(140px)',
    'rotateX(0deg) rotateY(180deg) translateZ(140px)',
    'rotateX(180deg) rotateY(0deg) translateZ(140px)',
    'rotateX(180deg) rotateY(60deg) translateZ(140px)',
    'rotateX(180deg) rotateY(-60deg) translateZ(140px)'
  ]
  
  return transforms[index % transforms.length]
}

function animate() {
  rotation.value.x += 0.2
  rotation.value.y += 0.3
  rotation.value.z += 0.1
  
  animationId.value = requestAnimationFrame(animate)
}

function handleClick() {
  emit('click')
}

onMounted(() => {
  createPolyhedronFaces()
  animate()
})

onUnmounted(() => {
  if (animationId.value) {
    cancelAnimationFrame(animationId.value)
  }
})
</script>

<style scoped>
.jarvis-core {
  position: relative;
  width: 200px;
  height: 200px;
  transform-style: preserve-3d;
  cursor: pointer;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.jarvis-core:hover {
  transform: scale(1.05);
}

.jarvis-sphere {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.8), rgba(0, 255, 255, 0.6), rgba(0, 191, 255, 0.4));
  box-shadow: 0 0 30px rgba(0, 255, 255, 0.5), inset 0 0 20px rgba(255, 255, 255, 0.3);
  transition: background 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.work-mode .jarvis-sphere {
  background: radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.8), rgba(255, 0, 0, 0.6), rgba(255, 51, 51, 0.4));
  box-shadow: 0 0 30px rgba(255, 0, 0, 0.5), inset 0 0 20px rgba(255, 255, 255, 0.3);
}

.monitor-mode .jarvis-sphere {
  background: radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.8), rgba(255, 215, 0, 0.6), rgba(255, 180, 0, 0.4));
  box-shadow: 0 0 30px rgba(255, 215, 0, 0.5), inset 0 0 20px rgba(255, 255, 255, 0.3);
}

.jarvis-core.speaking .jarvis-sphere {
  animation: breathe 1s ease-in-out infinite;
}

.polyhedron {
  position: absolute;
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
}

.polyhedron.icosa {
  animation: spin 20s linear infinite;
}

.polyhedron.octa {
  animation: spinReverse 15s linear infinite;
}

.polyhedron.tetra {
  animation: spin 10s linear infinite;
}

.polyhedron.dodeca {
  animation: spinReverse 25s linear infinite;
}

.poly-face {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 1px solid rgba(0, 255, 255, 0.5);
  background: rgba(0, 255, 255, 0.1);
  backface-visibility: visible;
  transition: border-color 0.3s cubic-bezier(0.4, 0, 0.2, 1), background 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.work-mode .poly-face {
  border-color: rgba(255, 0, 0, 0.5);
  background: rgba(255, 0, 0, 0.1);
}

@keyframes spin {
  from {
    transform: rotateZ(0deg);
  }
  to {
    transform: rotateZ(360deg);
  }
}

@keyframes spinReverse {
  from {
    transform: rotateZ(360deg);
  }
  to {
    transform: rotateZ(0deg);
  }
}

@keyframes breathe {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 30px rgba(0, 255, 255, 0.5);
  }
  50% {
    transform: scale(1.1);
    box-shadow: 0 0 40px rgba(0, 255, 255, 0.7);
  }
}

.work-mode @keyframes breathe {
  0%, 100% {
    box-shadow: 0 0 30px rgba(255, 0, 0, 0.5);
  }
  50% {
    box-shadow: 0 0 40px rgba(255, 0, 0, 0.7);
  }
}
</style>
