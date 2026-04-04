import { api } from './index';
import type { ApiResponse } from '@/types/api';
import type { Material, MaterialCreateDTO, MaterialUpdateDTO } from '@/types/material';

export const materialsApi = {
  getMaterials(params: Record<string, any> = {}): Promise<ApiResponse<Material[]>> {
    return api.get<ApiResponse<Material[]>>('/api/materials', params);
  },

  getMaterial(id: number | string): Promise<ApiResponse<Material>> {
    return api.get<ApiResponse<Material>>(`/api/materials/${id}`);
  },

  createMaterial(data: MaterialCreateDTO): Promise<ApiResponse<Material>> {
    return api.post<ApiResponse<Material>>('/api/materials', data);
  },

  updateMaterial(id: number | string, data: MaterialUpdateDTO): Promise<ApiResponse<Material>> {
    return api.put<ApiResponse<Material>>(`/api/materials/${id}`, data);
  },

  deleteMaterial(id: number | string): Promise<ApiResponse<void>> {
    return api.delete<ApiResponse<void>>(`/api/materials/${id}`);
  },

  batchDeleteMaterials(materialIds: (number | string)[]): Promise<ApiResponse<void>> {
    return api.post<ApiResponse<void>>('/api/materials/batch-delete', { material_ids: materialIds });
  },

  getLowStockMaterials(): Promise<ApiResponse<Material[]>> {
    return api.get<ApiResponse<Material[]>>('/api/materials/low-stock');
  },

  searchMaterials(query: string, category: string): Promise<ApiResponse<Material[]>> {
    const params: Record<string, any> = {};
    if (query) params.search = query;
    if (category) params.category = category;
    return api.get<ApiResponse<Material[]>>('/api/materials', params);
  },

  exportMaterialsXlsx(params: Record<string, any> = {}): Promise<Response> {
    return api.download('/api/materials/export', params);
  }
};

export default materialsApi;
