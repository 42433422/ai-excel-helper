import { ref, computed, nextTick, onMounted, watch, type Ref } from 'vue'
import { buildFullApiUrl } from '@/api/core'
import { KITTEN_PHASE, type KittenPhase } from '@/composables/useKittenWorkflowState'
import { downloadBlob, getFilenameFromDisposition } from '@/utils'
import { safeJsonRequest } from '@/utils/safeJsonRequest'
import { appAlert } from '@/utils/appDialog'
import { chatApi, parseChatStreamErrorResponse } from '@/api/chat'
import { resolvePlannerChatPath } from '@/utils/plannerChatPaths'
import {
  readPlannerSseResponse,
  isChatStreamEnabled,
  type PlannerSseEvent,
} from '@/utils/chatSseStream'
import type { KittenFieldProfile } from '@/utils/kittenDatasetParser'

const MAX_CHAT_MESSAGES = 120
const KITTEN_SNAPSHOT_CACHE_MS = 90_000

/** Planner + 工具（如 generate_office_document）可能远超过 120s；过短会 Abort 后走 JSON 再次挂死且无超时 */
const KITTEN_CHAT_TIMEOUT_MS = (() => {
  const raw = String(import.meta.env.VITE_KITTEN_CHAT_TIMEOUT_MS || '').trim()
  const n = raw ? Number.parseInt(raw, 10) : NaN
  const base = Number.isFinite(n) && n > 0 ? n : 300_000
  return Math.min(600_000, Math.max(60_000, base))
})()

export const KITTEN_WELCOME_HTML =
  '你好，我是 <strong>小猫分析</strong>：日常问答、简单推理、文案与表格草稿。需要时可在右侧<strong>设置</strong>里打开业务库摘要或联网；也可上传表格或从输入旁回形针添加文件。<br><br>直接提问即可。'

export const kittenWorkflowSteps = [
  { key: 'ingest', label: '数据接入', desc: '上传或粘贴数据' },
  { key: 'schema', label: '结构识别', desc: '字段与类型预览' },
  { key: 'analyze', label: '洞察分析', desc: '自然语言与快捷意图' },
  { key: 'deliver', label: '报告输出', desc: '结论、图表与导出' }
] as const

export const kittenOrgCards = [
  { key: 'ingest', title: '数据接入层', desc: 'Excel / CSV / JSON 本地解析，首屏预览' },
  { key: 'schema', title: '语义理解层', desc: '自然语言需求与快捷意图（趋势、ROI、预测等）' },
  { key: 'analyze', title: '分析执行层', desc: '调用后端 /api/ai/chat（专业链路），结合会话上下文与多轮追问' },
  { key: 'deliver', title: '交付层', desc: '右侧「分析输出」汇总，支持导出与清除' }
] as const

export const kittenQuickActions = [
  { text: '分析销量趋势', label: '销量趋势' },
  { text: '计算渠道ROI', label: '渠道ROI' },
  { text: '预测下月销量', label: '销量预测' },
  { text: '数据质量检查', label: '数据清洗' }
] as const

export interface KittenDatasetSummary {
  name: string
  rows: number
  columns: number
  fieldNames: string[]
  previewText: string
}

export interface KittenChatMessage {
  role: 'user' | 'ai'
  content: string
  time: string
}

export interface KittenAnalysisResult {
  id: number
  title: string
  summary: string
  chart: boolean
  type: string
  kind: string
}

export type KittenChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'area'
export type KittenChartAggregate = 'count' | 'sum' | 'avg' | 'max' | 'min'

export interface KittenChartConfig {
  type: KittenChartType
  xField: string
  yField: string
  groupField: string
  aggregate: KittenChartAggregate
}

export interface KittenChartRecommendation {
  id: string
  label: string
  description: string
  config: KittenChartConfig
}

function makeKittenUserId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `kitten_${crypto.randomUUID()}`
  }
  return `kitten_${Date.now()}_${Math.random().toString(16).slice(2)}`
}

function pushBounded<T>(arrRef: Ref<T[]>, item: T, maxSize: number) {
  arrRef.value.push(item)
  const overflow = arrRef.value.length - maxSize
  if (overflow > 0) {
    arrRef.value.splice(0, overflow)
  }
}

function escapeHtml(s: string) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function textToHtml(s: string) {
  return escapeHtml(s).replace(/\n/g, '<br>')
}

