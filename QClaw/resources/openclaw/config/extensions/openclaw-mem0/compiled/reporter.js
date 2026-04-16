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
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { homedir, platform, hostname } from 'node:os';
import { REPORT_URL, ELECTRON_REPORT_TOKEN, TELEMETRY_CONFIG_FILENAME } from './constants.js';
import { addQclawPrefix } from './util.js';
// ==================== 常量 ====================
/** QClaw 状态目录名 */
const QCLAW_STATE_DIR_NAME = '.qclaw';
/** QClaw 元信息文件名 */
const QCLAW_META_FILE_NAME = 'qclaw.json';
/** 待上报队列最大长度 */
const PENDING_QUEUE_MAX_SIZE = 1000;
/** HTTP 请求超时时间（毫秒） */
const HTTP_TIMEOUT_MS = 5000;
/** 上报间隔（毫秒），队列中有事件时定时刷新 */
const FLUSH_INTERVAL_MS = 3000;
/** 限流：每个时间窗口内最大上报条数 */
const RATE_LIMIT_MAX_TOKENS = 2;
/** 限流：时间窗口大小（毫秒），即 1 秒 */
const RATE_LIMIT_WINDOW_MS = 1000;
/** 共享参数同步间隔（毫秒），3 分钟 */
const SHARED_PARAMS_SYNC_INTERVAL_MS = 3 * 60 * 1000;
/** SDK 版本号（用于上报协议） */
const SDK_VERSION = '1.0.0';
/** 待上报事件队列 */
let pendingQueue = [];
/** 是否正在上报 */
let isFlushing = false;
/** 上报调度定时器 */
let flushTimer = null;
/** 限流：当前时间窗口内已消耗的令牌数 */
let rateLimitTokensUsed = 0;
/** 限流：当前时间窗口的起始时间戳（毫秒） */
let rateLimitWindowStart = 0;
/** 公共参数缓存（通过 setCommonParams 设置） */
let cachedParams = {};
/** 日志接口（initReporter 时注入） */
let logger = console;
/** 是否已启用上报（配置文件 enabled 字段） */
let enabled = true;
/** 是否已调用 initReporter */
let initialized = false;
/** 初始化配置缓存 */
let initConfig = null;
/** 上次 initReporter 的参数缓存（用于 gateway restart 后自恢复） */
let lastInitOptions = null;
/** 共享参数同步定时器 */
let sharedParamsSyncTimer = null;
/** 设备 ID（从共享参数或生成） */
let deviceId = '';
/** Session ID */
let sessionId = '';
/** OpenClaw 版本号（从 api.runtime.version 获取） */
let openclawVersion = '';
/** 插件名称（从配置文件 pluginName 读取，用于上报 page_id） */
let pluginName = '';
// ==================== 工具函数 ====================
/**
 * 生成唯一 ID（简化版 UUID）
 */
function generateId(length = 16) {
    const chars = '0123456789abcdef';
    let result = '';
    for (let i = 0; i < length; i++) {
        result += chars[Math.floor(Math.random() * chars.length)];
    }
    return result;
}
/**
 * 生成 UUID v4 格式的 ID
 */
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}
/**
 * 获取当前时间戳（毫秒）
 */
function now() {
    return Date.now();
}
/**
 * 安全 JSON 序列化
 */
function safeStringify(obj) {
    try {
        return JSON.stringify(obj);
    }
    catch {
        return '{}';
    }
}
/**
 * 从 ~/.qclaw/qclaw.json 读取主进程共享的运行时参数
 */
export function readSharedParams() {
    try {
        const metaPath = join(homedir(), QCLAW_STATE_DIR_NAME, QCLAW_META_FILE_NAME);
        if (!existsSync(metaPath)) {
            return {};
        }
        const raw = readFileSync(metaPath, 'utf-8');
        const meta = JSON.parse(raw);
        if (typeof meta.sharedParams === 'object' && meta.sharedParams !== null) {
            return meta.sharedParams;
        }
        return {};
    }
    catch (err) {
        logger.warn('[claw-plugin-report] 读取共享参数失败:', err);
        return {};
    }
}
/**
 * 从共享参数同步到 cachedParams
 */
