import { api } from './index';
import type { ApiResponse } from '@/types/api';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface User {
  id: number;
  username: string;
  display_name: string;
  email: string;
  role: string;
  is_active: boolean;
}

export interface LoginResponse {
  success: boolean;
  user?: User;
  session_id?: string;
  expires_at?: string;
  message?: string;
  error?: any;
}

export const authApi = {
  async login(username: string, password: string): Promise<ApiResponse<LoginResponse>> {
    return api.post<ApiResponse<LoginResponse>>('/api/auth/login', { username, password });
  },

  async logout(): Promise<ApiResponse<void>> {
    return api.post<ApiResponse<void>>('/api/auth/logout', {});
  },

  async getCurrentUser(): Promise<ApiResponse<{ user: User; permissions: string[] }>> {
    return api.get<ApiResponse<{ user: User; permissions: string[] }>>('/api/auth/me');
  },

  async validateSession(): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>('/api/auth/session/validate');
  }
};

export default authApi;
