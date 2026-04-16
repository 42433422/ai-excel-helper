/**
 * claw-plugin-report — 工具函数
 *
 * 上报参数处理工具。
 */
/**
 * 为上报参数添加统一前缀（如 PC_Qclaw_name, PC_Qclaw_guid）
 *
 * 与 packages/report/src/galileo/util.ts → addQclawPrefix 一致。
 */
export declare function addQclawPrefix(options: Record<string, any>): Record<string, any>;
/**
 * 根据平台和架构生成上报用的平台标识
 *
 * 与 packages/report/src/galileo/util.ts → getDevicePlatform 一致。
 *
 * - Windows → Qclaw_Win
 * - macOS ARM → Qclaw_MAC_ARM
 * - macOS Intel → Qclaw_MAC_INTEL
 */
export declare function getDevicePlatform({ platform, arch, }: {
    platform: string;
    arch: string;
}): string;
