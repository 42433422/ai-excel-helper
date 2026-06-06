import { APPROVAL_BRIDGE_MOD_ID, readApprovalModFacadeEnabled } from '@/constants/approvalMod'

export function useApprovalModFacade(): boolean {
  return readApprovalModFacadeEnabled()
}

/** 将 /api/approval/... 映射到 Mod 门面或宿主 */
export function resolveApprovalApiPath(hostPath: string): string {
  const p = hostPath.startsWith('/') ? hostPath : `/${hostPath}`
  if (!useApprovalModFacade()) return p
  const prefix = '/api/approval'
  if (p === prefix) return `/api/mod/${APPROVAL_BRIDGE_MOD_ID}`
  if (p.startsWith(`${prefix}/`)) {
    return `/api/mod/${APPROVAL_BRIDGE_MOD_ID}${p.slice(prefix.length)}`
  }
  return p
}
