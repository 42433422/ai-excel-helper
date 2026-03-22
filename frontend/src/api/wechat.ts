import { api } from './index';
import type { ApiResponse } from '@/types/api';

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
    return api.get<ApiResponse<WechatTask[]>>('/api/wechat/tasks', params);
  },

  confirmTask(id: number | string): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>(`/api/wechat/task/${id}/confirm`);
  },

  ignoreTask(id: number | string): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>(`/api/wechat/task/${id}/ignore`);
  },

  getContacts(params: Record<string, any> = {}): Promise<ApiResponse<WechatContact[]>> {
    return api.get<ApiResponse<WechatContact[]>>('/api/wechat/contacts', params);
  },

  addContact(data: any): Promise<ApiResponse<WechatContact>> {
    return api.post<ApiResponse<WechatContact>>('/api/wechat/contacts', data);
  },

  getContact(id: number | string): Promise<ApiResponse<WechatContact>> {
    return api.get<ApiResponse<WechatContact>>(`/api/wechat/contacts/${id}`);
  },

  updateContact(id: number | string, data: any): Promise<ApiResponse<WechatContact>> {
    return api.put<ApiResponse<WechatContact>>(`/api/wechat/contacts/${id}`, data);
  },

  deleteContact(id: number | string): Promise<ApiResponse<void>> {
    return api.delete<ApiResponse<void>>(`/api/wechat/contacts/${id}`);
  },

  scanMessages(): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/wechat/scan');
  },

  getContactContext(id: number | string): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>(`/api/wechat/contacts/${id}/context`);
  },

  // Legacy-compatible contacts endpoints used by current console pages.
  getStarredContacts(params: Record<string, any> = {}): Promise<ApiResponse<WechatContact[]>> {
    return api.get<ApiResponse<WechatContact[]>>('/api/wechat_contacts', params);
  },

  ensureContactCache(): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>('/api/wechat_contacts/ensure_contact_cache');
  },

  searchContacts(query: string): Promise<ApiResponse<WechatContact[]>> {
    return api.get<ApiResponse<WechatContact[]>>('/api/wechat_contacts/search', { q: query || '' });
  },

  addStarredContact(data: any): Promise<ApiResponse<WechatContact>> {
    return api.post<ApiResponse<WechatContact>>('/api/wechat_contacts', data);
  },

  updateStarredContact(id: number | string, data: any): Promise<ApiResponse<WechatContact>> {
    return api.put<ApiResponse<WechatContact>>(`/api/wechat_contacts/${id}`, data);
  },

  deleteStarredContact(id: number | string): Promise<ApiResponse<void>> {
    return api.delete<ApiResponse<void>>(`/api/wechat_contacts/${id}`);
  },

  unstarAllContacts(): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/wechat_contacts/unstar_all', {});
  },

  getStarredContactContext(id: number | string): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>(`/api/wechat_contacts/${id}/context`);
  },

  refreshContactMessages(id: number | string): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>(`/api/wechat_contacts/${id}/refresh_messages`, {});
  },

  refreshMessagesCache(): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/wechat_contacts/refresh_messages_cache', {});
  },

  refreshContactCache(): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/wechat_contacts/refresh_contact_cache', {});
  },

  openChat(contactName: string): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/wechat_contacts/open_chat', { contact_name: contactName });
  },

  sendMessage(contactName: string, message: string): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/wechat_contacts/send_message', {
      contact_name: contactName,
      message
    });
  }
};

export default wechatApi;
