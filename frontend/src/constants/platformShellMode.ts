import {
  readBuildEdition,
  shouldAutoEnableEditionPlatformShell,
  shouldAutoEnableMinimalPlatformShell,
  shouldAutoEnablePlatformShell,
} from '@/constants/genericModPack'

/**
 * 通用化宿主壳模式（里程碑 A/D）：默认只展示壳菜单 + Mod 入口，隐藏内置 ERP 业务页。
 *
 * 启用方式（任一）：
 * - 构建环境变量 VITE_XCAGI_PLATFORM_SHELL=1
 * - URL 参数 ?shell=1
 * - localStorage xcagi_platform_shell_mode=1
 * - 构建 VITE_XCAGI_DEFAULT_PLATFORM_SHELL=1（通用发行版默认壳）
 * - 安装通用 Mod 包后自动开启（见 genericModPack.ts）
 */

export const LS_PLATFORM_SHELL_MODE = 'xcagi_platform_shell_mode'

export const LS_PLATFORM_SHELL_AUTO_GENERIC = 'xcagi_platform_shell_auto_generic'

export const LS_PLATFORM_SHELL_AUTO_MINIMAL = 'xcagi_platform_shell_auto_minimal'

/** 壳模式保留的侧栏 key（与 router name 对齐） */
export const SHELL_CORE_MENU_KEYS = new Set([
  'chat',
  'product-onboarding',
  'mod-store',
  'settings',
  'tools',
  'other-tools',
  'workflow-employee-space',
  'workflow-visualization',
  'chat-debug',
  'ai-ecosystem',
  'brain',
  'wechat-contacts',
  'lan-gate',
  'login',
])

/** 壳模式允许注册的路由 name */
export const SHELL_CORE_ROUTE_NAMES = new Set([
  ...SHELL_CORE_MENU_KEYS,
  'mod-landing',
  'workflow-employee-stitch-full',
  'lan-gate',
  'login',
])

export function readPlatformShellModeFromStorage(): boolean {
  if (typeof localStorage === 'undefined') return false
  try {
    return localStorage.getItem(LS_PLATFORM_SHELL_MODE) === '1'
  } catch {
    return false
  }
}

export function isMinimalEditionBuild(): boolean {
  return readBuildEdition() === 'minimal'
}

export function isGenericEditionBuild(): boolean {
  if (readBuildEdition() === 'generic') return true
  const def = String(import.meta.env.VITE_XCAGI_DEFAULT_PLATFORM_SHELL || '').trim().toLowerCase()
  return def === '1' || def === 'true' || def === 'yes'
}

export function isShellEditionBuild(): boolean {
  return isMinimalEditionBuild() || isGenericEditionBuild()
}

/** @deprecated 使用 isGenericEditionBuild */
function isDefaultPlatformShellBuild(): boolean {
  return isGenericEditionBuild()
}

/**
 * 须在 import router 之前调用（里程碑 I）：通用发行版构建默认写入壳模式偏好。
 */
export function bootstrapMinimalEditionDefaults(): void {
  if (!isMinimalEditionBuild()) return
  if (typeof localStorage === 'undefined') return
  try {
    if (localStorage.getItem(LS_PLATFORM_SHELL_MODE) === '0') return
    localStorage.setItem(LS_PLATFORM_SHELL_MODE, '1')
    localStorage.setItem(LS_PLATFORM_SHELL_AUTO_MINIMAL, 'minimal_edition_build')
  } catch {
    /* ignore */
  }
}

export function bootstrapGenericEditionDefaults(): void {
  if (!isGenericEditionBuild() || isMinimalEditionBuild()) return
  if (typeof localStorage === 'undefined') return
  try {
    if (localStorage.getItem(LS_PLATFORM_SHELL_MODE) === '0') return
    localStorage.setItem(LS_PLATFORM_SHELL_MODE, '1')
    localStorage.setItem(LS_PLATFORM_SHELL_AUTO_GENERIC, 'generic_edition_build')
  } catch {
    /* ignore */
  }
}

/** 须在 import router 之前调用（里程碑 Q/I） */
export function bootstrapEditionDefaults(): void {
  bootstrapMinimalEditionDefaults()
  bootstrapGenericEditionDefaults()
}

function isEnterpriseProductSkuBuild(): boolean {
  const raw = String(import.meta.env.VITE_XCAGI_PRODUCT_SKU || '').trim().toLowerCase()
  return raw === 'enterprise'
}

/** 企业版默认完整侧栏与路由，不进入通用平台壳 */
export function bootstrapEnterpriseShellDefaults(): void {
  if (!isEnterpriseProductSkuBuild()) return
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(LS_PLATFORM_SHELL_MODE, '0')
  } catch {
    /* ignore */
  }
}

export function isPlatformShellModeEnabled(): boolean {
  if (isEnterpriseProductSkuBuild()) return false
  if (typeof window !== 'undefined') {
    if (new URLSearchParams(window.location.search).has('shell')) return true
    if (new URLSearchParams(window.location.search).has('full')) return false
  }
  if (typeof localStorage !== 'undefined') {
    try {
      const stored = localStorage.getItem(LS_PLATFORM_SHELL_MODE)
      if (stored === '0') return false
      if (stored === '1') return true
    } catch {
      /* ignore */
    }
  }
  const env = String(import.meta.env.VITE_XCAGI_PLATFORM_SHELL || '').trim().toLowerCase()
  if (env === '1' || env === 'true' || env === 'yes') return true
  if (isShellEditionBuild()) return true
  return false
}

/** Mod 列表加载后：minimal 发行包自动壳 */
export function applyMinimalPackPlatformShell(installedModIds: string[]): void {
  if (!shouldAutoEnableMinimalPlatformShell(installedModIds)) return
  if (typeof localStorage === 'undefined') return
  try {
    if (localStorage.getItem(LS_PLATFORM_SHELL_MODE) === '0') return
    localStorage.setItem(LS_PLATFORM_SHELL_MODE, '1')
    localStorage.setItem(LS_PLATFORM_SHELL_AUTO_MINIMAL, '1')
  } catch {
    /* ignore */
  }
}

/** Mod 列表加载后：完整 generic 发行包自动壳 */
export function applyGenericPackPlatformShell(installedModIds: string[]): void {
  if (!shouldAutoEnablePlatformShell(installedModIds)) return
  if (typeof localStorage === 'undefined') return
  try {
    if (localStorage.getItem(LS_PLATFORM_SHELL_MODE) === '0') return
    localStorage.setItem(LS_PLATFORM_SHELL_MODE, '1')
    localStorage.setItem(LS_PLATFORM_SHELL_AUTO_GENERIC, '1')
  } catch {
    /* ignore */
  }
}

/** 按构建 edition 或已安装 Mod 集自动开壳 */
export function applyEditionPackPlatformShell(installedModIds: string[]): void {
  const edition = readBuildEdition()
  if (edition === 'minimal') {
    applyMinimalPackPlatformShell(installedModIds)
    return
  }
  if (edition === 'generic') {
    applyGenericPackPlatformShell(installedModIds)
    return
  }
  if (shouldAutoEnableMinimalPlatformShell(installedModIds)) {
    applyMinimalPackPlatformShell(installedModIds)
    return
  }
  applyGenericPackPlatformShell(installedModIds)
}

export function setPlatformShellModeEnabled(on: boolean): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(LS_PLATFORM_SHELL_MODE, on ? '1' : '0')
  } catch {
    /* ignore */
  }
}

export function isHostBusinessMenuKey(key: string): boolean {
  return !SHELL_CORE_MENU_KEYS.has(key)
}
