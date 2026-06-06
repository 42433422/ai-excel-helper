import { api, buildFullApiUrl } from './core';
import { LS_MARKET_ACCESS_TOKEN } from './marketAccount';
import { readCsrfTokenFromCookie, shouldAttachCsrfHeader } from '@/utils/csrfCookie';
import type { RequestOptions } from './core';
import type { ApiResponse } from '@/types/api';
import type { ChatRequest, ChatResponse, ChatSession } from '@/types/chat';
import { isProductsReadGateGraceActive, readStoredDbTokens } from '@/fhd/dbTokenHeaders';
import {
  readPlannerSseResponse,
  resolveChatStreamPath,
  type PlannerSseEvent,
} from '@/utils/chatSseStream';
import {
  resolvePlannerChatBatchPath,
  resolvePlannerChatPath,
  resolvePlannerIntentTestPath,
  resolvePlannerUnifiedChatBatchPath,
  resolvePlannerUnifiedChatPath,
} from '@/utils/plannerChatPaths';

export type { PlannerSseEvent };

interface ChatContextParams {
  user_id?: string;
  source?: string;
  mode?: string;
}

export type ChatStreamRequestInit = RequestInit & {
  /** 覆盖默认路径（否则用 ``VITE_CHAT_STREAM_PATH`` 或 ``/api/ai/chat/stream``） */
  streamPath?: string;
};

function readMarketBearerHeader(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = String(window.localStorage.getItem(LS_MARKET_ACCESS_TOKEN) || '').trim();
  if (!token) return {};
  return { Authorization: token.toLowerCase().startsWith('bearer ') ? token : `Bearer ${token}` };
}

function withMarketAuthorization(options: RequestOptions = {}): RequestOptions {
  const existing = options.headers as Record<string, string> | undefined;
  if (existing?.Authorization || existing?.authorization) return options;
  const auth = readMarketBearerHeader();
  if (!auth.Authorization) return options;
  return {
    ...options,
    headers: {
      ...existing,
      ...auth,
    },
  };
}

/** Planner SSE：非 2xx 时解析 JSON 错误文案 */
export async function parseChatStreamErrorResponse(res: Response): Promise<string> {
  let msg = `流式请求失败（${res.status}）`;
  try {
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      const j = await res.json();
      msg = String((j as any)?.message || (j as any)?.detail || msg);
    }
  } catch {
    /* ignore */
  }
  return msg;
}

export const chatApi = {
  sendChat(
    payload: ChatRequest,
    options: RequestOptions = {}
  ): Promise<ApiResponse<ChatResponse>> {
    return api.post<ApiResponse<ChatResponse>>(
      resolvePlannerChatPath(),
      payload,
      withMarketAuthorization(options),
    );
  },

  /**
   * 真实 Planner SSE：``POST`` + ``text/event-stream``，返回原生 ``Response``（``body`` 为流）。
   * 与 ``api.post`` 不同，不能用 JSON/blob 封装。自动合并数据库令牌：
   * - 一级：仅在 5 分钟读授权窗口内注入 ``db_read_token``
   * - 二级：须由调用方在 payload 中传入 ``db_write_token``（经弹窗确认后单次附带，见 ``armNextPlannerChatDbWriteToken``）
   */
  sendChatStream(payload: ChatRequest & Record<string, unknown>, init: ChatStreamRequestInit = {}): Promise<Response> {
    const { streamPath, headers: hdr, ...rest } = init;
    const url = buildFullApiUrl((streamPath || '').trim() || resolveChatStreamPath());
    const { read: readTok } = readStoredDbTokens();
    const readAllowed = isProductsReadGateGraceActive();
    const body = JSON.stringify({
      ...payload,
      ...(readAllowed && readTok ? { db_read_token: readTok } : {}),
    });
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...readMarketBearerHeader(),
      ...(hdr as Record<string, string>),
    };
    if (shouldAttachCsrfHeader('POST', headers)) {
      const tok = readCsrfTokenFromCookie();
      if (tok) headers['X-CSRF-Token'] = tok;
    }
    return fetch(url, {
      method: 'POST',
      credentials: 'include',
      headers,
      body,
      ...rest,
    });
  },

  /**
   * 发起流式对话并读完 SSE（直到 ``done`` / ``error``）。``!res.ok`` 时抛错（文案来自 JSON）。
   */
  async consumeChatStream(
    payload: ChatRequest & Record<string, unknown>,
    onEvent: (ev: PlannerSseEvent) => void,
    init: ChatStreamRequestInit = {}
  ): Promise<void> {
    const res = await chatApi.sendChatStream(payload, init);
    if (!res.ok) {
      throw new Error(await parseChatStreamErrorResponse(res));
    }
    await readPlannerSseResponse(res, onEvent);
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
    return api.post<ApiResponse<any>>(resolvePlannerIntentTestPath(), data);
  },

  sendUnifiedChat(
    payload: ChatRequest,
    options: RequestOptions = {}
  ): Promise<ApiResponse<ChatResponse>> {
    return api.post<ApiResponse<ChatResponse>>(
      resolvePlannerUnifiedChatPath(),
      payload,
      withMarketAuthorization(options),
    );
  },

  /** 专业链路：多条消息一次 HTTP，按顺序 process_chat */
  sendChatBatch(
    payload: ChatRequest & { messages: string[] },
    options: RequestOptions = {}
  ): Promise<ApiResponse<{ success: boolean; results: ChatResponse[]; count: number; batch?: boolean }>> {
    return api.post(resolvePlannerChatBatchPath(), payload, withMarketAuthorization(options));
  },

  /** 普通 unified：多条消息一次 HTTP */
  sendUnifiedChatBatch(
    payload: ChatRequest & { messages: string[] },
    options: RequestOptions = {}
  ): Promise<ApiResponse<{ success: boolean; results: ChatResponse[]; count: number; batch?: boolean }>> {
    return api.post(resolvePlannerUnifiedChatBatchPath(), payload, withMarketAuthorization(options));
  },

  getConversations(params: Record<string, any> = {}): Promise<ApiResponse<ChatSession[]>> {
    return api.get<ApiResponse<ChatSession[]>>('/api/conversations/sessions', params);
  },

  clearConversations(data: Record<string, any> = {}): Promise<ApiResponse<{ deleted: number }>> {
    return api.post<ApiResponse<{ deleted: number }>>('/api/conversations/sessions/clear', data);
  },

  getConversation(sessionId: string): Promise<ApiResponse<ChatSession>> {
    return api.get<ApiResponse<ChatSession>>(`/api/conversations/${sessionId}`);
  },

  saveMessage(payload: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/conversations/message', payload);
  },

  newConversation(data: Record<string, any> = {}): Promise<ApiResponse<{ session_id: string }>> {
    return api.post<ApiResponse<{ session_id: string }>>('/api/ai/conversation/new', data);
  },
};

export default chatApi;
