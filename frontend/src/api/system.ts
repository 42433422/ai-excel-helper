import { api } from './core';
import type { ApiResponse } from '@/types/api';

export interface Industry {
  id: number;
  name: string;
  code: string;
  description?: string;
  config?: Record<string, any>;
  [key: string]: any;
}

export const systemApi = {
  getIndustries(): Promise<ApiResponse<Industry[]>> {
    return api.get<ApiResponse<Industry[]>>('/api/system/industries');
  },

  getCurrentIndustry(): Promise<ApiResponse<Industry>> {
    return api.get<ApiResponse<Industry>>('/api/system/industry');
  },

  setIndustry(industryId: number | string): Promise<ApiResponse<Industry>> {
    return api.post<ApiResponse<Industry>>('/api/system/industry', { industry_id: industryId });
  },

  getIndustryDetail(industryId: number | string): Promise<ApiResponse<Industry>> {
    return api.get<ApiResponse<Industry>>(`/api/system/industry/${industryId}`);
  },

  getSystemConfig(): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>('/api/system/config');
  },

  getHostProfile(): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>('/api/system/host-profile');
  },

  getIndustryPresets(): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>('/api/system/industry-presets');
  },

  getWorkflowEmployeeCatalog(): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>('/api/system/workflow-employee-catalog');
  },

  getEmployeeRegistryRules(): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>('/api/system/employee-registry-rules');
  },
};

export default systemApi;
