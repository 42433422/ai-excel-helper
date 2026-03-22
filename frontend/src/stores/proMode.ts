import { defineStore } from 'pinia'
import { ref, type Ref } from 'vue'

interface ProModeState {
  isActive: boolean;
  isTransitioning: boolean;
  isWorkMode: boolean;
  isMonitorMode: boolean;
  currentStage: string;
  selectedCompany: any | null;
  selectedProduct: any | null;
  coreScale: number;
  orbitLayerScale: number;
  stageHistory: string[];
}

export const useProModeStore = defineStore('proMode', () => {
  const isActive = ref(false)
  const isTransitioning = ref(false)
  const isWorkMode = ref(false)
  const isMonitorMode = ref(false)
  const currentStage = ref('idle')
  const selectedCompany = ref<any | null>(null)
  const selectedProduct = ref<any | null>(null)
  const coreScale = ref(1)
  const orbitLayerScale = ref(1)
  const stageHistory = ref<string[]>([])

  const isEntering = ref(false)
  const isExiting = ref(false)

  function toggleProMode() {
    if (isActive.value) {
      exitProMode()
    } else {
      enterProMode()
    }
  }

  function enterProMode() {
    isTransitioning.value = true
    isActive.value = true
    
    setTimeout(() => {
      isTransitioning.value = false
    }, 500)
  }

  function exitProMode() {
    isTransitioning.value = true
    isActive.value = false
    currentStage.value = 'idle'
    selectedCompany.value = null
    selectedProduct.value = null
    coreScale.value = 1
    orbitLayerScale.value = 1
    
    setTimeout(() => {
      isTransitioning.value = false
    }, 500)
  }

  function enterWorkMode() {
    isWorkMode.value = true
  }

  function exitWorkMode() {
    isWorkMode.value = false
  }

  function enterMonitorMode() {
    isMonitorMode.value = true
  }

  function exitMonitorMode() {
    isMonitorMode.value = false
  }

  function setStage(stage: string, payload: { company?: any; product?: any } = {}) {
    if (stage !== 'idle' && stage !== currentStage.value) {
      stageHistory.value.push(currentStage.value)
      if (stageHistory.value.length > 10) {
        stageHistory.value.shift()
      }
    }
    
    currentStage.value = stage
    
    switch (stage) {
      case 'idle':
        coreScale.value = 1
        orbitLayerScale.value = 1
        break
      case 'companies':
        coreScale.value = 0.82
        orbitLayerScale.value = 0.86
        break
      case 'company_selected':
        coreScale.value = 0.68
        orbitLayerScale.value = 0.74
        break
      case 'product_selected':
        coreScale.value = 0.54
        orbitLayerScale.value = 0.62
        break
    }
    
    if (payload.company) {
      selectedCompany.value = payload.company
    }
    
    if (payload.product) {
      selectedProduct.value = payload.product
    }
  }

  function stepBack() {
    if (stageHistory.value.length === 0) {
      exitProMode()
      return
    }
    
    const previousStage = stageHistory.value.pop()
    if (previousStage) {
      setStage(previousStage)
    }
  }

  function resetTransientState() {
    setStage('idle')
    selectedCompany.value = null
    selectedProduct.value = null
    coreScale.value = 1
    orbitLayerScale.value = 1
  }

  return {
    isActive,
    isTransitioning,
    isWorkMode,
    isMonitorMode,
    currentStage,
    selectedCompany,
    selectedProduct,
    coreScale,
    orbitLayerScale,
    stageHistory,
    isEntering,
    isExiting,
    toggleProMode,
    enterProMode,
    exitProMode,
    enterWorkMode,
    exitWorkMode,
    enterMonitorMode,
    exitMonitorMode,
    setStage,
    stepBack,
    resetTransientState
  }
})
