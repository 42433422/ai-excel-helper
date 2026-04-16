/**
 * 电脑管家 AI 安全插件 (PCMgr AI Security Plugin)
 *
 * 提供 Prompt 安全检测、工具调用审计、Skill 加载审计和脚本写入审计能力。
 */

import path from "node:path";
import pkg from "./package.json";

import { LLMShieldClient, ContentType } from "./src/client";
import { setEndpointEnv, getEndpointEnv, getModerateUrl, type EndpointEnv } from "./src/endpoints";
import { getDeviceFingerprint } from "./src/utils";
import { MessageCache } from "./src/cache";
import { setSecurityConfig, getDeviceFingerprintValue } from "./src/security";
import { setupFetchInterceptor } from "./src/interceptor";
import { registerBeforeToolCall, registerAfterToolCall } from "./src/hooks";
import { LOG_TAG } from "./src/constants";
import { fileLog } from "./src/logger";
import { initSwitches, getSwitches, updateSwitches, pullRemoteConfig } from "./src/runtime-config";

export { LOG_TAG };

/** 从 pluginConfig 中解析各项开关和配置 */
function parsePluginConfig(api: any) {
  const pluginCfg = api.pluginConfig ?? {};
  const { appId } = pluginCfg;

  const logRecord = pluginCfg.logRecord !== undefined ? Boolean(pluginCfg.logRecord) : false;
  // 审计开关默认全开，运行时由 HTTP 配置下发接口 (GET /api/plugin-config) 覆盖
  const enablePromptAudit = true;
  const enableSkillAudit = true;
  const enableScriptAudit = true;

  let stateDir: string;
  if (pluginCfg.stateDir !== undefined) {
    stateDir = pluginCfg.stateDir;
  } else {
    stateDir = api.runtime.state.resolveStateDir();
    api.logger.debug(`[${LOG_TAG}] stateDir: ${stateDir}`);
  }

  const auditReportUrl = typeof pluginCfg.auditReportUrl === "string" ? pluginCfg.auditReportUrl : "";

  // 从环境变量获取 AES 加密后的用户 token（由 Electron 主进程 createCleanEnv() 加密后注入）
  const userToken = process.env.QCLAW_USER_TOKEN_ENCRYPTED ?? "";

  return {
    appId, stateDir, logRecord, userToken,
    enablePromptAudit, enableSkillAudit, enableScriptAudit,
    auditReportUrl,
    pluginCfg,
  };
}

/** 验证端点可用性（发一次测试请求） */
async function verifyEndpoint(api: any, client: LLMShieldClient, appId: string): Promise<boolean> {
  const url = getModerateUrl();
  const env = getEndpointEnv();
  api.logger.debug(`[${LOG_TAG}] Verifying endpoint: ${url}`);
  fileLog(`[verifyEndpoint] start | env=${env} | url=${url} | appId=${appId}`);
  try {
    await client.moderate(
      {
        Message: {
          Role: "user",
          MultiPart: [{ Content: "hello", ContentType: ContentType.TEXT }],
        },
        Scene: appId,
      },
      { "X-Device-Fingerprint": getDeviceFingerprintValue() }
    );
    fileLog(`[verifyEndpoint] success`);
    return true;
  } catch (e: any) {
    const detail = [
      `[verifyEndpoint] FAILED`,
      `  url: ${url}`,
      `  env: ${env}`,
      `  appId: ${appId}`,
      `  error.name: ${e.name}`,
      `  error.message: ${e.message}`,
      `  error.cause: ${e.cause?.message ?? "N/A"}`,
      `  error.status: ${e.status ?? "N/A"}`,
      `  error.body: ${typeof e.body === "string" ? e.body : JSON.stringify(e.body ?? null)}`,
      `  stack: ${e.stack}`,
    ].join("\n");
    fileLog(detail);
    api.logger.error(
      `[${LOG_TAG}] Registration failed: Verification failed for endpoint ${url}. Please check your network, apiKey, or appId configuration. Error: ${e.message || e}`
    );
    return false;
  }
}

