import { defineStore } from 'pinia'
import { systemApi } from '@/api/system'

export const useIndustryStore = defineStore('industry', {
  state: () => ({
    industries: [],
    currentIndustry: null,
    currentConfig: null,
    loading: false,
    error: null
  }),

  getters: {
    currentIndustryName: (state) => {
      return state.currentIndustry?.name || '未知'
    },

    currentIndustryId: (state) => {
      return state.currentIndustry?.id || '涂料'
    },

    primaryUnit: (state) => {
      return state.currentConfig?.units?.primary || '桶'
    },

    primaryLabel: (state) => {
      return state.currentConfig?.quantity_fields?.primary_label || '桶数'
    },

    isLoaded: (state) => {
      return state.currentIndustry !== null
    }
  },

  actions: {
    async loadIndustries() {
      this.loading = true
      this.error = null

      try {
        const response = await systemApi.getIndustries()
        if (response.success) {
          this.industries = response.data.industries || []
        }
      } catch (error) {
        this.error = error.message
        console.error('Failed to load industries:', error)
      } finally {
        this.loading = false
      }
    },

    async loadCurrentIndustry() {
      this.loading = true
      this.error = null

      try {
        const response = await systemApi.getCurrentIndustry()
        if (response.success) {
          this.currentIndustry = response.data
          this.currentConfig = response.data
        }
      } catch (error) {
        this.error = error.message
        console.error('Failed to load current industry:', error)
      } finally {
        this.loading = false
      }
    },

    async switchIndustry(industryId) {
      this.loading = true
      this.error = null

      try {
        const response = await systemApi.setIndustry(industryId)
        if (response.success) {
          await this.loadCurrentIndustry()
          return true
        } else {
          this.error = response.error
          return false
        }
      } catch (error) {
        this.error = error.message
        console.error('Failed to switch industry:', error)
        return false
      } finally {
        this.loading = false
      }
    },

    async initialize() {
      await this.loadIndustries()
      await this.loadCurrentIndustry()
    },

    getIndustryById(id) {
      return this.industries.find(ind => ind.id === id)
    }
  }
})

export default useIndustryStore
