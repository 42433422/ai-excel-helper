/**
 * claw-plugin-report — 工具函数
 *
 * 上报参数处理工具。
 */
import { DEFAULT_APPKEY } from './constants.js';
/**
 * 为上报参数添加统一前缀（如 PC_Qclaw_name, PC_Qclaw_guid）
 *
 * 与 packages/report/src/galileo/util.ts → addQclawPrefix 一致。
 */
export function addQclawPrefix(options) {
    const params = {};
    for (const key of Object.keys(options)) {
        params[`${DEFAULT_APPKEY}_${key}`] = options[key];
    }
    return params;
}
/**
 * 根据平台和架构生成上报用的平台标识
 *
 * 与 packages/report/src/galileo/util.ts → getDevicePlatform 一致。
 *
 * - Windows → Qclaw_Win
 * - macOS ARM → Qclaw_MAC_ARM
 * - macOS Intel → Qclaw_MAC_INTEL
 */
export function getDevicePlatform({ platform, arch, }) {
    if (platform === 'win32')
        return 'Qclaw_Win';
    if (platform === 'darwin') {
        return arch === 'arm64' ? 'Qclaw_MAC_ARM' : 'Qclaw_MAC_INTEL';
    }
    return `Qclaw_${platform}_${arch}`;
}
//# sourceMappingURL=util.js.map