export function syncFromSharedParams(forceUpdate = false) {
    const shared = readSharedParams();
    const toSync = {};
    let hasUpdate = false;
    if (shared.sessionId) {
        if (forceUpdate) {
            if (sessionId !== shared.sessionId) {
                sessionId = shared.sessionId;
                hasUpdate = true;
            }
        }
        else if (!sessionId) {
            sessionId = shared.sessionId;
        }
    }
    if (shared.guid && !cachedParams.guid) {
        toSync.guid = shared.guid;
        deviceId = shared.guid;
    }
    if (shared.appVersion && !cachedParams.app_version) {
        toSync.app_version = shared.appVersion;
    }
    if (shared.appChannel && !cachedParams.app_channel) {
        toSync.app_channel = shared.appChannel;
    }
    if (shared.platform && !cachedParams.platform) {
        toSync.platform = shared.platform;
    }
    if (Object.keys(toSync).length > 0) {
        cachedParams = { ...cachedParams, ...toSync };
    }
    return hasUpdate;
}
/**
 * 启动共享参数定时同步
 */
function startSharedParamsSync() {
    if (sharedParamsSyncTimer) {
        return;
    }
    sharedParamsSyncTimer = setInterval(() => {
        try {
            syncFromSharedParams(true);
        }
        catch (err) {
            logger.warn('[claw-plugin-report] 定时同步共享参数失败:', err);
        }
    }, SHARED_PARAMS_SYNC_INTERVAL_MS);
}
/**
 * 停止共享参数定时同步
 */
function stopSharedParamsSync() {
    if (sharedParamsSyncTimer) {
        clearInterval(sharedParamsSyncTimer);
        sharedParamsSyncTimer = null;
    }
}
// ==================== 配置文件加载 ====================
/**
 * 从插件根目录加载 claw-plugin-report.config.json
 */
function loadConfig(configDir) {
    try {
        const configPath = join(configDir, TELEMETRY_CONFIG_FILENAME);
        const raw = readFileSync(configPath, 'utf-8');
        return JSON.parse(raw);
    }
    catch (err) {
        logger.warn('[claw-plugin-report] 加载配置文件失败，将使用默认配置:', err);
        return null;
    }
}
// ==================== HTTP 上报 ====================
/**
 * 构建单条上报数据的 d2 格式（符合伽利略网页上报协议）
 *
 * 关键字段说明：
 * - topic: 必填，项目 token
 * - bean: 用户/设备信息
 * - scheme: 必填，固定值 "v2"
 * - d2: 数据数组（单条上报只包含一个元素）
 *   - fields: 必填，JSON 字符串，必须包含 type 和 level（自定义日志 type 为 "normal"）
 *   - message: 必填，string 数组，在 message 里按需增加想要上报的字段
 *   - timestamp: 上报当前时间戳（毫秒）
 */
function buildReportPayload(event) {
    const osPlatform = platform(); // 操作系统平台，如 win32, darwin, linux
    const currentTimestamp = now();
    // 构建 bean（用户/设备信息）
    const bean = {
        uid: cachedParams.guid || deviceId || generateUUID(),
        // 优先使用 openclawVersion（从 api.runtime.version 获取），fallback 到 cachedParams
        version: openclawVersion || cachedParams.app_version || SDK_VERSION,
        aid: deviceId || generateUUID(),
        env: initConfig?.env || 'production',
        platform: osPlatform, // 操作系统平台，如 win32, darwin, linux
        referer: 'plugin', // 标识来源
        from: '127.0.0.1', // 当前页面URL（插件环境使用本地地址）
        netType: 'unknown', // 网络类型（插件环境无法获取）
        sessionId: sessionId
    };
    // 构建 ext（扩展字段）
    const ext = {
        hostname: hostname(),
        node_version: process.version,
        from: 'plugin',
        sessionId: sessionId
    };
    // 合并参数
    const params = { name: event.name, ...cachedParams, ...event.options };
    const prefixedParams = addQclawPrefix(params);
    // 构建 fields（必须包含 type 和 level）
    // session.id 用于标识会话
    const fieldsObj = {
        type: 'custom_event',
        level: 'info',
        plugin: 'custom',
    };
    // 在 fields 中添加 session（对象格式 { id: sessionId }）
    if (sessionId) {
        fieldsObj.session = { id: sessionId };
    }
    // 构建 message 内容（在 message 里按需增加想要上报的字段）
    // 包含所有业务上报字段
    const messageObj = {
        // 事件代码（对应 event_code）
        event_code: event.name,
        name: event.name,
        // 事件参数（JSON 字符串，对应 event_value）
        event_value: safeStringify(params),
        // 事件时间戳
        timestamp: event.timestamp,
        // 业务字段（带前缀）
        ...prefixedParams,
        // 标识字段
        aegisv2_goto: generateId(16),
    };
    // 插件用 session（放在 message 中）
    if (sessionId) {
        messageObj.sessionId = sessionId;
    }
    // OpenClaw 版本号（从 api.runtime.version 获取）
    if (openclawVersion) {
        messageObj.openclaw_version = openclawVersion;
    }
    // 构建最终 payload（单条上报，d2 只有一个元素）
    const payload = {
        topic: initConfig?.reportToken || ELECTRON_REPORT_TOKEN,
        bean,
        ext: safeStringify(ext),
        scheme: 'v2',
        d2: [{
                fields: safeStringify(fieldsObj),
                message: [safeStringify(messageObj)],
                timestamp: currentTimestamp,
            }],
    };
    return safeStringify(payload);
}
/**
 * 通过 HTTP POST 发送单条上报数据
 */
