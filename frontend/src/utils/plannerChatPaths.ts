import { PLANNER_FACADE_MOD_ID, readPlannerModFacadeEnabled } from '@/constants/plannerMod'

/** 是否走 Mod 门面（需已安装 xcagi-planner-bridge 且用户未关闭） */
export function usePlannerModFacade(): boolean {
  return readPlannerModFacadeEnabled()
}

export function resolvePlannerChatPath(): string {
  if (usePlannerModFacade()) {
    return `/api/mod/${PLANNER_FACADE_MOD_ID}/chat`
  }
  return '/api/ai/chat'
}

export function resolvePlannerChatStreamPath(): string {
  if (usePlannerModFacade()) {
    return `/api/mod/${PLANNER_FACADE_MOD_ID}/chat/stream`
  }
  const env = (import.meta.env.VITE_CHAT_STREAM_PATH as string | undefined)?.trim()
  return env || '/api/ai/chat/stream'
}

export function resolvePlannerChatBatchPath(): string {
  if (usePlannerModFacade()) {
    return `/api/mod/${PLANNER_FACADE_MOD_ID}/chat/batch`
  }
  return '/api/ai/chat/batch'
}

export function resolvePlannerUnifiedChatPath(): string {
  if (usePlannerModFacade()) {
    return `/api/mod/${PLANNER_FACADE_MOD_ID}/unified_chat`
  }
  return '/api/ai/unified_chat'
}

export function resolvePlannerUnifiedChatBatchPath(): string {
  if (usePlannerModFacade()) {
    return `/api/mod/${PLANNER_FACADE_MOD_ID}/unified_chat/batch`
  }
  return '/api/ai/unified_chat/batch'
}

export function resolvePlannerIntentTestPath(): string {
  if (usePlannerModFacade()) {
    return `/api/mod/${PLANNER_FACADE_MOD_ID}/intent/test`
  }
  return '/api/ai/intent/test'
}
