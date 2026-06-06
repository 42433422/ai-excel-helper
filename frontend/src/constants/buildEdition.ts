import { readBuildEdition, type HostEdition } from '@/constants/genericModPack'

/** Vite 构建期 edition（与运行时 readBuildEdition 一致） */
export function buildTimeEdition(): HostEdition {
  return readBuildEdition()
}

export function isMinimalBuild(): boolean {
  return buildTimeEdition() === 'minimal'
}

export function isGenericBuild(): boolean {
  return buildTimeEdition() === 'generic'
}

/** minimal 发行仅打包这三类 Mod 的前端资源 */
export const MINIMAL_BUILD_MOD_IDS = [
  'xcagi-planner-bridge',
  'xcagi-neuro-bus-bridge',
  'xcagi-office-employee-pack-bridge',
] as const
