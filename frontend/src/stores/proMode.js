import { defineStore } from 'pinia'

export const useProModeStore = defineStore('proMode', {
  state: () => ({
    isActive: false,
    isTransitioning: false,
    isWorkMode: false,
    isMonitorMode: false,
    currentStage: 'idle',
    selectedCompany: null,
    selectedProduct: null,
    coreScale: 1,
    orbitLayerScale: 1,
    stageHistory: []
  }),

  getters: {
    isEntering: (state) => state.isTransitioning && state.isActive,
    isExiting: (state) => state.isTransitioning && !state.isActive
  },

  actions: {
    toggleProMode() {
      if (this.isActive) {
        this.exitProMode()
      } else {
        this.enterProMode()
      }
    },

    enterProMode() {
      this.isTransitioning = true
      this.isActive = true
      
      setTimeout(() => {
        this.isTransitioning = false
      }, 500)
    },

    exitProMode() {
      this.isTransitioning = true
      this.isActive = false
      this.currentStage = 'idle'
      this.selectedCompany = null
      this.selectedProduct = null
      this.coreScale = 1
      this.orbitLayerScale = 1
      
      setTimeout(() => {
        this.isTransitioning = false
      }, 500)
    },

    enterWorkMode() {
      this.isWorkMode = true
    },

    exitWorkMode() {
      this.isWorkMode = false
    },

    enterMonitorMode() {
      this.isMonitorMode = true
    },

    exitMonitorMode() {
      this.isMonitorMode = false
    },

    setStage(stage, payload = {}) {
      if (stage !== 'idle' && stage !== this.currentStage) {
        this.stageHistory.push(this.currentStage)
        if (this.stageHistory.length > 10) {
          this.stageHistory.shift()
        }
      }
      
      this.currentStage = stage
      
      switch (stage) {
        case 'idle':
          this.coreScale = 1
          this.orbitLayerScale = 1
          break
        case 'companies':
          this.coreScale = 0.82
          this.orbitLayerScale = 0.86
          break
        case 'company_selected':
          this.coreScale = 0.68
          this.orbitLayerScale = 0.74
          break
        case 'product_selected':
          this.coreScale = 0.54
          this.orbitLayerScale = 0.62
          break
      }
      
      if (payload.company) {
        this.selectedCompany = payload.company
      }
      
      if (payload.product) {
        this.selectedProduct = payload.product
      }
    },

    stepBack() {
      if (this.stageHistory.length === 0) {
        this.exitProMode()
        return
      }
      
      const previousStage = this.stageHistory.pop()
      this.setStage(previousStage)
    },

    resetTransientState() {
      this.setStage('idle')
      this.selectedCompany = null
      this.selectedProduct = null
      this.coreScale = 1
      this.orbitLayerScale = 1
    }
  }
})
