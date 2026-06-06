import { CORE_WORKFLOW_MOD_ID, readCoreWorkflowModPagesEnabled } from '@/constants/coreWorkflowMod'

const MOD_PREFIX = `/mod/${CORE_WORKFLOW_MOD_ID}`

const HOST_ROUTE_NAME_TO_MOD: Record<string, string> = {
  'workflow-visualization': '/workflow-visualization',
}

export function useWorkflowModPages(): boolean {
  return readCoreWorkflowModPagesEnabled()
}

export function resolveWorkflowPageRedirectForRouteName(routeName: string): string | null {
  if (!useWorkflowModPages()) return null
  const seg = HOST_ROUTE_NAME_TO_MOD[routeName]
  if (!seg) return null
  return `${MOD_PREFIX}${seg}`
}
