import { api } from './index';
import type { ApiResponse } from '@/types/api';
import type { ChatRequest, ChatResponse, ChatSession } from '@/types/chat';

export const chatApi = {
  sendChat(payload: ChatRequest): Promise<ApiResponse<ChatResponse>> {
    return api.post<ApiResponse<ChatResponse>>('/api/ai/chat', payload);
  },

  sendChatStream(payload: ChatRequest): Promise<Response> {
    return api.post('/api/ai/chat/stream', payload, { responseType: 'blob' }) as Promise<Response>;
  },

  getContext(params: Record<string, any> = {}): Promise<ApiResponse<ChatSession>> {
    return api.get<ApiResponse<ChatSession>>('/api/ai/context', params);
  },

  clearContext(data: Record<string, any> = {}): Promise<ApiResponse<void>> {
    return api.post<ApiResponse<void>>('/api/ai/context/clear', data);
  },

  getConfig(): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>('/api/ai/config');
  },

  testIntent(data: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/ai/intent/test', data);
  },

  sendUnifiedChat(payload: ChatRequest): Promise<ApiResponse<ChatResponse>> {
    return api.post<ApiResponse<ChatResponse>>('/api/ai/unified_chat', payload);
  },

  getConversations(params: Record<string, any> = {}): Promise<ApiResponse<ChatSession[]>> {
    return api.get<ApiResponse<ChatSession[]>>('/api/conversations/sessions', params);
  },

  getConversation(sessionId: string): Promise<ApiResponse<ChatSession>> {
    return api.get<ApiResponse<ChatSession>>(`/api/conversations/${sessionId}`);
  },

  saveMessage(payload: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/conversations/message', payload);
  },

  newConversation(data: Record<string, any> = {}): Promise<ApiResponse<{ session_id: string }>> {
    return api.post<ApiResponse<{ session_id: string }>>('/api/ai/conversation/new', data);
  }
};

export default chatApi;
