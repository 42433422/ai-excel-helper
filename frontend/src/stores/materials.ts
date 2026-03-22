import { defineStore } from 'pinia'
import { ref, computed, type Ref } from 'vue'
import materialsApi from '../api/materials'
import type { Material, MaterialCreateDTO, MaterialUpdateDTO } from '@/types/material'
import type { ApiResponse } from '@/types/api'

interface OperationResult {
  success: boolean;
  data?: any;
  message?: string;
  total?: number;
}

export const useMaterialsStore = defineStore('materials', () => {
  const materials = ref<Material[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const materialCount = computed(() => materials.value.length)

  const lowStockMaterials = computed(() => {
    return materials.value.filter(m =>
      m.quantity !== null && (m as any).min_stock !== null && m.quantity < (m as any).min_stock
    )
  })

  const categories = computed(() => {
    const cats = new Set(materials.value.map((m: any) => m.category).filter(Boolean))
    return Array.from(cats)
  })

  async function fetchMaterials(params: Record<string, any> = {}): Promise<OperationResult> {
    loading.value = true
    error.value = null
    try {
      const data = await materialsApi.getMaterials(params)
      if (data.success) {
        materials.value = data.data || []
        return { success: true, data: data.data, total: data.total || 0 }
      } else {
        error.value = data.message || '加载原材料失败'
        return { success: false, message: error.value }
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载原材料失败'
      console.error('加载原材料失败:', e)
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  async function createMaterial(materialData: MaterialCreateDTO): Promise<OperationResult> {
    loading.value = true
    error.value = null
    try {
      const data = await materialsApi.createMaterial(materialData)
      if (data.success) {
        await fetchMaterials()
        return { success: true }
      } else {
        error.value = data.message || '创建原材料失败'
        return { success: false, message: error.value }
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '创建原材料失败'
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  async function updateMaterial(id: number, materialData: MaterialUpdateDTO): Promise<OperationResult> {
    loading.value = true
    error.value = null
    try {
      const data = await materialsApi.updateMaterial(id, materialData)
      if (data.success) {
        await fetchMaterials()
        return { success: true }
      } else {
        error.value = data.message || '更新原材料失败'
        return { success: false, message: error.value }
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '更新原材料失败'
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  async function deleteMaterial(id: number): Promise<OperationResult> {
    loading.value = true
    error.value = null
    try {
      const data = await materialsApi.deleteMaterial(id)
      if (data.success) {
        materials.value = materials.value.filter(m => m.id !== id)
        return { success: true }
      } else {
        error.value = data.message || '删除原材料失败'
        return { success: false, message: error.value }
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '删除原材料失败'
      return { success: false, message: error.value }
    } finally {
      loading.value = false
    }
  }

  async function batchDelete(ids: (number | string)[]): Promise<OperationResult> {
    loading.value = true
    error.value = null
    try {
      const data = await materialsApi.batchDeleteMaterials(ids)
      if (data.success) {
        materials.value = materials.value.filter(m => !ids.includes(m.id))
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
    materials,
    loading,
    error,
    materialCount,
    lowStockMaterials,
    categories,
    fetchMaterials,
    createMaterial,
    updateMaterial,
    deleteMaterial,
    batchDelete
  }
})