/** Word/Excel 为 ZIP，魔数 PK；若误下到 JSON/HTML 则抛错避免存成 .docx */
async function assertKittenFileBlob(resp: Response, blob: Blob, label: string): Promise<void> {
  const ct = (resp.headers.get('content-type') || '').toLowerCase()
  if (ct.includes('application/json') || ct.includes('text/html')) {
    const t = await blob.text()
    let msg = `${label}：服务器返回了 ${ct || '非文件'} 而非二进制文档`
    try {
      const j = JSON.parse(t) as { message?: string; detail?: string }
      msg = String(j.message || j.detail || msg)
    } catch {
      const clip = t.trim().slice(0, 200)
      if (clip) msg = `${msg}（片段：${clip}）`
    }
    throw new Error(msg)
  }
  const head = new Uint8Array(await blob.slice(0, 4).arrayBuffer())
  if (head.length >= 2 && head[0] === 0x50 && head[1] === 0x4b) {
    return
  }
  if (head.length >= 1 && (head[0] === 0x7b || head[0] === 0x5b)) {
    const t = await blob.text()
    let msg = `${label}：内容像 JSON（常为 API 基址错误或未登录）`
    try {
      const j = JSON.parse(t) as { message?: string }
      if (typeof j.message === 'string') msg = j.message
    } catch {
      /* ignore */
    }
    throw new Error(msg)
  }
}

function extractChatApiText(data: Record<string, unknown> | null | undefined): string {
  if (!data || typeof data !== 'object') return ''
  if (typeof data.response === 'string' && data.response.trim()) return data.response.trim()
  const inner = data.data as Record<string, unknown> | undefined
  if (inner && typeof inner.text === 'string' && inner.text.trim()) return inner.text.trim()
  return ''
}

function extractWebSearchHits(body: unknown): Array<{ title: string; url: string; snippet: string }> {
  if (!body || typeof body !== 'object') return []
  const d = body as Record<string, unknown>
  const layer1 = d.data as Record<string, unknown> | undefined
  const raw = layer1?.web_search_results
  if (!Array.isArray(raw)) return []
  return raw
    .filter(Boolean)
    .map((x) => {
      const o = x as Record<string, unknown>
      return {
        title: String(o.title ?? ''),
        url: String(o.url ?? ''),
        snippet: String(o.snippet ?? '')
      }
    })
}

function buildPreviewTextFromData(data: {
  preview?: unknown[]
  columns?: unknown[]
}): string {
  const preview = data.preview
  const cols = data.columns
  if (!preview || !preview.length) return ''
  const lines: string[] = []
  for (const row of preview.slice(0, 3)) {
    if (Array.isArray(row)) {
      lines.push(row.map((c) => String(c ?? '')).join('\t'))
    } else if (row && typeof row === 'object') {
      const keys = Array.isArray(cols) && cols.length ? cols.map(String) : Object.keys(row as object)
      lines.push(keys.map((k) => `${k}: ${(row as Record<string, unknown>)[k] ?? ''}`).join(' | '))
    }
  }
  return lines.join('\n')
}

function formatKittenSnapshotStatsHint(stats: Record<string, unknown> | null | undefined): string {
  if (!stats || typeof stats !== 'object') return ''
  const parts: string[] = []
  if (stats.materials_total != null) parts.push(`原材料 ${stats.materials_total} 条`)
  if (stats.material_inventory_value_estimate != null) {
    parts.push(`原料库存估 ¥${stats.material_inventory_value_estimate}`)
  }
  if (stats.products_total != null) parts.push(`产品 ${stats.products_total} 条`)
  if (stats.product_inventory_value_estimate != null) {
    parts.push(`成品货值估 ¥${stats.product_inventory_value_estimate}`)
  }
  if (stats.shipments_sample_count != null) {
    parts.push(`近期出货样例 ${stats.shipments_sample_count} 条`)
  }
  return parts.length ? `已就绪：${parts.join(' · ')}` : ''
}

function htmlToPlainText(html: string): string {
  if (!html) return ''
  const normalized = String(html).replace(/<br\s*\/?>/gi, '\n')
  const el = document.createElement('div')
  el.innerHTML = normalized
  return (el.textContent || '').trim()
}

