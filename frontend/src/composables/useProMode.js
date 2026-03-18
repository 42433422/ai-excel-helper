import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useProModeStore } from '@/stores/proMode'

export function useProMode() {
  const store = useProModeStore()
  
  const isAnimating = ref(false)
  const animationId = ref(null)
  
  const toggleProMode = () => {
    store.toggleProMode()
  }
  
  const enterProMode = () => {
    store.enterProMode()
  }
  
  const exitProMode = () => {
    store.exitProMode()
  }
  
  const enterWorkMode = () => {
    store.enterWorkMode()
  }
  
  const exitWorkMode = () => {
    store.exitWorkMode()
  }
  
  const setStage = (stage, payload = {}) => {
    store.setStage(stage, payload)
  }
  
  const resetTransientState = () => {
    store.resetTransientState()
  }
  
  const isActive = computed(() => store.isActive)
  const isTransitioning = computed(() => store.isTransitioning)
  const isWorkMode = computed(() => store.isWorkMode)
  const currentStage = computed(() => store.currentStage)
  const selectedCompany = computed(() => store.selectedCompany)
  const selectedProduct = computed(() => store.selectedProduct)
  const coreScale = computed(() => store.coreScale)
  const orbitLayerScale = computed(() => store.orbitLayerScale)
  
  onUnmounted(() => {
    if (animationId.value) {
      cancelAnimationFrame(animationId.value)
    }
  })
  
  return {
    isActive,
    isTransitioning,
    isWorkMode,
    currentStage,
    selectedCompany,
    selectedProduct,
    coreScale,
    orbitLayerScale,
    toggleProMode,
    enterProMode,
    exitProMode,
    enterWorkMode,
    exitWorkMode,
    setStage,
    resetTransientState
  }
}
