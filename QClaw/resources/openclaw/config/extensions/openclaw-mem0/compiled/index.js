/**
 * claw-plugin-report — 模块入口
 *
 * 为 OpenClaw 插件提供统一的伽利略上报 API。
 * 采用单例类 `GalileoReport` 封装，外部通过 `GalileoReport.getInstance()` 获取实例。
 *
 * @example
 * ```ts
 * import { GalileoReport, REPORT_CONST } from './claw-plugin-report/index.js';
 *
 * const reporter = GalileoReport.getInstance();
 *
 * // 1. 初始化（在插件 register 阶段调用）
 * reporter.initReport({ configDir: __dirname, logger: api.logger });
 *
 * // 2. 设置 OpenClaw 版本号
 * reporter.setOpenclawVersion(api.runtime?.version ?? '');
 *
 * // 3. 设置公共参数
 * reporter.setCommonParams({ plugin_id: 'openclaw-mem0', mem0_mode: 'cloud' });
 *
 * // 4. 上报事件（fire-and-forget）
 * reporter.reportFunc(REPORT_CONST.CLICK_NEW, { page_id: 'openclaw-mem0', action: 'plugin_registered' });
 *
 * // 5. 异步上报（可 await）
 * await reporter.reportFuncAsync(REPORT_CONST.SUBMIT, { page_id: 'openclaw-mem0', action: 'checkpoint' });
 *
 * // 6. 获取插件名称（用于上报 page_id）
 * const pluginName = reporter.getPluginName();
 *
 * // 7. 销毁（插件卸载时调用）
 * reporter.destroy();
 * ```
 */
import { initReporter, reportEvent, reportEventAsync, setCommonParams as setReporterCommonParams, setOpenclawVersion as setReporterOpenclawVersion, getPluginName as getReporterPluginName, isInitialized as getReporterInitialized, destroy as destroyReporter, readSharedParams as readReporterSharedParams, syncFromSharedParams as syncReporterFromSharedParams, } from './reporter.js';
// ==================== 单例类 ====================
/**
 * GalileoReport — 伽利略上报单例
 *
 * 封装所有上报 API，通过 `GalileoReport.getInstance()` 获取全局唯一实例。
 *
 * @example
 * ```ts
 * const reporter = GalileoReport.getInstance();
 * reporter.initReport({ configDir: __dirname, logger: api.logger });
 * reporter.reportFunc(REPORT_CONST.CLICK_NEW, { action: 'test' });
 * ```
 */
export class GalileoReport {
    /** 单例实例 */
    static instance = null;
    /** 私有构造函数，禁止外部 new */
    constructor() { }
    /**
     * 获取 GalileoReport 全局唯一实例
     */
    static getInstance() {
        if (!GalileoReport.instance) {
            GalileoReport.instance = new GalileoReport();
        }
        return GalileoReport.instance;
    }
    /**
     * 初始化全局上报实例
     *
     * 在插件 register 阶段调用一次。如果不调用，后续 reportFunc 将静默跳过（不抛异常）。
     * 上报采用纯 HTTP POST 方式，符合伽利略网页上报协议。
     *
     * @param options - 初始化选项
     */
    initReport(options) {
        initReporter(options);
    }
    /**
     * 上报事件（fire-and-forget）
     *
     * 对应 packages/report 的 reportFunc。
     * 如果 initReport 未调用，静默返回，不抛异常。
     *
     * @param name - 事件名称（建议使用 REPORT_CONST 中的常量）
     * @param options - 事件参数
     */
    reportFunc(name, options = {}) {
        if (!name) {
            console.warn('[claw-plugin-report] 事件名称不能为空');
            return;
        }
        reportEvent(name, options);
    }
    /**
     * 异步上报事件（可 await）
     *
     * 对应 packages/report 的 reportFuncAsync。
     * 如果 initReport 未调用，静默返回，不抛异常。
     *
     * @param name - 事件名称
     * @param options - 事件参数
     */
    async reportFuncAsync(name, options = {}) {
        if (!name) {
            console.warn('[claw-plugin-report] 事件名称不能为空');
            return;
        }
        await reportEventAsync(name, options);
    }
    /**
     * 设置上报公共参数
     *
     * 设置后每次 reportFunc 自动携带这些参数。
     * 常见参数：guid, app_version, platform, app_channel, plugin_id
     *
     * @param params - 公共参数
     */
    setCommonParams(params) {
        setReporterCommonParams(params);
    }
    /**
     * 设置 OpenClaw 版本号（从 api.runtime.version 获取）
     *
     * 在插件 register 阶段调用，从 api.runtime.version 获取版本信息。
     * 设置后 bean.version 和 message.openclaw_version 将使用此值。
     *
     * @param version - OpenClaw 版本号
     */
    setOpenclawVersion(version) {
        setReporterOpenclawVersion(version);
    }
    /**
     * 获取插件名称（从配置文件 pluginName 读取，用于上报 page_id）
     */
    getPluginName() {
        return getReporterPluginName();
    }
    /**
     * 检查上报模块是否已初始化
     */
    isInitialized() {
        return getReporterInitialized();
    }
    /**
     * 销毁上报模块实例（插件卸载时调用）
     */
    destroy() {
        destroyReporter();
    }
    /**
     * 从 ~/.qclaw/qclaw.json 读取主进程共享的运行时参数
     */
    readSharedParams() {
        return readReporterSharedParams();
    }
    /**
     * 从共享参数同步到 SDK 内部缓存
     */
    syncFromSharedParams(forceUpdate = false) {
        return syncReporterFromSharedParams(forceUpdate);
    }
}
// ==================== 常量导出 ====================
export { REPORT_CONST, DEFAULT_APPKEY, REPORT_URL, ELECTRON_REPORT_TOKEN } from './constants.js';
// ==================== 工具函数导出 ====================
export { addQclawPrefix, getDevicePlatform } from './util.js';
//# sourceMappingURL=index.js.map