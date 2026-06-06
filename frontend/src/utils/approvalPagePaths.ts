import { APPROVAL_BRIDGE_MOD_ID, readApprovalModFacadeEnabled } from '@/constants/approvalMod'

const MOD_PREFIX = `/mod/${APPROVAL_BRIDGE_MOD_ID}`

const HOST_PATH_TO_MOD: Record<string, string> = {
  '/approval-hub': '/approval-hub',
  '/approval-hub/workspace': '/approval-hub/workspace',
  '/approval-hub/flow-management': '/approval-hub/flow-management',
  '/approval-hub/rules': '/approval-hub/rules',
}

const HOST_ROUTE_NAME_TO_MOD: Record<string, string> = {
  'approval-hub': '/approval-hub/workspace',
  'approval-workspace': '/approval-hub/workspace',
  'approval-flow-management': '/approval-hub/flow-management',
  'approval-rules': '/approval-hub/rules',
}

export function useApprovalModPages(): boolean {
  return readApprovalModFacadeEnabled()
}

export function resolveApprovalPagePath(hostPath: string): string {
  const raw = hostPath.startsWith('/') ? hostPath : `/${hostPath}`
  const pathOnly = raw.split('?')[0]?.split('#')[0] || raw
  if (!useApprovalModPages()) return raw
  const seg = HOST_PATH_TO_MOD[pathOnly]
  if (!seg) return raw
  return `${MOD_PREFIX}${seg}${raw.slice(pathOnly.length)}`
}

export function resolveApprovalPageRedirectForRouteName(routeName: string): string | null {
  if (!useApprovalModPages()) return null
  const seg = HOST_ROUTE_NAME_TO_MOD[routeName]
  if (!seg) return null
  return `${MOD_PREFIX}${seg}`
}
