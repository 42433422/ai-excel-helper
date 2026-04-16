/**
 * claw-plugin-report — 公共常量
 *
 * 上报事件代码、默认 AppKey、默认上报地址等。
 * 与 packages/report/src/constants.ts 和 galileo/constants.ts 保持一致。
 */
/** 伽利略默认上报地址 */
export declare const REPORT_URL = "https://galileotelemetry.tencent.com/collect";
/** Electron 端使用的伽利略上报 Token（与主进程一致） */
export declare const ELECTRON_REPORT_TOKEN = "SDK-034b2f6d3e5cabfdd8eb";
/** 默认 AppKey（上报参数前缀） */
export declare const DEFAULT_APPKEY = "PC_Qclaw";
/** 上报事件常量（与 Electron 主进程 packages/report 一致） */
export declare const REPORT_CONST: {
    /** 点击事件 */
    readonly CLICK_NEW: "click_new";
    /** 曝光事件 */
    readonly EXPO: "expo";
    /** 提交事件（如更新下载执行等） */
    readonly SUBMIT: "submit";
    /** 资源监控事件（CPU/内存/磁盘IO 定时采集上报） */
    readonly RESOURCE_MONITOR: "resource_monitor";
    /** Crash 事件（崩溃信息上报） */
    readonly CRASH_EVENT: "crash_event";
    /** 交互事件（交互响应耗时上报） */
    readonly INTERACTION_EVENT: "interaction_event";
    /** 卡顿事件（帧率/掉帧/卡顿检测上报） */
    readonly JANK_EVENT: "jank_event";
    /** 插件事件 */
    readonly PLUGIN: "plugin";
};
export type ReportConstType = (typeof REPORT_CONST)[keyof typeof REPORT_CONST];
/** 上报配置文件名 */
export declare const TELEMETRY_CONFIG_FILENAME = "claw-plugin-report.config.json";
