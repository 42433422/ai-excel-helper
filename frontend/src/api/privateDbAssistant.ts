import { api } from './core';
import type { ApiResponse } from '@/types/api';

export const PRIVATE_DB_READ_ASSISTANT_MOD_ID = 'private-db-read-assistant';

const BASE = `/api/mod/${PRIVATE_DB_READ_ASSISTANT_MOD_ID}`;

const MOD_UNAVAILABLE: ApiResponse<never> = {
  success: false,
  message: 'private-db-read-assistant Mod 未安装或不可用',
};

let modRouteAvailable: boolean | null = null;

async function isPrivateDbModRouteAvailable(): Promise<boolean> {
  if (modRouteAvailable !== null) return modRouteAvailable;
  try {
    const { api } = await import('./core');
    const resp = await api.get<{ success?: boolean; data?: Array<{ id?: string; enabled?: boolean }> }>(
      '/api/mods/',
    );
    const mods = Array.isArray(resp?.data) ? resp.data : [];
    modRouteAvailable =
      resp?.success !== false &&
      mods.some((m) => m?.id === PRIVATE_DB_READ_ASSISTANT_MOD_ID && m?.enabled !== false);
  } catch {
    modRouteAvailable = false;
  }
  return modRouteAvailable;
}

export interface PrivateDbSource {
  id: string;
  label: string;
  description?: string;
  status?: 'available' | 'planned';
  category?: 'im' | 'mail' | 'erp' | 'office' | 'ecommerce' | 'generic';
  icon?: string;
  capabilities?: string[];
  requires_authorization?: boolean;
}

export interface PrivateDbContact {
  id?: number | null;
  display_name: string;
  contact_name?: string;
  remark?: string;
  source_user_id?: string;
  contact_type?: string;
  is_starred?: boolean;
}

async function modGet<T>(path: string): Promise<ApiResponse<T>> {
  if (!(await isPrivateDbModRouteAvailable())) {
    return MOD_UNAVAILABLE as ApiResponse<T>;
  }
  try {
    return await api.get<ApiResponse<T>>(path);
  } catch {
    modRouteAvailable = false;
    return MOD_UNAVAILABLE as ApiResponse<T>;
  }
}

async function modPost<T>(path: string, body?: unknown): Promise<ApiResponse<T>> {
  if (!(await isPrivateDbModRouteAvailable())) {
    return MOD_UNAVAILABLE as ApiResponse<T>;
  }
  try {
    return await api.post<ApiResponse<T>>(path, body);
  } catch {
    modRouteAvailable = false;
    return MOD_UNAVAILABLE as ApiResponse<T>;
  }
}

export const privateDbAssistantApi = {
  status(): Promise<ApiResponse<any>> {
    return modGet(`${BASE}/status`);
  },

  listSources(): Promise<ApiResponse<PrivateDbSource[]>> {
    return modGet(`${BASE}/sources`);
  },

  selectSource(sourceId: string): Promise<ApiResponse<any>> {
    return modPost(`${BASE}/sources/select`, { source_id: sourceId });
  },

  refreshSource(sourceId: string, refreshType: 'contacts' | 'messages' | 'all' = 'contacts'): Promise<ApiResponse<any>> {
    return modPost(`${BASE}/sources/refresh`, {
      source_id: sourceId,
      refresh_type: refreshType,
    });
  },

  searchContacts(sourceId: string, q: string): Promise<ApiResponse<PrivateDbContact[]>> {
    return modGet(`${BASE}/contacts/search?source_id=${encodeURIComponent(sourceId)}&q=${encodeURIComponent(q)}`);
  },

  getContext(sourceId: string, contactId: number | string): Promise<ApiResponse<any[]>> {
    return modGet(
      `${BASE}/contacts/${encodeURIComponent(String(contactId))}/context?source_id=${encodeURIComponent(sourceId)}`,
    );
  },

  sendMessage(sourceId: string, contactName: string, message: string): Promise<ApiResponse<any>> {
    return modPost(`${BASE}/send`, {
      source_id: sourceId,
      contact_name: contactName,
      message,
    });
  },
};

export default privateDbAssistantApi;
