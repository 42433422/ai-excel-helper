import { api } from './index';
import type { ApiResponse } from '@/types/api';

export interface IntentPackage {
  id: number;
  name: string;
  description?: string;
  enabled: boolean;
  intents?: string[];
  [key: string]: any;
}

export const intentPackagesApi = {
  getPackages(): Promise<ApiResponse<IntentPackage[]>> {
    return api.get<ApiResponse<IntentPackage[]>>('/api/intent-packages');
  },

  updatePackages(packages: IntentPackage[]): Promise<ApiResponse<IntentPackage[]>> {
    return api.post<ApiResponse<IntentPackage[]>>('/api/intent-packages', packages);
  },

  updatePackage(packageId: number | string, enabled: boolean): Promise<ApiResponse<IntentPackage>> {
    return api.put<ApiResponse<IntentPackage>>(`/api/intent-packages/${packageId}`, { enabled });
  }
};

export default intentPackagesApi;
