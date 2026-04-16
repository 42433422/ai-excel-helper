import crypto from "node:crypto";
import type { NormalizedMessage } from "./types";

export const generateRequestId = (): string => {
  return crypto.randomUUID();
};

/** 生成指定长度的随机 hex 字符串 */
const genHex = (len: number): string => {
  const bytes = crypto.randomBytes(Math.ceil(len / 2));
  return bytes.toString("hex").slice(0, len);
};

/** 格式化当前时间为 yyyyMMddHHmmssSSS */
const formatCurrentTime = (): string => {
  const now = new Date();
  const pad = (n: number): string => (n < 10 ? "0" + n : n.toString());
  return (
    now.getFullYear().toString() +
    pad(now.getMonth() + 1) +
    pad(now.getDate()) +
    pad(now.getHours()) +
    pad(now.getMinutes()) +
    pad(now.getSeconds()) +
    now.getMilliseconds().toString().padStart(3, "0")
  );
};

/** 生成 32 位 trace-id（每轮 LLM 调用刷新一次） */
export const generateTraceId = (): string => {
  return `${genHex(13)}af${formatCurrentTime()}`;
};

/** 生成 W3C traceparent header 值；可传入已有 traceId 以保证同一轮调用共享，可传入 spanId 作为 parent-id */
export const generateTraceparent = (traceId?: string, spanId?: string): { traceparent: string; traceId: string } => {
  // 去掉 traceId 中的 -（外部传入可能是 UUID 格式），确保 W3C traceparent 合法
  const tid = (traceId ?? generateTraceId()).replace(/-/g, "");
  // 优先使用传入的 spanId 作为 parent-id，否则生成随机值
  const parentId = spanId ?? crypto.randomUUID().replace(/-/g, "").substring(0, 16).toLowerCase();
  return { traceparent: `00-${tid}-${parentId}-01`, traceId: tid };
};


export const getCurrentTimestamp = (): number => {
  return Math.floor(Date.now() / 1000);
};


export const normalizeMessage = (message: any, format: string = "openai"): NormalizedMessage => {
  if (format === "openai") {
    let content = "";
    if (typeof message.content === "string") {
      // 简单字符串格式（最常见）
      content = message.content;
    } else if (Array.isArray(message.content)) {
      // 多模态格式：提取所有 type=text 的部分，用换行拼接
      content = message.content
        .filter((part: any) => part.type === "text" && typeof part.text === "string")
        .map((part: any) => part.text)
        .join("\n");
    }
    return {
      role: message.role || "",
      content,
    };
  }

  // 非 OpenAI 格式：content 直接转为字符串
  return {
    role: message.role || "",
    content:
      typeof message.content === "string"
        ? message.content
        : JSON.stringify(message.content || ""),
  };
};


/**
 * 判断 messages 数组中最后一条 user 消息是否为工具结果回传（而非真实用户输入）。
 *
 * 判断依据：
 * 1. OpenAI 格式：最后一条 user 消息之前紧邻的 assistant 消息带有 tool_calls
 * 2. Anthropic 格式：最后一条 user 消息的 content 数组中包含 type=tool_result 的部分
 */
const isToolResultMessage = (messages: any[], lastUserIndex: number): boolean => {
  const lastUserMsg = messages[lastUserIndex];

  // Anthropic 格式：content 数组中含有 tool_result
  if (Array.isArray(lastUserMsg?.content)) {
    const hasToolResult = lastUserMsg.content.some(
      (part: any) => part.type === "tool_result" || part.type === "tool_use",
    );
    if (hasToolResult) return true;
  }

  // OpenAI 格式：向前找最近的 assistant 消息，若带有 tool_calls 则说明当前 user 是工具结果回传
  for (let i = lastUserIndex - 1; i >= 0; i--) {
    const msg = messages[i];
    if (msg.role === "assistant") {
      if (Array.isArray(msg.tool_calls) && msg.tool_calls.length > 0) {
        return true;
      }
      // 找到 assistant 消息但没有 tool_calls，停止向前查找
      break;
    }
    // 跳过 tool 角色消息（OpenAI tool result 消息）
    if (msg.role === "tool") {
      return true;
    }
  }

  return false;
};

export const extractLastUserMessage = (body: any): NormalizedMessage[] => {
  if (!body || typeof body !== "object") return [];

  if (Array.isArray(body.messages) && body.messages.length > 0) {
    const lastMessage = body.messages[body.messages.length - 1];
    const normalized = normalizeMessage(lastMessage, "openai");
    // 只审核 user 消息，跳过 system / assistant 消息
    if (normalized.role !== "user") {
      return [];
    }
    if (normalized.content.length === 0) {
      return [];
    }
    // 工具结果回传不是真实用户输入，跳过输入送审
    const lastUserIndex = body.messages.length - 1;
    if (isToolResultMessage(body.messages, lastUserIndex)) {
      return [];
    }
    return [normalized];
  }

  // 旧版 Completion API：prompt 字段
  if (typeof body.prompt === "string") return [{ role: "user", content: body.prompt }];
  // 自定义 API：input 字段
  if (typeof body.input === "string") return [{ role: "user", content: body.input }];

  return [];
};


