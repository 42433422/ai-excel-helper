/**
 * Prompt 优化器插件 (prompt-optimizer)
 *
 * 通过劫持全局 fetch，拦截发往 LLM 的请求：
 *   - ordered_system_prompt: 从请求体的 system prompt 中按 section 名称提取并重新排列
 *   - inject_user_query: 从请求体的 system prompt 中提取指定 section 注入到 user query 前
 *   - inject_user_query_suffix: 在 inject_user_query 之后、真实 user query 之前插入自定义文本
 *
 * section 的识别规则：system prompt 中所有以 "## " 开头的行即为 section 标题，
 * 无需任何外部文件，完全从请求体中动态解析。
 *
 * 配置文件：插件目录下的 prompt-optimizer.config.json
 */

import fs from "node:fs";
import path from "node:path";

const LOG_TAG = "prompt-optimizer";

/** 用于标记已处理过的请求体，防止 fetch 被多次拦截导致重复注入 */
const PROCESSED_MARKER = "__prompt_optimizer_processed__";

const PLUGIN_DIR = __dirname;
const CONFIG_FILE = path.join(PLUGIN_DIR, "prompt-optimizer.config.json");

interface Config {
  /** 在 system prompt 最前面插入的自定义文本 */
  system_prompt_prefix?: string;
  /** 按 section 名称列表从请求的 system prompt 中提取并重新排列，顺序即最终顺序 */
  ordered_system_prompt?: string[];
  /** 按 section 名称列表从请求的 system prompt 中提取，注入到最后一条 user query 前面 */
  inject_user_query?: string[];
  /** 在 inject_user_query 之后、真实 user query 之前插入的自定义文本 */
  inject_user_query_suffix?: string;
  /** 是否启用动态路径替换（默认 true）：自动检测 system prompt 中的绝对路径并替换为占位符 */
  enable_path_replacements?: boolean;
}

/** section 名称 -> 内容（含标题行） */
type SectionMap = Map<string, string>;

/** 从配置文件读取配置，读取失败时返回空配置 */
function loadConfig(logger: any): Config {
  try {
    const raw = fs.readFileSync(CONFIG_FILE, "utf-8");
    return JSON.parse(raw) as Config;
  } catch (e) {
    logger.warn(`[${LOG_TAG}] 读取配置文件失败，使用空配置: ${e}`);
    return {};
  }
}

/**
 * 直接从给定文本（请求体中的 system prompt）中扫描所有 "## " 标题，
 * 动态切分出各 section，返回 Map<sectionName, content>。
 * content 包含标题行本身及其后续内容，直到下一个 ## 标题或文本结束。
 */
function extractSections(text: string): SectionMap {
  const map: SectionMap = new Map();
  if (!text) return map;

  const lines = text.split("\n");
  let currentKey: string | null = null;
  let currentLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("## ")) {
      // 遇到新的 ## 标题，保存上一个 section
      if (currentKey !== null) {
        map.set(currentKey, currentLines.join("\n"));
      }
      currentKey = line.slice(3).trim();
      currentLines = [line];
    } else {
      if (currentKey !== null) {
        currentLines.push(line);
      }
      // ## 之前的内容（preamble）直接忽略
    }
  }
  // 保存最后一个 section
  if (currentKey !== null) {
    map.set(currentKey, currentLines.join("\n"));
  }

  // 对路径形式的 section 标题，额外用文件名（basename）作为别名存入 map，
  // 这样配置文件中可以只写 "HEARTBEAT.md" 而非 "/Users/xxx/.qclaw/workspace/HEARTBEAT.md"，
  // 实现跨平台兼容（换电脑后路径不同也不影响）。
  // 注意：如果多个路径 section 有相同的 basename，后者会覆盖前者（实际场景中不太可能冲突）。
  for (const [key, value] of map) {
    if (key.includes("/") || key.includes("\\")) {
      const basename = key.split(/[\/\\]/).pop();
      if (basename && !map.has(basename)) {
        map.set(basename, value);
      }
    }
  }

  return map;
}

