/** 侧栏 view key → vue-router name（与 MainLayout 一致） */

export const SIDEBAR_ROUTE_ALIASES: Record<string, string> = {
  'approval-hub': 'approval-workspace',
  'mod-approval-hub': 'approval-workspace',
  'mod-taiyangniao-pro-home': 'taiyangniao-pro-home',
  'mod-taiyangniao-pro-settings': 'taiyangniao-pro-settings',
}

export function resolveNavRouteName(viewKey: string, modPath?: string): string {
  const key = String(viewKey || '').trim()
  if (!key) return ''
  const aliased = SIDEBAR_ROUTE_ALIASES[key]
  if (aliased) return aliased
  if (key.startsWith('mod-') && modPath) {
    const pathOnly = String(modPath).split('?')[0]?.split('#')[0] || ''
    if (pathOnly.includes('/approval-hub/workspace')) return 'approval-workspace'
    const lastSeg = pathOnly.split('/').filter(Boolean).pop()
    if (lastSeg) return lastSeg
  }
  return key
}