async function sendReport(event) {
    const payload = buildReportPayload(event);
    const url = initConfig?.hostUrl || REPORT_URL;
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), HTTP_TIMEOUT_MS);
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'text/plain;charset=UTF-8',
            },
            body: payload,
            signal: controller.signal,
        });
        clearTimeout(timeoutId);
        if (response.ok) {
            try {
                const result = await response.json();
                if (result.code === 0) {
                    return true;
                }
                else {
                    logger.warn(`[claw-plugin-report] 上报返回错误，响应: ${safeStringify(result)}`);
                    return false;
                }
            }
            catch {
                // 响应不是 JSON，但 HTTP 状态码是成功的
                return true;
            }
        }
        else {
            logger.warn(`[claw-plugin-report] 上报失败，状态码: ${response.status}`);
            return false;
        }
    }
    catch (err) {
        if (err.name === 'AbortError') {
            logger.warn('[claw-plugin-report] 上报超时');
        }
        else {
            logger.error('[claw-plugin-report] 上报异常:', err);
        }
        return false;
    }
}
/**
 * 尝试获取一个上报令牌（令牌桶限流）
 *
 * 每个时间窗口（RATE_LIMIT_WINDOW_MS）内最多消耗 RATE_LIMIT_MAX_TOKENS 个令牌。
 * 窗口过期后自动重置。
 *
 * @returns 如果获取成功返回 true；如果当前窗口已用完返回 false
 */
function tryAcquireToken() {
    const currentTime = now();
    // 时间窗口已过期，重置令牌桶
    if (currentTime - rateLimitWindowStart >= RATE_LIMIT_WINDOW_MS) {
        rateLimitWindowStart = currentTime;
        rateLimitTokensUsed = 0;
    }
    if (rateLimitTokensUsed < RATE_LIMIT_MAX_TOKENS) {
        rateLimitTokensUsed++;
        return true;
    }
    return false;
}
/**
 * 计算距离当前限流窗口结束还剩多少毫秒
 */
function remainingWindowMs() {
    const elapsed = now() - rateLimitWindowStart;
    return Math.max(RATE_LIMIT_WINDOW_MS - elapsed, 0);
}
/**
 * 刷新待上报队列（逐条发送，受限流控制：每秒最多 2 条）
 */
async function flushQueue() {
    if (isFlushing || pendingQueue.length === 0) {
        return;
    }
    isFlushing = true;
    try {
        while (pendingQueue.length > 0) {
            // 限流检查：当前窗口令牌已用完，等待下一个窗口
            if (!tryAcquireToken()) {
                const waitMs = remainingWindowMs();
                // 等待当前窗口结束后继续
                await new Promise((resolve) => setTimeout(resolve, waitMs + 10));
                continue;
            }
            const event = pendingQueue.shift();
            const success = await sendReport(event);
            if (!success) {
                // 上报失败，将事件放回队列头部（等待重试）
                // 但如果队列已满，则丢弃该事件
                if (pendingQueue.length < PENDING_QUEUE_MAX_SIZE) {
                    pendingQueue.unshift(event);
                }
                // 失败后暂停，等待下次调度重试
                break;
            }
        }
    }
    finally {
        isFlushing = false;
    }
    // 如果还有待上报事件，调度下一次刷新
    if (pendingQueue.length > 0) {
        scheduleFlush();
    }
}
/**
 * 调度队列刷新
 */
function scheduleFlush() {
    if (flushTimer) {
        return;
    }
    flushTimer = setTimeout(() => {
        flushTimer = null;
        void flushQueue();
    }, FLUSH_INTERVAL_MS);
}
// ==================== 初始化 ====================
/**
 * 初始化上报模块
 */