/**
 * 防重入标记：OpenClaw 运行时在 gateway 启动过程中可能因 cacheKey 差异
 * 多次调用 loadOpenClawPlugins → register()，导致 fetch 拦截器、event hook
 * 等副作用被重复注册。此标记确保这些一次性副作用只执行一次。
 *
 * 注意：HTTP 路由注册不受此标记保护，因为 OpenClaw 只有在 gateway 阶段
 * （第二次 register() 调用）注册的路由才会被 HTTP 服务器识别。
 */
let _sideEffectsDone = false;

/** 缓存 LLMShieldClient 实例，供 HTTP route handler 跨 register() 调用复用 */
let _client: LLMShieldClient | null = null;

const plugin = {
  id: "pcmgr-ai-security",
  name: pkg.name,
  description:
    "电脑管家 AI 安全插件 - 提供 Prompt 安全检测、工具调用审计、Skill 加载审计和脚本写入审计能力。",

  register(api: any) {
    // ================================================================
    // Phase 1: HTTP 路由注册（每次 register 都执行）
    //
    // OpenClaw 会调用 register() 两次（插件加载 + gateway 启动），
    // 只有 gateway 阶段注册的路由才会被 HTTP 服务器识别，
    // 因此 HTTP 路由注册不能被防重入标记跳过。
    // ================================================================
    api.logger.debug(`[${LOG_TAG}] register() — registering HTTP routes (sideEffectsDone=${_sideEffectsDone})`);

    // --- 注册动态配置 HTTP endpoint ---
    api.registerHttpRoute({
      path: "/plugins/pcmgr-ai-security/config",
      auth: "gateway",
      match: "exact",
      handler: async (req: any, res: any) => {
        if (req.method === "GET") {
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify(getSwitches()));
          return true;
        }

        if (req.method === "POST" || req.method === "PUT") {
          const chunks: Buffer[] = [];
          for await (const chunk of req) chunks.push(chunk as Buffer);
          const body = JSON.parse(Buffer.concat(chunks).toString("utf-8"));
          const updated = updateSwitches(body);
          fileLog(`[config] switches updated: ${JSON.stringify(updated)}`);
          api.logger.info(`[${LOG_TAG}] Config updated: ${JSON.stringify(updated)}`);
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ success: true, config: updated }));
          return true;
        }

        res.writeHead(405);
        res.end("Method Not Allowed");
        return true;
      },
    });

    // --- 注册 token 动态更新 HTTP endpoint ---
    // 解决时序问题：OpenClaw 进程启动时用户可能尚未登录，环境变量中无 token；
    // 登录成功后，Electron 主进程通过此端点将加密 token 推送给插件。
    api.registerHttpRoute({
      path: "/plugins/pcmgr-ai-security/token",
      auth: "gateway",
      match: "exact",
      handler: async (req: any, res: any) => {
        if (req.method === "POST" || req.method === "PUT") {
          const chunks: Buffer[] = [];
          for await (const chunk of req) chunks.push(chunk as Buffer);
          try {
            const body = JSON.parse(Buffer.concat(chunks).toString("utf-8"));
            const newToken = typeof body.encryptedUserToken === "string" ? body.encryptedUserToken : "";
            if (newToken && _client) {
              _client.setEncryptedUserToken(newToken);
              fileLog(`[token] encrypted user token updated (length=${newToken.length})`);
              api.logger.info(`[${LOG_TAG}] Encrypted user token updated dynamically.`);
              res.writeHead(200, { "Content-Type": "application/json" });
              res.end(JSON.stringify({ success: true }));
            } else {
              res.writeHead(400, { "Content-Type": "application/json" });
              res.end(JSON.stringify({ success: false, error: newToken ? "client not initialized" : "encryptedUserToken is required" }));
            }
          } catch (e: any) {
            fileLog(`[token] parse error: ${e.message}`);
            res.writeHead(400, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ success: false, error: `Invalid JSON: ${e.message}` }));
          }
          return true;
        }

        res.writeHead(405);
        res.end("Method Not Allowed");
        return true;
      },
    });

    // ================================================================
    // Phase 2: 一次性副作用（仅首次 register 执行）
    //
    // FetchInterceptor、Hook、Client 创建等只需要执行一次，
    // 重复执行会导致拦截器和 Hook 被多次注册。
    // ================================================================
    if (_sideEffectsDone) {
      api.logger.info(`[${LOG_TAG}] register() called again — HTTP routes re-registered, skipping side effects.`);
      fileLog(`[register] duplicate call — routes re-registered, side effects skipped`);
      return;
    }
    _sideEffectsDone = true;

    api.logger.debug(`[${LOG_TAG}] register()`);

    const config = parsePluginConfig(api);
    const {
      appId, stateDir, logRecord, userToken,
      enablePromptAudit, enableSkillAudit, enableScriptAudit,
      auditReportUrl, pluginCfg,
    } = config;

    // --- 环境切换 ---
    if (pluginCfg.env) {
      const env = pluginCfg.env as EndpointEnv;
      setEndpointEnv(env);
      api.logger.info(`[${LOG_TAG}] Endpoint environment set to "${env}".`);
    } else {
      api.logger.debug(`[${LOG_TAG}] Using default endpoint environment: "${getEndpointEnv()}".`);
    }

    fileLog(`[register] start | version=${pkg.version}`);
    fileLog(`[register] config: appId=${appId} env=${pluginCfg.env ?? "(default)"} userToken=${userToken ? "(set)" : "(empty)"}`);
    fileLog(`[register] flags: promptAudit=${enablePromptAudit} skillAudit=${enableSkillAudit} scriptAudit=${enableScriptAudit} logRecord=${logRecord}`);

    // --- 初始化运行时开关 ---
    initSwitches({ enablePromptAudit, enableSkillAudit, enableScriptAudit, auditReportUrl });

    // --- Security & cache setup ---
    setSecurityConfig({ deviceFingerprint: getDeviceFingerprint() });

    const messageCachePath = path.join(stateDir, "pcmgr-ai-security_cache.json");
    const messageCache = new MessageCache(messageCachePath, api.logger, LOG_TAG);

    setSecurityConfig({
      failureThreshold: pluginCfg.failureThreshold !== undefined ? Number(pluginCfg.failureThreshold) : undefined,
      cooldownMs: pluginCfg.cooldownSeconds !== undefined ? Number(pluginCfg.cooldownSeconds) * 1000 : undefined,
    });

    const client = new LLMShieldClient({
      gid: getDeviceFingerprintValue(),
      timeoutMs: pluginCfg.timeoutMs ? Number(pluginCfg.timeoutMs) : undefined,
      encryptedUserToken: userToken,
    });
    _client = client; // 缓存供 HTTP route handler 使用

    // --- Async initialization ---
    (async () => {
      // 启动时拉取远程配置（此时 fetch 尚未被劫持）
      await pullRemoteConfig();
      fileLog(`[register] effective config after pull: ${JSON.stringify(getSwitches())}`);

      // 始终注册 interceptor（开关判断移入内部）
      setupFetchInterceptor({ api, client, sceneId: appId, enableLogging: logRecord, messageCache, modes: ["security", "audit"] });

      // 始终注册 hooks（开关判断移入内部）
      registerBeforeToolCall({ api, client, appId, stateDir, logRecord });
      registerAfterToolCall({ api, client, appId, stateDir, logRecord });

      api.logger.info(
        `[${LOG_TAG}] Plugin initialized (promptAudit:${getSwitches().enablePromptAudit}, skillAudit:${getSwitches().enableSkillAudit}, scriptAudit:${getSwitches().enableScriptAudit}).`
      );
    })();
  },
};

export default plugin;
