import type { RouteLocationNormalizedLoaded } from 'vue-router'

/** 宿主侧栏「智能对话」项 key */
export const SIDEBAR_CHAT_NAV_KEY = 'chat'

const CHAT_SIDEBAR_KEYS = new Set([SIDEBAR_CHAT_NAV_KEY, 'mod-planner-chat'])

const CHAT_ROUTE_NAMES = new Set(['chat', 'mod-planner-chat'])

/** Mod 菜单 path / 宿主 path 是否对应对话页 */
export function isChatLikePath(path: string): boolean {
  const p = String(path || '')
    .split('?')[0]
    .split('#')[0]
    .replace(/\/$/, '') || '/'
  if (p === '/' || p === '/chat') return true
  return /\/chat$/i.test(p) && !/\/chat-debug/i.test(p)
}

/** 将 Mod 对话路由归一为侧栏 ``chat``，便于高亮与悬浮钮互斥 */
export function normalizeSidebarActiveKey(rawKey: string, route?: Pick<RouteLocationNormalizedLoaded, 'name' | 'path'>): string {
  const key = String(rawKey || '').trim()
  const routeName = String(route?.name || '').trim()
  if (CHAT_SIDEBAR_KEYS.has(key) || CHAT_ROUTE_NAMES.has(routeName)) return SIDEBAR_CHAT_NAV_KEY
  if (route && isChatLikePath(route.path)) return SIDEBAR_CHAT_NAV_KEY
  return key || routeName || SIDEBAR_CHAT_NAV_KEY
}

export function isChatSidebarActive(
  sidebarKey: string,
  route: Pick<RouteLocationNormalizedLoaded, 'name' | 'path'>,
): boolean {
  return normalizeSidebarActiveKey(sidebarKey, route) === SIDEBAR_CHAT_NAV_KEY
}
