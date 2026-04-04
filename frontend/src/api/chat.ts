import { api } from './index';
import type { RequestOptions } from './core';
import type { ApiResponse } from '@/types/api';
import type { ChatRequest, ChatResponse, ChatSession } from '@/types/chat';

interface ChatContextParams {
  user_id?: string;
  source?: string;
  mode?: string;
}

export const chatApi = {
  sendChat(
    payload: ChatRequest,
    options: RequestOptions = {}
  ): Promise<ApiResponse<ChatResponse>> {
    return api.post<ApiResponse<ChatResponse>>('/api/ai/chat', payload, options);
  },

  sendChatStream(payload: ChatRequest): Promise<Response> {
    return api.post('/api/ai/chat/stream', payload, { responseType: 'blob' }) as Promise<Response>;
  },

  getContext(params: ChatContextParams = {}): Promise<ApiResponse<ChatSession>> {
    return api.get<ApiResponse<ChatSession>>('/api/ai/context', params);
  },

  clearContext(data: { user_id?: string } = {}): Promise<ApiResponse<void>> {
    return api.post<ApiResponse<void>>('/api/ai/context/clear', data);
  },

  getConfig(): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>('/api/ai/config');
  },

  testIntent(data: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/ai/intent/test', data);
  },

  sendUnifiedChat(
    payload: ChatRequest,
    options: RequestOptions = {}
  ): Promise<ApiResponse<ChatResponse>> {
    return api.post<ApiResponse<ChatResponse>>('/api/ai/unified_chat', payload, options);
  },

  /** 专业链路：多条消息一次 HTTP，按顺序 process_chat */
  sendChatBatch(
    payload: ChatRequest & { messages: string[] },
    options: RequestOptions = {}
  ): Promise<ApiResponse<{ success: boolean; results: ChatResponse[]; count: number; batch?: boolean }>> {
    return api.post('/api/ai/chat/batch', payload, options);
  },

  /** 普通 unified：多条消息一次 HTTP */
  sendUnifiedChatBatch(
    payload: ChatRequest & { messages: string[] },
    options: RequestOptions = {}
  ): Promise<ApiResponse<{ success: boolean; results: ChatResponse[]; count: number; batch?: boolean }>> {
    return api.post('/api/ai/unified_chat/batch', payload, options);
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
