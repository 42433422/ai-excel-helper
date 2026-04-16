/**
 * claw-plugin-report — 类型定义
 *
 * 定义伽利略上报 SDK 所需的配置、初始化选项和日志接口。
 */

// ==================== 配置文件结构 ====================

/**
 * claw-plugin-report.config.json 的类型定义
 */
export interface TelemetryConfig {
  /** 是否启用上报（默认 true） */
  enabled?: boolean;
  /** 伽利略项目上报 ID（Aegis reportToken），默认从配置文件读取 */
  reportToken?: string;
  /** 上报地址，默认从配置文件读取 */
  hostUrl?: string;
  /** 环境标识：production | test，默认从配置文件读取 */
  env?: string;
  /** 插件名称，用于上报事件的 page_id 字段 */
  pluginName?: string;
}

// ==================== 初始化选项 ====================

/**
 * initReport() 的初始化选项
 */
export interface TelemetryInitOptions {
  /** 插件根目录，用于定位 claw-plugin-report.config.json */
  configDir: string;
  /** 可选日志接口（使用插件的 api.logger） */
  logger?: Logger;
  /** 可选，覆盖配置文件中的 reportToken */
  reportToken?: string;
  /** 可选，覆盖配置文件中的 hostUrl */
  hostUrl?: string;
  /** 可选，覆盖配置文件中的 env */
  env?: string;
  /** 可选，Electron 主进程共享的 sessionId */
  sessionId?: string;
}

// ==================== 日志接口 ====================

/**
 * 日志接口
 *
 * 与 OpenClaw 插件 api.logger 兼容。
 * 如果不传入，SDK 内部使用 console 作为 fallback。
 */
export interface Logger {
  info(...args: unknown[]): void;
  warn(...args: unknown[]): void;
  error(...args: unknown[]): void;
}
