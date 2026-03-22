import { defineStore } from 'pinia'
import { ref, computed, type Ref } from 'vue'
import productsApi from '../api/products'
import type { Product, ProductCreateDTO, ProductUpdateDTO, ProductQueryParams } from '@/types/product'
import type { ApiResponse } from '@/types/api'

interface OperationResult {
  success: boolean;
  data?: any;
  message?: string;
  total?: number;
}

export const useProductsStore = defineStore('products', () => {
  const products = ref<Product[]>([]) as Ref<Product[]>
  const loading = ref(false)
  const error = ref<string | null>(null)
  const units = ref<any[]>([])

  const productCount = computed(() => products.value.length)

  async function fetchProducts(params: ProductQueryParams = {}): Promise<OperationResult> {
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
      error.value = e instanceof Error ? e.message : '加载产品失败'
      console.error('加载产品失败:', e)
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  async function createProduct(productData: ProductCreateDTO): Promise<OperationResult> {
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
      error.value = e instanceof Error ? e.message : '创建产品失败'
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  async function updateProduct(id: number, productData: ProductUpdateDTO): Promise<OperationResult> {
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
      error.value = e instanceof Error ? e.message : '更新产品失败'
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  async function deleteProduct(id: number): Promise<OperationResult> {
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
      error.value = e instanceof Error ? e.message : '删除产品失败'
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  async function batchDelete(ids: (number | string)[]): Promise<OperationResult> {
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
      error.value = e instanceof Error ? e.message : '批量删除失败'
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
