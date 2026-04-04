import { ref, computed, nextTick, onMounted, watch, type Ref } from 'vue'
import { KITTEN_PHASE, useKittenWorkflowState } from '@/composables/useKittenWorkflowState'
import { downloadBlob, getFilenameFromDisposition } from '@/utils'
import { safeJsonRequest } from '@/utils/safeJsonRequest'

const MAX_CHAT_MESSAGES = 120
const KITTEN_SNAPSHOT_CACHE_MS = 90_000

export const KITTEN_WELCOME_HTML =
  '欢迎使用 <strong>AI生态分析助手</strong><br><br>我可以：<br>・ 解析上传的Excel/CSV/JSON文件<br>・ 理解自然语言分析需求<br>・ 自动识别字段、清洗数据<br>・ 生成图表和分析报告<br><br>请上传文件或直接输入需求开始。'

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

function extractChatApiText(data: Record<string, unknown> | null | undefined): string {
  if (!data || typeof data !== 'object') return ''
  if (typeof data.response === 'string' && data.response.trim()) return data.response.trim()
  const inner = data.data as Record<string, unknown> | undefined
  if (inner && typeof inner.text === 'string' && inner.text.trim()) return inner.text.trim()
  return ''
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

function formatExportTimestamp(date = new Date()): string {
  const pad = (num: number) => String(num).padStart(2, '0')
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}_${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`
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
  const isDatasetParsing = ref(false)
  const kittenPhase = ref(KITTEN_PHASE.idle)
  const currentResult = ref<KittenAnalysisResult | null>(null)
  const fileInput = ref<HTMLInputElement | null>(null)
  const chatMessagesRef = ref<HTMLElement | null>(null)

  const datasetSummary = ref<KittenDatasetSummary | null>(null)
  const kittenIncludeBusinessDb = ref(false)
  const kittenDbStatsHint = ref('')
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
      kitten_include_business_db: kittenIncludeBusinessDb.value
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

  const buildKittenChatPayload = (query: string) => ({
    message: query,
    user_id: kittenSessionUserId.value,
    source: 'pro',
    mode: 'pro',
    context: buildKittenRequestContext()
  })

  const hasDataset = computed(() => Boolean(datasetSummary.value))
  const { activeStepIndex: activeWorkflowStepIndex, activeLayerKey: activeOrgLayerKey } =
    useKittenWorkflowState(kittenPhase, hasDataset)

  const datasetFieldPreview = computed(() => {
    const names = datasetSummary.value?.fieldNames
    if (!Array.isArray(names)) return []
    return names.slice(0, 8)
  })

  const loadingStatusText = computed(() => {
    if (isDatasetParsing.value) return '正在解析数据文件...'
    if (isChatLoading.value) return 'AI 正在分析数据...'
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
    kittenIncludeBusinessDb.value = false
    kittenDbStatsHint.value = ''
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

      addMessage(
        'ai',
        `文件解析完成！<br>检测到 <strong>${data.rows} 行</strong> 数据，<strong>${fieldNames.length} 个字段</strong><br>${preview}`
      )

      currentResult.value = {
        id: Date.now(),
        title: '数据概览',
        summary: `${fieldNames.slice(0, 12).join('、')}${fieldNames.length > 12 ? '…' : ''}`,
        chart: false,
        type: 'table',
        kind: 'datasetOverview'
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

    return workbook
  }

  const exportReportViaBackend = async () => {
    const payload = {
      phase: kittenPhase.value,
      result: currentResult.value || {},
      dataset: datasetSummary.value || null,
      messages: messages.value || [],
      industry: localStorage.getItem('currentIndustry') || '通用行业'
    }
    const resp = await fetch('/api/ai/kitten/report/export', {
      method: 'POST',
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
    const filename = getFilenameFromDisposition(
      resp.headers.get('content-disposition'),
      `小猫分析报告_${formatExportTimestamp()}.xlsx`
    )
    downloadBlob(blob, filename)
  }

  const sendMessage = async () => {
    if (!inputText.value.trim()) return
    if (isChatLoading.value || isDatasetParsing.value) return

    const query = inputText.value.trim()
    addMessage('user', query)
    inputText.value = ''
    isChatLoading.value = true
    kittenPhase.value = KITTEN_PHASE.analyzing

    if (!kittenSessionUserId.value) {
      kittenSessionUserId.value = makeKittenUserId()
    }

    try {
      const result = await safeJsonRequest<Record<string, unknown>>('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildKittenChatPayload(query))
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
      const rid = Date.now()
      const plain = replyText
      const failed = !result.ok || !(result.data as { success?: boolean })?.success
      currentResult.value = {
        id: rid,
        title: failed ? '请求失败' : 'AI 分析',
        summary: plain.slice(0, 220) + (plain.length > 220 ? '…' : ''),
        chart: false,
        type: failed ? 'error' : 'analysis',
        kind: failed ? 'chatError' : 'analysis'
      }
      kittenPhase.value = failed ? KITTEN_PHASE.error : KITTEN_PHASE.delivered
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
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
        window.alert(`导出失败：${errMessage}`)
      }
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
    isDatasetParsing,
    kittenPhase,
    currentResult,
    fileInput,
    chatMessagesRef,
    datasetSummary,
    kittenIncludeBusinessDb,
    kittenDbStatsHint,
    kittenWorkflowSteps,
    kittenOrgCards,
    kittenQuickActions,
    activeWorkflowStepIndex,
    activeOrgLayerKey,
    datasetFieldPreview,
    loadingStatusText,
    resetSession,
    onKittenBusinessDbToggle,
    triggerFileUpload,
    handleFileSelect,
    sendMessage,
    sendQuickAction,
    exportResult,
    clearResult,
    handleInputKeydown
  }
}
