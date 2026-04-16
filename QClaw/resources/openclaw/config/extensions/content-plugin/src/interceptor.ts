import { SessionType } from "./types";
import type { InterceptorConfig } from "./types";
import {
  extractLastUserMessage,
  extractAssistantContent,
  sliceText,
  checkSlicesParallel,
  generateTraceparent,
  generateTraceId,
  writeSecurityLog,
} from "./utils";
import { stripPromptMetadata } from "./service";
import { checkContentSecurity } from "./security";
import {
  getSessionId,
  ensureQAIDForTurn,
  isSessionBlocked,
  clearSessionBlocked,
  addBlockedContent,
  sanitizeMessages,
} from "./session";
import {
  getExternalTraceId,
  getCurrentAgentCtx,
  getCurrentAgentSpanId,
  getCurrentLlmAuditContext,
  consumePendingChatSpanCallback,
} from "./state";


const PROMPT_MAX_LENGTH = 4000;

const OUTPUT_MAX_LENGTH = 120;

const FETCH_INTERCEPTOR_STATE = Symbol.for("openclaw.contentSecurity.fetchInterceptorState");

interface FetchInterceptorState {
  installed: boolean;
  setupAttempts: number;
  triggerCount: number;
  llmRequestCount: number;
  outputAuditEndCount: number;
}

type GlobalWithFetchInterceptorState = typeof globalThis & {
  [FETCH_INTERCEPTOR_STATE]?: FetchInterceptorState;
};

const getFetchInterceptorState = (): FetchInterceptorState => {
  const globalState = globalThis as GlobalWithFetchInterceptorState;
  if (!globalState[FETCH_INTERCEPTOR_STATE]) {
    globalState[FETCH_INTERCEPTOR_STATE] = {
      installed: false,
      setupAttempts: 0,
      triggerCount: 0,
      llmRequestCount: 0,
      outputAuditEndCount: 0,
    };
  }
  return globalState[FETCH_INTERCEPTOR_STATE]!;
};



/** phase → 可读标签映射，方便日志一眼区分类别 */
const PHASE_LABEL: Record<string, string> = {
  // LLM 请求 / 返回
  llm_request:            "LLM→  请求发出",
  llm_request_error:      "LLM✗  请求失败",
  llm_response_received:  "←LLM  响应头",
  llm_response_json:      "←LLM  响应体(JSON)",
  // 输入送审 / 返回
  audit_input_start:        "送审→  输入开始",
  audit_input_slice_send:   "送审→  输入分片",
  audit_input_slice_result: "←送审  输入结果",
  audit_input_slice_result_degraded: "←送审 输入结果(降级)",
  audit_input_end:          "←送审  输入汇总",
  audit_input_end_degraded: "←送审 输入汇总(降级)",
  // LLM 流体返回
  llm_response_stream_body:  "←LLM  响应体(SSE流)",
  // 输出送审 / 返回
  audit_output_slice_send:   "送审→  输出分片",
  audit_output_slice_result: "←送审  输出结果",
  audit_output_slice_result_degraded: "←送审 输出结果(降级)",
  audit_output_end_send:     "送审→  输出末尾",
  audit_output_end_result:   "←送审  输出末尾结果",
  audit_output_end_result_degraded: "←送审 输出末尾结果(降级)",
  audit_output_json_send:    "送审→  输出(JSON)",
  // session 写入
  session_write_redact_input:  "→session 写入(输入拦截/REDACT)",
  session_write_redact_output: "→session 写入(输出拦截/REDACT)",
};

const logInterceptorDebug = (phase: string, data: Record<string, unknown>): void => {
  const label = PHASE_LABEL[phase] ?? phase;
  writeSecurityLog(label, data);
};

// ==================== REDACT 区间过滤 ====================

const messageHasRedact = (msg: any): boolean => {
  if (!msg) return false;
  if (typeof msg.content === "string") {
    return msg.content.includes("<!--REDACT-->");
  }
  if (Array.isArray(msg.content)) {
    return msg.content.some(
        (part: any) => part.type === "text" && typeof part.text === "string" && part.text.includes("<!--REDACT-->"),
    );
  }
  return false;
};

