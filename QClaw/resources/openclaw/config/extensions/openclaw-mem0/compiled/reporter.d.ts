/**
 * claw-plugin-report — 纯 HTTP 上报实现
 *
 * 不依赖任何 Aegis SDK，直接通过 HTTP POST 请求上报到伽利略服务器。
 *
 * 关键要点：
 * - 上报端点: https://galileotelemetry.tencent.com/collect
 * - Content-Type: text/plain;charset=UTF-8
 * - topic: 必填，对应注册前端观测 target 后得到的 token
 * - scheme: 必填，固定值 "v2"
 * - d2[].fields: 必填，JSON 字符串，必须包含 type 和 level
 * - d2[].message: 必填，string 数组，每项为 JSON 字符串
 * - env: 必须为 "production" 才会上报到正式环境
 */
import type { TelemetryInitOptions } from './types.js';
/**
 * 主进程写入的共享运行时参数接口
 */
export interface QClawSharedParams {
    sessionId?: string;
    guid?: string;
    appVersion?: string;
    appChannel?: string;
    platform?: string;
}
/**
 * 从 ~/.qclaw/qclaw.json 读取主进程共享的运行时参数
 */
export declare function readSharedParams(): QClawSharedParams;
/**
 * 从共享参数同步到 cachedParams
 */
export declare function syncFromSharedParams(forceUpdate?: boolean): boolean;
/**
 * 初始化上报模块
 */
export declare function initReporter(options: TelemetryInitOptions): void;
/**
 * 上报自定义事件（fire-and-forget）
 */
export declare function reportEvent(name: string, options?: Record<string, any>): void;
/**
 * 异步上报自定义事件（可 await）
 */
export declare function reportEventAsync(name: string, options?: Record<string, any>): Promise<void>;
/**
 * 设置上报公共参数
 */
export declare function setCommonParams(params: Record<string, any>): void;
/**
 * 设置 OpenClaw 版本号（从 api.runtime.version 获取）
 */
export declare function setOpenclawVersion(version: string): void;
/**
 * 获取 OpenClaw 版本号
 */
export declare function getOpenclawVersion(): string;
/**
 * 获取插件名称（从配置文件 pluginName 读取）
 */
export declare function getPluginName(): string;
/**
 * 检查上报模块是否已初始化
 */
export declare function isInitialized(): boolean;
/**
 * 销毁上报模块
 */
export declare function destroy(): void;