export const sliceText = (text: string, maxLength: number): string[] => {
  if (text.length <= maxLength) {
    return [text];
  }

  const slices: string[] = [];
  for (let i = 0; i < text.length; i += maxLength) {
    slices.push(text.substring(i, i + maxLength));
  }
  return slices;
};


export const injectSecurityMarker = (
  content: any,
  securityReason: string,
  blocked: boolean,
): any => {
  if (typeof content === "string") {
    if (blocked) {
      // BLOCK：完全替换，LLM 只看到安全拦截指令
      return securityReason;
    }
    // MARK：追加到原始内容后
    return `${content}\n${securityReason}`;
  }

  if (Array.isArray(content)) {
    // OpenAI 多模态格式：递归处理每个 type=text 的部分
    return content.map((part: any) => {
      if (part.type === "text" && typeof part.text === "string") {
        return {
          ...part,
          text: injectSecurityMarker(part.text, securityReason, blocked),
        };
      }
      // 非文本部分（图片、音频等）保持不变
      return part;
    });
  }

  // 其他类型（null、object 等）保持不变
  return content;
};


/**
 * 并发分片审核（带并发上限控制和批次间短路优化）。
 *
 * 将分片按 concurrencyLimit 分批，每批内并行发起审核请求：
 * - 批内任一分片被 blocked → 整批结束后立即返回 blocked，跳过后续批次（保留部分短路能力）
 * - 单片快速路径：只有 1 个分片时直接审核，避免 Promise.all 包装开销
 *
 * @param slices        - 待审核的文本分片数组
 * @param checkFn       - 单片审核函数，接收分片文本和分片索引，返回 { blocked: boolean }
 * @param concurrencyLimit - 每批最大并发数，默认 3
 * @returns 是否有任一分片被 blocked
 */
export const checkSlicesParallel = async (
  slices: string[],
  checkFn: (slice: string, index: number) => Promise<{ blocked: boolean }>,
  concurrencyLimit: number = 3,
): Promise<boolean> => {
  if (slices.length === 0) return false;

  // 单片快速路径：避免 Promise.all 包装开销
  if (slices.length === 1) {
    const result = await checkFn(slices[0], 0);
    return result.blocked;
  }

  // 多片：按 concurrencyLimit 分批并行
  for (let start = 0; start < slices.length; start += concurrencyLimit) {
    const batch = slices.slice(start, start + concurrencyLimit);
    const batchStartIndex = start;

    const results = await Promise.all(
      batch.map((slice, i) => checkFn(slice, batchStartIndex + i)),
    );

    if (results.some((r) => r.blocked)) {
      return true; // 当前批次有 blocked，跳过后续批次
    }
  }

  return false;
};

// ==================== 通用本地日志工具 ====================

/** 是否开启内容安全日志，统一由此字段控制 */
export const ENABLE_CONTENT_SECURITY_LOG = false;

let _sharedLogStream: any = null;

const getLogFileStream = (): any => {
  if (_sharedLogStream) return _sharedLogStream;
  try {
    const fs = require("fs");
    const path = require("path");
    const os = require("os");
    const logDir = path.join(os.homedir(), "openclaw-logs");
    try {
      if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
    } catch { }
    const dateStr = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
    const logPath = path.join(logDir, `content-security-${dateStr}.log`);
    _sharedLogStream = fs.createWriteStream(logPath, { flags: "a", encoding: "utf8" });
    if (ENABLE_CONTENT_SECURITY_LOG) console.log(`[content-security] 日志文件路径: ${logPath}`);
  } catch { }
  return _sharedLogStream;
};

/**
 * 写入一条内容安全日志。
 * 格式：[ISO时间] [content-security] [phase] {JSON数据}
 * 受 ENABLE_CONTENT_SECURITY_LOG 控制，关闭时静默跳过。
 */
export const writeSecurityLog = (phase: string, data: Record<string, unknown>): void => {
  if (!ENABLE_CONTENT_SECURITY_LOG) return;
  try {
    const ts = new Date().toISOString();
    const line = `[${ts}] [content-security] [${phase}] ${JSON.stringify(data)}`;
    console.log(line);
    const stream = getLogFileStream();
    if (stream) stream.write(line + "\n");
  } catch { }
};

export const extractAssistantContent = (body: any): string => {
  if (!body || typeof body !== "object") return "";

  // OpenAI Chat Completion 格式
  if (Array.isArray(body.choices) && body.choices.length > 0) {
    const choice = body.choices[0];
    const message = choice.message;
    if (!message) return "";

    if (typeof message.content === "string") {
      return message.content;
    }
    // 多模态格式：提取所有 type=text 的部分
    if (Array.isArray(message.content)) {
      return message.content
        .filter((part: any) => part.type === "text" && typeof part.text === "string")
        .map((part: any) => part.text)
        .join("\n");
    }
  }

  return "";
};