export function initReporter(options) {
    if (options.logger) {
        logger = options.logger;
    }
    // 缓存初始化参数，用于 gateway restart 后自恢复
    lastInitOptions = { ...options };
    logger.info(`[claw-plugin-report] initReporter 开始, configDir=${options.configDir}`);
    // 1. 加载配置文件
    const fileConfig = loadConfig(options.configDir);
    // 2. 合并配置
    const reportToken = options.reportToken ?? fileConfig?.reportToken ?? ELECTRON_REPORT_TOKEN;
    const hostUrl = options.hostUrl ?? fileConfig?.hostUrl ?? REPORT_URL;
    const env = options.env ?? fileConfig?.env ?? 'production';
    enabled = fileConfig?.enabled !== false;
    pluginName = fileConfig?.pluginName ?? '';
    if (!enabled) {
        initialized = true;
        return;
    }
    // 3. 从 ~/.qclaw/qclaw.json 读取共享参数
    syncFromSharedParams();
    // 4. 覆盖 sessionId
    if (options.sessionId) {
        sessionId = options.sessionId;
    }
    // 5. 生成设备 ID（如果没有从共享参数获取）
    if (!deviceId) {
        deviceId = generateUUID();
    }
    // 6. 生成 sessionId（如果没有从共享参数获取）
    if (!sessionId) {
        sessionId = generateUUID();
    }
    // 7. 缓存配置
    initConfig = { reportToken, hostUrl, env };
    initialized = true;
    // 8. 启动定时同步
    startSharedParamsSync();
}
// ==================== 事件上报 ====================
/**
 * 尝试从缓存参数自恢复初始化（应对 gateway in-process restart 导致的模块状态重置）
 * @returns 恢复后是否已初始化
 */
function tryAutoRecover() {
    if (initialized)
        return true;
    if (!lastInitOptions)
        return false;
    logger.info('[claw-plugin-report] 检测到模块未初始化但有缓存参数，尝试自恢复...');
    try {
        initReporter(lastInitOptions);
        return initialized;
    }
    catch (err) {
        logger.warn(`[claw-plugin-report] 自恢复失败: ${String(err)}`);
        return false;
    }
}
/**
 * 上报自定义事件（fire-and-forget）
 */
export function reportEvent(name, options = {}) {
    if (!enabled) {
        return;
    }
    if (!initialized && !tryAutoRecover()) {
        logger.warn('[claw-plugin-report] reportEvent: 模块未初始化');
        return;
    }
    // 加入待上报队列
    if (pendingQueue.length >= PENDING_QUEUE_MAX_SIZE) {
        const dropped = pendingQueue.shift();
        logger.warn(`[claw-plugin-report] 队列已满，丢弃最早事件: ${dropped?.name}`);
    }
    pendingQueue.push({
        name,
        options,
        timestamp: now(),
    });
    // 调度批量刷新
    scheduleFlush();
}
/**
 * 异步上报自定义事件（可 await）
 */
export async function reportEventAsync(name, options = {}) {
    if (!enabled) {
        return;
    }
    if (!initialized && !tryAutoRecover()) {
        return;
    }
    // 直接发送单条事件
    const event = {
        name,
        options,
        timestamp: now(),
    };
    await sendReport(event);
}
// ==================== 公共参数 ====================
/**
 * 设置上报公共参数
 */
export function setCommonParams(params) {
    if (params.guid) {
        deviceId = params.guid;
    }
    if (params.sessionId) {
        sessionId = params.sessionId;
    }
    cachedParams = { ...cachedParams, ...params };
}
/**
 * 设置 OpenClaw 版本号（从 api.runtime.version 获取）
 */
export function setOpenclawVersion(version) {
    openclawVersion = version;
}
/**
 * 获取 OpenClaw 版本号
 */
export function getOpenclawVersion() {
    return openclawVersion;
}
/**
 * 获取插件名称（从配置文件 pluginName 读取）
 */
export function getPluginName() {
    return pluginName;
}
// ==================== 状态查询 ====================
/**
 * 检查上报模块是否已初始化
 */
export function isInitialized() {
    return initialized && enabled;
}
/**
 * 销毁上报模块
 */
export function destroy() {
    stopSharedParamsSync();
    if (flushTimer) {
        clearTimeout(flushTimer);
        flushTimer = null;
    }
    // 尝试发送剩余事件
    if (pendingQueue.length > 0) {
        void flushQueue();
    }
    pendingQueue = [];
    isFlushing = false;
    cachedParams = {};
    enabled = true;
    initialized = false;
    initConfig = null;
    // 注意: lastInitOptions 故意不重置，以支持 gateway restart 后自恢复
    deviceId = '';
    sessionId = '';
    openclawVersion = '';
    pluginName = '';
    rateLimitTokensUsed = 0;
    rateLimitWindowStart = 0;
}
//# sourceMappingURL=reporter.js.map