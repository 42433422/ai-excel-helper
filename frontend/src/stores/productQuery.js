import { defineStore } from 'pinia'
import { productsApi } from '@/api/products'

export const useProductQueryStore = defineStore('productQuery', {
  state: () => ({
    companies: [],
    products: [],
    selectedCompany: null,
    selectedProduct: null,
    searchQuery: '',
    loading: false,
    error: null
  }),

  getters: {
    filteredProducts: (state) => {
      if (!state.searchQuery) return state.products
      
      const query = state.searchQuery.toLowerCase()
      return state.products.filter(product => 
        product.name?.toLowerCase().includes(query) ||
        product.model?.toLowerCase().includes(query) ||
        product.code?.toLowerCase().includes(query)
      )
    },

    companyProducts: (state) => (companyId) => {
      return state.products.filter(product => product.companyId === companyId)
    }
  },

  actions: {
    async loadCompanies() {
      this.loading = true
      this.error = null
      
      try {
        const response = await productsApi.getCompanies()
        this.companies = response.data || []
      } catch (error) {
        this.error = error.message
        console.error('Failed to load companies:', error)
      } finally {
        this.loading = false
      }
    },

    async loadProducts(companyId) {
      this.loading = true
      this.error = null
      
      try {
        const response = await productsApi.getProducts({ companyId })
        this.products = response.data || []
      } catch (error) {
        this.error = error.message
        console.error('Failed to load products:', error)
      } finally {
        this.loading = false
      }
    },

    async loadAllProducts() {
      this.loading = true
      this.error = null
      
      try {
        const response = await productsApi.getProducts()
        this.products = response.data || []
        
        const uniqueCompanies = [...new Set(this.products.map(p => p.companyId))]
        this.companies = uniqueCompanies.map(id => ({
          id,
          name: this.products.find(p => p.companyId === id)?.companyName || `公司${id}`
        }))
      } catch (error) {
        this.error = error.message
        console.error('Failed to load products:', error)
      } finally {
        this.loading = false
      }
    },

    selectCompany(company) {
      this.selectedCompany = company
      this.selectedProduct = null
      
      if (company) {
        this.loadProducts(company.id)
      }
    },

    selectProduct(product) {
      this.selectedProduct = product
    },

    searchProducts(query) {
      this.searchQuery = query
    },

    async updateProduct(productId, data) {
      this.loading = true
      this.error = null
      
      try {
        await productsApi.updateProduct(productId, data)
        
        const index = this.products.findIndex(p => p.id === productId)
        if (index !== -1) {
          this.products[index] = { ...this.products[index], ...data }
        }
      } catch (error) {
        this.error = error.message
        console.error('Failed to update product:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    async exportProducts(companyId = null) {
      try {
        const params = companyId ? { companyId } : {}
        await productsApi.exportUnitProductsXlsx(params)
      } catch (error) {
        this.error = error.message
        console.error('Failed to export products:', error)
        throw error
      }
    },

    reset() {
      this.companies = []
      this.products = []
      this.selectedCompany = null
      this.selectedProduct = null
      this.searchQuery = ''
      this.loading = false
      this.error = null
    }
  }
})
