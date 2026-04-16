/**
 * cron-delivery-guard — 定时任务投递守护插件
 *
 * 核心机制：通过 before_tool_call 钩子拦截 cron 工具调用，
 * 当 delivery.mode 为 "announce" 且未指定 channel 时，
 * 自动注入 bestEffort: true，使投递失败时静默降级，
 * 不影响 cron 执行结果的保存。
 *
 * 背景：
 * - 定时任务的 delivery 设为 announce 模式，如果没有指定 channel，
 *   投递可能因找不到有效渠道而失败
 * - bestEffort: true 让框架在投递失败时不报错，避免丢失执行结果
 */

const LOG_TAG = 'cron-delivery-guard'

// ---- 类型定义 ----

interface ToolCallEvent {
  toolName: string
  toolCallId: string
  params: Record<string, unknown>
  result?: { content: string }
}

interface HookContext {
  agentId: string
  sessionKey: string
}

interface BeforeToolCallResult {
  block?: boolean
  blockReason?: string
  params?: Record<string, unknown>
}

// ---- delivery 类型 ----

interface CronDelivery {
  mode?: string
  channel?: string
  to?: string
  bestEffort?: boolean
  [key: string]: unknown
}

// ---- 辅助函数 ----

/**
 * 判断是否为 cron 工具调用
 */
function isCronTool(toolName: string): boolean {
  return toolName === 'cron'
}

/**
 * 从 cron 参数中提取 delivery 配置
 * cron 工具的参数结构可能是:
 * - params.delivery (顶层)
 * - params.job.delivery (嵌套在 job 中)
 */
function extractDelivery(params: Record<string, unknown>): CronDelivery | null {
  // 尝试顶层 delivery
  if (params.delivery && typeof params.delivery === 'object') {
    return params.delivery as CronDelivery
  }

  // 尝试 job.delivery
  const job = params.job as Record<string, unknown> | undefined
  if (job?.delivery && typeof job.delivery === 'object') {
    return job.delivery as CronDelivery
  }

  // 尝试 payload 中的 deliver 相关字段 (兼容 qqbot-cron 风格)
  const payload = job?.payload as Record<string, unknown> | undefined
  if (payload?.deliver === true && payload.channel === undefined) {
    // payload 风格: { deliver: true, channel?: string }
    // 这种情况不是 delivery 对象，跳过
    return null
  }

  return null
}

/**
 * 判断 delivery 是否需要注入 bestEffort
 * 条件: mode 为 "announce" 且没有 channel
 */
function needsBestEffort(delivery: CronDelivery): boolean {
  return delivery.mode === 'announce' && 
    !delivery.bestEffort && 
    (!delivery.channel || delivery.channel === 'webchat' || delivery.channel === 'last')
}

/**
 * 深拷贝 params 并注入 bestEffort: true
 */
function injectBestEffort(params: Record<string, unknown>): Record<string, unknown> {
  const newParams = JSON.parse(JSON.stringify(params)) as Record<string, unknown>

  // 顶层 delivery
  if (newParams.delivery && typeof newParams.delivery === 'object') {
    ;(newParams.delivery as CronDelivery).bestEffort = true
    return newParams
  }

  // job.delivery
  const job = newParams.job as Record<string, unknown> | undefined
  if (job?.delivery && typeof job.delivery === 'object') {
    ;(job.delivery as CronDelivery).bestEffort = true
    return newParams
  }

  return newParams
}

// ---- 插件定义 ----

const plugin = {
  name: 'cron-delivery-guard',
  version: '1.0.0',

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register(api: any) {
    console.log(`[${LOG_TAG}] registered.`)

    // ---- before_tool_call: 拦截 cron 工具，注入 bestEffort ----
    api.on(
      'before_tool_call',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      async (...args: any[]): Promise<BeforeToolCallResult | undefined> => {
        const event = args[0] as ToolCallEvent
        const { toolName, params, toolCallId } = event

        // 仅处理 cron 工具
        if (!isCronTool(toolName)) {
          return undefined
        }

        const delivery = extractDelivery(params)
        if (!delivery) {
          console.log(
            `[${LOG_TAG}] cron call (${toolCallId}) has no delivery config, skip.`
          )
          return undefined
        }

        if (!needsBestEffort(delivery)) {
          console.log(
            `[${LOG_TAG}] cron call (${toolCallId}) delivery does not need bestEffort ` +
            `(mode=${String(delivery.mode)}, channel=${String(delivery.channel)}, bestEffort=${String(delivery.bestEffort)}), skip.`
          )
          return undefined
        }

        // ★ 核心：注入 bestEffort: true
        const newParams = injectBestEffort(params)
        console.log(
          `[${LOG_TAG}] cron call (${toolCallId}) injected bestEffort=true ` +
          `(mode=announce, no channel). delivery=${JSON.stringify((newParams.delivery || (newParams.job as Record<string, unknown>)?.delivery))}`
        )

        return { params: newParams }
      }
    )
  },
}

export default plugin