const filterRedactedMessages = (messages: any[]): any[] => {
  if (!Array.isArray(messages) || messages.length === 0) return messages;

  // 标记需要移除的索引
  const indicesToRemove = new Set<number>();

  for (let i = 0; i < messages.length; i++) {
    if (!messageHasRedact(messages[i])) continue;

    // 找到该消息向前最近的 user 消息（含自身）
    let rangeStart = i;
    for (let j = i; j >= 0; j--) {
      if (messages[j].role === "user") {
        rangeStart = j;
        break;
      }
    }

    // 找到该消息向后下一条 user 消息（不含）
    let rangeEnd = messages.length; // 默认到末尾
    for (let j = i + 1; j < messages.length; j++) {
      if (messages[j].role === "user") {
        rangeEnd = j;
        break;
      }
    }

    // 标记区间内所有消息为需要移除
    for (let j = rangeStart; j < rangeEnd; j++) {
      indicesToRemove.add(j);
    }
  }

  if (indicesToRemove.size === 0) return messages;

  return messages.filter((_, idx) => !indicesToRemove.has(idx));
};

const EXTERNAL_BLOCK_PATTERNS: RegExp[] = [];

const isExternalBlockedResponse = (content: string): boolean => {
  if (!content || content.length === 0) return false;
  return EXTERNAL_BLOCK_PATTERNS.some((pattern) => pattern.test(content));
};

// ==================== 核心：fetch 拦截器安装函数 ====================

