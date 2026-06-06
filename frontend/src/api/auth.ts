import { api, primeCsrfCookie } from './core';
import { LS_MARKET_ACCESS_TOKEN, LS_MARKET_USER_JSON } from './marketAccount';
import { invalidateEnterpriseSessionCache } from '@/utils/authSessionCache';
import type { ApiResponse } from '@/types/api';

export type AccountKind = 'personal' | 'enterprise' | 'admin';

export interface LoginRequest {
  username: string;
  password: string;
  account_kind?: AccountKind;
}

export interface User {
  id: number;
  username: string;
  display_name: string;
  email: string;
  role: string;
  is_active: boolean;
  avatar_url?: string;
}

export interface UserProfilePayload {
  display_name?: string;
  email?: string;
}

export interface LoginResponse {
  success: boolean;
  user?: User;
  session_id?: string;
  expires_at?: string;
  message?: string;
  error?: any;
  market_access_token?: string;
  market_refresh_token?: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  email?: string;
  verification_code?: string;
  display_name?: string;
}

export const authApi = {
  async login(
    username: string,
    password: string,
    accountKind: AccountKind = 'enterprise',
  ): Promise<ApiResponse<LoginResponse>> {
    await primeCsrfCookie();
    invalidateEnterpriseSessionCache();
    const res = await api.post<ApiResponse<LoginResponse>>('/api/auth/login', {
      username,
      password,
      account_kind: accountKind,
    });
    invalidateEnterpriseSessionCache();
    return res;
  },

  async updateCompanyBrand(companyBrand: string) {
    return api.post('/api/auth/company-brand', { company_brand: companyBrand });
  },

  async register(payload: RegisterRequest): Promise<ApiResponse<LoginResponse>> {
    await primeCsrfCookie();
    invalidateEnterpriseSessionCache();
    const res = await api.post<ApiResponse<LoginResponse>>('/api/auth/register', payload);
    invalidateEnterpriseSessionCache();
    return res;
  },

  async logout(): Promise<ApiResponse<void>> {
    invalidateEnterpriseSessionCache();
    try {
      const { useAccountProfileStore } = await import('@/stores/accountProfile');
      useAccountProfileStore().clear();
    } catch {
      /* ignore */
    }
    try {
      window.localStorage.removeItem(LS_MARKET_ACCESS_TOKEN);
      window.localStorage.removeItem(LS_MARKET_USER_JSON);
    } catch {
      /* ignore */
    }
    await primeCsrfCookie();
    return api.post<ApiResponse<void>>('/api/auth/logout', {});
  },

  async getCurrentUser(): Promise<ApiResponse<{ user: User; permissions: string[] }>> {
    return api.get<ApiResponse<{ user: User; permissions: string[] }>>('/api/auth/me');
  },

  async getProfile(): Promise<ApiResponse<{ user: User }>> {
    return api.get<ApiResponse<{ user: User }>>('/api/auth/profile');
  },

  async updateProfile(payload: UserProfilePayload): Promise<ApiResponse<{ user: User }>> {
    await primeCsrfCookie();
    return api.patch<ApiResponse<{ user: User }>>('/api/auth/profile', payload);
  },

  async uploadAvatar(file: File): Promise<ApiResponse<{ avatar_url: string }>> {
    await primeCsrfCookie();
    const form = new FormData();
    form.append('file', file);
    return api.post<ApiResponse<{ avatar_url: string }>>('/api/auth/profile/avatar', form);
  },

  async validateSession(): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>('/api/auth/session/validate');
  },

  async forgotAccount(email: string): Promise<
    ApiResponse<{ usernames: string[]; found: boolean }>
  > {
    await primeCsrfCookie();
    return api.post<ApiResponse<{ usernames: string[]; found: boolean }>>('/api/auth/forgot-account', {
      email,
    });
  },

  async sendForgotPasswordCode(email: string): Promise<ApiResponse<unknown>> {
    await primeCsrfCookie();
    return api.post<ApiResponse<unknown>>('/api/auth/forgot-password/send-code', { email });
  },

  async resetForgotPassword(
    email: string,
    code: string,
    newPassword: string,
  ): Promise<ApiResponse<{ local_users_updated?: number }>> {
    await primeCsrfCookie();
    return api.post<ApiResponse<{ local_users_updated?: number }>>(
      '/api/auth/forgot-password/reset',
      { email, code, new_password: newPassword },
    );
  },
};

export default authApi;