/**
 * 将路径中的反斜杠统一归一化为正斜杠，用于跨平台路径比较和前缀统计。
 */
function normalizeSeparator(p: string): string {
  return p.replace(/\\/g, "/");
}

/**
 * 从 system prompt 文本中动态检测所有绝对路径，自动归类并生成占位符映射表。
 * 跨平台兼容：同时支持 Unix 路径（/xxx/yyy）和 Windows 路径（C:\xxx\yyy 或 C:/xxx/yyy）。
 *
 * 检测规则：
 * 1. 匹配所有以 / 开头的路径（Unix 绝对路径）
 * 2. 匹配 ~/.xxx 形式的 home 目录相对路径
 * 3. 匹配 C:\xxx 或 C:/xxx 形式的 Windows 绝对路径
 * 4. 提取路径的目录前缀，按出现频次和语义自动归类
 *
 * 返回的映射表中，占位符对应的值始终使用**原始文本中出现的路径形式**（保留原始分隔符），
 * 以确保 applyPathReplacements 能精确匹配并替换。
 *
 * 返回 Record<占位符, 绝对路径>，如 { "{skill_root_dir}": "/Applications/.../skills" }
 */
function detectPathReplacements(text: string): Record<string, string> {
  if (!text) return {};

  // 收集所有绝对路径（原始形式 + 归一化形式）
  // Unix 绝对路径: /xxx/yyy
  const unixPathRegex = /(?:\/[\w@.\-]+){2,}/g;
  // home 目录相对路径: ~/.xxx/yyy
  const tildePathRegex = /~\/\.?[\w@.\-]+(?:\/[\w@.\-]+)*/g;
  // Windows 绝对路径: C:\xxx\yyy 或 C:/xxx/yyy（盘符+冒号+分隔符开头）
  const winPathRegex = /[A-Za-z]:[\\|/][\w@.\-\\/ ]+/g;

  // rawPaths: 原始路径文本, normalizedPaths: 归一化后路径（统一用 /）
  const rawPaths: string[] = [];

  let m: RegExpExecArray | null;
  while ((m = unixPathRegex.exec(text)) !== null) {
    rawPaths.push(m[0]);
  }
  while ((m = tildePathRegex.exec(text)) !== null) {
    rawPaths.push(m[0]);
  }
  while ((m = winPathRegex.exec(text)) !== null) {
    // 去除尾部空格（Windows 路径正则可能捕获尾部空格）
    rawPaths.push(m[0].trimEnd());
  }

  if (rawPaths.length === 0) return {};

  // 归一化后做前缀频次统计（统一使用 / 分隔符）
  const prefixCount = new Map<string, number>();
  for (const p of rawPaths) {
    const normalized = normalizeSeparator(p);
    const parts = normalized.split("/");
    // 逐级累加前缀
    for (let depth = 2; depth <= parts.length; depth++) {
      const prefix = parts.slice(0, depth).join("/");
      prefixCount.set(prefix, (prefixCount.get(prefix) || 0) + 1);
    }
  }

  // 已知路径模式规则（按优先级排序）
  // 使用 [/\\] 同时匹配正斜杠和反斜杠，兼容 Unix 和 Windows
  // 注意：prefixCount 中的 key 已经归一化为 /，所以这里只需匹配 /
  const knownPatterns: Array<{ test: RegExp; placeholder: string; priority: number }> = [
    // 按路径长度从长到短排列，确保最精确的匹配优先
    { test: /\/node_modules\/[^/]+\/skills$/, placeholder: "{skill_node_modules_dir}", priority: 10 },
    { test: /\/node_modules\/[^/]+\/docs$/, placeholder: "{docs_root_dir}", priority: 10 },
    { test: /\/config\/skills$/, placeholder: "{skill_root_dir}", priority: 10 },
    { test: /\.qclaw\/workspace$/, placeholder: "{workspace_root_dir}", priority: 10 },
    { test: /~\/.agents\/skills$/, placeholder: "{user_skill_dir}", priority: 10 },
  ];

  const replacements: Record<string, string> = {};
  const usedPrefixes = new Set<string>();

  // 优先用已知模式匹配（prefixCount 中的 key 已归一化为 /）
  for (const { test, placeholder } of knownPatterns) {
    for (const [normalizedPrefix] of prefixCount) {
      if (test.test(normalizedPrefix) && !usedPrefixes.has(normalizedPrefix)) {
        // 需要找到原始文本中实际出现的路径形式，用于后续替换
        // 从 rawPaths 中找到包含该归一化前缀的原始路径，提取其原始前缀
        const originalPrefix = findOriginalPrefix(rawPaths, normalizedPrefix);
        replacements[placeholder] = originalPrefix;
        usedPrefixes.add(normalizedPrefix);
        break;
      }
    }
  }

  return replacements;
}