/** 从气泡 HTML / 纯文本 / 内嵌 JSON 中解析小猫文档取件链接（绝对或 /api 相对路径） */
export function extractKittenDocumentPickupUrl(content: string): string | null {
  if (!content) return null
  const decoded = String(content)
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, '&')
  const absolute = decoded.match(
    /https?:\/\/[^\s"'<>)\]]+\/api\/ai\/kitten\/document\/pickup\/[^\s"'<>)\]]+/
  )
  if (absolute) return absolute[0]
  const relative = decoded.match(/\/api\/ai\/kitten\/document\/pickup\/[^\s"'<>)\]]+/)
  if (relative) return relative[0]
  const jm = decoded.match(/"download_url"\s*:\s*"((?:[^"\\]|\\.)*)"/)
  if (jm?.[1]) {
    const u = jm[1].replace(/\\\//g, '/')
    if (u.includes('/api/ai/kitten/document/pickup/')) {
      if (u.startsWith('http')) return u
      if (u.startsWith('/')) return u
    }
  }
  return null
}

function buildKittenResultSummary(plain: string, max = 220): string {
  const url = extractKittenDocumentPickupUrl(plain)
  if (plain.length <= max) return plain
  if (url) {
    const idx = plain.indexOf(url)
    const before = (idx >= 0 ? plain.slice(0, idx) : plain.replace(url, '')).replace(/\s+/g, ' ').trim()
    const headMax = Math.max(24, max - url.length - 2)
    const head = before.slice(0, headMax).trimEnd()
    const ell = before.length > headMax ? '…' : ''
    return `${head}${ell}\n${url}`
  }
  return `${plain.slice(0, max)}…`
}

function formatExportTimestamp(date = new Date()): string {
  const pad = (num: number) => String(num).padStart(2, '0')
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}_${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`
}

const emptyChartConfig = (): KittenChartConfig => ({
  type: 'bar',
  xField: '',
  yField: '',
  groupField: '',
  aggregate: 'count'
})

function buildRecommendedCharts(fields: KittenFieldProfile[]): KittenChartRecommendation[] {
  const numericFields = fields.filter((f) => f.type === 'number')
  const categoryFields = fields.filter((f) => f.type === 'category')
  const dateFields = fields.filter((f) => f.type === 'date')
  const textFields = fields.filter((f) => f.type === 'text')
  const dimension = categoryFields[0] || textFields[0]
  const metric = numericFields[0]
  const secondMetric = numericFields[1]
  const recommendations: KittenChartRecommendation[] = []

  if (dimension) {
    recommendations.push({
      id: `category-count-${dimension.name}`,
      label: `${dimension.name} 分布`,
      description: '按分类字段统计记录数',
      config: { type: 'bar', xField: dimension.name, yField: '', groupField: '', aggregate: 'count' }
    })
  }
  if (dimension && metric) {
    recommendations.push({
      id: `category-sum-${dimension.name}-${metric.name}`,
      label: `${metric.name} 分类汇总`,
      description: '按分类字段汇总核心数值',
      config: { type: 'bar', xField: dimension.name, yField: metric.name, groupField: '', aggregate: 'sum' }
    })
  }
  if (dateFields[0] && metric) {
    recommendations.push({
      id: `date-line-${dateFields[0].name}-${metric.name}`,
      label: `${metric.name} 时间趋势`,
      description: '按日期字段观察数值变化',
      config: { type: 'line', xField: dateFields[0].name, yField: metric.name, groupField: '', aggregate: 'sum' }
    })
  }
  if (dimension) {
    recommendations.push({
      id: `pie-${dimension.name}`,
      label: `${dimension.name} 占比`,
      description: '用饼图查看分类占比',
      config: { type: 'pie', xField: dimension.name, yField: metric?.name || '', groupField: '', aggregate: metric ? 'sum' : 'count' }
    })
  }
  if (metric && secondMetric) {
    recommendations.push({
      id: `scatter-${metric.name}-${secondMetric.name}`,
      label: `${metric.name} / ${secondMetric.name} 相关性`,
      description: '用散点图查看两个数值字段关系',
      config: { type: 'scatter', xField: metric.name, yField: secondMetric.name, groupField: '', aggregate: 'sum' }
    })
  }

  return recommendations.slice(0, 5)
}

export function useKittenAnalyzer() {
  const messages = ref<KittenChatMessage[]>([
    {
      role: 'ai',
      content: KITTEN_WELCOME_HTML,
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }
  ])

  const inputText = ref('')
  const isChatLoading = ref(false)
  /** 流式生成时隐藏底部「正在分析」占位条，改由气泡内逐字更新 */
  const isKittenStreaming = ref(false)
  const isDatasetParsing = ref(false)
  const kittenPhase = ref<KittenPhase>(KITTEN_PHASE.idle)
  const currentResult = ref<KittenAnalysisResult | null>(null)
  const fileInput = ref<HTMLInputElement | null>(null)
  const chatMessagesRef = ref<HTMLElement | null>(null)

  const datasetSummary = ref<KittenDatasetSummary | null>(null)
  const datasetRows = ref<Record<string, unknown>[]>([])
  const fieldProfiles = ref<KittenFieldProfile[]>([])
  const chartConfig = ref<KittenChartConfig>(emptyChartConfig())
  const recommendedCharts = computed(() => buildRecommendedCharts(fieldProfiles.value))
  const kittenIncludeBusinessDb = ref(false)
  const kittenIncludeWebSearch = ref(true)
  const kittenDbStatsHint = ref('')
  const lastWebSearchHits = ref<Array<{ title: string; url: string; snippet: string }>>([])
  let kittenSnapshotCache = { at: 0, text: '' }
  const kittenSessionUserId = ref(makeKittenUserId())

  let xlsxLibPromise: Promise<typeof import('xlsx')> | null = null
  let parseDatasetFilePromise: Promise<typeof import('@/utils/kittenDatasetParser')> | null = null

  const loadXlsx = async () => {
    if (!xlsxLibPromise) xlsxLibPromise = import('xlsx')
    return xlsxLibPromise
  }

  const loadDatasetParser = async () => {
    if (!parseDatasetFilePromise) parseDatasetFilePromise = import('@/utils/kittenDatasetParser')
    return parseDatasetFilePromise
  }

  const buildKittenRequestContext = () => {
    const ds = datasetSummary.value
    const base = {
      kitten_analyzer: true,
      kitten_include_business_db: kittenIncludeBusinessDb.value,
      kitten_web_search: kittenIncludeWebSearch.value,
      kitten_session_id: kittenSessionUserId.value
    }
    if (!ds) {
      return {
        ...base,
        has_dataset: false,
        kitten_dataset: null
      }
    }
    const fields = Array.isArray(ds.fieldNames) ? ds.fieldNames.map((x) => String(x)) : []
    return {
      ...base,
      has_dataset: true,
      kitten_dataset: {
        file_name: ds.name,
        name: ds.name,
        rows: ds.rows,
        columns: ds.columns,
        fields,
        field_names: fields,
        preview_text: ds.previewText || ''
      }
    }
  }

  const buildKittenChatPayload = (query: string) => {
    const compactHistory = (messages.value || [])
      .slice(-6)
      .map((m) => ({
        role: m.role,
        content: String(m.content || '')
          .replace(/<br\s*\/?>/gi, '\n')
          .replace(/<[^>]*>/g, '')
          .slice(0, 500)
      }))
    return {
      message: query,
      user_id: kittenSessionUserId.value,
      source: 'pro',
      mode: 'pro',
      context: {
        ...buildKittenRequestContext(),
        recent_messages: compactHistory
      }
    }
  }

  const hasDataset = computed(() => Boolean(datasetSummary.value))

  /** 侧栏「下载本次生成的文档」：从最近一条含取件链接的 AI 气泡读取（不受 summary 截断影响） */
  const lastDocumentPickupUrl = computed(() => {
    const list = messages.value
    for (let i = list.length - 1; i >= 0; i--) {
      const m = list[i]
      if (m.role !== 'ai' || !m.content) continue
      const fromRaw = extractKittenDocumentPickupUrl(m.content)
      if (fromRaw) return fromRaw
      const plain = htmlToPlainText(m.content)
      const fromPlain = extractKittenDocumentPickupUrl(plain)
      if (fromPlain) return fromPlain
    }
    return null
  })

  const datasetFieldPreview = computed(() => {
    const names = datasetSummary.value?.fieldNames
    if (!Array.isArray(names)) return []
    return names.slice(0, 8)
  })

  const loadingStatusText = computed(() => {
    if (isDatasetParsing.value) return '正在解析数据文件...'
    if (isChatLoading.value) return '正在回复…'
    return ''
  })

  const scrollChatToBottom = () => {
    nextTick(() => {
      const el = chatMessagesRef.value
      if (el) el.scrollTop = el.scrollHeight
    })
  }

  const addMessage = (role: 'user' | 'ai', content: string) => {
    pushBounded(
      messages,
      {
        role,
        content,
        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      },
      MAX_CHAT_MESSAGES
    )
    scrollChatToBottom()
  }

  const resetSession = async () => {
    const uid = kittenSessionUserId.value
    if (uid) {
      const clearResult = await safeJsonRequest('/api/ai/context/clear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: uid })
      })
      if (!clearResult.ok || (clearResult.data as { success?: boolean })?.success === false) {
        console.warn(
          '清理会话上下文失败:',
          clearResult.message || (clearResult.data as { message?: string })?.message || 'unknown'
        )
      }
    }
    kittenSessionUserId.value = makeKittenUserId()
    messages.value = [
      {
        role: 'ai',
        content: KITTEN_WELCOME_HTML,
        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      }
    ]
    inputText.value = ''
    isChatLoading.value = false
    isDatasetParsing.value = false
    kittenPhase.value = KITTEN_PHASE.idle
    currentResult.value = null
    datasetSummary.value = null
    datasetRows.value = []
    fieldProfiles.value = []
    chartConfig.value = emptyChartConfig()
    kittenIncludeBusinessDb.value = false
    kittenIncludeWebSearch.value = false
    kittenDbStatsHint.value = ''
    lastWebSearchHits.value = []
    kittenSnapshotCache = { at: 0, text: '' }
    scrollChatToBottom()
  }

  const refreshKittenBusinessSnapshotHint = async () => {
    if (!kittenIncludeBusinessDb.value) {
      kittenDbStatsHint.value = ''
      return
    }
    const now = Date.now()
    if (now - kittenSnapshotCache.at < KITTEN_SNAPSHOT_CACHE_MS && kittenSnapshotCache.text) {
      kittenDbStatsHint.value = kittenSnapshotCache.text
      return
    }
    const r = await safeJsonRequest<{ success?: boolean; data?: { stats?: Record<string, unknown> } }>(
      '/api/ai/kitten/business-snapshot'
    )
    const payload = r.data?.data
    if (!r.ok || r.data?.success === false || !payload) {
      kittenDbStatsHint.value = '业务库快照预检失败，发送时服务端仍会重试聚合。'
      return
    }
    const hint = formatKittenSnapshotStatsHint(payload.stats) || '业务库快照已生成。'
    kittenSnapshotCache = { at: now, text: hint }
    kittenDbStatsHint.value = hint
  }

  const onKittenBusinessDbToggle = () => {
    void refreshKittenBusinessSnapshotHint()
  }

  watch(kittenIncludeBusinessDb, (on) => {
    if (!on) kittenDbStatsHint.value = ''
  })

  const triggerFileUpload = () => {
    fileInput.value?.click()
  }

  const generateDataPreview = (data: { columns: string[]; rows: number }) =>
    `字段：${data.columns.slice(0, 5).join('、')}${data.columns.length > 5 ? '...' : ''}<br>共 ${data.rows} 条记录`

  const setChartConfig = (next: Partial<KittenChartConfig>) => {
    chartConfig.value = {
      ...chartConfig.value,
      ...next
    }
    const cfg = chartConfig.value
    if (cfg.xField) {
      currentResult.value = {
        id: Date.now(),
        title: '图表分析',
        summary: `${cfg.type} · ${cfg.xField}${cfg.yField ? ` / ${cfg.yField}` : ''} · ${cfg.aggregate}`,
        chart: true,
        type: 'chart',
        kind: 'datasetChart'
      }
      kittenPhase.value = KITTEN_PHASE.delivered
    }
  }

  const applyChartRecommendation = (rec: KittenChartRecommendation) => {
    setChartConfig(rec.config)
  }

  const handleFileSelect = async (e: Event) => {
    const input = e.target as HTMLInputElement
    const file = input.files?.[0]
    if (!file) return

    addMessage('user', `上传文件：${file.name}`)
    isDatasetParsing.value = true
    kittenPhase.value = KITTEN_PHASE.ingesting

    try {
      const { parseDatasetFile } = await loadDatasetParser()
      const data = await parseDatasetFile(file)
      const preview = generateDataPreview(data)
      const fieldNames = Array.isArray(data.columns) ? data.columns.map((c) => String(c)) : []

      datasetSummary.value = {
        name: file.name,
        rows: data.rows,
        columns: fieldNames.length,
        fieldNames,
        previewText: buildPreviewTextFromData(data)
      }
      datasetRows.value = Array.isArray(data.sampleRows) ? data.sampleRows : []
      fieldProfiles.value = Array.isArray(data.fieldProfiles) ? data.fieldProfiles : []
      const firstRecommendation = buildRecommendedCharts(fieldProfiles.value)[0]
      chartConfig.value = firstRecommendation?.config || emptyChartConfig()

      addMessage(
        'ai',
        `文件解析完成！<br>检测到 <strong>${data.rows} 行</strong> 数据，<strong>${fieldNames.length} 个字段</strong><br>${preview}`
      )

      currentResult.value = {
        id: Date.now(),
        title: '数据概览',
        summary: `${fieldNames.slice(0, 12).join('、')}${fieldNames.length > 12 ? '…' : ''}`,
        chart: Boolean(firstRecommendation),
        type: firstRecommendation ? 'chart' : 'table',
        kind: firstRecommendation ? 'datasetChart' : 'datasetOverview'
      }
      kittenPhase.value = KITTEN_PHASE.schemaReady
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      addMessage('ai', `文件解析失败：${msg}`)
      kittenPhase.value = KITTEN_PHASE.error
    } finally {
      isDatasetParsing.value = false
      input.value = ''
    }
  }

  const buildReportWorkbook = (XLSX: typeof import('xlsx')) => {
    const workbook = XLSX.utils.book_new()
    const now = new Date()
    const ds = datasetSummary.value
    const result = currentResult.value
    const summaryRows: (string | number)[][] = [
      ['报告标题', result?.title || 'AI 分析'],
      ['报告时间', now.toLocaleString('zh-CN')],
      ['分析阶段', kittenPhase.value],
      ['摘要', result?.summary || ''],
      ['来源', '小猫分析工作台']
    ]
    if (ds) {
      summaryRows.push(['数据文件', ds.name || ''])
      summaryRows.push(['数据规模', `${ds.rows || 0} 行 / ${ds.columns || 0} 列`])
    }
    XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(summaryRows), '报告摘要')

    const messageRows = messages.value.map((msg, idx) => ({
      序号: idx + 1,
      角色: msg.role === 'ai' ? 'AI' : '用户',
      时间: msg.time || '',
      内容: htmlToPlainText(msg.content)
    }))
    XLSX.utils.book_append_sheet(
      workbook,
      XLSX.utils.json_to_sheet(
        messageRows.length ? messageRows : [{ 序号: 1, 角色: '系统', 时间: '', 内容: '暂无对话记录' }]
      ),
      '对话记录'
    )

    if (ds) {
      const dataRows: (string | number)[][] = [
        ['文件名', ds.name || ''],
        ['总行数', ds.rows || 0],
        ['总列数', ds.columns || 0],
        ['字段列表', Array.isArray(ds.fieldNames) ? ds.fieldNames.join('、') : ''],
        ['预览文本', ds.previewText || '']
      ]
      XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(dataRows), '数据摘要')
    }

    if (chartConfig.value.xField) {
      const chartRows: (string | number)[][] = [
        ['图表类型', chartConfig.value.type],
        ['X 字段', chartConfig.value.xField],
        ['Y 字段', chartConfig.value.yField || '记录数'],
        ['分组字段', chartConfig.value.groupField || ''],
        ['聚合方式', chartConfig.value.aggregate]
      ]
      XLSX.utils.book_append_sheet(workbook, XLSX.utils.aoa_to_sheet(chartRows), '图表配置')
    }

    return workbook
  }

  const exportReportViaBackend = async () => {
    const payload = {
      phase: kittenPhase.value,
      result: currentResult.value || {},
      dataset: datasetSummary.value || null,
      chart: chartConfig.value.xField ? chartConfig.value : undefined,
      messages: messages.value || [],
      industry: localStorage.getItem('currentIndustry') || '通用行业',
      web_search_results: lastWebSearchHits.value.length ? lastWebSearchHits.value : undefined
    }
    const resp = await fetch(buildFullApiUrl('/api/ai/kitten/report/export'), {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!resp.ok) {
      let errText = ''
      try {
        errText = await resp.text()
      } catch {
        errText = ''
      }
      throw new Error(`后端导出失败（${resp.status}）${errText ? `：${errText.slice(0, 160)}` : ''}`)
    }
    const blob = await resp.blob()
    await assertKittenFileBlob(resp, blob, 'Excel 导出')
    const filename = getFilenameFromDisposition(
      resp.headers.get('content-disposition'),
      `小猫分析报告_${formatExportTimestamp()}.xlsx`
    )
    downloadBlob(blob, filename)
  }

  const exportDocxViaBackend = async () => {
    const payload = {
      phase: kittenPhase.value,
      result: currentResult.value || {},
      dataset: datasetSummary.value || null,
      chart: chartConfig.value.xField ? chartConfig.value : undefined,
      messages: messages.value || [],
      industry: localStorage.getItem('currentIndustry') || '通用行业',
      web_search_results: lastWebSearchHits.value.length ? lastWebSearchHits.value : undefined
    }
    const resp = await fetch(buildFullApiUrl('/api/ai/kitten/report/export-docx'), {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!resp.ok) {
      let errText = ''
      try {
        errText = await resp.text()
      } catch {
        errText = ''
      }
      throw new Error(`Word 导出失败（${resp.status}）${errText ? `：${errText.slice(0, 160)}` : ''}`)
    }
    const blob = await resp.blob()
    await assertKittenFileBlob(resp, blob, 'Word 导出')
    const filename = getFilenameFromDisposition(
      resp.headers.get('content-disposition'),
      `小猫分析报告_${formatExportTimestamp()}.docx`
    )
    downloadBlob(blob, filename)
  }

  const isDocGenLoading = ref(false)

  const generateAiOfficeDocument = async (prompt: string, format: 'docx' | 'xlsx') => {
    const p = (prompt || '').trim()
    if (!p) {
      await appAlert('请先描述要生成的文档内容')
      return
    }
    isDocGenLoading.value = true
    try {
      const resp = await fetch(buildFullApiUrl('/api/ai/kitten/document/generate'), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: p, format })
      })
      if (!resp.ok) {
        let msg = ''
        try {
          const j = await resp.json()
          msg = typeof j?.message === 'string' ? j.message : ''
        } catch {
          msg = await resp.text()
        }
        throw new Error(msg || `生成失败（${resp.status}）`)
      }
      const blob = await resp.blob()
      await assertKittenFileBlob(resp, blob, format === 'xlsx' ? '表格生成' : '文档生成')
      const filename = getFilenameFromDisposition(
        resp.headers.get('content-disposition'),
        format === 'xlsx' ? `生成表格_${formatExportTimestamp()}.xlsx` : `生成文档_${formatExportTimestamp()}.docx`
      )
      downloadBlob(blob, filename)
      addMessage('ai', `已生成并下载：<strong>${filename}</strong><br>（内容由模型起草，正式签署前请法务审核）`)
    } catch (err) {
      const errMessage = err instanceof Error ? err.message : '未知错误'
      await appAlert(`文档生成失败：${errMessage}`)
    } finally {
      isDocGenLoading.value = false
    }
  }

  const runFinancialBrief = async () => {
    const r = await safeJsonRequest<{
      success?: boolean
      message?: string
      data?: Record<string, unknown>
      analysis_id?: string
    }>('/api/ai/kitten/financial/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        metadata: { source: 'kitten-workbench', industry: localStorage.getItem('currentIndustry') || '' }
      })
    })
    if (!r.ok || r.data?.success === false) {
      const msg = (r.data as { message?: string })?.message || r.message || '财务简报生成失败'
      addMessage('ai', textToHtml(msg))
      return
    }
    const data = r.data?.data
    let summary = ''
    if (data && typeof data === 'object') {
      try {
        summary = JSON.stringify(data, null, 2)
      } catch {
        summary = String(data)
      }
    } else {
      summary = (r.data as { message?: string })?.message || '财务简报已生成'
    }
    const clipped = summary.length > 8000 ? `${summary.slice(0, 8000)}…` : summary
    addMessage('ai', textToHtml(`【财务简报】\n${clipped}`))
    kittenPhase.value = KITTEN_PHASE.delivered
  }

  const sendMessage = async () => {
    if (!inputText.value.trim()) return
    if (isChatLoading.value || isDatasetParsing.value) return

    const query = inputText.value.trim()
    addMessage('user', query)
    inputText.value = ''
    isChatLoading.value = true
    isKittenStreaming.value = false
    kittenPhase.value = KITTEN_PHASE.analyzing

    if (!kittenSessionUserId.value) {
      kittenSessionUserId.value = makeKittenUserId()
    }

    const finishWithAiText = (
      replyText: string,
      envelope: Record<string, unknown> | null,
      failed: boolean
    ) => {
      const hits = envelope ? extractWebSearchHits(envelope) : []
      lastWebSearchHits.value = hits
      const rid = Date.now()
      const plain = replyText
      currentResult.value = {
        id: rid,
        title: failed ? '请求失败' : 'AI 分析',
        summary: buildKittenResultSummary(plain),
        chart: false,
        type: failed ? 'error' : 'analysis',
        kind: failed ? 'chatError' : 'analysis'
      }
      kittenPhase.value = failed ? KITTEN_PHASE.error : KITTEN_PHASE.delivered
    }

    try {
      if (isChatStreamEnabled()) {
        isKittenStreaming.value = true
        const streamTime = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
        pushBounded(
          messages,
          { role: 'ai', content: '', time: streamTime },
          MAX_CHAT_MESSAGES
        )
        const aiIdx = messages.value.length - 1
        let streamPlain = ''
        let doneResult: unknown = null
        let sseError: string | null = null
        const controller = new AbortController()
        const killTimer = window.setTimeout(() => controller.abort(), KITTEN_CHAT_TIMEOUT_MS)
        let streamOk = false
        try {
          const res = await chatApi.sendChatStream(buildKittenChatPayload(query), {
            signal: controller.signal,
          })
          if (!res.ok) {
            throw new Error(await parseChatStreamErrorResponse(res))
          }
          await readPlannerSseResponse(res, (ev: PlannerSseEvent) => {
            if (ev.type === 'token') {
              streamPlain += ev.text || ''
              messages.value[aiIdx].content = textToHtml(streamPlain)
              scrollChatToBottom()
            } else if (ev.type === 'done') {
              doneResult = ev.result
            } else if (ev.type === 'error') {
              sseError = String(ev.message || '流式接口错误')
            } else if (ev.type === 'requires_token') {
              const tokenName = ev.token_name || ''
              const humanLabel = String(tokenName || '').toUpperCase().includes('READ')
                ? '一级数据库查看令牌'
                : '二级数据库写入令牌'
              streamPlain += `\n[需要${humanLabel}：${ev.token_description || tokenName || 'DB_TOKEN'}]\n`
              messages.value[aiIdx].content = textToHtml(streamPlain)
              scrollChatToBottom()
            }
          })
          if (sseError) {
            throw new Error(sseError)
          }
          const dr = doneResult as Record<string, unknown> | null
          const finalText =
            String((dr as { response?: string } | null)?.response ?? streamPlain).trim() ||
            streamPlain ||
            '（无内容）'
          messages.value[aiIdx].content = textToHtml(finalText)
          const failed = dr ? (dr as { success?: boolean }).success === false : false
          finishWithAiText(finalText, dr, failed)
          streamOk = true
        } catch (err) {
          const atIdx = messages.value[aiIdx]
          if (atIdx?.role === 'ai') {
            messages.value.splice(aiIdx, 1)
          }
          if (import.meta.env.DEV) {
            console.warn('kitten stream failed, falling back to JSON chat', err)
          }
        } finally {
          window.clearTimeout(killTimer)
          isKittenStreaming.value = false
        }
        if (streamOk) {
          return
        }
      }

      const jsonAbort = new AbortController()
      const jsonKill = window.setTimeout(() => jsonAbort.abort(), KITTEN_CHAT_TIMEOUT_MS)
      try {
        const result = await safeJsonRequest<Record<string, unknown>>(resolvePlannerChatPath(), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(buildKittenChatPayload(query)),
          signal: jsonAbort.signal
        })

        let replyText = ''
        if (result.ok && (result.data as { success?: boolean })?.success) {
          replyText = extractChatApiText(result.data as Record<string, unknown>)
        } else {
          const d = result.data as { message?: string } | null
          const errMsg = d?.message || result.message || '请求失败'
          replyText = `请求失败：${errMsg}`
        }

        if (!replyText.trim()) {
          replyText = '服务器未返回有效回复内容。'
        }

        addMessage('ai', textToHtml(replyText))
        const env = result.data as Record<string, unknown> | null
        const failed = !result.ok || !(result.data as { success?: boolean })?.success
        finishWithAiText(replyText, env, failed)
      } finally {
        window.clearTimeout(jsonKill)
      }
    } catch (err) {
      const raw = err instanceof Error ? err.message : String(err)
      const msg =
        err instanceof Error && err.name === 'AbortError'
          ? `请求超时（>${Math.floor(KITTEN_CHAT_TIMEOUT_MS / 1000)}s）或已中断`
          : raw
      addMessage('ai', textToHtml(`网络异常：${msg}`))
      currentResult.value = {
        id: Date.now(),
        title: '网络异常',
        summary: msg.slice(0, 220),
        chart: false,
        type: 'error',
        kind: 'networkError'
      }
      kittenPhase.value = KITTEN_PHASE.error
    } finally {
      isChatLoading.value = false
      isKittenStreaming.value = false
      scrollChatToBottom()
    }
  }

  const sendQuickAction = (btn: { text: string }) => {
    inputText.value = btn.text
    void sendMessage()
  }

  const exportResult = async () => {
    if (!currentResult.value) return
    try {
      await exportReportViaBackend()
    } catch (backendErr) {
      console.warn('后端导出失败，回退前端本地导出：', backendErr)
      try {
        const XLSX = await loadXlsx()
        const workbook = buildReportWorkbook(XLSX)
        const workbookArray = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' })
        const blob = new Blob([workbookArray], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })
        const fileName = `小猫分析报告_${formatExportTimestamp()}.xlsx`
        downloadBlob(blob, fileName)
      } catch (err) {
        console.error('导出报告失败:', err)
        const errMessage = err instanceof Error ? err.message : '未知错误'
        await appAlert(`导出失败：${errMessage}`)
      }
    }
  }

  const exportDocx = async () => {
    if (!currentResult.value) return
    try {
      await exportDocxViaBackend()
    } catch (err) {
      console.error('Word 导出失败:', err)
      const errMessage = err instanceof Error ? err.message : '未知错误'
      await appAlert(`Word 导出失败：${errMessage}`)
    }
  }

  const clearResult = () => {
    currentResult.value = null
    kittenPhase.value = hasDataset.value ? KITTEN_PHASE.schemaReady : KITTEN_PHASE.idle
  }

  const handleInputKeydown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void sendMessage()
    }
  }

  onMounted(() => {
    scrollChatToBottom()
  })

  return {
    messages,
    inputText,
    isChatLoading,
    isKittenStreaming,
    isDatasetParsing,
    kittenPhase,
    currentResult,
    fileInput,
    chatMessagesRef,
    datasetSummary,
    datasetRows,
    fieldProfiles,
    chartConfig,
    recommendedCharts,
    kittenIncludeBusinessDb,
    kittenIncludeWebSearch,
    kittenDbStatsHint,
    lastWebSearchHits,
    kittenQuickActions,
    datasetFieldPreview,
    lastDocumentPickupUrl,
    loadingStatusText,
    resetSession,
    onKittenBusinessDbToggle,
    triggerFileUpload,
    handleFileSelect,
    setChartConfig,
    applyChartRecommendation,
    sendMessage,
    sendQuickAction,
    exportResult,
    exportDocx,
    isDocGenLoading,
    generateAiOfficeDocument,
    runFinancialBrief,
    clearResult,
    handleInputKeydown
  }
}
