import { defineStore } from 'pinia'
import { ref, computed, type Ref } from 'vue'
import ordersApi from '../api/orders'
import type { Order } from '@/types/order'
import type { ApiResponse } from '@/types/api'

interface OperationResult {
  success: boolean;
  data?: any;
  message?: string;
}

export const useOrdersStore = defineStore('orders', () => {
  const orders = ref<Order[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const orderCount = computed(() => orders.value.length)

  function normalizeOrders(data: any): Order[] {
    if (Array.isArray(data?.data)) return data.data
    if (Array.isArray(data?.orders)) return data.orders
    if (Array.isArray(data)) return data
    return []
  }

  async function fetchOrders(params: Record<string, any> = {}): Promise<OperationResult> {
    loading.value = true
    error.value = null
    try {
      const data = await ordersApi.getOrders(params)
      if (data?.success === false) {
        error.value = data?.message || '加载订单失败'
        return { success: false, message: error.value }
      }
      orders.value = normalizeOrders(data)
      return { success: true }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载订单失败'
      console.error('加载订单失败:', e)
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  async function searchOrders(keyword: string): Promise<OperationResult> {
    loading.value = true
    error.value = null
    try {
      const data = await ordersApi.searchOrders(keyword)
      if (data?.success === false) {
        error.value = data?.message || '搜索订单失败'
        return { success: false, message: error.value }
      }
      orders.value = normalizeOrders(data)
      return { success: true }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '搜索订单失败'
      console.error('搜索订单失败:', e)
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  async function deleteOrder(orderNumber: string): Promise<OperationResult> {
    loading.value = true
    error.value = null
    try {
      const data = await ordersApi.deleteOrder(orderNumber)
      if (!data?.success) {
        error.value = data?.message || '删除失败'
        return { success: false, message: error.value }
      }
      orders.value = orders.value.filter(o =>
        (o.order_number || o.id) !== orderNumber
      )
      return { success: true }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '删除失败'
      console.error('删除订单失败:', e)
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  async function clearAllOrders(): Promise<OperationResult> {
    loading.value = true
    error.value = null
    try {
      const data = await ordersApi.clearAllOrders()
      if (!data?.success) {
        error.value = data?.message || '清空失败'
        return { success: false, message: error.value }
      }
      orders.value = []
      return { success: true }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '清空失败'
      console.error('清空订单失败:', e)
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  return {
    orders,
    loading,
    error,
    orderCount,
    fetchOrders,
    searchOrders,
    deleteOrder,
    clearAllOrders
  }
})