export const setupFetchInterceptor = (config: InterceptorConfig, logTag: string = ""): void => {
  const interceptorState = getFetchInterceptorState();
  interceptorState.setupAttempts += 1;

  if (interceptorState.installed) {
    return;
  }

  const { api, client, enableLogging, shieldEndpoint } = config;

  const originalFetch = globalThis.fetch;

  const newFetch = async function (this: any, ...args: any[]) {
    const triggerSeq = interceptorState.triggerCount + 1;
    interceptorState.triggerCount = triggerSeq;

    const url = args[0]?.toString() || "";
    const options = args[1] || {};


    const parentCtx = getCurrentAgentCtx() ?? undefined;

    if (shieldEndpoint && url.includes(shieldEndpoint)) {
      return originalFetch.apply(this, args as any);
    }

    // ==================== 生成链路追踪信息 ====================

    const roundTraceId = getExternalTraceId() || generateTraceId();

    const currentSpanId = getCurrentAgentSpanId() ?? undefined;

    const { traceparent } = generateTraceparent(roundTraceId, currentSpanId);


    const runtimeAuditCtx = getCurrentLlmAuditContext();
    const sessionKey = runtimeAuditCtx?.sessionKey || `fetch:${url}`;
    const turnKey = runtimeAuditCtx?.turnKey || roundTraceId;


    let jsonBody: any;
    // 标记当前请求是否为 OpenClaw 后台 Memory Compaction（增量记忆压缩）请求。
    // Memory Compaction 是 OpenClaw 在 context 超过阈值时自动触发的后台行为，
    // 用于将历史对话压缩成摘要以腾出 context window，不属于用户主动输入，
    // 因此不需要走内容安全审核，直接放行。
    let isMemoryCompactionRequest = false;
    if (options.body) {
      let rawBody: string | undefined;

      if (typeof options.body === "string") {
        rawBody = options.body;
      } else if (options.body instanceof Uint8Array || options.body instanceof ArrayBuffer) {
        rawBody = new TextDecoder().decode(options.body);
      }

      // 尝试将原始字符串解析为 JSON
      if (rawBody) {
        try {
          jsonBody = JSON.parse(rawBody);
        } catch {
        }
      }

      if (jsonBody) {
        const messagesToModerate = extractLastUserMessage(jsonBody);

        // 提取最后一条 user 消息的前 300 字符，用于识别是否为 Memory Compaction 请求。
        // 注意：必须在 filterRedactedMessages 之前提取原始内容，
        // 否则若最后一条 user 消息恰好含有 REDACT 标记被过滤掉，会导致识别失败。
        const lastUserMsgPreview = (() => {
          if (!Array.isArray(jsonBody?.messages)) return "";
          for (let i = jsonBody.messages.length - 1; i >= 0; i--) {
            if (jsonBody.messages[i].role === "user") {
              const c = jsonBody.messages[i].content;
              const text = typeof c === "string" ? c : (Array.isArray(c) ? c.map((p: any) => p.text ?? "").join("") : "");
              return text.slice(0, 300);
            }
          }
          return "";
        })();

        // OpenClaw Memory Compaction 请求的最后一条 user 消息固定以 "You summarize a SEGMENT" 开头，
        // 这是 OpenClaw 框架内部硬编码的 prompt 模板，不是用户输入，直接跳过内容安全审核。
        isMemoryCompactionRequest = lastUserMsgPreview.startsWith("You summarize a SEGMENT");

        if (Array.isArray(jsonBody.messages)) {
          let lastUserMsgIndex = -1;
          for (let i = jsonBody.messages.length - 1; i >= 0; i--) {
            if (jsonBody.messages[i].role === "user") {
              lastUserMsgIndex = i;
              break;
            }
          }

          const redactFilteredMessages = filterRedactedMessages(jsonBody.messages);
          const redactRemovedCount = jsonBody.messages.length - redactFilteredMessages.length;

          if (redactRemovedCount > 0) {
            jsonBody.messages = redactFilteredMessages;
            lastUserMsgIndex = -1;
            for (let i = jsonBody.messages.length - 1; i >= 0; i--) {
              if (jsonBody.messages[i].role === "user") {
                lastUserMsgIndex = i;
                break;
              }
            }
          }

          const sanitizedCount = sanitizeMessages(jsonBody.messages, lastUserMsgIndex);

          if (redactRemovedCount > 0 || sanitizedCount > 0) {
            const newBody = JSON.stringify(jsonBody);

            if (typeof options.body === "string") {
              options.body = newBody;
            } else if (options.body instanceof Uint8Array) {
              options.body = new TextEncoder().encode(newBody);
            } else if (options.body instanceof ArrayBuffer) {
              const encoded = new TextEncoder().encode(newBody);
              options.body = encoded.buffer;
            }

            args[1] = options;
          }
        }

        if (isSessionBlocked(sessionKey)) {
          if (messagesToModerate.length > 0) {
            clearSessionBlocked(sessionKey);
          } else {
          }
        }

        // Memory Compaction 请求跳过输入送审；
        // filterRedactedMessages 已在上方执行，REDACT 问答对不会被带入摘要。
        if (messagesToModerate.length > 0 && !isMemoryCompactionRequest) {
          const msg = messagesToModerate[0];

          const sessionId = getSessionId(sessionKey);
          const qaid = ensureQAIDForTurn(sessionKey, turnKey);

          const slices = sliceText(msg.content, PROMPT_MAX_LENGTH);

          logInterceptorDebug("audit_input_start", {
            sessionKey,
            qaid,
            sliceCount: slices.length,
            totalLength: msg.content.length,
            contentPreview: msg.content.slice(0, 200),
          });

          const inputBlocked = await checkSlicesParallel(
              slices,
              async (slice, i) => {
                const contentToCheck = i === 0 ? stripPromptMetadata(slice) : slice;
                logInterceptorDebug("audit_input_slice_send", {
                  sessionKey,
                  qaid,
                  sliceIndex: i,
                  sliceLength: contentToCheck.length,
                  contentPreview: contentToCheck.slice(0, 100),
                });
                const result = await checkContentSecurity(
                    api,
                    client,
                    "prompt",
                    [{ Data: contentToCheck, MediaType: "Text" }],
                    sessionId,
                    SessionType.QUESTION,
                    "llm_request",
                    enableLogging,
                    logTag,
                    qaid,
                    parentCtx,
                );
                logInterceptorDebug(result.degraded ? "audit_input_slice_result_degraded" : "audit_input_slice_result", {
                  sessionKey,
                  qaid,
                  sliceIndex: i,
                  blocked: result.blocked,
                  resultCode: result.resultCode ?? "",
                  resultType: result.resultType ?? "",
                  level: result.level ?? "",
                  degraded: result.degraded ?? false,
                  errorType: result.errorType ?? "",
                  traceId: result.traceId ?? "",
                  requestId: result.requestId ?? "",
                });
                return result;
              },
          );

          logInterceptorDebug("audit_input_end", {
            sessionKey,
            qaid,
            blocked: inputBlocked,
          });

          if (inputBlocked) {

            const blockedReplyText = "<!--REDACT-->抱歉，这个问题我暂时无法解答，让我们换个话题吧~\n\n你可以试试让我帮你： 🔍 搜索与查询 · ✍️ 内容创作 · ⏰ 定时提醒 · ⚙️ 系统操作<!--/REDACT-->";
            const sseChunk = JSON.stringify({
              id: `blocked-${Date.now()}`,
              object: "chat.completion.chunk",
              created: Math.floor(Date.now() / 1000),
              model: "content-security",
              choices: [{
                index: 0,
                delta: { role: "assistant", content: blockedReplyText },
                finish_reason: "stop",
              }],
            });
            const sseBody = `data: ${sseChunk}\n\ndata: [DONE]\n\n`;
            const encoder = new TextEncoder();

            logInterceptorDebug("session_write_redact_input", {
              sessionKey,
              qaid,
              reason: "input_blocked",
              content: blockedReplyText,
            });

            return new Response(encoder.encode(sseBody), {
              status: 200,
              statusText: "OK",
              headers: {
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
              },
            });
          }

          clearSessionBlocked(sessionKey);
        }
      }
    }

    const isLLMRequest = !!(jsonBody && (
        Array.isArray(jsonBody.messages) || typeof jsonBody.prompt === "string" || typeof jsonBody.input === "string"
    ));

    if (isLLMRequest) {
      interceptorState.llmRequestCount += 1;
      logInterceptorDebug("llm_request", {
        seq: interceptorState.llmRequestCount,
        url,
        model: jsonBody?.model ?? "",
        messageCount: Array.isArray(jsonBody?.messages) ? jsonBody.messages.length : 0,
        lastUserMsgPreview: (() => {
          if (!Array.isArray(jsonBody?.messages)) return "";
          for (let i = jsonBody.messages.length - 1; i >= 0; i--) {
            if (jsonBody.messages[i].role === "user") {
              const c = jsonBody.messages[i].content;
              const text = typeof c === "string" ? c : (Array.isArray(c) ? c.map((p: any) => p.text ?? "").join("") : "");
              return text.slice(0, 200);
            }
          }
          return "";
        })(),
        stream: jsonBody?.stream ?? false,
      });
    }

    if (isLLMRequest) {
      consumePendingChatSpanCallback();
    }


    if (!options.headers) {
      options.headers = {};
    }

    const conversationId = getSessionId(sessionKey);
    const conversationRequestId = roundTraceId;

    if (options.headers instanceof Headers) {
      options.headers.set("traceparent", traceparent);
      options.headers.set("X-Conversation-ID", conversationId);
      options.headers.set("X-Conversation-Request-ID", conversationRequestId);
    } else if (Array.isArray(options.headers)) {
      options.headers.push(["traceparent", traceparent]);
      options.headers.push(["X-Conversation-ID", conversationId]);
      options.headers.push(["X-Conversation-Request-ID", conversationRequestId]);
    } else {
      options.headers["traceparent"] = traceparent;
      options.headers["X-Conversation-ID"] = conversationId;
      options.headers["X-Conversation-Request-ID"] = conversationRequestId;
    }
    args[1] = options;

    let resp: Response;
    const fetchStartTime = Date.now();
    try {
      resp = await originalFetch.apply(this, args as any);
    } catch (fetchError: any) {
      if (isLLMRequest) {
        logInterceptorDebug("llm_request_error", {
          url,
          error: (fetchError as any)?.message ?? String(fetchError),
          durationMs: Date.now() - fetchStartTime,
        });
      }
      throw fetchError;
    }

    if (isLLMRequest) {
      logInterceptorDebug("llm_response_received", {
        url,
        status: resp.status,
        contentType: resp.headers.get("content-type") ?? "",
        durationMs: Date.now() - fetchStartTime,
      });
    }

    if (isLLMRequest && resp.ok) {
      if (isSessionBlocked(sessionKey)) {
        return resp;
      }

      // Memory Compaction 请求跳过输出送审，直接透传 LLM 响应给 OpenClaw 框架。
      if (isMemoryCompactionRequest) {
        return resp;
      }

      const sessionId = getSessionId(sessionKey);
      const qaid = ensureQAIDForTurn(sessionKey, turnKey);

      const auditOutputSlices = async (
        assistantContent: string,
        source: string,
        finalSessionType: SessionType = SessionType.ANSWER_END,
      ): Promise<void> => {
        if (assistantContent.length === 0) {
          if (finalSessionType === SessionType.ANSWER_END) {
            interceptorState.outputAuditEndCount += 1;
          }
          const emptyResult = await checkContentSecurity(
              api,
              client,
              "output",
              [{ Data: "", MediaType: "Text" }],
              sessionId,
              finalSessionType,
              source,
              enableLogging,
              logTag,
              qaid,
              parentCtx,
          );
          return;
        }

        const slices = sliceText(assistantContent, OUTPUT_MAX_LENGTH);

        for (let i = 0; i < slices.length; i++) {
          const isLastSlice = i === slices.length - 1;
          const sessionType = isLastSlice ? finalSessionType : SessionType.ANSWER;

          if (isLastSlice && finalSessionType === SessionType.ANSWER_END) {
            interceptorState.outputAuditEndCount += 1;
          }

          const result = await checkContentSecurity(
              api,
              client,
              "output",
              [{ Data: slices[i], MediaType: "Text" }],
              sessionId,
              sessionType,
              source,
              enableLogging,
              logTag,
              qaid,
              parentCtx,
          );
        }
      };

      const contentType = resp.headers.get("content-type") || "";
      const isSSE = contentType.includes("text/event-stream");

      if (isSSE) {

        const body = resp.body;
        if (body) {
          const reader = body.getReader();
          const decoder = new TextDecoder();
          const encoder = new TextEncoder();

          let auditBuffer = "";
          let fullContent = "";
          let sliceIndex = 0;
          let lineBuf = "";
          let outputBlocked = false;
          let blockedReasonDetail: Record<string, unknown> = {};
          let blockedResponseSent = false;
          let receivedDone = false;
          let lastFinishReason: string | null = null;
          let pullCallCount = 0;
          let enqueuedChunkCount = 0;
          let sseErrorMessage: string | null = null;
          const streamStartTime = performance.now();

          const parseDeltaContent = (line: string): string => {
            if (!line.startsWith("data:")) return "";
            const dataStr = line.slice(5).trim();
            if (dataStr === "[DONE]") {
              receivedDone = true;
              return "";
            }
            try {
              const json = JSON.parse(dataStr);
              if (Array.isArray(json.choices) && json.choices.length > 0) {
                const choice = json.choices[0];
                const delta = choice.delta;
                if (delta && typeof delta.content === "string") {
                  return delta.content;
                }
              }
            } catch {
            }
            return "";
          };

          const parseFinishReason = (line: string): string | null => {
            if (!line.startsWith("data:")) return null;
            const dataStr = line.slice(5).trim();
            if (dataStr === "[DONE]") return null;
            try {
              const json = JSON.parse(dataStr);
              if (Array.isArray(json.choices) && json.choices.length > 0) {
                const finishReason = json.choices[0]?.finish_reason;
                if (finishReason) return finishReason;
              }
              if (json.stopReason) return json.stopReason;
              if (json.stop_reason) return json.stop_reason;
              if (json.error) {
                // 提取业务错误信息，用于后续透传给用户
                if (typeof json.error.message === "string" && json.error.message.length > 0) {
                  sseErrorMessage = json.error.message;
                }
                return "error";
              }
            } catch {
              // 忽略
            }
            return null;
          };

          const flushAuditBuffer = async (): Promise<void> => {
            while (auditBuffer.length >= OUTPUT_MAX_LENGTH) {
              const slice = auditBuffer.slice(0, OUTPUT_MAX_LENGTH);
              auditBuffer = auditBuffer.slice(OUTPUT_MAX_LENGTH);
              sliceIndex++;

              logInterceptorDebug("audit_output_slice_send", {
                sessionKey,
                qaid,
                sliceIndex,
                sliceLength: slice.length,
                contentPreview: slice.slice(0, 100),
                sessionType: "ANSWER",
              });

              const result = await checkContentSecurity(
                  api,
                  client,
                  "output",
                  [{ Data: slice, MediaType: "Text" }],
                  sessionId,
                  SessionType.ANSWER,
                  "llm_response_sse",
                  enableLogging,
                  logTag,
                  qaid,
                  parentCtx,
              );

              logInterceptorDebug(result.degraded ? "audit_output_slice_result_degraded" : "audit_output_slice_result", {
                sessionKey,
                qaid,
                sliceIndex,
                blocked: result.blocked,
                resultCode: result.resultCode ?? "",
                resultType: result.resultType ?? "",
                level: result.level ?? "",
                degraded: result.degraded ?? false,
                errorType: result.errorType ?? "",
                traceId: result.traceId ?? "",
                requestId: result.requestId ?? "",
              });

              if (result.blocked) {
                outputBlocked = true;
                blockedReasonDetail = {
                  source: "audit_output_slice",
                  sliceIndex,
                  resultCode: result.resultCode ?? "",
                  resultType: result.resultType ?? "",
                  level: result.level ?? "",
                  degraded: result.degraded ?? false,
                  traceId: result.traceId ?? "",
                  requestId: result.requestId ?? "",
                };
                addBlockedContent(slice);
                break;
              }
            }
          };

          const enqueueBlockedMarker = (controller: ReadableStreamDefaultController): void => {
            if (blockedResponseSent) return;
            blockedResponseSent = true;

            logInterceptorDebug("llm_response_stream_body", {
              url,
              totalLength: fullContent.length,
              blocked: true,
              blockedReasonDetail,
              content: fullContent,
            });

            const blockedReplyText = "<!--REDACT-->抱歉，这个问题我暂时无法解答，让我们换个话题吧~\n\n你可以试试让我帮你： 🔍 搜索与查询 · ✍️ 内容创作 · ⏰ 定时提醒 · ⚙️ 系统操作<!--/REDACT-->";
            const llmFinishReason = "stop";
            const redactChunk = JSON.stringify({
              id: `output-blocked-${Date.now()}`,
              object: "chat.completion.chunk",
              created: Math.floor(Date.now() / 1000),
              model: "content-security",
              choices: [{
                index: 0,
                delta: { content: blockedReplyText },
                finish_reason: llmFinishReason,
              }],
            });
            controller.enqueue(encoder.encode(`data: ${redactChunk}\n\n`));
            controller.enqueue(encoder.encode(`data: [DONE]\n\n`));

            const blockedAtMs = (performance.now() - streamStartTime).toFixed(1);

            try {
              controller.close();
            } catch {
            }

            try {
              reader.cancel();
            } catch {
            }

            (() => {
              const sourceMap: Record<string, string> = {
                audit_output_slice:       "送审命中",
                llm_finish_reason:        "LLM截断",
                external_blocked_response: "话术检测",
              };
              const src = String(blockedReasonDetail.source ?? "");
              const srcLabel = sourceMap[src] ?? src;
              let reasonSuffix = srcLabel;
              if (src === "audit_output_slice") {
                reasonSuffix = `${srcLabel} resultCode=${blockedReasonDetail.resultCode} resultType=${blockedReasonDetail.resultType} level=${blockedReasonDetail.level} slice#${blockedReasonDetail.sliceIndex}`;
              } else if (src === "llm_finish_reason") {
                reasonSuffix = `${srcLabel}(${blockedReasonDetail.finishReason})`;
              }
              const label = `→session 写入(输出拦截/REDACT) ⛔ ${reasonSuffix}`;
              writeSecurityLog(label, {
                url,
                sessionKey,
                qaid,
                blockedReasonDetail,
                llmOriginalLength: fullContent.length,
                llmOriginalPreview: fullContent.slice(0, 200),
                content: blockedReplyText,
              });
            })();
          };

          const transformedStream = new ReadableStream({
            start(_controller) {
              // no-op
            },
            async pull(controller) {
              try {
                const { done, value } = await reader.read();

                if (done) {
                  if (blockedResponseSent) {
                    return;
                  }

                  if (lineBuf.trim()) {
                    const content = parseDeltaContent(lineBuf);
                    if (content) {
                      auditBuffer += content;
                      fullContent += content;
                    }
                  }

                  sliceIndex++;

                  if (!outputBlocked && !receivedDone && lastFinishReason === null && auditBuffer.length > 0) {
                    outputBlocked = true;
                    addBlockedContent(auditBuffer);
                    enqueueBlockedMarker(controller);
                    return;
                  }

                  if (!outputBlocked && isExternalBlockedResponse(auditBuffer)) {
                    outputBlocked = true;
                    enqueueBlockedMarker(controller);
                    return;
                  }
                  if (outputBlocked) {
                    enqueueBlockedMarker(controller);
                    return;
                  }

                  logInterceptorDebug("llm_response_stream_body", {
                    url,
                    totalLength: fullContent.length,
                    content: fullContent,
                  });

                  controller.close();

                  setTimeout(() => {
                    // finish_reason 为 tool_calls 表示中间轮次，用 ANSWER；stop 或无 finish_reason 表示最终轮次，用 ANSWER_END
                    const isIntermediateRound = lastFinishReason === "tool_calls";
                    const auditSessionType = isIntermediateRound ? SessionType.ANSWER : SessionType.ANSWER_END;

                    if (!isIntermediateRound) {
                      interceptorState.outputAuditEndCount += 1;
                    }

                    logInterceptorDebug("audit_output_end_send", {
                      sessionKey,
                      qaid,
                      bufferLength: auditBuffer.length,
                      contentPreview: auditBuffer.slice(0, 200),
                      sessionType: isIntermediateRound ? "ANSWER" : "ANSWER_END",
                      lastFinishReason,
                    });

                    checkContentSecurity(
                        api,
                        client,
                        "output",
                        [{ Data: auditBuffer, MediaType: "Text" }],
                        sessionId,
                        auditSessionType,
                        "llm_response_sse",
                        enableLogging,
                        logTag,
                        qaid,
                        parentCtx,
                    ).then((endResult) => {
                      logInterceptorDebug(endResult.degraded ? "audit_output_end_result_degraded" : "audit_output_end_result", {
                        sessionKey,
                        qaid,
                        blocked: endResult.blocked,
                        resultCode: endResult.resultCode ?? "",
                        resultType: endResult.resultType ?? "",
                        level: endResult.level ?? "",
                        degraded: endResult.degraded ?? false,
                        errorType: endResult.errorType ?? "",
                        traceId: endResult.traceId ?? "",
                        requestId: endResult.requestId ?? "",
                      });
                      if (endResult.blocked) {
                        addBlockedContent(auditBuffer);
                      }
                    }).catch((e) => {
                    });
                  }, 0);

                  return;
                }

                if (outputBlocked) {
                  return;
                }

                lineBuf += decoder.decode(value, { stream: true });

                const lines = lineBuf.split("\n");
                lineBuf = lines.pop() || "";

                // 逐行过滤，只收集正常内容行，跳过 error 行，避免原始字节直接透传
                const safeLines: string[] = [];
                let hitError = false;

                for (const line of lines) {
                  // if (line.trim()) {
                  //   logInterceptorDebug("sse_raw_line", {
                  //     sessionKey,
                  //     qaid,
                  //     line,
                  //   });
                  // }
                  const finishReason = parseFinishReason(line);
                  if (finishReason && finishReason !== "content_filter" && finishReason !== "error") {
                    lastFinishReason = finishReason;
                  }
                  if (finishReason === "content_filter" || finishReason === "error") {
                    // 如果是业务错误（如服务繁忙），透传错误信息给用户，不走 REDACT 拦截
                    if (finishReason === "error" && sseErrorMessage) {
                      hitError = true;
                      break;
                    }
                    outputBlocked = true;
                    blockedReasonDetail = { source: "llm_finish_reason", finishReason };
                    addBlockedContent(auditBuffer);
                    enqueueBlockedMarker(controller);
                    return;
                  }
                  const content = parseDeltaContent(line);
                  if (content) {
                    auditBuffer += content;
                    fullContent += content;
                  }
                  safeLines.push(line);
                }

                // 检测到业务错误：丢弃已积累的 <think> 等内容，直接透传错误信息
                if (hitError) {
                  const encoder2 = new TextEncoder();
                  const errChunk = JSON.stringify({
                    id: `error-${Date.now()}`,
                    object: "chat.completion.chunk",
                    created: Math.floor(Date.now() / 1000),
                    model: "content-security",
                    choices: [{
                      index: 0,
                      delta: { role: "assistant", content: sseErrorMessage },
                      finish_reason: "stop",
                    }],
                  });
                  controller.enqueue(encoder2.encode(`data: ${errChunk}\n\n`));
                  controller.enqueue(encoder2.encode(`data: [DONE]\n\n`));
                  try { controller.close(); } catch { }
                  try { reader.cancel(); } catch { }
                  return;
                }

                pullCallCount++;
                if (isExternalBlockedResponse(auditBuffer)) {
                  outputBlocked = true;
                  blockedReasonDetail = { source: "external_blocked_response", auditBufferPreview: auditBuffer.slice(0, 100) };
                  addBlockedContent(auditBuffer);
                  enqueueBlockedMarker(controller);
                  return;
                }

                // 只 enqueue 过滤后的安全行，而非原始 value
                if (safeLines.length > 0) {
                  const safeChunk = safeLines.join("\n") + "\n";
                  enqueuedChunkCount++;
                  controller.enqueue(encoder.encode(safeChunk));
                }

                await flushAuditBuffer();

                if (outputBlocked) {
                  enqueueBlockedMarker(controller);
                  return;
                }
              } catch (e) {
                controller.close();
              }
            },
          });

          return new Response(transformedStream, {
            status: resp.status,
            statusText: resp.statusText,
            headers: resp.headers,
          });
        }
      } else {
        const clonedResp = resp.clone();

        try {
          const respBody = await clonedResp.json();

          logInterceptorDebug("llm_response_json", {
            url,
            stopReason: respBody?.stopReason ?? respBody?.stop_reason ?? "",
            hasChoices: Array.isArray(respBody?.choices),
            choiceCount: Array.isArray(respBody?.choices) ? respBody.choices.length : 0,
          });

          if (respBody?.stopReason === "error" || respBody?.stop_reason === "error") {
            const errorMessage: string | undefined = respBody?.errorMessage;
            const encoder = new TextEncoder();

            // 如果有 errorMessage，说明是业务错误（如服务繁忙），直接透传给用户，不走 REDACT 拦截
            if (errorMessage) {
              const sseChunk = JSON.stringify({
                id: `error-${Date.now()}`,
                object: "chat.completion.chunk",
                created: Math.floor(Date.now() / 1000),
                model: "content-security",
                choices: [{
                  index: 0,
                  delta: { role: "assistant", content: errorMessage },
                  finish_reason: "stop",
                }],
              });
              const sseBody = `data: ${sseChunk}\n\ndata: [DONE]\n\n`;
              return new Response(encoder.encode(sseBody), {
                status: 200,
                statusText: "OK",
                headers: {
                  "Content-Type": "text/event-stream",
                  "Cache-Control": "no-cache",
                  "Connection": "keep-alive",
                },
              });
            }

            // 没有 errorMessage，视为内容安全拦截，走 REDACT 流程
            addBlockedContent(JSON.stringify(respBody));
            const blockedReplyText = "<!--REDACT-->抱歉，这个问题我暂时无法解答，让我们换个话题吧~\n\n你可以试试让我帮你： 🔍 搜索与查询 · ✍️ 内容创作 · ⏰ 定时提醒 · ⚙️ 系统操作<!--/REDACT-->";
            const sseChunk = JSON.stringify({
              id: `blocked-${Date.now()}`,
              object: "chat.completion.chunk",
              created: Math.floor(Date.now() / 1000),
              model: "content-security",
              choices: [{
                index: 0,
                delta: { role: "assistant", content: blockedReplyText },
                finish_reason: "llm_output_error",
              }],
            });
            const sseBody = `data: ${sseChunk}\n\ndata: [DONE]\n\n`;
            return new Response(encoder.encode(sseBody), {
              status: 200,
              statusText: "OK",
              headers: {
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
              },
            });
          }

          const assistantContent = extractAssistantContent(respBody);

          logInterceptorDebug("audit_output_json_send", {
            sessionKey,
            qaid,
            contentLength: assistantContent.length,
            contentPreview: assistantContent.slice(0, 200),
          });

          auditOutputSlices(assistantContent, "llm_response_json").catch(() => {});
        } catch (e) {
          // JSON 解析失败或审核出错，忽略（不影响响应返回）
        }
      }
    }

    return resp;
  };

  globalThis.fetch = newFetch as typeof fetch;

  interceptorState.installed = true;
};