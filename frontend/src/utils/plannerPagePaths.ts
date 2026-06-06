import { PLANNER_FACADE_MOD_ID, readPlannerModFacadeEnabled } from '@/constants/plannerMod'
import { isProtectedClientModId } from '@/constants/protectedMods'
import { readActiveExtensionModId } from '@/utils/erpDomainPaths'

const MOD_PREFIX = `/mod/${PLANNER_FACADE_MOD_ID}`

const HOST_PATH_TO_MOD: Record<string, string> = {
  '/': '/chat',
  '/chat': '/chat',
  '/ai-ecosystem': '/ai-ecosystem',
  '/brain': '/brain',
  '/chat-debug': '/chat-debug',
}

const HOST_ROUTE_NAME_TO_MOD: Record<string, string> = {
  chat: '/chat',
  'ai-ecosystem': '/ai-ecosystem',
  brain: '/brain',
  'chat-debug': '/chat-debug',
}

export function usePlannerModPages(): boolean {
  if (!readPlannerModFacadeEnabled()) return false
  const active = readActiveExtensionModId()
  if (isProtectedClientModId(active)) return false
  return true
}

export function resolvePlannerPagePath(hostPath: string): string {
  const raw = hostPath.startsWith('/') ? hostPath : `/${hostPath}`
  const pathOnly = raw.split('?')[0]?.split('#')[0] || raw
  if (!usePlannerModPages()) return raw
  const seg = HOST_PATH_TO_MOD[pathOnly]
  if (!seg) return raw
  return `${MOD_PREFIX}${seg}${raw.slice(pathOnly.length)}`
}

export function resolvePlannerPageRedirectForRouteName(routeName: string): string | null {
  if (!usePlannerModPages()) return null
  const seg = HOST_ROUTE_NAME_TO_MOD[routeName]
  if (!seg) return null
  return `${MOD_PREFIX}${seg}`
}

/** 壳模式 / 守卫回退用的对话首页（Mod 或宿主 `/`） */
export function resolvePlannerChatHomePath(): string {
  return resolvePlannerPagePath('/')
}