/**
 * 从原始路径列表中，找到与归一化前缀匹配的原始路径前缀。
 * 返回原始文本中使用的分隔符形式，确保 applyPathReplacements 能精确匹配。
 */
function findOriginalPrefix(rawPaths: string[], normalizedPrefix: string): string {
  for (const rawPath of rawPaths) {
    const normalized = normalizeSeparator(rawPath);
    if (normalized.startsWith(normalizedPrefix)) {
      // 从原始路径中截取与归一化前缀等长的部分
      return rawPath.substring(0, normalizedPrefix.length);
    }
  }
  // fallback: 直接返回归一化前缀（不太可能走到这里）
  return normalizedPrefix;
}

/**
 * 将文本中的绝对路径替换为占位符（正向替换）。
 * 替换时按绝对路径长度从长到短排序，避免短路径误匹配长路径的前缀。
 *
 * 跨平台兼容：对于每个绝对路径，同时尝试替换原始形式和反转分隔符的形式，
 * 以处理 system prompt 中可能混合出现 / 和 \ 的情况。
 */
function applyPathReplacements(text: string, replacements: Record<string, string>): string {
  if (!text || !replacements || Object.keys(replacements).length === 0) return text;
  // 按绝对路径长度降序排列，确保长路径优先替换
  const entries = Object.entries(replacements).sort((a, b) => b[1].length - a[1].length);
  let result = text;
  for (const [placeholder, absolutePath] of entries) {
    // 替换原始形式
    result = result.split(absolutePath).join(placeholder);

    // 同时替换反转分隔符的形式（处理混合分隔符的情况）
    // 例如原始是 C:\Users\...，同时替换 C:/Users/... 形式；反之亦然
    const flipped = absolutePath.includes("\\")
      ? absolutePath.replace(/\\/g, "/")
      : absolutePath.replace(/\//g, "\\");
    if (flipped !== absolutePath) {
      result = result.split(flipped).join(placeholder);
    }
  }
  return result;
}

/**
 * 构建路径映射表文本块，追加到 inject_user_query 中。
 * 格式: {placeholder} = absolute_path
 */
function buildPathMappingBlock(replacements: Record<string, string>): string {
  const lines = Object.entries(replacements).map(
    ([placeholder, absolutePath]) => `${placeholder} = ${absolutePath}`
  );
  return (
    `\n**Path Variable Mappings**: The system prompt uses path placeholders (e.g. {skill_root_dir}, {workspace_root_dir}) ` +
    `for caching optimization. When you need to resolve actual file paths — such as reading skill files, ` +
    `listing directories, or referencing workspace files — replace these placeholders with their real absolute paths below:\n` +
    lines.join("\n")
  );
}

/**
 * 根据 section 名称列表，从 sectionMap 中按顺序拼接内容。
 * 找不到的 section 会打印警告并跳过。
 */
function buildContent(names: string[], sectionMap: SectionMap, logger: any): string {
  const parts: string[] = [];
  for (const name of names) {
    if (sectionMap.has(name)) {
      parts.push(sectionMap.get(name)!.trim());
    } else {
      logger.warn(`[${LOG_TAG}] 在请求的 system prompt 中找不到 section: "${name}"，已跳过`);
    }
  }
  return parts.join("\n\n");
}

function setupFetchInterceptor(api: any) {
  const originalFetch = (globalThis as any).fetch;

  (globalThis as any).fetch = async function (this: any, ...args: Parameters<typeof fetch>) {
    const options: RequestInit = (args[1] as RequestInit) || {};

    // 只处理有 body 的请求
    if (!options.body) {
      return originalFetch.apply(this, args);
    }

    // 解析请求体
    let rawBody: string | undefined;
    if (typeof options.body === "string") {
      rawBody = options.body;
    } else if (options.body instanceof Uint8Array || options.body instanceof ArrayBuffer) {
      rawBody = new TextDecoder().decode(options.body);
    }

    if (!rawBody) return originalFetch.apply(this, args);

    let jsonBody: any;
    try {
      jsonBody = JSON.parse(rawBody);
    } catch {
      return originalFetch.apply(this, args);
    }

    // 只处理 OpenAI 格式（含 messages 数组）的请求
    if (!jsonBody || !Array.isArray(jsonBody.messages)) {
      return originalFetch.apply(this, args);
    }

    // 防重入：如果已经处理过，直接放行
    if (jsonBody[PROCESSED_MARKER]) {
      return originalFetch.apply(this, args);
    }

    // 每次请求时重新读取配置文件，支持热更新
    const config = loadConfig(api.logger);
    const hasSystemPrefix = !!config.system_prompt_prefix;
    const hasSystemConfig = config.ordered_system_prompt && config.ordered_system_prompt.length > 0;
    const hasUserConfig = config.inject_user_query && config.inject_user_query.length > 0;
    const hasUserSuffix = !!config.inject_user_query_suffix;

    if (!hasSystemPrefix && !hasSystemConfig && !hasUserConfig && !hasUserSuffix) {
      return originalFetch.apply(this, args);
    }

    const messages: any[] = jsonBody.messages;

    // 找到请求体中的 system prompt 内容
    let systemContent = "";
    let systemIndex = -1;
    for (let i = 0; i < messages.length; i++) {
      if (messages[i].role === "system") {
        systemContent = typeof messages[i].content === "string" ? messages[i].content : "";
        systemIndex = i;
        break;
      }
    }

    // 直接从请求体的 system prompt 中动态提取所有 section
    const sectionMap = extractSections(systemContent);
    api.logger.info(`[${LOG_TAG}] 从请求 system prompt 中动态识别到 ${sectionMap.size} 个 section`);

    let changed = false;

    // 动态检测路径替换（默认启用）
    const enablePathReplacements = config.enable_path_replacements !== false;
    const dynamicReplacements = enablePathReplacements ? detectPathReplacements(systemContent) : {};
    const hasPathReplacements = Object.keys(dynamicReplacements).length > 0;
    if (hasPathReplacements) {
      api.logger.info(
        `[${LOG_TAG}] 动态检测到 ${Object.keys(dynamicReplacements).length} 条路径替换规则: ` +
        Object.entries(dynamicReplacements).map(([k, v]) => `${k}=${v}`).join(", ")
      );
    }

    // ── 按 ordered_system_prompt 列表重组 system prompt ──
    if (hasSystemConfig || hasSystemPrefix) {
      const prefix = hasSystemPrefix ? config.system_prompt_prefix!.trim() : "";
      let body = hasSystemConfig
        ? buildContent(config.ordered_system_prompt!, sectionMap, api.logger)
        : systemContent;

      // 对 system prompt 内容执行动态路径替换（绝对路径 → 占位符）
      if (hasPathReplacements) {
        body = applyPathReplacements(body, dynamicReplacements);
        api.logger.info(`[${LOG_TAG}] 已对 system prompt 执行路径替换，共 ${Object.keys(dynamicReplacements).length} 条规则`);
      }

      const newSystemContent = prefix && body ? `${prefix}\n\n${body}` : prefix || body;
      if (systemIndex >= 0) {
        messages[systemIndex] = { ...messages[systemIndex], content: newSystemContent };
        changed = true;
        api.logger.info(
          `[${LOG_TAG}] system prompt 已重组，原长度=${systemContent.length}，新长度=${newSystemContent.length}，` +
          `hasSystemPrefix=${hasSystemPrefix}，使用 ${config.ordered_system_prompt?.length ?? 0} 个 section`
        );
      } else if (newSystemContent) {
        messages.unshift({ role: "system", content: newSystemContent });
        changed = true;
        api.logger.info(`[${LOG_TAG}] 已插入新的 system prompt，长度=${newSystemContent.length}`);
      }
    }

    // ── 按 inject_user_query + inject_user_query_suffix 注入到最后一条 user query 前面 ──
    if (hasUserConfig || hasUserSuffix) {
      let injection = hasUserConfig ? buildContent(config.inject_user_query!, sectionMap, api.logger) : "";

      // 在 inject_user_query 内容末尾追加路径映射表（因为 Runtime 等动态 section 在这里，LLM 需要知道真实路径）
      if (injection && hasPathReplacements) {
        injection = injection + "\n" + buildPathMappingBlock(dynamicReplacements);
      }
      const suffix = hasUserSuffix ? config.inject_user_query_suffix!.trim() : "";

      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i].role === "user") {
          const rawContent = messages[i].content;
          const contentType = typeof rawContent;
          const isArray = Array.isArray(rawContent);

          // 提取原始文本：兼容字符串和数组两种格式
          let original = "";
          if (typeof rawContent === "string") {
            original = rawContent;
          } else if (isArray) {
            // OpenAI 多模态格式：[{type:"text", text:"..."}, ...]
            // 找到最后一个 type=text 的项作为原始 query
            const textItem = [...rawContent].reverse().find((item: any) => item?.type === "text");
            original = textItem?.text ?? "";
          }


          const parts: string[] = [];
          if (injection) parts.push(injection);
          if (suffix) parts.push(suffix);
          parts.push(original);
          const newContent = parts.join("\n\n");

          // 根据原始 content 类型决定如何写回
          if (isArray) {
            // 数组格式：找到最后一个 type=text 的项并替换其 text
            const newContentArray = [...rawContent];
            let replaced = false;
            for (let j = newContentArray.length - 1; j >= 0; j--) {
              if (newContentArray[j]?.type === "text") {
                newContentArray[j] = { ...newContentArray[j], text: newContent };
                replaced = true;
                break;
              }
            }
            if (!replaced) {
              // 没有 text 项，在最前面插入
              newContentArray.unshift({ type: "text", text: newContent });
            }
            messages[i] = { ...messages[i], content: newContentArray };
          } else {
            messages[i] = { ...messages[i], content: newContent };
          }

          changed = true;
          api.logger.info(
            `[${LOG_TAG}] user query 已注入内容，inject_user_query=${injection.length > 0}，` +
            `inject_user_query_suffix=${suffix.length > 0}，contentType=${contentType}，isArray=${isArray}`
          );
          break;
        }
      }
    }

    if (changed) {
      // 打上已处理标记，防止重入时重复注入
      jsonBody[PROCESSED_MARKER] = true;
      (options as any).body = JSON.stringify(jsonBody);

    }

    return originalFetch.apply(this, [args[0], options]);
  };

  api.logger.info(`[${LOG_TAG}] fetch 拦截器已安装，配置文件=${CONFIG_FILE}`);
}

const plugin = {
  id: "prompt-optimizer",
  name: "Prompt 优化器",

  register(api: any) {
    const config = loadConfig(api.logger);
    api.logger.info(
      `[${LOG_TAG}] 插件已加载，配置文件=${CONFIG_FILE}，` +
      `system_prompt_prefix=${config.system_prompt_prefix ? "(已设置)" : "(未设置)"}，` +
      `ordered_system_prompt=${config.ordered_system_prompt ? `[${config.ordered_system_prompt.length} sections]` : "(未设置)"}，` +
      `inject_user_query=${config.inject_user_query ? `[${config.inject_user_query.length} sections]` : "(未设置)"}，` +
      `inject_user_query_suffix=${config.inject_user_query_suffix ? "(已设置)" : "(未设置)"}`
    );
    queueMicrotask(() => setupFetchInterceptor(api));
  },
};

export default plugin;
