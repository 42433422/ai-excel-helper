import { api } from './core';
import { ApiError } from './core';
import type { ApiResponse } from '@/types/api';
import { resolveErpApiPath } from '@/utils/erpDomainPaths';

const erp = (path: string) => resolveErpApiPath(path);

export interface WechatTask {
  id: number;
  type: string;
  content: string;
  status: 'pending' | 'confirmed' | 'ignored' | 'completed';
  created_at?: string;
  [key: string]: any;
}

export interface WechatContact {
  id: number;
  name: string;
  wechat_id?: string;
  phone?: string;
  tags?: string[];
  is_starred: boolean;
  created_at?: string;
  updated_at?: string;
  [key: string]: any;
}

export const wechatApi = {
  getTasks(params: Record<string, any> = {}): Promise<ApiResponse<WechatTask[]>> {
    return api.get<ApiResponse<WechatTask[]>>(erp('/api/wechat/tasks'), params);
  },

  confirmTask(id: number | string): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>(erp(`/api/wechat/task/${id}/confirm`));
  },

  ignoreTask(id: number | string): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>(erp(`/api/wechat/task/${id}/ignore`));
  },

  getContacts(params: Record<string, any> = {}): Promise<ApiResponse<WechatContact[]>> {
    return api.get<ApiResponse<WechatContact[]>>(erp('/api/wechat/contacts'), params);
  },

  addContact(data: any): Promise<ApiResponse<WechatContact>> {
    return api.post<ApiResponse<WechatContact>>(erp('/api/wechat/contacts'), data);
  },

  getContact(id: number | string): Promise<ApiResponse<WechatContact>> {
    return api.get<ApiResponse<WechatContact>>(erp(`/api/wechat/contacts/${id}`));
  },

  updateContact(id: number | string, data: any): Promise<ApiResponse<WechatContact>> {
    return api.put<ApiResponse<WechatContact>>(erp(`/api/wechat/contacts/${id}`), data);
  },

  deleteContact(id: number | string): Promise<ApiResponse<void>> {
    return api.delete<ApiResponse<void>>(erp(`/api/wechat/contacts/${id}`));
  },

  scanMessages(): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>(erp('/api/wechat/scan'));
  },

  getContactContext(id: number | string): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>(erp(`/api/wechat/contacts/${id}/context`));
  },

  // Legacy-compatible contacts endpoints used by current console pages.
  getStarredContacts(params: Record<string, any> = {}): Promise<ApiResponse<WechatContact[]>> {
    return api.get<ApiResponse<WechatContact[]>>(erp('/api/wechat_contacts'), params);
  },

  async ensureContactCache(): Promise<ApiResponse<any>> {
    const normalizeNoSource404 = (error: unknown): string => {
      if (!(error instanceof ApiError) || error.status !== 404) return '';
      const message = String(error?.data?.message || error.message || '');
      if (!message) return '';
      if (/未找到可导入的联系人源|contact\.db|Name2Id/i.test(message)) {
        return message;
      }
      return '';
    };

    const tryPostFallback = async (): Promise<ApiResponse<any>> => {
      try {
        return await api.post<ApiResponse<any>>(erp('/api/wechat_contacts/ensure_contact_cache'), {});
      } catch (postError) {
        const noSourceMessage = normalizeNoSource404(postError);
        if (noSourceMessage) {
          return { success: true, message: noSourceMessage, data: { skipped: true } };
        }
        if (postError instanceof ApiError && (postError.status === 404 || postError.status === 405)) {
          return api.post<ApiResponse<any>>(erp('/api/wechat_contacts/refresh_contact_cache'), {});
        }
        throw postError;
      }
    };

    try {
      return await api.get<ApiResponse<any>>(erp('/api/wechat_contacts/ensure_contact_cache'));
    } catch (error) {
      const noSourceMessage = normalizeNoSource404(error);
      if (noSourceMessage) {
        return { success: true, message: noSourceMessage, data: { skipped: true } };
      }
      if (error instanceof ApiError && (error.status === 404 || error.status === 405)) {
        return tryPostFallback();
      }
      throw error;
    }
  },

  searchContacts(query: string): Promise<ApiResponse<WechatContact[]>> {
    return api.get<ApiResponse<WechatContact[]>>(erp('/api/wechat_contacts/search'), { q: query || '' });
  },

  addStarredContact(data: any): Promise<ApiResponse<WechatContact>> {
    return api.post<ApiResponse<WechatContact>>(erp('/api/wechat_contacts'), data);
  },

  updateStarredContact(id: number | string, data: any): Promise<ApiResponse<WechatContact>> {
    return api.put<ApiResponse<WechatContact>>(erp(`/api/wechat_contacts/${id}`), data);
  },

  deleteStarredContact(id: number | string): Promise<ApiResponse<void>> {
    return api.delete<ApiResponse<void>>(erp(`/api/wechat_contacts/${id}`));
  },

  unstarAllContacts(): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>(erp('/api/wechat_contacts/unstar_all'), {});
  },

  getStarredContactContext(id: number | string): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>(erp(`/api/wechat_contacts/${id}/context`));
  },

  refreshContactMessages(id: number | string): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>(erp(`/api/wechat_contacts/${id}/refresh_messages`), {});
  },

  refreshMessagesCache(): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>(erp('/api/wechat_contacts/refresh_messages_cache'), {});
  },

  refreshContactCache(): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>(erp('/api/wechat_contacts/refresh_contact_cache'), {});
  },

  openChat(contactName: string): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>(erp('/api/wechat_contacts/open_chat'), { contact_name: contactName });
  },

  sendMessage(contactName: string, message: string): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>(erp('/api/wechat_contacts/send_message'), {
      contact_name: contactName,
      message
    });
  }
};

export default wechatApi;
