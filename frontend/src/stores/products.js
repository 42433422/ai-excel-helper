import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import productsApi from '../api/products'

export const useProductsStore = defineStore('products', () => {
  const products = ref([])
  const loading = ref(false)
  const error = ref(null)
  const units = ref([])

  const productCount = computed(() => products.value.length)

  async function fetchProducts(params = {}) {
    loading.value = true
    error.value = null
    try {
      const data = await productsApi.getProducts(params)
      if (data.success) {
        products.value = data.data || []
        return { success: true, data: data.data, total: data.total || 0 }
      } else {
        error.value = data.message || '加载产品失败'
        return { success: false, message: error.value }
      }
    } catch (e) {
      error.value = e.message || '加载产品失败'
      console.error('加载产品失败:', e)
      return { success: false, message: e.message }
    } finally {
      loading.value = false
    }
  }

  async function createProduct(productData) {
    loading.value = true
    error.value = null
    try {
      const data = await productsApi.createProduct(productData)
      if (data.success) {
        await fetchProducts()
        return { success: true }
      } else {
        error.value = data.message || '创建产品失败'
        return { success: false, message: error.value }
      }
    } catch (e) {
      error.value = e.message || '创建产品失败'
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  async function updateProduct(id, productData) {
    loading.value = true
    error.value = null
    try {
      const data = await productsApi.updateProduct(id, productData)
      if (data.success) {
        await fetchProducts()
        return { success: true }
      } else {
        error.value = data.message || '更新产品失败'
        return { success: false, message: error.value }
      }
    } catch (e) {
      error.value = e.message || '更新产品失败'
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  async function deleteProduct(id) {
    loading.value = true
    error.value = null
    try {
      const data = await productsApi.deleteProduct(id)
      if (data.success) {
        products.value = products.value.filter(p => p.id !== id)
        return { success: true }
      } else {
        error.value = data.message || '删除产品失败'
        return { success: false, message: error.value }
      }
    } catch (e) {
      error.value = e.message || '删除产品失败'
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  async function batchDelete(ids) {
    loading.value = true
    error.value = null
    try {
      const data = await productsApi.batchDeleteProducts(ids)
      if (data.success) {
        products.value = products.value.filter(p => !ids.includes(p.id))
        return { success: true }
      } else {
        error.value = data.message || '批量删除失败'
        return { success: false, message: error.value }
      }
    } catch (e) {
      error.value = e.message || '批量删除失败'
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  return {
    products,
    loading,
    error,
    units,
    productCount,
    fetchProducts,
    createProduct,
    updateProduct,
    deleteProduct,
    batchDelete
  }
})
