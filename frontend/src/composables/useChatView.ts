import { ref, computed, watch, onMounted, onBeforeUnmount, type Ref } from 'vue'
import { useRouter } from 'vue-router'
import { useTutorialStore } from '@/stores/tutorial'
import { useModsStore } from '@/stores/mods'
import { useWorkflowAiEmployeesStore } from '@/stores/workflowAiEmployees'
import {
  buildModWorkflowPanelMeta,
  findWorkflowEmployeeEntry,
  resolvePhoneAgentApiBase,
} from '@/utils/modWorkflowEmployees'
import { useChatMessages, type ChatMessage } from './useChatMessages'
import { useShipmentTask, type ShipmentTask } from './useShipmentTask'
import { usePrintService } from './usePrintService'
import { useExcelAnalysis } from './useExcelAnalysis'
import { isStartPrintMessage, detectRuntimeModeCommand, normalizeModel, toNumber } from '../utils/textParser'
import chatApi from '../api/chat'
import productsApi from '../api/products'
import { inferWechatCustomerIntent } from '@/utils/wechatIntent'
import { fetchShipmentRecordsForUnit, summarizeShipmentRecordsForAudit } from '@/utils/shipmentMgmtPostPrint'

/** 刷新后仍能把「分析 Excel」结果随 /api/ai/chat 的 context 带上，避免「加入数据库」落 LLM 空转 */
const EXCEL_ANALYSIS_STORAGE_PREFIX = 'xcagi_excel_analysis_ctx_'

function readPersistedExcelAnalysisContext(sessionKey: string): Record<string, any> | null {
  if (typeof sessionStorage === 'undefined') return null
  try {
    const raw = sessionStorage.getItem(EXCEL_ANALYSIS_STORAGE_PREFIX + sessionKey)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}

function persistExcelAnalysisContext(sessionKey: string, ctx: Record<string, any> | null) {
  if (typeof sessionStorage === 'undefined') return
  try {
    const key = EXCEL_ANALYSIS_STORAGE_PREFIX + sessionKey
    if (!ctx) sessionStorage.removeItem(key)
    else sessionStorage.setItem(key, JSON.stringify(ctx))
  } catch {
    /* quota / private mode */
  }
}

/** 从常见「查价/查型号」话术里抽关键词，用于在等 AI 完整响应前先打开产品副窗并行查库 */
function extractLikelyProductQueryKeyword(raw: string): string | null {
  const t = String(raw || '').trim()
  if (t.length < 2 || t.length > 200) return null
  if (/^(什么|怎么|如何|为什么|能否|请|帮)/.test(t)) return null
  if (/(出货单|发货单|订单列表|客户列表|工作流|批量|导入|上传|数据库|打印标签|打印\s|有哪些客户|今天.*单)/.test(t)) {
    return null
  }
  const patterns: RegExp[] = [
    /^查询\s*(.+)$/u,
    /^查一下\s*(.+?)\s*的?(?:价格|价钱|多少钱)?\s*[。！？…]*$/iu,
    /^帮我查(?:询)?\s*(.+?)\s*(?:的)?(?:价格|多少钱)?\s*[。！？…]*$/iu
  ]
  for (const re of patterns) {
    const m = t.match(re)
    if (m?.[1]) {
      let k = String(m[1]).trim().replace(/[。！？…]+$/g, '').trim()
      if ((k.startsWith('「') && k.endsWith('」')) || (k.startsWith('"') && k.endsWith('"')) || (k.startsWith('『') && k.endsWith('』'))) {
        k = k.slice(1, -1).trim()
      }
      k = k.replace(/^(产品|型号|货号)[是为：:\s]+/i, '').trim()
      if (k.length >= 1 && k.length <= 120) return k
    }
  }
  return null
}

export interface UseChatViewOptions {
  sessionId: Ref<string>
  proIntentExperienceEnabled?: Ref<boolean>
}

type TaskStatus = 'queued' | 'running' | 'success' | 'failed' | 'cancelled'

interface TaskItem {
  id: string
  type: string
  title: string
  source: 'workflow' | 'excel' | 'print' | 'shipment' | 'manual' | 'system' | 'wechat'
  status: TaskStatus
  progress?: number
  stage?: string
  summary?: string
  error?: string
  startedAt: number
  updatedAt: number
  messageRef?: string
  payload?: Record<string, any>
}

export function useChatView(options: UseChatViewOptions) {
  const router = useRouter()
  const tutorialStore = useTutorialStore()
  const modsStore = useModsStore()
  const workflowAiEmployeesStore = useWorkflowAiEmployeesStore()
  const { sessionId } = options
  const proIntentExperienceEnabled = options.proIntentExperienceEnabled

  const {
    messages,
    lastMessage,
    addMessage,
    addAndSaveMessage,
    clearMessages,
    loadMessages,
    syncFromServer
  } = useChatMessages(sessionId)

  const currentTask = ref<ShipmentTask | null>(null)
  const orderNumberFetching = ref(false)
  const isLoading = ref(false)
  const isExecuting = ref(false)
  const latestAssistantPush = ref<{ title: string; description: string } | null>(null)
  const proRuntimeTask = ref<{ title: string; statusText: string; statusClass: string; description: string } | null>(null)
  const taskList = ref<TaskItem[]>([])
  const activeTaskId = ref<string>('')
  const expandedTaskIds = ref<string[]>([])
  const taskFilter = ref<'all' | 'running' | 'success' | 'failed'>('all')
  const TASK_HISTORY_LIMIT = 20

  const {
    lastShipmentExecution,
    handleModifyCommand: handleShipmentModify,
    hydrateTaskOrderNumber,
    enrichShipmentPreviewProducts,
    getTaskTableColumns,
    getTaskTableItems,
    getTaskOrderNumber
  } = useShipmentTask({ addAndSaveMessage }, currentTask)

  const {
    isPrinting,
    executePrintTask,
    buildPrintSummaryMessage
  } = usePrintService()

  const lastExcelAnalysisContext = ref<Record<string, any> | null>(null)
  const linkedExcelSheet = ref<{ sheet_name: string; sheet_index: number } | null>(null)

  const {
    excelAnalyzeUploading,
    excelAnalyzeInputRef,
    triggerExcelAnalyzeUpload,
    onExcelAnalyzeFileChange
  } = useExcelAnalysis(
    { addAndSaveMessage },
    {
      onAnalyzed: ({ fileName, summary, result }) => {
        const payload = {
          file_name: fileName,
          summary,
          fields: Array.isArray(result?.fields) ? result.fields : [],
          preview_data: result?.preview_data || {},
          sheets: Array.isArray(result?.sheets) ? result.sheets : []
        }
        lastExcelAnalysisContext.value = payload
        const names = Array.isArray(result?.preview_data?.sheet_names) ? result.preview_data.sheet_names : []
        const allSheets = Array.isArray(result?.sheets)
          ? result.sheets
          : (Array.isArray(result?.preview_data?.all_sheets) ? result.preview_data.all_sheets : [])
        const firstSheetName = String(allSheets?.[0]?.sheet_name || names?.[0] || result?.preview_data?.sheet_name || '').trim()
        linkedExcelSheet.value = firstSheetName ? { sheet_name: firstSheetName, sheet_index: 1 } : null
        window.dispatchEvent(new CustomEvent('xcagi:excel-sheet-context', {
          detail: {
            selected_sheet: linkedExcelSheet.value,
            excel_analysis: payload
          }
        }))
        const sid = String(sessionId.value || '').trim() || 'default'
        persistExcelAnalysisContext(sid, payload)
        const task = taskList.value.find((t) => t.type === 'excel_analyze' && t.status === 'running')
        if (task) {
          upsertTask({
            id: task.id,
            title: task.title,
            type: task.type,
            source: task.source,
            status: 'success',
            progress: 100,
            summary,
            messageRef: getLastAiMessageRef()
          })
        }
      },
      onAnalyzeStart: ({ fileName }) => {
        upsertTask({
          id: createTaskId('excel'),
          title: `分析Excel：${fileName}`,
          type: 'excel_analyze',
          source: 'excel',
          status: 'running',
          progress: 5
        })
      },
      onAnalyzeProgress: ({ step, progress }) => {
        const task = taskList.value.find((t) => t.type === 'excel_analyze' && t.status === 'running')
        if (!task) return
        upsertTask({
          id: task.id,
          title: task.title,
          type: task.type,
          source: task.source,
          status: 'running',
          progress: progress ?? task.progress,
          stage: step
        })
      },
      onAnalyzeDone: ({ success, message }) => {
        const task = taskList.value.find((t) => t.type === 'excel_analyze' && t.status === 'running')
        if (!task) return
        if (success) {
          finishTask(task.id, task.summary || 'Excel 分析完成')
        } else {
          failTask(task.id, message || 'Excel 分析失败')
        }
      }
    }
  )

  const showHistory = ref(false)
  const historySessions = ref<any[]>([])
  const pushCopied = ref(false)
  const chatMessagesRef = ref<HTMLElement | null>(null)
  const loadingProgressText = ref('处理中...')
  let waitProgressTicker: number | null = null
  const lastRequestContextSummary = ref('')

  const isProMode = ref(false)
  const excelSheetOptions = computed(() => {
    const ctx = resolveExcelAnalysisContextForRequest()
    if (!ctx) return [] as Array<{ sheet_name: string; sheet_index: number }>
    const result: Array<{ sheet_name: string; sheet_index: number }> = []
    const allSheets = Array.isArray(ctx?.preview_data?.all_sheets) ? ctx.preview_data.all_sheets : []
    if (allSheets.length) {
      allSheets.forEach((s: any, idx: number) => {
        const name = String(s?.sheet_name || '').trim()
        if (name) result.push({ sheet_name: name, sheet_index: Number(s?.sheet_index) || idx + 1 })
      })
    } else {
      const names = Array.isArray(ctx?.preview_data?.sheet_names) ? ctx.preview_data.sheet_names : []
      names.forEach((name: any, idx: number) => {
        const n = String(name || '').trim()
        if (n) result.push({ sheet_name: n, sheet_index: idx + 1 })
      })
    }
    return result
  })
  const taskTableColumns = computed(() => getTaskTableColumns(currentTask.value as any))
  const taskTableItems = computed(() => getTaskTableItems(currentTask.value as any))
  const taskOrderNumber = computed(() => getTaskOrderNumber(currentTask.value))

  function generateSessionId(): string {
    return Date.now().toString(36) + Math.random().toString(36).substr(2)
  }

  function scrollToBottom() {
    if (chatMessagesRef.value) {
      chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight
    }
  }

  function normalizeServerContentToHtml(raw: unknown): string {
    const text = String(raw || '')
    if (/<[a-z][\s\S]*>/i.test(text)) return text
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML.replace(/\n/g, '<br>')
  }

  function createTaskId(prefix: string): string {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  }

  function sortTaskList() {
    taskList.value.sort((a, b) => {
      const rank = (s: TaskStatus) => (s === 'running' ? 0 : s === 'queued' ? 1 : s === 'failed' ? 2 : s === 'success' ? 3 : 4)
      const r = rank(a.status) - rank(b.status)
      if (r !== 0) return r
      // 状态相同时，按 startedAt 升序排列（先创建的任务在前面），避免频繁更新导致顺序抖动
      const startedDiff = (a.startedAt || 0) - (b.startedAt || 0)
      if (startedDiff !== 0) return startedDiff
      // 如果 startedAt 也相同，使用 id 作为稳定排序键
      return a.id.localeCompare(b.id)
    })
    if (taskList.value.length > TASK_HISTORY_LIMIT) {
      taskList.value = taskList.value.slice(0, TASK_HISTORY_LIMIT)
    }
  }

  function upsertTask(partial: Partial<TaskItem> & { id: string; title: string; source: TaskItem['source']; type: string }) {
    const now = Date.now()
    const idx = taskList.value.findIndex((t) => t.id === partial.id)
    if (idx === -1) {
      taskList.value.unshift({
        id: partial.id,
        title: partial.title,
        type: partial.type,
        source: partial.source,
        status: partial.status || 'queued',
        progress: partial.progress,
        stage: partial.stage,
        summary: partial.summary,
        error: partial.error,
        startedAt: partial.startedAt || now,
        updatedAt: now,
        messageRef: partial.messageRef,
        payload: partial.payload || {}
      })
    } else {
      const current = taskList.value[idx]
      taskList.value[idx] = {
        ...current,
        ...partial,
        payload: { ...(current.payload || {}), ...(partial.payload || {}) },
        updatedAt: now
      } as TaskItem
    }
    if (!activeTaskId.value) activeTaskId.value = partial.id
    sortTaskList()
  }

  function finishTask(id: string, summary: string = '') {
    const task = taskList.value.find((t) => t.id === id)
    if (!task) return
    upsertTask({
      id,
      title: task.title,
      type: task.type,
      source: task.source,
      status: 'success',
      progress: 100,
      summary: summary || task.summary
    })
  }

  function failTask(id: string, error: string) {
    const task = taskList.value.find((t) => t.id === id)
    if (!task) return
    upsertTask({
      id,
      title: task.title,
      type: task.type,
      source: task.source,
      status: 'failed',
      error
    })
  }

  function cancelTaskById(id: string) {
    const task = taskList.value.find((t) => t.id === id)
    if (!task) return
    upsertTask({
      id,
      title: task.title,
      type: task.type,
      source: task.source,
      status: 'cancelled',
      summary: '任务已取消'
    })
  }

  function retryTask(id: string) {
    const task = taskList.value.find((t) => t.id === id)
    if (!task) return
    upsertTask({
      id,
      title: `${task.title}（重试）`,
      type: task.type,
      source: task.source,
      status: 'running',
      progress: 0,
      error: ''
    })
  }

  function toggleTaskExpanded(id: string) {
    if (expandedTaskIds.value.includes(id)) {
      expandedTaskIds.value = expandedTaskIds.value.filter((x) => x !== id)
    } else {
      expandedTaskIds.value = [...expandedTaskIds.value, id]
    }
  }

  /** 副窗星标轮询 + 微信 AI 员工链路：写入右侧任务列表（仅 API/事件，不模拟点击） */
  function onWechatAiTaskEnqueue(evt: Event) {
    const d = (evt as CustomEvent).detail || {}
    const msg = String(d.messageText || '').trim()
    const contactId = String(d.contactId ?? '').trim()
    if (!msg && !contactId) return
    const taskId = createTaskId('wechat_ai')
    const name = String(d.contactName || '星标联系人').trim()
    const title = `微信消息处理 · ${name}`
    const lines: string[] = []
    if (msg) lines.push(`最新消息：${msg}`)
    lines.push(`预处理意图：${String(d.intentLabel || '—').trim()}`)
    const idetail = String(d.intentDetail || '').trim()
    if (idetail) lines.push(idetail)
    const pi = String(d.primaryIntent || '').trim()
    if (pi) lines.push(`primary_intent：${pi}`)
    const toolKey = String(d.toolKey || '').trim()
    if (toolKey) lines.push(`tool_key：${toolKey}`)
    upsertTask({
      id: taskId,
      type: 'wechat_intent',
      source: 'wechat',
      title,
      status: 'success',
      progress: 100,
      stage: d.sourceApi === 'intent_test' ? '专业模式·意图 API' : '本地规则预处理',
      summary: lines.join('\n'),
      payload: { ...d }
    })

    const wf = taskList.value.find((t) => t.id === 'workflow_emp_wechat_msg')
    if (wf) {
      upsertWorkflowEmployeeTask('wechat_msg', {
        lastWechat: {
          at: Date.now(),
          line: `${name}：${msg.replace(/\s+/g, ' ').slice(0, 120)}`,
        },
      })
    }
  }

  /** 与副窗「一键托管」员工开关一致：启用后在任务面板展示工作流状态 */
  const WORKFLOW_AI_EMPLOYEES_STORAGE_KEY = 'xcagi_workflow_ai_employees'
  const STAR_REFRESH_STORAGE_KEY = 'xcagi_auto_refresh_starred_wechat'
  const PRO_INTENT_STORAGE_KEY = 'xcagi_pro_intent_experience'

  type WorkflowStepRow = { id: string; label: string; status: 'done' | 'active' | 'pending' }

  const WORKFLOW_EMPLOYEE_PANEL_META: Record<string, { title: string; summary: string }> = {
    label_print: {
      title: '工作流 · 标签打印 AI 员工',
      summary:
        '仅接收星标微信经意图预处理后的「标签/打印」类信号（与微信消息员工共用星标轮询与同一套意图规则）。未命中前不推进执行；命中后请在智能对话补充型号/张数并触发打印。',
    },
    shipment_mgmt: {
      title: '工作流 · 出货管理 AI 员工',
      summary:
        '对话完成发货单并在「开始打印」成功后，自动拉取本单位出货记录做统计与审计，并给出保存（导出 Excel 存档）与推送（转发摘要/文件）建议。生成环节已写入数据库，打印后侧重核对与对外同步。',
    },
    receipt_confirm: {
      title: '工作流 · 收货确认 AI 员工',
      summary:
        '与「微信消息处理」共用星标轮询与同一套意图预处理：客户发来收货、到货、签收、对账等反馈时，自动把对应联系人与业务进程摘要写入本工作流，便于在对话中跟进确认。',
    },
    wechat_msg: {
      title: '工作流 · 微信消息处理 AI 员工',
      summary:
        '整条链路：启用员工 → 星标自动刷新 → 拉取消息与推送 → 意图预处理 → 结果写入本列表。下方为各步状态与当前工作情况。',
    },
    // 微信电话 / 真实电话：标题与摘要由各 Mod manifest.workflow_employees 提供（buildModWorkflowPanelMeta）
  }

  function resolveWorkflowEmployeePanelMeta(empId: string): { title: string; summary: string } | null {
    const builtIn = WORKFLOW_EMPLOYEE_PANEL_META[empId]
    if (builtIn) return builtIn
    const modMap = buildModWorkflowPanelMeta(modsStore.modsForUi)
    return modMap[empId] || null
  }

  /** 关闭 Mod 界面或 manifest 无该员工时，去掉任务面板中已无 meta 的工作流项 */
  function pruneStaleWorkflowEmployeeTasks() {
    for (let i = taskList.value.length - 1; i >= 0; i--) {
      const t = taskList.value[i]
      if (t?.type !== 'workflow_employee') continue
      const id = t.id
      if (typeof id !== 'string' || !id.startsWith('workflow_emp_')) continue
      const empId = id.slice('workflow_emp_'.length)
      if (resolveWorkflowEmployeePanelMeta(empId)) continue
      taskList.value.splice(i, 1)
      if (activeTaskId.value === id) {
        activeTaskId.value = taskList.value[0]?.id || ''
      }
    }
  }

  /** 与 GET /api/mod/sz-qsm-pro/phone-agent/status 的 data 对齐，并带 lastPolledAt */
  type PhoneAgentStatusPayload = {
    phone_channel?: 'wechat' | 'adb' | string
    running?: boolean
    window_monitor_available?: boolean
    audio_capture_available?: boolean
    asr_available?: boolean
    intent_handler_available?: boolean
    tts_available?: boolean
    vb_cable_available?: boolean
    /** 本机 TTS 写入的 VB 播放设备名（系统「播放」列表里那路，常见名含 CABLE Input） */
    vb_cable_playback_device_name?: string | null
    /** 当前写入采样率（与解码一致），多为 44100/48000 */
    vb_cable_stream_sample_hz?: number | null
    ffmpeg_on_path?: boolean
    /** ffmpeg 或 miniaudio 至少一种可用即可解码 MP3 */
    mp3_decode_available?: boolean
    /** 后端提示：微信麦克风须选 CABLE Output 对方才能听到合成音 */
    remote_hear_tts_hint?: string
    /** VB：以声音设置为准——CABLE Input 在播放侧、CABLE Output 在录制侧（勿按字面 Input=录制） */
    vb_cable_roles_zh?: string
    lastPolledAt?: number
    /** 后端 window_monitor 上报：识别到微信来电弹窗 */
    last_popup_detected_at_ms?: number
    last_popup_source?: string
    last_popup_title?: string
    last_popup_class_name?: string
    last_popup_hwnd?: number | null
    last_popup_w?: number | null
    last_popup_h?: number | null
    /** 后端上报：自动接听点击 */
    last_click_at_ms?: number | null
    last_click_ok?: boolean | null
    last_click_method?: string | null
    last_click_x?: number | null
    last_click_y?: number | null
    last_click_error?: string | null
    last_opening_at_ms?: number | null
    last_opening_ok?: boolean | null
    last_opening_error?: string | null
    last_call_ended_at_ms?: number | null
    last_call_end_reason?: string | null
    /** 最近一次对方语音 ASR 文本与时间（与 ⑤ 监控行对应） */
    last_asr_text?: string | null
    last_asr_at_ms?: number | null
    last_reply_text?: string | null
    last_reply_at_ms?: number | null
    last_pipeline_error?: string | null
    /** 兼容旧字段：与 phone_asr_rms_speech_hi 相同 */
    phone_asr_rms_silence_threshold?: number
    phone_asr_rms_speech_hi?: number
    phone_asr_rms_silence_lo?: number
    phone_capture_peak_rms_since_last_poll?: number
    phone_input_devices?: Array<{ index: number; name: string }>
    phone_asr_hint?: string
    /** wasapi_loopback | pyaudio | none */
    phone_capture_backend?: string
    /** false 表示采音线程已退出，RMS 会持续≈0 */
    phone_capture_thread_alive?: boolean | null
    /** 后端给出的采音故障说明（若有） */
    phone_capture_problem_zh?: string
    phone_audio_capture_started_ok?: boolean
    /** Whisper 模型名，如 tiny、base */
    phone_whisper_model?: string
    phone_whisper_backend?: string
    phone_whisper_device?: string
    phone_whisper_compute_type?: string
    /** 拉取 /phone-agent/status 失败时的原因（网络、HTTP、后端 message） */
    fetchError?: string
    phone_agent_manager_load_failed?: boolean
    phone_agent_manager_load_message?: string
    /** 后端 get_status() 抛错时由 /status 降级返回 */
    phone_agent_get_status_failed?: boolean
    phone_agent_get_status_message?: string
    phone_agent_status_route_failed?: boolean
    phone_agent_status_route_message?: string
    /** 最近一次 POST /start 失败或 start() 异常原因（便于「未运行」时对照） */
    phone_agent_last_start_error?: string | null
    /** 轮询瞬间是否检测到微信通话中界面（含手动接听） */
    phone_in_call_ui_visible?: boolean
    /** window_monitor 会话：自动接听成功后直至挂断 */
    phone_wechat_call_session_active?: boolean
    /** PhoneAgentManager：接听成功后的语音会话标志（与上项通常同步） */
    phone_agent_voice_session_active?: boolean
    adb_available?: boolean
    adb_device_connected?: boolean
    adb_device_serial?: string | null
    adb_call_state?: string | null
    adb_last_poll_at_ms?: number | null
    adb_last_answer_at_ms?: number | null
    adb_last_answer_ok?: boolean | null
    adb_last_error?: string | null
    /** 后端是否已安装 pywin32（微信来电窗口监控；与 TTS/VB 无关） */
    phone_pywin32_installed?: boolean
    /** 窗口监控不可用时的人读说明（例如缺 pywin32） */
    phone_window_monitor_hint_zh?: string | null
  }

  /** 是否进入「真实来电/通话」步骤进度（否则仅显示链路待命，不计百分比） */
  function phoneAgentWorkflowProgressShouldStart(ps: PhoneAgentStatusPayload | null | undefined): boolean {
    if (!ps?.running) return false
    if (ps.last_popup_detected_at_ms != null && ps.last_popup_detected_at_ms !== undefined) return true
    if (ps.last_click_at_ms != null && ps.last_click_at_ms !== undefined) return true
    if (ps.last_opening_at_ms != null && ps.last_opening_at_ms !== undefined) return true
    if (ps.last_asr_at_ms != null && ps.last_asr_at_ms !== undefined) return true
    if (ps.phone_in_call_ui_visible === true) return true
    if (ps.phone_wechat_call_session_active === true) return true
    if (ps.phone_agent_voice_session_active === true) return true
    return false
  }

  /** 与后端 phone_agent 的 click_attempt.error 对齐，便于任务面板可读 */
  function formatPhoneClickError(code: string | null | undefined): string {
    const c = String(code || '').trim()
    if (!c) return ''
    const map: Record<string, string> = {
      wechat_not_minimized_manual_required: '微信主窗口需最小化或收进托盘后再自动接听',
      wechat_main_visible_manual_required: '微信主窗口需最小化或收进托盘后再自动接听',
      no_hwnd: '未取到来电窗口句柄，无法自动点击',
    }
    return map[c] || c
  }

  /** click_attempt.method：模板/坐标等方式说明 */
  function formatPhoneClickMethod(method: string | null | undefined): string {
    const m = String(method || '').trim()
    if (!m) return '—'
    const map: Record<string, string> = {
      fallback_geometry: '几何坐标兜底（未命中屏幕模板时）',
    }
    return map[m] || m
  }

  function formatOpeningError(code: string | null | undefined): string {
    const c = String(code || '').trim()
    if (!c) return '原因未知，请看后端日志'
    const map: Record<string, string> = {
      vb_play_pcm_decode_failed: 'MP3解码失败：pip install miniaudio（可无 ffmpeg）后重启后端',
      tts_or_vb_unavailable: 'TTS 或 VB-Cable 未就绪',
      tts_synthesize_failed: 'TTS 合成失败',
    }
    return map[c] || c
  }

  function formatCallEndReason(reason: string | null | undefined): string {
    const r = String(reason || '').trim()
    const map: Record<string, string> = {
      in_call_ui_gone: '通话界面已消失',
      in_call_ui_never_detected_timeout: '未识别到通话界面（已清空）',
    }
    return map[r] || r || '—'
  }

  function formatPhonePipelineError(code: string | null | undefined): string {
    const c = String(code || '').trim()
    if (!c) return ''
    const map: Record<string, string> = {
      tts_vb_play_failed: 'TTS 已合成但 VB 解码/入队失败',
      tts_synthesize_failed: 'TTS 合成失败',
    }
    return map[c] || c
  }

  const PHONE_AGENT_POLL_MS = 2000
  let phoneAgentPollTimer: ReturnType<typeof setInterval> | null = null

  function resolvePhoneChannelByEmployee(empId: string): 'wechat' | 'adb' {
    return empId === 'real_phone' ? 'adb' : 'wechat'
  }

  /** 所有已启用的电话类员工（微信 / ADB 各一条，需分别带 channel 拉 status）；无 manifest 时不算启用 */
  function getEnabledPhoneEmployeeIds(): Array<'wechat_phone' | 'real_phone'> {
    const enabled = readWorkflowEmployeeEnabledMap()
    const out: Array<'wechat_phone' | 'real_phone'> = []
    if (enabled.wechat_phone && resolveWorkflowEmployeePanelMeta('wechat_phone')) out.push('wechat_phone')
    if (enabled.real_phone && resolveWorkflowEmployeePanelMeta('real_phone')) out.push('real_phone')
    return out
  }

  /** 与 manifest 对齐；原版模式或未加载 Mod 时返回空字符串，禁止隐式请求 /api/mod/* */
  function getPhoneAgentApiBase(empId: string): string {
    const e = findWorkflowEmployeeEntry(modsStore.modsForUi, empId)
    if (e) {
      const b = resolvePhoneAgentApiBase(e, e.modId)
      if (b) return b
    }
    return ''
  }

  /** 与 TopAssistantFloat 一致：启用微信电话员工时应启动后端 phone-agent。重启 run.py 后 _running 为 false，仅靠 localStorage 开关不会再次 POST /start，故在轮询侧兜底。 */
  async function requestPhoneAgentStart(empId: 'wechat_phone' | 'real_phone'): Promise<void> {
    const base = getPhoneAgentApiBase(empId).replace(/\/+$/, '')
    if (!base) return
    const ch = resolvePhoneChannelByEmployee(empId)
    try {
      const resp = await fetch(`${base}/start?channel=${ch}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel: ch }),
      })
      const raw = await resp.text()
      let data: { success?: boolean; message?: string; error?: string } = {}
      try {
        data = raw ? (JSON.parse(raw) as typeof data) : {}
      } catch {
        data = {}
      }
      if (!data.success) {
        const msg =
          (typeof data.message === 'string' && data.message.trim()) ||
          (typeof data.error === 'string' && data.error.trim()) ||
          (resp.ok ? '未知错误' : `HTTP ${resp.status}`)
        const hint = !raw.trim().startsWith('{') ? raw.slice(0, 200) : ''
        console.warn('[奇士美 PRO] phone-agent/start:', msg + (hint ? ` | body: ${hint}` : ''))
      }
    } catch (e) {
      console.warn('[奇士美 PRO] phone-agent/start 请求失败:', e)
    }
  }

  async function fetchPhoneAgentStatusPayload(
    empId: 'wechat_phone' | 'real_phone'
  ): Promise<PhoneAgentStatusPayload> {
    const base = getPhoneAgentApiBase(empId).replace(/\/+$/, '')
    const lastPolledAt = Date.now()
    if (!base) {
      return { lastPolledAt, running: false, fetchError: '当前为原版模式或未加载 Mod，无电话扩展接口' }
    }
    const ch = resolvePhoneChannelByEmployee(empId)
    try {
      const r = await fetch(`${base}/status?channel=${ch}`)
      const j = await r.json().catch(() => ({}))
      if (j?.success && j?.data && typeof j.data === 'object') {
        return { ...j.data, lastPolledAt } as PhoneAgentStatusPayload
      }
      const msg =
        typeof j?.message === 'string' && j.message.trim()
          ? j.message.trim()
          : !r.ok
            ? r.status === 404
              ? `HTTP 404（请确认路径为 ${base}/status，勿使用 /statu 等拼写错误）`
              : `HTTP ${r.status}`
            : '响应缺少 data'
      return { lastPolledAt, running: false, fetchError: msg }
    } catch (e) {
      const err = e instanceof Error ? e.message : String(e)
      return { lastPolledAt, running: false, fetchError: err }
    }
  }

  function stopPhoneAgentStatusPoll() {
    if (phoneAgentPollTimer) {
      window.clearInterval(phoneAgentPollTimer)
      phoneAgentPollTimer = null
    }
  }

  async function pollPhoneAgentStatusForEnabledEmployees(): Promise<void> {
    const ids = getEnabledPhoneEmployeeIds()
    if (ids.length === 0) {
      stopPhoneAgentStatusPoll()
      return
    }
    const enabled = readWorkflowEmployeeEnabledMap()
    for (const empId of ids) {
      if (!enabled[empId]) continue
      await requestPhoneAgentStart(empId)
      let ps = await fetchPhoneAgentStatusPayload(empId)
      if (!ps.fetchError && !ps.running) {
        await requestPhoneAgentStart(empId)
        ps = await fetchPhoneAgentStatusPayload(empId)
      }
      upsertWorkflowEmployeeTask(empId, { phoneStatus: ps })
    }
  }

  function startPhoneAgentStatusPoll() {
    stopPhoneAgentStatusPoll()
    void pollPhoneAgentStatusForEnabledEmployees()
    phoneAgentPollTimer = window.setInterval(() => {
      void pollPhoneAgentStatusForEnabledEmployees()
    }, PHONE_AGENT_POLL_MS)
  }

  function isStarredChatAutoRefreshOn(): boolean {
    try {
      return localStorage.getItem(STAR_REFRESH_STORAGE_KEY) === '1'
    } catch {
      return false
    }
  }

  function isProIntentExperienceOn(): boolean {
    try {
      return localStorage.getItem(PRO_INTENT_STORAGE_KEY) === '1'
    } catch {
      return false
    }
  }

  function formatWorkflowHintTime(ts: number): string {
    try {
      return new Date(ts).toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return ''
    }
  }

  function formatWorkflowClock(ts: number): string {
    try {
      return new Date(ts).toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      })
    } catch {
      return ''
    }
  }

  type WorkflowMonitorPayload = {
    lastPolledAt: number
    pollIntervalMs: number
    starredContactCount?: number
    pollOk?: boolean
  }

  function computeWorkflowProgressFromSteps(steps: WorkflowStepRow[]): { pct: number; label: string } {
    if (!steps.length) return { pct: 0, label: '0 / 0 步' }
    const total = steps.length
    const done = steps.filter((s) => s.status === 'done').length
    const hasActive = steps.some((s) => s.status === 'active')
    const visual = done + (hasActive ? 0.5 : 0)
    const pct = Math.min(100, Math.round((visual / total) * 100))
    const label = `${done} / ${total} 步已完成${hasActive ? ' · 1 步进行中' : ''}`
    return { pct, label }
  }

  function buildWorkflowMonitorLine(
    empId: string,
    steps: WorkflowStepRow[],
    monitor?: WorkflowMonitorPayload,
    lastWechat?: { at: number; line: string },
    lastLabelPrint?: { at: number; line: string },
    lastShipmentAudit?: { at: number; line: string; detail?: string },
    lastReceiptFeedback?: { at: number; line: string; detail?: string },
    phoneStatus?: PhoneAgentStatusPayload
  ): string {
    if (empId === 'wechat_msg') {
      const refreshOn = isStarredChatAutoRefreshOn()
      if (!refreshOn) {
        return '监控已暂停：未开启「星标聊天自动刷新」，无法定时拉取星标会话。'
      }
      if (monitor?.lastPolledAt) {
        const t = formatWorkflowClock(monitor.lastPolledAt)
        const sec = Math.max(1, Math.round((monitor.pollIntervalMs || 60000) / 1000))
        const n = monitor.starredContactCount
        const cnt = typeof n === 'number' ? `星标联系人 ${n} 位` : '星标联系人'
        const ok = monitor.pollOk !== false ? '拉取通道正常' : '上次拉取失败，将重试'
        const tail = lastWechat
          ? ` · 最近预处理：${formatWorkflowHintTime(lastWechat.at)}`
          : ' · 持续监听新消息'
        return `${ok} · 上次检查 ${t} · 每 ${sec}s 轮询 · ${cnt}${tail}`
      }
      return '监控就绪：等待首次轮询（通常 1 分钟内）…'
    }
    if (empId === 'label_print') {
      const refreshOn = isStarredChatAutoRefreshOn()
      if (!refreshOn) {
        return '未开星标自动刷新：无法从微信侧接收标签/打印信号。'
      }
      if (lastLabelPrint) {
        const line = lastLabelPrint.line.slice(0, 100)
        return `已接收标签/打印类信号 · ${formatWorkflowHintTime(lastLabelPrint.at)} · ${line}${
          lastLabelPrint.line.length > 100 ? '…' : ''
        }`
      }
      return '星标轮询中：尚未命中标签/打印类意图；命中后本工作流才会推进。'
    }
    if (empId === 'shipment_mgmt') {
      if (lastShipmentAudit) {
        const line = lastShipmentAudit.line.slice(0, 100)
        return `打印后审计 · ${formatWorkflowHintTime(lastShipmentAudit.at)} · ${line}${
          lastShipmentAudit.line.length > 100 ? '…' : ''
        }`
      }
      return '等待「开始打印」成功：结束后将自动统计出货记录并提示保存/推送建议。'
    }
    if (empId === 'receipt_confirm') {
      const refreshOn = isStarredChatAutoRefreshOn()
      if (!refreshOn) {
        return '未开星标自动刷新：无法从微信侧接收客户收货/对账类反馈。'
      }
      if (lastReceiptFeedback) {
        const line = lastReceiptFeedback.line.slice(0, 100)
        return `客户业务进程 · ${formatWorkflowHintTime(lastReceiptFeedback.at)} · ${line}${
          lastReceiptFeedback.line.length > 100 ? '…' : ''
        }`
      }
      return '星标轮询中：尚未命中收货/对账类客户反馈；命中后将写入进程摘要。'
    }
    if (empId === 'wechat_phone') {
      const ps = phoneStatus
      const phoneBase = getPhoneAgentApiBase('wechat_phone').replace(/\/+$/, '')
      if (!ps) {
        if (!phoneBase) {
          return '当前为原版模式（已关闭 Mod 界面）：不包含微信电话扩展。'
        }
        return `尚未同步后端：副窗勾选本员工后约每 ${Math.round(PHONE_AGENT_POLL_MS / 1000)} 秒拉取 phone-agent 状态；若已勾选仍如此，请刷新页面并确认后端与 Mod 已加载。`
      }
      if (ps.fetchError) {
        if (!phoneBase) {
          return `无法拉取 phone-agent：${ps.fetchError}`
        }
        return `无法拉取 phone-agent 状态：${ps.fetchError}。请确认后端已启动（如 127.0.0.1:5000）、Mod 已加载，开发环境需 Vite 将 /api 代理到该端口。接口：GET ${phoneBase}/status`
      }
      if (ps.phone_agent_get_status_failed) {
        return `phone-agent 状态异常（get_status）：${ps.phone_agent_get_status_message || '见后端日志'}`
      }
      if (ps.phone_agent_status_route_failed) {
        return `phone-agent 状态接口异常：${ps.phone_agent_status_route_message || '见后端日志'}`
      }
      if (ps.phone_agent_manager_load_failed) {
        return `phone-agent 管理器未加载：${ps.phone_agent_manager_load_message || '见后端日志（import_mod_backend_py services）'}`
      }
      const t = ps.lastPolledAt ? formatWorkflowClock(ps.lastPolledAt) : ''
      const run = ps.running
        ? 'phone-agent 运行中'
        : (() => {
            const err = String(ps.phone_agent_last_start_error || '').trim()
            if (err) {
              const short = err.length > 100 ? `${err.slice(0, 100)}…` : err
              return `phone-agent 未运行（${short}）`
            }
            return 'phone-agent 未运行'
          })()
      const wm = ps.window_monitor_available
        ? '窗口监控可用'
        : ps.phone_pywin32_installed === false
          ? '窗口监控不可用（未检测到 pywin32）'
          : '窗口监控不可用'
      const cap =
        ps.phone_capture_thread_alive === false && ps.running
          ? '采音=线程已退出（请重启电话业务员）'
          : ps.phone_capture_backend === 'wasapi_loopback'
            ? '采音=WASAPI扬声器回环'
            : ps.phone_capture_backend === 'pyaudio'
              ? '采音=PyAudio·输入'
              : ps.phone_capture_backend === 'none'
                ? '采音=未就绪(none)'
                : ''
      const tail = t ? ` · 上次同步 ${t}` : ''
      const wmModel =
        ps.phone_whisper_model && String(ps.phone_whisper_model).trim()
          ? ` · Whisper=${String(ps.phone_whisper_model).trim()}${
              ps.phone_whisper_backend ? `(${ps.phone_whisper_backend})` : ''
            }`
          : ''
      const head = `${run} · ${wm}${cap ? ` · ${cap}` : ''}${wmModel}${tail}`
      const speechHi =
        typeof ps.phone_asr_rms_speech_hi === 'number'
          ? ps.phone_asr_rms_speech_hi
          : typeof ps.phone_asr_rms_silence_threshold === 'number'
            ? ps.phone_asr_rms_silence_threshold
            : null
      const silenceLoRaw = typeof ps.phone_asr_rms_silence_lo === 'number' ? ps.phone_asr_rms_silence_lo : null
      const peak = typeof ps.phone_capture_peak_rms_since_last_poll === 'number' ? ps.phone_capture_peak_rms_since_last_poll : null
      const silenceLo = silenceLoRaw != null ? silenceLoRaw : 95
      const diagLine =
        peak != null && speechHi != null
          ? `采音诊断：RMS峰值≈${Math.round(peak)} · 语音段阈值≥${Math.round(speechHi)} · 句末静音<${Math.round(
              silenceLo,
            )}（峰值是轮询窗内最大块；分段用双阈值：对端小声需块 RMS 常≥语音阈值才会送 ASR；环境吵可调高两阈值）`
          : ''
      const titleShort = String(ps.last_popup_title || '').replace(/\s+/g, ' ').slice(0, 36)
      const inCallSig =
        ps.phone_in_call_ui_visible === true ||
        ps.phone_wechat_call_session_active === true ||
        ps.phone_agent_voice_session_active === true
      const step1 = ps.last_popup_detected_at_ms
        ? `① 识别弹窗：已识别 · ${formatWorkflowClock(ps.last_popup_detected_at_ms)} · ${ps.last_popup_source || '—'}${titleShort ? ` · ${titleShort}` : ''}`
        : inCallSig
          ? '① 识别弹窗：无弹窗时间戳，但当前可见通话界面或会话（常见于手动接听）'
          : '① 识别弹窗：尚未识别（来电时此处应出现时间；若一直没有请看后端日志）'
      let step2 = '② 点击接听：尚未执行'
      if (ps.last_click_at_ms != null && ps.last_click_at_ms !== undefined) {
        const ok = ps.last_click_ok === true
        const m = formatPhoneClickMethod(ps.last_click_method)
        const xy =
          ps.last_click_x != null && ps.last_click_y != null ? ` · 坐标(${ps.last_click_x},${ps.last_click_y})` : ''
        const errRaw = formatPhoneClickError(ps.last_click_error)
        const err = errRaw ? ` · ${errRaw.slice(0, 120)}` : ''
        step2 = `② 点击接听：${ok ? '已执行' : '失败'} · ${formatWorkflowClock(ps.last_click_at_ms)} · ${m}${xy}${err}`
      } else if (inCallSig) {
        step2 = '② 点击接听：无自动点击记录，但已判定通话中（可能手动接听或未上报点击）'
      }
      const playDev = (ps.vb_cable_playback_device_name || '').trim() || 'CABLE Input'
      const hz =
        typeof ps.vb_cable_stream_sample_hz === 'number' && ps.vb_cable_stream_sample_hz > 0
          ? `${ps.vb_cable_stream_sample_hz} Hz`
          : '—'
      const noMp3 =
        ps.mp3_decode_available === false ||
        (ps.mp3_decode_available === undefined && ps.ffmpeg_on_path === false)
      const ff = noMp3 ? ' · MP3 解码依赖未就绪（pip install miniaudio）' : ''
      let step3 = `③ 对方听合成音：微信麦克风须选「CABLE Output」。TTS 写入「${playDev}」@ ${hz}${ff}`
      if (ps.last_opening_at_ms != null && ps.last_opening_at_ms !== undefined) {
        const oOk = ps.last_opening_ok === true
        const oErr = (ps.last_opening_error || '').trim()
        step3 = `③ 开场白：${oOk ? '已播到 VB' : '失败'} · ${formatWorkflowClock(ps.last_opening_at_ms)}${
          !oOk ? ` · ${formatOpeningError(ps.last_opening_error).slice(0, 120)}` : ''
        } · 若仍无声请检查微信麦克风是否为 CABLE Output`
      }
      const cap5 =
        ps.phone_capture_backend === 'wasapi_loopback'
          ? '采音=WASAPI扬声器回环'
          : ps.phone_capture_backend === 'pyaudio'
            ? '采音=PyAudio·输入'
            : '采音方式见上方'
      const pyaudioRemoteHint =
        ps.phone_capture_backend === 'pyaudio'
          ? ' · PyAudio 时：对端须从扬声器放出并被「立体声混音」或正确设备采到；或装 pywin32 后重启以恢复 WASAPI 回环（见状态里「谁进 ASR」）'
          : ''
      let step5 = `⑤ 对方语音→ASR：尚无识别结果（${cap5}；对端说话且 Whisper 出字后此处显示时间与文字。无字请对照：采音诊断、XCAGI_PHONE_RMS_SPEECH/SILENCE_LO、后端「句末静音送 ASR」与 Whisper 日志）${pyaudioRemoteHint}`
      if (ps.last_asr_at_ms != null && ps.last_asr_at_ms !== undefined) {
        const raw = String(ps.last_asr_text || '').replace(/\s+/g, ' ').trim()
        const slice = raw.slice(0, 80)
        step5 = `⑤ 对方语音(ASR)：${formatWorkflowClock(ps.last_asr_at_ms)} · 「${slice}${
          raw.length > 80 ? '…' : ''
        }」`
      }
      let step6 = '⑥ 回复→VB：尚无（需先有 ASR 并完成意图与 TTS）'
      if (ps.last_reply_at_ms != null && ps.last_reply_at_ms !== undefined) {
        const raw = String(ps.last_reply_text || '').replace(/\s+/g, ' ').trim()
        const slice = raw.length ? raw.slice(0, 80) : '（空）'
        const pe = (ps.last_pipeline_error || '').trim()
        const peShow = pe ? ` · ${formatPhonePipelineError(pe).slice(0, 72)}` : ''
        step6 = `⑥ 回复→VB：${formatWorkflowClock(ps.last_reply_at_ms)} · 「${slice}${
          raw.length > 80 ? '…' : ''
        }」${peShow}`
      } else if (
        (ps.last_pipeline_error || '').trim() &&
        ps.last_asr_at_ms != null &&
        ps.last_asr_at_ms !== undefined
      ) {
        const pe = formatPhonePipelineError(ps.last_pipeline_error).slice(0, 120)
        step6 = `⑥ 回复→VB：失败 · ${pe}`
      }
      const step4 =
        ps.last_call_ended_at_ms != null && ps.last_call_ended_at_ms !== undefined
          ? `④ 通话结束：${formatWorkflowClock(ps.last_call_ended_at_ms)} · ${formatCallEndReason(
              ps.last_call_end_reason,
            )} · ①②③⑤⑥ 已初始化`
          : ''
      const problemZh = String(ps.phone_capture_problem_zh || '').trim()
      const problemLine =
        problemZh.length > 0 ? problemZh.slice(0, 240) + (problemZh.length > 240 ? '…' : '') : ''
      const wmHint = String(ps.phone_window_monitor_hint_zh || '').trim()
      const wmHintLine =
        wmHint.length > 0 ? wmHint.slice(0, 360) + (wmHint.length > 360 ? '…' : '') : ''
      return [head, wmHintLine, diagLine, problemLine, step1, step2, step3, step5, step6, step4]
        .filter(Boolean)
        .join('\n')
    }
    if (empId === 'real_phone') {
      const a = steps.find((s) => s.status === 'active')
      if (a) return `真实电话业务员运行中：${a.label.replace(/^[①②③④⑤⑥]\s*/, '')}`
      const d = steps.filter((s) => s.status === 'done').length
      return `真实电话业务员已启用：完成 ${d}/${steps.length} 步，等待来电触发下一阶段。`
    }
    const a = steps.find((s) => s.status === 'active')
    if (a) return `运行中：${a.label.replace(/^[①②③④⑤]\s*/, '')}`
    return '待命：等待对话或条件触发下一步。'
  }

  function buildWorkflowStepsForEmployee(
    empId: string,
    ctx?: {
      lastWechat?: { at: number; line: string }
      lastLabelPrint?: { at: number; line: string }
      lastShipmentAudit?: { at: number; line: string; detail?: string }
      lastReceiptFeedback?: { at: number; line: string; detail?: string }
      phoneStatus?: PhoneAgentStatusPayload
    }
  ): WorkflowStepRow[] {
    if (empId === 'wechat_msg') {
      const refreshOn = isStarredChatAutoRefreshOn()
      const proIntent = isProIntentExperienceOn()
      const last = ctx?.lastWechat
      const preface = proIntent ? '调用 POST /api/ai/intent/test' : '本地关键词规则（inferWechatCustomerIntent）'
      return [
        { id: 'wx1', label: '① 副窗「一键托管」启用「微信消息处理 AI 员工」', status: 'done' },
        { id: 'wx2', label: '② 智能对话勾选「星标聊天自动刷新（1分钟）」', status: refreshOn ? 'done' : 'active' },
        {
          id: 'wx3',
          label: '③ 定时拉取星标联系人最新消息，并同步副窗「推送」提醒',
          status: refreshOn ? 'active' : 'pending',
        },
        {
          id: 'wx4',
          label: `④ 新消息到达 → 意图预处理（${preface}）`,
          status: last ? 'done' : 'pending',
        },
        {
          id: 'wx5',
          label: '⑤ 预处理结果写入本列表（「微信消息处理 · 联系人」类条目）',
          status: last ? 'done' : 'pending',
        },
      ]
    }
    if (empId === 'label_print') {
      const sig = ctx?.lastLabelPrint
      const refreshOn = isStarredChatAutoRefreshOn()
      return [
        { id: 'lp1', label: '① 副窗启用「标签打印 AI 员工」', status: 'done' },
        {
          id: 'lp2',
          label: refreshOn
            ? '② 星标新消息 → 意图预处理（与微信消息员工同源）'
            : '② 请开启「星标聊天自动刷新」以接收微信侧信号',
          status: refreshOn ? (sig ? 'done' : 'active') : 'active',
        },
        {
          id: 'lp3',
          label: sig
            ? '③ 在智能对话补充型号/张数并触发打印链路'
            : '③ 命中标签/打印意图后，在对话中执行打印',
          status: sig ? 'active' : 'pending',
        },
      ]
    }
    if (empId === 'shipment_mgmt') {
      const audit = ctx?.lastShipmentAudit
      return [
        { id: 'sm1', label: '① 副窗启用「出货管理 AI 员工」', status: 'done' },
        {
          id: 'sm2',
          label: '② 对话完成发货单生成并在确认后执行「开始打印」',
          status: audit ? 'done' : 'active',
        },
        {
          id: 'sm3',
          label: audit
            ? '③ 已输出打印后审计：请到出货记录核对，按需导出/推送'
            : '③ 打印后将自动统计本单位出货记录并给出保存/推送建议',
          status: audit ? 'active' : 'pending',
        },
      ]
    }
    if (empId === 'receipt_confirm') {
      const sig = ctx?.lastReceiptFeedback
      const refreshOn = isStarredChatAutoRefreshOn()
      return [
        { id: 'rc1', label: '① 副窗启用「收货确认 AI 员工」', status: 'done' },
        {
          id: 'rc2',
          label: refreshOn
            ? '② 星标微信 → 意图预处理（与微信消息员工同源），捕捉收货/对账类客户反馈'
            : '② 请开启「星标聊天自动刷新」以接收客户侧业务进程',
          status: refreshOn ? (sig ? 'done' : 'active') : 'active',
        },
        {
          id: 'rc3',
          label: sig
            ? '③ 已展示客户业务进程摘要，请在智能对话中跟进确认'
            : '③ 命中收货/对账类意图后写入进程信息',
          status: sig ? 'active' : 'pending',
        },
      ]
    }
    if (empId === 'wechat_phone') {
      const ps = ctx?.phoneStatus
      const run = !!ps?.running
      const wm = !!ps?.window_monitor_available
      const popupDone = !!(ps as PhoneAgentStatusPayload | undefined)?.last_popup_detected_at_ms
      const inCallUi = (ps as PhoneAgentStatusPayload | undefined)?.phone_in_call_ui_visible === true
      const sessionActive =
        (ps as PhoneAgentStatusPayload | undefined)?.phone_wechat_call_session_active === true ||
        (ps as PhoneAgentStatusPayload | undefined)?.phone_agent_voice_session_active === true
      const clickTried =
        ps != null && (ps as PhoneAgentStatusPayload).last_click_at_ms != null &&
        (ps as PhoneAgentStatusPayload).last_click_at_ms !== undefined
      const clickOk = (ps as PhoneAgentStatusPayload | undefined)?.last_click_ok === true
      const hasAsr =
        ps != null && ps.last_asr_at_ms != null && ps.last_asr_at_ms !== undefined
      const hasOpening =
        ps != null && ps.last_opening_at_ms != null && ps.last_opening_at_ms !== undefined
      const answered = clickOk || inCallUi || hasAsr || sessionActive || hasOpening
      const popupOrCallUi = popupDone || inCallUi
      const pipelineReady = !!(
        ps?.audio_capture_available &&
        ps?.asr_available &&
        ps?.intent_handler_available &&
        ps?.tts_available &&
        ps?.vb_cable_available
      )
      return [
        { id: 'wp1', label: '① 副窗「一键托管」启用「微信电话对接业务员」', status: 'done' },
        {
          id: 'wp2',
          label: '② 后端 phone-agent 已启动',
          status: !ps ? 'pending' : run ? 'done' : 'active',
        },
        {
          id: 'wp3',
          label: '③ Win32 窗口监控可用（检测来电）',
          status: !ps ? 'pending' : run ? (wm ? 'done' : 'active') : 'pending',
        },
        {
          id: 'wp4',
          label: popupDone
            ? `④ 已识别来电弹窗（${(ps as PhoneAgentStatusPayload).last_popup_source || '—'}）`
            : inCallUi
              ? '④ 已检测到微信通话界面（手动接听或未记录来电弹窗时亦可识别）'
              : '④ 等待识别微信来电弹窗…',
          status: !ps ? 'pending' : popupOrCallUi ? 'done' : run && wm ? 'active' : 'pending',
        },
        {
          id: 'wp5',
          label: clickTried
            ? `⑤ 接听点击：${clickOk ? '已成功' : '已失败'}（${(ps as PhoneAgentStatusPayload).last_click_method || '—'}）`
            : answered
              ? '⑤ 通话已接通（自动未点接听或手动接听）'
              : '⑤ 等待执行接听点击…',
          status: !ps
            ? 'pending'
            : clickOk || answered
              ? 'done'
              : clickTried && !clickOk
                ? 'active'
                : popupOrCallUi
                  ? 'active'
                  : 'pending',
        },
        {
          id: 'wp6',
          label:
            ps?.last_asr_at_ms != null && ps.last_asr_at_ms !== undefined
              ? `⑥ 音频→ASR→回复：已识别「${String(ps.last_asr_text || '').replace(/\s+/g, ' ').trim().slice(0, 36)}${
                  String(ps.last_asr_text || '').length > 36 ? '…' : ''
                }」`
              : '⑥ 音频采集 → ASR → 意图 → TTS → VB-Cable',
          status: !ps || !run || !wm
            ? 'pending'
            : hasAsr
              ? 'done'
              : pipelineReady
                ? 'active'
                : 'active',
        },
      ]
    }
    if (empId === 'real_phone') {
      const ps = ctx?.phoneStatus
      const run = !!ps?.running
      const adbOk = ps?.adb_available === true
      const devOk = ps?.adb_device_connected === true
      const callState = String(ps?.adb_call_state || 'UNKNOWN').toUpperCase()
      const answerTried = ps?.adb_last_answer_at_ms != null && ps?.adb_last_answer_at_ms !== undefined
      const answerOk = ps?.adb_last_answer_ok === true
      return [
        { id: 'rp1', label: '① 副窗启用「真实电话业务员」', status: 'done' },
        {
          id: 'rp2',
          label: devOk
            ? `② ADB 设备连通检查：已连接（${ps?.adb_device_serial || 'unknown'}）`
            : adbOk
              ? '② ADB 设备连通检查：已发现 adb，等待在线设备'
              : '② ADB 设备连通检查：等待 adb 可用',
          status: !ps ? 'pending' : devOk ? 'done' : run ? 'active' : 'active',
        },
        {
          id: 'rp3',
          label:
            callState === 'RINGING'
              ? '③ 来电状态：振铃中，准备自动接听'
              : callState === 'OFFHOOK'
                ? '③ 来电状态：已进入通话'
                : '③ 来电状态轮询中（等待振铃）',
          status: !ps || !run ? 'pending' : callState === 'OFFHOOK' ? 'done' : devOk ? 'active' : 'pending',
        },
        {
          id: 'rp4',
          label: answerTried
            ? `④ 自动接听：${answerOk ? '已执行成功' : '执行失败'}`
            : '④ 自动接听指令（振铃时触发）',
          status: !ps || !run ? 'pending' : answerOk ? 'done' : callState === 'RINGING' ? 'active' : 'pending',
        },
        {
          id: 'rp5',
          label: callState === 'OFFHOOK' ? '⑤ 通话已接通（保持状态监控）' : '⑤ 等待接通',
          status: !ps || !run ? 'pending' : callState === 'OFFHOOK' ? 'done' : 'pending',
        },
        {
          id: 'rp6',
          label:
            ps?.adb_last_poll_at_ms != null && ps.adb_last_poll_at_ms !== undefined
              ? `⑥ 状态回写已同步（${formatWorkflowClock(ps.adb_last_poll_at_ms)}）`
              : '⑥ 状态回写到任务面板',
          status: !ps || !run ? 'pending' : ps?.adb_last_poll_at_ms ? 'active' : 'pending',
        },
      ]
    }
    return []
  }

  function computeWorkflowCurrentHint(
    empId: string,
    steps: WorkflowStepRow[],
    lastWechat?: { at: number; line: string },
    monitor?: WorkflowMonitorPayload,
    lastLabelPrint?: { at: number; line: string },
    lastShipmentAudit?: { at: number; line: string; detail?: string },
    lastReceiptFeedback?: { at: number; line: string; detail?: string },
    phoneStatus?: PhoneAgentStatusPayload
  ): string {
    if (empId === 'wechat_msg') {
      const refreshOn = isStarredChatAutoRefreshOn()
      if (!refreshOn) {
        return '请先勾选「星标聊天自动刷新」以启动监控轮询。'
      }
      if (lastWechat) {
        return `最近一条客户消息已预处理并写入列表：${lastWechat.line.slice(0, 120)}${lastWechat.line.length > 120 ? '…' : ''}`
      }
      if (monitor?.lastPolledAt) {
        return '尚未捕获到新消息签名变化；监控轮询在运行，有新聊天时会自动执行意图预处理。'
      }
      return '工作流已就绪；首次轮询完成后，上方「工作状态」将显示上次检查时间。'
    }
    if (empId === 'label_print') {
      const refreshOn = isStarredChatAutoRefreshOn()
      if (!refreshOn) {
        return '请先勾选「星标聊天自动刷新」；标签打印员工仅从星标微信链路接收「标签/打印」类信号。'
      }
      if (lastLabelPrint) {
        return `最近命中标签/打印意图：${lastLabelPrint.line.slice(0, 120)}${lastLabelPrint.line.length > 120 ? '…' : ''}`
      }
      return '等待星标会话中出现标签/打印类消息；未命中前本工作流不执行后续步骤。'
    }
    if (empId === 'shipment_mgmt') {
      if (lastShipmentAudit) {
        const d = String(lastShipmentAudit.detail || lastShipmentAudit.line || '').trim()
        return d.length > 220 ? `${d.slice(0, 220)}…` : d || lastShipmentAudit.line
      }
      return '「开始打印」成功后，将自动拉取出货记录、汇总条数并提示是否导出存档或推送同事。'
    }
    if (empId === 'receipt_confirm') {
      const refreshOn = isStarredChatAutoRefreshOn()
      if (!refreshOn) {
        return '请先勾选「星标聊天自动刷新」；收货确认员工依赖微信消息员工同源链路获取客户反馈。'
      }
      if (lastReceiptFeedback) {
        const d = String(lastReceiptFeedback.detail || lastReceiptFeedback.line || '').trim()
        return d.length > 220 ? `${d.slice(0, 220)}…` : d || lastReceiptFeedback.line
      }
      return '等待星标客户发送收货、到货、签收、对账等消息；命中后在此展示对应业务进程摘要。'
    }
    if (empId === 'wechat_phone') {
      const ps = phoneStatus
      const phoneBase = getPhoneAgentApiBase('wechat_phone').replace(/\/+$/, '')
      if (!ps) {
        if (!phoneBase) {
          return '原版模式：未加载 Mod 电话扩展。'
        }
        return `正在连接后端状态；请确认 Mod 已加载且本机可访问 ${phoneBase}/status。`
      }
      if (ps.fetchError) {
        return `状态接口异常：${ps.fetchError}`
      }
      if (ps.phone_agent_get_status_failed) {
        return `get_status 失败：${ps.phone_agent_get_status_message || '见后端日志'}`
      }
      if (ps.phone_agent_status_route_failed) {
        return `路由异常：${ps.phone_agent_status_route_message || '见后端日志'}`
      }
      if (ps.phone_agent_manager_load_failed) {
        return `phone-agent 管理器未加载：${ps.phone_agent_manager_load_message || '见后端日志'}`
      }
      if (!ps.running) {
        const err = String(ps.phone_agent_last_start_error || '').trim()
        const tail = err
          ? ` 启动失败原因：${err.length > 200 ? `${err.slice(0, 200)}…` : err}`
          : ''
        return `phone-agent 未处于运行状态：请在一键托管中打开「微信电话对接业务员」，并检查运行后端的 Python 是否已安装 soundcard / 音频设备（详见后端日志）。${tail}`
      }
      if (!ps.window_monitor_available) {
        return '窗口监控不可用：请确认在 Windows 上运行且已安装 pywin32。'
      }
      const bits: string[] = []
      if (ps.audio_capture_available) bits.push('音频采集')
      if (ps.asr_available) bits.push('ASR')
      if (ps.intent_handler_available) bits.push('意图')
      if (ps.tts_available) bits.push('TTS')
      if (ps.vb_cable_available) bits.push('VB-Cable')
      const chain = bits.length ? `链路组件：${bits.join('、')}` : '语音链路组件状态未知'
      const inCall =
        ps.phone_in_call_ui_visible === true ||
        ps.phone_wechat_call_session_active === true ||
        ps.phone_agent_voice_session_active === true
      if (inCall) {
        return `当前处于通话阶段；${chain}。对方说话后将更新 ASR；若长期无文本请检查扬声器回环与 RMS 阈值（见状态里的采音说明）。`
      }
      return `来电时将尝试自动接听；${chain}。若无法接听，请更新微信 PC 版或查看后端接听按钮定位日志。`
    }
    if (empId === 'real_phone') {
      const ps = phoneStatus
      if (!ps) return '正在连接 ADB 电话状态接口…'
      if (ps.fetchError) return `状态接口异常：${ps.fetchError}`
      if (!ps.running) {
        const err = String(ps.phone_agent_last_start_error || ps.adb_last_error || '').trim()
        return err ? `ADB 链路未运行：${err}` : 'ADB 链路未运行：请在一键托管启用真实电话业务员。'
      }
      if (!ps.adb_available) return '未检测到 adb，请确认 adb 已安装并在 PATH。'
      if (!ps.adb_device_connected) return 'adb 已可用，但未发现在线设备（请检查 USB 调试与授权）。'
      const st = String(ps.adb_call_state || 'UNKNOWN').toUpperCase()
      if (st === 'RINGING') return '检测到来电振铃，正在尝试自动接听。'
      if (st === 'OFFHOOK') return '通话中：ADB 状态轮询正常。'
      return '设备在线，等待来电（轮询中）。'
    }
    const active = steps.find((s) => s.status === 'active')
    if (active) return `当前步骤：${active.label.replace(/^[①②③④⑤]\s*/, '')}`
    return '工作流已启用，等待下一步触发。'
  }

  function computeWorkflowStageLine(
    empId: string,
    lastWechat?: { at: number; line: string },
    lastLabelPrint?: { at: number; line: string },
    lastShipmentAudit?: { at: number; line: string; detail?: string },
    lastReceiptFeedback?: { at: number; line: string; detail?: string },
    phoneStatus?: PhoneAgentStatusPayload
  ): string {
    if (empId === 'wechat_msg') {
      if (!isStarredChatAutoRefreshOn()) return '等待开启星标自动刷新'
      return lastWechat ? '监控中 · 最近已处理' : '监控中 · 等待新消息'
    }
    if (empId === 'label_print') {
      if (!isStarredChatAutoRefreshOn()) return '等待开启星标自动刷新'
      return lastLabelPrint ? '已收微信侧标签/打印信号' : '等待微信侧标签/打印信号'
    }
    if (empId === 'shipment_mgmt') {
      return lastShipmentAudit ? '已审计 · 建议核对出货记录' : '待命 · 等待打印完成后审计'
    }
    if (empId === 'receipt_confirm') {
      if (!isStarredChatAutoRefreshOn()) return '等待开启星标自动刷新'
      return lastReceiptFeedback ? '已收客户侧业务进程反馈' : '等待微信侧收货/对账类反馈'
    }
    if (empId === 'wechat_phone') {
      const ps = phoneStatus
      if (!ps) return '待命 · 同步状态中'
      if (!ps.running) {
        const err = String(ps.phone_agent_last_start_error || '').trim()
        if (err) {
          const short = err.length > 72 ? `${err.slice(0, 72)}…` : err
          return `待命 · 未运行（${short}）`
        }
        return '待命 · phone-agent 未运行'
      }
      if (ps.last_asr_at_ms != null && ps.last_asr_at_ms !== undefined) {
        return '运行中 · 已收对方语音(ASR)'
      }
      if (
        ps.phone_in_call_ui_visible === true ||
        ps.phone_wechat_call_session_active === true ||
        ps.phone_agent_voice_session_active === true
      ) {
        return '运行中 · 通话中（等待对方语音/ASR）'
      }
      return ps.window_monitor_available ? '运行中 · 等待来电并尝试自动接听' : '运行中 · 窗口监控不可用'
    }
    if (empId === 'real_phone') {
      const ps = phoneStatus
      if (!ps) return '待命 · 同步状态中'
      if (!ps.running) return '待命 · ADB 链路未运行'
      if (!ps.adb_available) return '异常 · adb 不可用'
      if (!ps.adb_device_connected) return '运行中 · 等待设备在线'
      const st = String(ps.adb_call_state || 'UNKNOWN').toUpperCase()
      if (st === 'RINGING') return '运行中 · 来电振铃（自动接听）'
      if (st === 'OFFHOOK') return '运行中 · 通话中'
      return '运行中 · 设备在线等待来电'
    }
    return '待命 · 等待对话触发'
  }

  function readWorkflowEmployeeEnabledMap(): Record<string, boolean> {
    return { ...workflowAiEmployeesStore.enabled }
  }

  function upsertWorkflowEmployeeTask(
    empId: string,
    opts?: {
      lastWechat?: { at: number; line: string }
      lastLabelPrint?: { at: number; line: string }
      lastShipmentAudit?: { at: number; line: string; detail?: string }
      lastReceiptFeedback?: { at: number; line: string; detail?: string }
      monitor?: WorkflowMonitorPayload | null
      phoneStatus?: PhoneAgentStatusPayload | null
    }
  ) {
    const taskId = `workflow_emp_${empId}`
    const existing = taskList.value.find((t) => t.id === taskId)
    const lastWechat =
      opts && opts.lastWechat !== undefined
        ? opts.lastWechat
        : empId === 'wechat_msg' && existing?.payload?.lastWechat
          ? (existing.payload.lastWechat as { at: number; line: string })
          : undefined

    const lastLabelPrint =
      opts && opts.lastLabelPrint !== undefined
        ? opts.lastLabelPrint
        : empId === 'label_print' && existing?.payload?.lastLabelPrint
          ? (existing.payload.lastLabelPrint as { at: number; line: string })
          : undefined

    const lastShipmentAudit =
      opts && opts.lastShipmentAudit !== undefined
        ? opts.lastShipmentAudit
        : empId === 'shipment_mgmt' && existing?.payload?.lastShipmentAudit
          ? (existing.payload.lastShipmentAudit as { at: number; line: string; detail?: string })
          : undefined

    const lastReceiptFeedback =
      opts && opts.lastReceiptFeedback !== undefined
        ? opts.lastReceiptFeedback
        : empId === 'receipt_confirm' && existing?.payload?.lastReceiptFeedback
          ? (existing.payload.lastReceiptFeedback as { at: number; line: string; detail?: string })
          : undefined

    let monitor: WorkflowMonitorPayload | undefined
    if (opts && 'monitor' in opts && opts.monitor !== undefined) {
      monitor = opts.monitor === null ? undefined : opts.monitor
    } else if (empId === 'wechat_msg' && existing?.payload?.monitor) {
      monitor = existing.payload.monitor as WorkflowMonitorPayload
    }

    let phoneStatus: PhoneAgentStatusPayload | undefined
    if (opts && 'phoneStatus' in opts && opts.phoneStatus !== undefined) {
      phoneStatus = opts.phoneStatus === null ? undefined : opts.phoneStatus
    } else if ((empId === 'wechat_phone' || empId === 'real_phone') && existing?.payload?.phoneStatus) {
      phoneStatus = existing.payload.phoneStatus as PhoneAgentStatusPayload
    }

    const steps = buildWorkflowStepsForEmployee(empId, {
      ...(lastWechat ? { lastWechat } : {}),
      ...(lastLabelPrint ? { lastLabelPrint } : {}),
      ...(lastShipmentAudit ? { lastShipmentAudit } : {}),
      ...(lastReceiptFeedback ? { lastReceiptFeedback } : {}),
      ...(phoneStatus ? { phoneStatus } : {}),
    })

    /** 微信员工：仅在实际「接收到新消息并完成一轮意图预处理」后才显示步骤进度，避免监控阶段出现 50% 等误导 */
    let progressPct = 0
    let progressLabel = ''
    let workflowProgressStarted = true
    if (empId === 'wechat_msg') {
      if (!lastWechat) {
        progressPct = 0
        progressLabel = isStarredChatAutoRefreshOn()
          ? '尚未进入处理：等待新消息'
          : '尚未进入处理：请先开启星标自动刷新'
        workflowProgressStarted = false
      } else {
        const p = computeWorkflowProgressFromSteps(steps)
        progressPct = p.pct
        progressLabel = p.label
        workflowProgressStarted = true
      }
    } else if (empId === 'label_print') {
      if (!lastLabelPrint) {
        progressPct = 0
        progressLabel = isStarredChatAutoRefreshOn()
          ? '尚未进入执行：等待微信侧标签/打印类消息'
          : '尚未进入执行：请先开启星标自动刷新'
        workflowProgressStarted = false
      } else {
        const p = computeWorkflowProgressFromSteps(steps)
        progressPct = p.pct
        progressLabel = p.label
        workflowProgressStarted = true
      }
    } else if (empId === 'shipment_mgmt') {
      if (!lastShipmentAudit) {
        progressPct = 0
        progressLabel = '尚未完成打印后审计：请先完成发货单打印'
        workflowProgressStarted = false
      } else {
        const p = computeWorkflowProgressFromSteps(steps)
        progressPct = p.pct
        progressLabel = p.label
        workflowProgressStarted = true
      }
    } else if (empId === 'receipt_confirm') {
      if (!lastReceiptFeedback) {
        progressPct = 0
        progressLabel = isStarredChatAutoRefreshOn()
          ? '尚未收到客户侧收货/对账类反馈'
          : '尚未进入：请先开启星标自动刷新'
        workflowProgressStarted = false
      } else {
        const p = computeWorkflowProgressFromSteps(steps)
        progressPct = p.pct
        progressLabel = p.label
        workflowProgressStarted = true
      }
    } else if (empId === 'wechat_phone') {
      const ps = phoneStatus
      const psBad =
        !ps ||
        !!(ps.fetchError && String(ps.fetchError).trim()) ||
        ps.phone_agent_get_status_failed ||
        ps.phone_agent_status_route_failed ||
        ps.phone_agent_manager_load_failed
      const started = !psBad && phoneAgentWorkflowProgressShouldStart(ps)
      if (!started) {
        progressPct = 0
        progressLabel = !ps
          ? '正在同步后端 phone-agent 状态…'
          : psBad
            ? '无法计算进度：请先排除状态接口或管理器异常'
            : !ps.running
              ? (() => {
                  const err = String(ps.phone_agent_last_start_error || '').trim()
                  return err
                    ? `待命：未运行 — ${err.length > 60 ? `${err.slice(0, 60)}…` : err}`
                    : '待命：phone-agent 未运行（多为音频采集未启动，见后端日志）'
                })()
              : '待命：链路就绪，等待来电或通话界面（下次轮询会检测微信通话窗）'
        workflowProgressStarted = false
      } else {
        const p = computeWorkflowProgressFromSteps(steps)
        progressPct = p.pct
        progressLabel = p.label
        workflowProgressStarted = true
      }
    } else if (empId === 'real_phone') {
      const ps = phoneStatus
      const started = !!(ps && ps.running && ps.adb_device_connected)
      if (!started) {
        progressPct = 0
        progressLabel = !ps
          ? '正在同步 ADB 电话状态…'
          : !ps.running
            ? '待命：ADB 链路未运行'
            : !ps.adb_available
              ? '待命：未检测到 adb'
              : '待命：等待设备在线'
        workflowProgressStarted = false
      } else {
        const p = computeWorkflowProgressFromSteps(steps)
        progressPct = p.pct
        progressLabel = p.label
        workflowProgressStarted = true
      }
    } else {
      const p = computeWorkflowProgressFromSteps(steps)
      progressPct = p.pct
      progressLabel = p.label
    }

    const workflowProgressIdle = !workflowProgressStarted

    const monitorLine = buildWorkflowMonitorLine(
      empId,
      steps,
      monitor,
      lastWechat,
      lastLabelPrint,
      lastShipmentAudit,
      lastReceiptFeedback,
      phoneStatus
    )
    const hint = computeWorkflowCurrentHint(
      empId,
      steps,
      lastWechat,
      monitor,
      lastLabelPrint,
      lastShipmentAudit,
      lastReceiptFeedback,
      phoneStatus
    )
    const meta = resolveWorkflowEmployeePanelMeta(empId)
    if (!meta) return
    const summaryParts = [meta.summary]
    if (lastWechat) {
      summaryParts.push(`最近处理 ${formatWorkflowHintTime(lastWechat.at)}：${lastWechat.line}`)
    }
    if (empId === 'label_print' && lastLabelPrint) {
      summaryParts.push(`最近标签/打印信号 ${formatWorkflowHintTime(lastLabelPrint.at)}：${lastLabelPrint.line}`)
    }
    if (empId === 'shipment_mgmt' && lastShipmentAudit) {
      summaryParts.push(`最近打印后审计 ${formatWorkflowHintTime(lastShipmentAudit.at)}：${lastShipmentAudit.line}`)
    }
    if (empId === 'receipt_confirm' && lastReceiptFeedback) {
      summaryParts.push(`最近客户反馈 ${formatWorkflowHintTime(lastReceiptFeedback.at)}：${lastReceiptFeedback.line}`)
    }
    if (empId === 'wechat_phone' && phoneStatus) {
      const ps = phoneStatus
      const bits = [
        ps.running ? '运行中' : '未运行',
        ps.window_monitor_available ? '窗口监控 OK' : '窗口监控不可用',
        ps.lastPolledAt ? `上次同步 ${formatWorkflowClock(ps.lastPolledAt)}` : '',
      ]
        .filter(Boolean)
        .join(' · ')
      summaryParts.push(`电话业务员状态：${bits}`)
      if (ps.last_popup_detected_at_ms) {
        summaryParts.push(
          `识别弹窗：${formatWorkflowClock(ps.last_popup_detected_at_ms)} · ${ps.last_popup_source || '—'} · ${String(ps.last_popup_title || '').slice(0, 60)}`
        )
      }
      if (ps.last_click_at_ms != null && ps.last_click_at_ms !== undefined) {
        summaryParts.push(
          `接听点击：${ps.last_click_ok ? '成功' : '失败'} · ${formatWorkflowClock(ps.last_click_at_ms)} · ${ps.last_click_method || '—'}`
        )
      }
      if (ps.last_asr_at_ms != null && ps.last_asr_at_ms !== undefined && (ps.last_asr_text || '').trim()) {
        summaryParts.push(
          `对方语音(ASR) ${formatWorkflowClock(ps.last_asr_at_ms)}：${String(ps.last_asr_text).slice(0, 160)}${
            String(ps.last_asr_text).length > 160 ? '…' : ''
          }`
        )
      }
      if (ps.last_reply_at_ms != null && ps.last_reply_at_ms !== undefined && (ps.last_reply_text || '').trim()) {
        summaryParts.push(
          `回复送 VB ${formatWorkflowClock(ps.last_reply_at_ms)}：${String(ps.last_reply_text).slice(0, 160)}${
            String(ps.last_reply_text).length > 160 ? '…' : ''
          }`
        )
      }
    }
    if (empId === 'real_phone' && phoneStatus) {
      const ps = phoneStatus
      const bits = [
        ps.running ? '运行中' : '未运行',
        ps.adb_available ? 'ADB OK' : 'ADB 不可用',
        ps.adb_device_connected ? `设备 ${ps.adb_device_serial || 'online'}` : '无在线设备',
        ps.adb_call_state ? `状态 ${String(ps.adb_call_state).toUpperCase()}` : '',
      ]
        .filter(Boolean)
        .join(' · ')
      summaryParts.push(`真实电话状态：${bits}`)
      if (ps.adb_last_error) {
        summaryParts.push(`最近错误：${String(ps.adb_last_error).slice(0, 120)}`)
      }
    }

    upsertTask({
      id: taskId,
      type: 'workflow_employee',
      source: 'system',
      title: meta.title,
      status: 'running',
      progress: progressPct,
      stage: computeWorkflowStageLine(
        empId,
        lastWechat,
        lastLabelPrint,
        lastShipmentAudit,
        lastReceiptFeedback,
        phoneStatus
      ),
      summary: summaryParts.join('\n\n'),
      payload: {
        employeeId: empId,
        workflowSteps: steps,
        workflowCurrentHint: hint,
        workflowProgressPct: progressPct,
        workflowProgressLabel: progressLabel,
        workflowProgressIdle,
        workflowProgressStarted,
        workflowMonitorLine: monitorLine,
        ...(lastWechat ? { lastWechat } : {}),
        ...(lastLabelPrint ? { lastLabelPrint } : {}),
        ...(lastShipmentAudit ? { lastShipmentAudit } : {}),
        ...(lastReceiptFeedback ? { lastReceiptFeedback } : {}),
        ...(monitor ? { monitor } : {}),
        ...(phoneStatus ? { phoneStatus } : {}),
      },
    })
  }

  function onWechatStarFeedPolled(evt: Event) {
    const d = (evt as CustomEvent).detail || {}
    const enabled = readWorkflowEmployeeEnabledMap()
    if (!enabled.wechat_msg) return
    if (!taskList.value.some((t) => t.id === 'workflow_emp_wechat_msg')) return
    upsertWorkflowEmployeeTask('wechat_msg', {
      monitor: {
        lastPolledAt: Number(d.at) || Date.now(),
        pollIntervalMs: Number(d.intervalMs) || 60000,
        starredContactCount: typeof d.contactCount === 'number' ? d.contactCount : undefined,
        pollOk: d.ok !== false,
      },
    })
  }

  function syncWorkflowEmployeePanelTasks(enabled: Record<string, boolean>) {
    const merged = { ...readWorkflowEmployeeEnabledMap(), ...enabled }
    const modMeta = buildModWorkflowPanelMeta(modsStore.modsForUi)
    const allEmpIds = new Set([
      ...Object.keys(WORKFLOW_EMPLOYEE_PANEL_META),
      ...Object.keys(modMeta),
    ])
    for (const empId of allEmpIds) {
      const taskId = `workflow_emp_${empId}`
      if (merged[empId]) {
        if (resolveWorkflowEmployeePanelMeta(empId)) {
          upsertWorkflowEmployeeTask(empId)
        }
      } else {
        const idx = taskList.value.findIndex((t) => t.id === taskId)
        if (idx !== -1) {
          taskList.value.splice(idx, 1)
          if (activeTaskId.value === taskId) {
            activeTaskId.value = taskList.value[0]?.id || ''
          }
        }
      }
    }
    pruneStaleWorkflowEmployeeTasks()
    sortTaskList()
    if (getEnabledPhoneEmployeeIds().length > 0) {
      if (!phoneAgentPollTimer) startPhoneAgentStatusPoll()
    } else {
      stopPhoneAgentStatusPoll()
    }
  }

  function resyncEnabledWorkflowEmployeeTasks() {
    const enabled = readWorkflowEmployeeEnabledMap()
    const modMeta = buildModWorkflowPanelMeta(modsStore.modsForUi)
    const allEmpIds = new Set([
      ...Object.keys(WORKFLOW_EMPLOYEE_PANEL_META),
      ...Object.keys(modMeta),
    ])
    for (const empId of allEmpIds) {
      if (enabled[empId] && resolveWorkflowEmployeePanelMeta(empId)) {
        upsertWorkflowEmployeeTask(empId)
      }
    }
    pruneStaleWorkflowEmployeeTasks()
    sortTaskList()
  }

  function onWorkflowAiEmployeesChanged(evt: Event) {
    const d = (evt as CustomEvent).detail || {}
    const en = d.enabled
    if (en && typeof en === 'object') {
      syncWorkflowEmployeePanelTasks(en as Record<string, boolean>)
      return
    }
    syncWorkflowEmployeePanelTasks(readWorkflowEmployeeEnabledMap())
  }

  function onWorkflowEmployeesStorage(e: StorageEvent) {
    if (e.key !== WORKFLOW_AI_EMPLOYEES_STORAGE_KEY) return
    workflowAiEmployeesStore.reloadFromLocalStorage()
    syncWorkflowEmployeePanelTasks(readWorkflowEmployeeEnabledMap())
  }

  function onStarRefreshOrIntentChangedForWorkflow() {
    resyncEnabledWorkflowEmployeeTasks()
  }

  /**
   * 兜底同步：避免仅靠自定义事件导致偶发漏同步（例如页面切换后返回聊天页）。
   * 只要本地存在已启用员工，就从 storage 重建任务面板常驻项。
   */
  function ensureWorkflowEmployeePanelTasksFromStorage() {
    const enabled = readWorkflowEmployeeEnabledMap()
    if (!Object.values(enabled).some(Boolean)) return
    syncWorkflowEmployeePanelTasks(enabled)
  }

  function onWindowFocusForWorkflowTasks() {
    ensureWorkflowEmployeePanelTasksFromStorage()
  }

  function onVisibilityChangeForWorkflowTasks() {
    if (document.visibilityState === 'visible') {
      ensureWorkflowEmployeePanelTasksFromStorage()
    }
  }

  const activeTask = computed(() => taskList.value.find((t) => t.id === activeTaskId.value) || null)
  const filteredTaskList = computed(() => {
    const list = taskList.value
    /** 工作流员工任务长期为 running，筛选「已完成/失败」时若不排除，会整列表被清空，看起来像「工作流程不见了」 */
    const wfPersistent = list.filter((t) => t.type === 'workflow_employee' && t.status === 'running')
    if (taskFilter.value === 'all') return list
    if (taskFilter.value === 'running') {
      return list.filter((t) => t.status === 'running' || t.status === 'queued')
    }
    if (taskFilter.value === 'success') {
      const rest = list.filter((t) => t.status === 'success')
      const ids = new Set(rest.map((t) => t.id))
      const wfExtra = wfPersistent.filter((t) => !ids.has(t.id))
      return [...wfExtra, ...rest]
    }
    const rest = list.filter((t) => t.status === 'failed' || t.status === 'cancelled')
    const ids = new Set(rest.map((t) => t.id))
    const wfExtra = wfPersistent.filter((t) => !ids.has(t.id))
    return [...wfExtra, ...rest]
  })

  watch(
    () => modsStore.modsForUi,
    (mods) => {
      workflowAiEmployeesStore.hydrateFromMods(mods)
      workflowAiEmployeesStore.pruneOrphanWorkflowEmployeeToggles(mods)
      syncWorkflowEmployeePanelTasks(readWorkflowEmployeeEnabledMap())
    },
    { deep: true }
  )

  watch(
    () => workflowAiEmployeesStore.enabled,
    () => {
      syncWorkflowEmployeePanelTasks(readWorkflowEmployeeEnabledMap())
    },
    { deep: true }
  )

  function setTaskFilter(filter: 'all' | 'running' | 'success' | 'failed') {
    taskFilter.value = filter
  }

  function clearTaskHistory() {
    taskList.value = taskList.value.filter((t) => t.status === 'running' || t.status === 'queued')
    expandedTaskIds.value = expandedTaskIds.value.filter((id) => taskList.value.some((t) => t.id === id))
  }

  function isProModeActiveFromDom(): boolean {
    const overlay = document.getElementById('proModeOverlay')
    const bodyActive = document.body.classList.contains('pro-mode-active')
    const overlayActive = !!overlay?.classList.contains('active')
    const overlayVisible = !!overlay && overlay.style.display !== 'none'
    return bodyActive || (overlayActive && overlayVisible)
  }

  function resolveEffectiveProModeState(): boolean {
    const domState = isProModeActiveFromDom()
    if (typeof window.__XCAGI_IS_PRO_MODE === 'boolean') {
      if (window.__XCAGI_IS_PRO_MODE !== domState) {
        window.__XCAGI_IS_PRO_MODE = domState
        window.dispatchEvent(new CustomEvent('xcagi:pro-mode-changed', {
          detail: { isProMode: domState }
        }))
      }
    }
    return domState
  }

  function syncProModeState() {
    isProMode.value = resolveEffectiveProModeState()
  }

  function getModeScopedUserId(proEnabled: boolean): string {
    const sid = String(sessionId.value || '').trim() || 'default'
    return proEnabled ? `web_pro_${sid}` : `web_normal_${sid}`
  }

  function resolveExcelAnalysisContextForRequest(): Record<string, any> | null {
    if (lastExcelAnalysisContext.value) {
      return lastExcelAnalysisContext.value
    }
    const sid = String(sessionId.value || '').trim() || 'default'
    const restored = readPersistedExcelAnalysisContext(sid)
    if (restored) {
      lastExcelAnalysisContext.value = restored
      return restored
    }
    return null
  }

  async function requestChatByMode(message: string, fetchOptions: RequestInit = {}): Promise<any> {
    const runtimeProEnabled = resolveEffectiveProModeState()
    isProMode.value = runtimeProEnabled

    // 勾选后仅切换到专业意图链路，不强制进入专业 UI 运行态。
    const proIntentEnabled = runtimeProEnabled || !!proIntentExperienceEnabled?.value
    const hybridNormalUiProChannel = proIntentEnabled && !runtimeProEnabled
    const user_id = getModeScopedUserId(proIntentEnabled)
    const compactHistory = (messages.value || [])
      .slice(-6)
      .map((m) => ({
        role: m.role,
        content: String(m.content || '')
          .replace(/<br\s*\/?>/gi, '\n')
          .replace(/<[^>]*>/g, '')
          .slice(0, 500)
      }))
    const contextPayload: Record<string, any> = {
      recent_messages: compactHistory
    }
    const contextParts: string[] = []
    contextParts.push(`最近对话 ${compactHistory.length} 条`)
    const excelCtx = resolveExcelAnalysisContextForRequest()
    if (excelCtx) {
      contextPayload.excel_analysis = excelCtx
      contextParts.push('Excel上下文 1 份')
      if (linkedExcelSheet.value?.sheet_name) {
        contextPayload.excel_analysis_selected_sheet = {
          sheet_name: linkedExcelSheet.value.sheet_name,
          sheet_index: linkedExcelSheet.value.sheet_index
        }
        contextPayload.preferred_sheet_name = linkedExcelSheet.value.sheet_name
        contextPayload.preferred_sheet_index = linkedExcelSheet.value.sheet_index
        contextParts.push(`已关联表 ${linkedExcelSheet.value.sheet_index}:${linkedExcelSheet.value.sheet_name}`)
      }
    }
    const linkedCount = compactHistory.length + (excelCtx ? 1 : 0)
    lastRequestContextSummary.value = `已关联上下文：${contextParts.join(' + ')}（共 ${linkedCount}）`
    if (hybridNormalUiProChannel) {
      contextPayload.ui_surface = 'normal'
      contextPayload.intent_channel = 'pro'
      contextPayload.tool_execution_profile = 'normal'
    }
    const reqOpts = { signal: fetchOptions.signal }
    if (proIntentEnabled) {
      return chatApi.sendChat(
        {
          message,
          source: 'pro',
          mode: 'professional',
          user_id,
          context: contextPayload
        },
        reqOpts
      )
    }
    return chatApi.sendUnifiedChat(
      {
        message,
        source: 'normal',
        mode: 'basic',
        user_id,
        context: contextPayload
      },
      reqOpts
    )
  }

  /** 与单条请求相同的 context / user_id，用于 /api/ai/chat/batch 与 unified_chat/batch */
  async function requestChatByModeBatch(batchTexts: string[], fetchOptions: RequestInit = {}): Promise<any> {
    const runtimeProEnabled = resolveEffectiveProModeState()
    isProMode.value = runtimeProEnabled
    const proIntentEnabled = runtimeProEnabled || !!proIntentExperienceEnabled?.value
    const hybridNormalUiProChannel = proIntentEnabled && !runtimeProEnabled
    const user_id = getModeScopedUserId(proIntentEnabled)
    const compactHistory = (messages.value || [])
      .slice(-6)
      .map((m) => ({
        role: m.role,
        content: String(m.content || '')
          .replace(/<br\s*\/?>/gi, '\n')
          .replace(/<[^>]*>/g, '')
          .slice(0, 500)
      }))
    const contextPayload: Record<string, any> = {
      recent_messages: compactHistory
    }
    const contextParts: string[] = []
    contextParts.push(`最近对话 ${compactHistory.length} 条`)
    const excelCtxBatch = resolveExcelAnalysisContextForRequest()
    if (excelCtxBatch) {
      contextPayload.excel_analysis = excelCtxBatch
      contextParts.push('Excel上下文 1 份')
      if (linkedExcelSheet.value?.sheet_name) {
        contextPayload.excel_analysis_selected_sheet = {
          sheet_name: linkedExcelSheet.value.sheet_name,
          sheet_index: linkedExcelSheet.value.sheet_index
        }
        contextPayload.preferred_sheet_name = linkedExcelSheet.value.sheet_name
        contextPayload.preferred_sheet_index = linkedExcelSheet.value.sheet_index
        contextParts.push(`已关联表 ${linkedExcelSheet.value.sheet_index}:${linkedExcelSheet.value.sheet_name}`)
      }
    }
    const linkedCount = compactHistory.length + (excelCtxBatch ? 1 : 0)
    lastRequestContextSummary.value = `已关联上下文：${contextParts.join(' + ')}（共 ${linkedCount}）`
    if (hybridNormalUiProChannel) {
      contextPayload.ui_surface = 'normal'
      contextPayload.intent_channel = 'pro'
      contextPayload.tool_execution_profile = 'normal'
    }
    const reqOpts = { signal: fetchOptions.signal }
    const batchBody = {
      messages: batchTexts,
      user_id,
      context: contextPayload,
      source: proIntentEnabled ? ('pro' as const) : ('normal' as const),
      mode: proIntentEnabled ? ('professional' as const) : ('basic' as const)
    }
    if (proIntentEnabled) {
      return chatApi.sendChatBatch(batchBody as any, reqOpts)
    }
    return chatApi.sendUnifiedChatBatch(batchBody as any, reqOpts)
  }

  function getChatBatchDebounceMs(): number {
    const v = (import.meta as any).env?.VITE_CHAT_BATCH_MS
    // 默认 0：单条消息立即发；需要合并连发时可设 VITE_CHAT_BATCH_MS
    if (v === undefined || v === '') return 0
    const n = Number(v)
    return Number.isFinite(n) && n >= 0 ? n : 0
  }

  let chatBatchTimer: ReturnType<typeof setTimeout> | null = null
  let chatBatchQueue: string[] = []

  function setLoadingProgress(step: string) {
    loadingProgressText.value = String(step || '').trim() || '处理中...'
  }

  function startWaitProgressTimer() {
    const startedAt = Date.now()
    if (waitProgressTicker) {
      window.clearInterval(waitProgressTicker)
    }
    waitProgressTicker = window.setInterval(() => {
      const elapsedSec = Math.max(1, Math.floor((Date.now() - startedAt) / 1000))
      const hint =
        elapsedSec >= 8
          ? ' 若持续无响应，请确认后端已启动，且 VITE_API_BASE_URL（如有）与浏览器能访问的地址一致。'
          : ''
      loadingProgressText.value = `已发送请求，正在等待服务端响应（${elapsedSec}s）...${hint}`
    }, 1000)
  }

  function stopLoadingProgress() {
    if (waitProgressTicker) {
      window.clearInterval(waitProgressTicker)
      waitProgressTicker = null
    }
    loadingProgressText.value = '处理中...'
  }

  async function requestChatByModeWithTimeout(message: string, timeoutMs: number = 45000): Promise<any> {
    const controller = new AbortController()
    const timeoutPromise = new Promise<never>((_, reject) => {
      window.setTimeout(() => {
        controller.abort()
        reject(new Error(`请求超时（>${Math.floor(timeoutMs / 1000)}s），请检查后端是否可达或接口是否卡住`))
      }, timeoutMs)
    })
    return Promise.race([
      requestChatByMode(message, { signal: controller.signal }),
      timeoutPromise
    ])
  }

  async function requestChatByModeBatchWithTimeout(batchTexts: string[], timeoutMs: number = 45000): Promise<any> {
    const controller = new AbortController()
    const timeoutPromise = new Promise<never>((_, reject) => {
      window.setTimeout(() => {
        controller.abort()
        reject(new Error(`批量请求超时（>${Math.floor(timeoutMs / 1000)}s），请检查后端是否可达或接口是否卡住`))
      }, timeoutMs)
    })
    return Promise.race([
      requestChatByModeBatch(batchTexts, { signal: controller.signal }),
      timeoutPromise
    ])
  }

  function resolveChatTimeoutMs(message: string): number {
    const text = String(message || '').trim()
    const isComplexTask = /(导入|入库|数据库|工作流|执行|创建|新增|批量|excel|上传|加入数据库)/i.test(text)
    return isComplexTask ? 90000 : 30000
  }

  onMounted(() => {
    const sid = String(sessionId.value || '').trim() || 'default'
    if (!lastExcelAnalysisContext.value) {
      const restored = readPersistedExcelAnalysisContext(sid)
      if (restored) lastExcelAnalysisContext.value = restored
    }
    if (!linkedExcelSheet.value) {
      const first = excelSheetOptions.value[0]
      if (first) linkedExcelSheet.value = first
    }
    window.addEventListener('xcagi:wechat-ai-task-enqueue', onWechatAiTaskEnqueue)
    window.addEventListener('xcagi:wechat-shipment-preview-task', onWechatShipmentPreviewTask)
    window.addEventListener('xcagi:workflow-label-print-signal', onWorkflowLabelPrintSignal)
    window.addEventListener('xcagi:workflow-receipt-feedback-signal', onWorkflowReceiptFeedbackSignal)
    window.addEventListener('xcagi:workflow-ai-employees-changed', onWorkflowAiEmployeesChanged)
    window.addEventListener('storage', onWorkflowEmployeesStorage)
    window.addEventListener('xcagi:auto-refresh-wechat-changed', onStarRefreshOrIntentChangedForWorkflow)
    window.addEventListener('xcagi:pro-intent-experience-changed', onStarRefreshOrIntentChangedForWorkflow)
    window.addEventListener('xcagi:wechat-star-feed-polled', onWechatStarFeedPolled)
    window.addEventListener('focus', onWindowFocusForWorkflowTasks)
    document.addEventListener('visibilitychange', onVisibilityChangeForWorkflowTasks)
    syncWorkflowEmployeePanelTasks(readWorkflowEmployeeEnabledMap())
    // 页面初次就绪后再做一次兜底，确保副窗状态与任务面板最终一致。
    window.setTimeout(() => ensureWorkflowEmployeePanelTasksFromStorage(), 120)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('xcagi:wechat-ai-task-enqueue', onWechatAiTaskEnqueue)
    window.removeEventListener('xcagi:wechat-shipment-preview-task', onWechatShipmentPreviewTask)
    window.removeEventListener('xcagi:workflow-label-print-signal', onWorkflowLabelPrintSignal)
    window.removeEventListener('xcagi:workflow-receipt-feedback-signal', onWorkflowReceiptFeedbackSignal)
    window.removeEventListener('xcagi:workflow-ai-employees-changed', onWorkflowAiEmployeesChanged)
    window.removeEventListener('storage', onWorkflowEmployeesStorage)
    window.removeEventListener('xcagi:auto-refresh-wechat-changed', onStarRefreshOrIntentChangedForWorkflow)
    window.removeEventListener('xcagi:pro-intent-experience-changed', onStarRefreshOrIntentChangedForWorkflow)
    window.removeEventListener('xcagi:wechat-star-feed-polled', onWechatStarFeedPolled)
    window.removeEventListener('focus', onWindowFocusForWorkflowTasks)
    document.removeEventListener('visibilitychange', onVisibilityChangeForWorkflowTasks)
    stopPhoneAgentStatusPoll()
  })

  /** 出货管理 AI 员工：打印成功后拉取出货记录、统计与审计，并提示保存（导出）/推送 */
  async function runShipmentMgmtAfterPrintSuccess(ctx: {
    purchaseUnit: string
    orderId: number | null
    filePath: string
    labelCount: number
  }): Promise<void> {
    const enabled = readWorkflowEmployeeEnabledMap()
    if (!enabled.shipment_mgmt) return
    const unit = String(ctx.purchaseUnit || '').trim()
    if (!unit) return

    const rows = await fetchShipmentRecordsForUnit(unit)
    const summary = summarizeShipmentRecordsForAudit(rows, unit, ctx.orderId)
    const fullText = summary.detailLines.join('\n')
    const at = Date.now()

    await addAndSaveMessage(`【出货管理 · 打印后审计】\n${fullText}`, 'ai')
    const auditMsgRef = getLastAiMessageRef()

    try {
      window.dispatchEvent(new CustomEvent('xcagi:shipment-record-updated'))
    } catch {
      /* ignore */
    }

    if (taskList.value.some((t) => t.id === 'workflow_emp_shipment_mgmt')) {
      upsertWorkflowEmployeeTask('shipment_mgmt', {
        lastShipmentAudit: {
          at,
          line: summary.headline,
          detail: fullText,
        },
      })
    }

    emitAssistantPush({
      title: '出货管理 · 打印后审计',
      description: `${summary.headline}。建议打开出货记录核对，按需导出 Excel 再推送同事。`,
      feature: 'shipment',
    })

    upsertTask({
      id: createTaskId('shipment_audit'),
      type: 'shipment_audit_hint',
      source: 'system',
      title: '出货记录 · 打印后审计建议',
      status: 'success',
      progress: 100,
      summary: fullText,
      messageRef: auditMsgRef,
      payload: {
        purchaseUnit: unit,
        suggestView: 'shipment-records',
        labelCount: ctx.labelCount,
        filePath: ctx.filePath,
      },
    })
  }

  async function handleStartPrintCommand(message: string): Promise<boolean> {
    if (!isStartPrintMessage(message)) return false
    const printTaskId = createTaskId('print')
    upsertTask({
      id: printTaskId,
      type: 'print',
      source: 'print',
      title: '打印任务',
      status: 'running',
      progress: 20
    })

    const context = lastShipmentExecution.value
    if (!context) {
      await addAndSaveMessage('暂无可打印任务。请先生成发货单，再发送"开始打印"。', 'ai')
      return true
    }

    const labelPaths = Array.isArray(context.labelPaths) ? context.labelPaths : []
    const filePath = context.filePath || ''
    const purchaseUnit = String(context.purchaseUnit || '').trim()
    const orderId = context.orderId

    if (!labelPaths.length && !filePath) {
      await addAndSaveMessage('最近一次任务未包含可打印文件。请重新生成发货单后再试。', 'ai')
      return true
    }

    const summary = await executePrintTask(labelPaths, filePath, orderId, purchaseUnit)
    const resultText = buildPrintSummaryMessage(summary, labelPaths.length, filePath, purchaseUnit)
    await addAndSaveMessage(resultText, 'ai')
    upsertTask({
      id: printTaskId,
      type: 'print',
      source: 'print',
      title: '打印任务',
      status: summary.success ? 'success' : 'failed',
      progress: 100,
      summary: resultText,
      error: summary.success ? '' : (summary.message || '打印失败'),
      messageRef: getLastAiMessageRef()
    })
    const shipmentListId = String(context?.taskListId || '').trim()
    if (shipmentListId) {
      if (summary.success) {
        upsertTask({
          id: shipmentListId,
          type: 'shipment',
          source: 'shipment',
          title: '发货单生成任务',
          status: 'success',
          progress: 100,
          stage: '',
          summary: `已生成并打印。${resultText.replace(/\s+/g, ' ').slice(0, 240)}`,
          messageRef: getLastAiMessageRef()
        })
      } else {
        upsertTask({
          id: shipmentListId,
          type: 'shipment',
          source: 'shipment',
          title: '发货单生成任务',
          status: 'failed',
          stage: '打印失败',
          error: summary.message || '打印失败',
          summary: '发货单文档已生成，打印未成功。可重试「开始打印」。'
        })
      }
    }
    if (summary.success) {
      await runShipmentMgmtAfterPrintSuccess({
        purchaseUnit,
        orderId,
        filePath,
        labelCount: labelPaths.length,
      })
    }
    return true
  }

  function applyProRuntimeMode(actionType: string, enabled: boolean): boolean {
    if (!isProMode.value) return false
    const shouldEnable = enabled !== false
    const toggleWorkMode = (window as any).setWorkModeFromChat
    const toggleMonitorMode = (window as any).setMonitorModeFromChat

    if (actionType === 'show_monitor') {
      if (typeof toggleMonitorMode === 'function') {
        toggleMonitorMode(shouldEnable)
      } else {
        console.warn('[pro-runtime] monitor mode entry missing; skip fallback to work mode')
        return false
      }
    } else {
      if (typeof toggleWorkMode !== 'function') {
        console.warn('[pro-runtime] work mode entry missing')
        return false
      }
      toggleWorkMode(shouldEnable)
    }

    if (shouldEnable && typeof (window as any).refreshWorkModeMonitorList === 'function') {
      ;(window as any).refreshWorkModeMonitorList()
    }

    window.dispatchEvent(new CustomEvent('xcagi:pro-runtime-mode-changed', {
      detail: { type: actionType, enabled: shouldEnable }
    }))
    return true
  }

  async function tryHandleRuntimeModeCommand(message: string): Promise<boolean> {
    if (!isProMode.value) return false
    const modeAction = detectRuntimeModeCommand(message)
    if (!modeAction) return false

    const switched = applyProRuntimeMode(modeAction, true)
    const reply = switched
      ? (modeAction === 'show_monitor' ? '正在切换到监控模式...' : '正在切换到工作模式...')
      : (modeAction === 'show_monitor'
        ? '监控模式入口不可用，已保持当前模式不变。'
        : '工作模式入口不可用，已保持当前模式不变。')
    await addAndSaveMessage(reply, 'ai')
    return true
  }

  async function refetchTaskOrderNumber() {
    const t = currentTask.value
    if (!t || t.type !== 'shipment_generate' || t.completed) return
    orderNumberFetching.value = true
    try {
      await hydrateTaskOrderNumber(t as any, { force: true })
    } finally {
      orderNumberFetching.value = false
    }
  }

  function showTaskConfirm(task: any) {
    const nextTask = { ...(task || {}) }
    currentTask.value = nextTask

    if (nextTask?.type !== 'shipment_generate' || nextTask?.completed) return

    const existingOrderNo = String(
      nextTask?.customOrderNumber
      || nextTask?.order_number
      || nextTask?.data?.order_number
      || nextTask?.document?.order_number
      || ''
    ).trim()

    if (existingOrderNo) {
      nextTask.customOrderNumber = existingOrderNo
      return
    }

    nextTask.customOrderNumber = ''
    hydrateTaskOrderNumber(nextTask as any).catch(() => {})
    enrichShipmentPreviewProducts(nextTask as any).catch(() => {})
  }

  function emitAssistantPush(payload: any = {}) {
    const detail = {
      title: String(payload.title || '任务推送').trim(),
      description: String(payload.description || '').trim(),
      feature: payload.feature || '',
      query: payload.query || ''
    }
    latestAssistantPush.value = detail
    window.dispatchEvent(new CustomEvent('xcagi:assistant-push', { detail }))
  }

  /** 待确认的发货单生成任务出现时收起顶部副窗，突出右侧「当前任务」面板；若同时需打开产品副窗则不收起 */
  function maybeCloseAssistantFloatForShipmentTask(task: any, autoAction: any) {
    // 教程步骤若声明了 assistantTab，需要副窗保持打开以定位高亮；否则发货任务触发的「收起副窗」会与教程打开副窗竞态，导致点空气。
    if (tutorialStore.isActive && tutorialStore.currentStep?.assistantTab) {
      return
    }
    if (!task || task.completed) return
    const toolId = String(
      task?.payload?.tool_id || task?.payload?.params?.tool_id || ''
    ).trim()
    const isShipment =
      task.type === 'shipment_generate' || toolId === 'shipment_generate'
    if (!isShipment) return
    const at = String(autoAction?.type || '').trim()
    if (at === 'show_products' || at === 'show_products_float') return
    window.dispatchEvent(
      new CustomEvent('xcagi:close-assistant-float', { detail: { reason: 'shipment_task_confirm' } })
    )
  }

  /** 微信星标链路解析出可开单话术时，右侧「当前任务」展示与对话内一致的发货单预览（确认/取消 + 对话侧增删改） */
  function onWechatShipmentPreviewTask(evt: Event) {
    const d = (evt as CustomEvent).detail || {}
    const task = d.task
    if (!task || task.type !== 'shipment_generate') return
    const contact = String(d.contactName || '').trim()
    const hint =
      '\n\n可在左侧对话发送「再加 / 删除第几行 / 改成…」调整明细后再点确认执行。（与智能对话内改预览一致）'
    const baseDesc = String(task.description || '').trim()
    const next = {
      ...task,
      title: contact ? `${task.title}（微信 · ${contact}）` : `${task.title}（微信消息）`,
      description: `${baseDesc}${hint}`,
      payload: {
        ...(task.payload || {}),
        wechat_preview_source: {
          contactName: d.contactName,
          contactId: d.contactId,
          messageText: d.messageText,
        },
      },
    }
    showTaskConfirm(next)
    maybeCloseAssistantFloatForShipmentTask(next, null)
    emitAssistantPush({
      title: '微信发货单预览',
      description: contact
        ? `来自 ${contact}，请在右侧任务面板确认或先对话改明细`
        : '请在右侧任务面板确认或先对话改明细',
    })
  }

  function onWorkflowLabelPrintSignal(evt: Event) {
    const d = (evt as CustomEvent).detail || {}
    const enabled = readWorkflowEmployeeEnabledMap()
    if (!enabled.label_print) return
    if (!taskList.value.some((t) => t.id === 'workflow_emp_label_print')) return
    const line = String(d.line || '').trim() || '标签/打印类消息'
    upsertWorkflowEmployeeTask('label_print', {
      lastLabelPrint: { at: Number(d.at) || Date.now(), line },
    })
  }

  /** 星标微信命中收货/对账类意图时，写入收货确认工作流（与微信消息员工同源预处理） */
  function onWorkflowReceiptFeedbackSignal(evt: Event) {
    const d = (evt as CustomEvent).detail || {}
    const enabled = readWorkflowEmployeeEnabledMap()
    if (!enabled.receipt_confirm) return
    if (!taskList.value.some((t) => t.id === 'workflow_emp_receipt_confirm')) return
    const contact = String(d.contactName || '星标联系人').trim()
    const msg = String(d.messageText || '').trim().slice(0, 400)
    const il = String(d.intentLabel || '').trim()
    const idetail = String(d.intentDetail || '').trim().slice(0, 240)
    const line = String(d.line || '').trim() || `${contact}：${msg.slice(0, 80)}`
    const detailParts = [
      `【客户反馈 · 业务进程】联系人：${contact}`,
      il ? `预处理意图：${il}` : '',
      idetail ? `说明：${idetail}` : '',
      msg ? `原文摘要：${msg}` : '',
    ].filter(Boolean)
    upsertWorkflowEmployeeTask('receipt_confirm', {
      lastReceiptFeedback: {
        at: Number(d.at) || Date.now(),
        line,
        detail: detailParts.join('\n'),
      },
    })
    emitAssistantPush({
      title: '收货确认 · 客户业务进程',
      description: line.length > 100 ? `${line.slice(0, 100)}…` : line,
      feature: 'assistant',
    })
  }

  function buildTaskCompletedDescription(successMsg: string, data: any): string {
    const parts = [successMsg || '任务执行成功']
    const docName = data?.doc_name || data?.data?.doc_name || data?.document?.filename
    const orderNo = data?.order_number || data?.data?.order_number || data?.document?.order_number
    const filePath = data?.file_path || data?.data?.file_path || data?.document?.filepath
    const labels = Array.isArray(data?.labels) ? data.labels : (Array.isArray(data?.data?.labels) ? data.data.labels : [])
    if (docName) parts.push(`文档：${docName}`)
    if (orderNo) parts.push(`单号：${orderNo}`)
    if (typeof data?.record_id !== 'undefined' && data?.record_id !== null) parts.push(`记录ID：${data.record_id}`)
    if (typeof data?.order_id !== 'undefined' && data?.order_id !== null) parts.push(`订单ID：${data.order_id}`)
    if (labels.length) parts.push(`标签：${labels.length} 张`)
    if (filePath) parts.push(`路径：${filePath}`)
    return parts.join('；')
  }

  function buildShipmentDownloadUrl(data: any): string {
    const directUrl = data?.download_url || data?.data?.download_url
    if (directUrl && typeof directUrl === 'string') return directUrl

    const docName = data?.doc_name || data?.data?.doc_name || data?.document?.filename
    if (!docName || typeof docName !== 'string') return ''

    return `/api/shipment/download/${encodeURIComponent(docName)}`
  }

  function normalizeRecordId(value: any): number | null {
    if (value === null || value === undefined || value === '') return null
    const n = Number(value)
    if (!Number.isFinite(n)) return null
    const normalized = Math.trunc(n)
    return normalized > 0 ? normalized : null
  }

  function extractShipmentExecutionContext(data: any) {
    const filePath = data?.file_path || data?.data?.file_path || data?.document?.filepath || ''
    const purchaseUnit = String(
      data?.purchase_unit
      ?? data?.data?.purchase_unit
      ?? data?.document?.purchase_unit
      ?? ''
    ).trim()
    const orderId = normalizeRecordId(
      data?.order_id
      ?? data?.record_id
      ?? data?.data?.order_id
      ?? data?.data?.record_id
      ?? data?.document?.order_id
      ?? data?.document?.record_id
      ?? data?.data?.document?.order_id
      ?? data?.data?.document?.record_id
    )
    const labelsRaw = Array.isArray(data?.labels)
      ? data.labels
      : (Array.isArray(data?.data?.labels) ? data.data.labels : [])

    const labelPaths: string[] = []
    labelsRaw.forEach((label: any) => {
      if (typeof label === 'string' && label.trim()) {
        labelPaths.push(label.trim())
        return
      }
      if (label && typeof label === 'object') {
        const p =
          label.file_path ||
          label.path ||
          label.filePath ||
          label.filepath ||
          ''
        if (typeof p === 'string' && p.trim()) {
          labelPaths.push(p.trim())
        }
      }
    })

    return {
      filePath,
      purchaseUnit,
      orderId,
      labelPaths: Array.from(new Set(labelPaths))
    }
  }

  async function confirmTask(): Promise<void> {
    if (!currentTask.value || isExecuting.value) return

    const task = currentTask.value
    const apiUrl = task.api_url
    const method = (task.method || 'POST').toUpperCase()
    const payload = { ...(task.payload || {}) }

    if (task?.type === 'shipment_generate') {
      if (!String(task?.customOrderNumber || '').trim()) {
        await hydrateTaskOrderNumber(task as any)
      }
      const customOrderNumber = String(task?.customOrderNumber || '').trim()
      payload.params = { ...(payload.params || {}) }
      if (customOrderNumber) {
        payload.params.order_number = customOrderNumber
      } else if (Object.prototype.hasOwnProperty.call(payload.params, 'order_number')) {
        delete payload.params.order_number
      }
    }

    if (!apiUrl) {
      await addAndSaveMessage('任务执行失败：缺少 API 地址', 'ai')
      currentTask.value = null
      return
    }

    isExecuting.value = true
    let keepTaskCard = false
    let shipmentTaskId = ''
    if (task?.type === 'shipment_generate') {
      shipmentTaskId = createTaskId('shipment')
      upsertTask({
        id: shipmentTaskId,
        type: 'shipment',
        source: 'shipment',
        title: '发货单生成任务',
        status: 'running',
        progress: 20
      })
    }

    try {
      let result
      if (method === 'GET') {
        result = await fetch(apiUrl)
      } else {
        result = await fetch(apiUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
      }

      const data = await result.json().catch(() => ({}))

      if (result.ok) {
        const successMsg = data.message || data.msg || '任务执行成功'
        const shipmentDocUrl =
          task?.type === 'shipment_generate' ? buildShipmentDownloadUrl(data) : ''
        await addAndSaveMessage('[成功] ' + successMsg, 'ai', {
          ...(shipmentDocUrl ? { shipmentDownloadUrl: shipmentDocUrl } : {})
        })
        if (task?.type === 'shipment_generate') {
          lastShipmentExecution.value = {
            ...extractShipmentExecutionContext(data),
            ...(shipmentTaskId ? { taskListId: shipmentTaskId } : {})
          }
          if (shipmentTaskId) {
            upsertTask({
              id: shipmentTaskId,
              type: 'shipment',
              source: 'shipment',
              title: '发货单生成任务',
              status: 'running',
              progress: 70,
              stage: '发货单已生成，待打印',
              summary: buildTaskCompletedDescription(successMsg, data),
              messageRef: getLastAiMessageRef()
            })
          }
        }
        currentTask.value = {
          ...task,
          title: `${task.title || '任务'}（已完成）`,
          description: buildTaskCompletedDescription(successMsg, data),
          order_number: data?.order_number || data?.data?.order_number || data?.document?.order_number || '',
          downloadUrl: task?.type === 'shipment_generate' ? buildShipmentDownloadUrl(data) : '',
          completed: true
        }
        keepTaskCard = true

        if (task.switch_view) {
          handleAutoAction({ type: task.switch_view })
        }
      } else {
        const errMsg = (data && (data.message || data.msg || data.error)) || `执行失败 (HTTP ${result.status})`
        await addAndSaveMessage('[失败] 任务执行失败：' + errMsg, 'ai')
        if (shipmentTaskId) {
          failTask(shipmentTaskId, errMsg)
        }
      }
    } catch (e: any) {
      await addAndSaveMessage('[失败] 任务执行失败：' + (e.message || '网络错误'), 'ai')
      if (shipmentTaskId) {
        failTask(shipmentTaskId, e.message || '网络错误')
      }
    } finally {
      isExecuting.value = false
      if (!keepTaskCard) {
        currentTask.value = null
      }
    }
  }

  function cancelTask() {
    currentTask.value = null
  }

  function handleAutoAction(action: any, userMessage: string = '') {
    console.log('[AutoAction] 触发:', action, '| 用户消息:', userMessage)
    const type = action?.type || ''
    const actionQuery = String(action?.query || action?.keyword || userMessage || '').trim()

    if (type === 'set_work_mode') {
      applyProRuntimeMode(type, action?.enabled)
    } else if (type === 'show_monitor') {
      applyProRuntimeMode(type, true)
    }

    // 与普通模式一致：无论是否专业 UI，产品副窗都应打开（工作流也会下发 show_products_float）
    if (type === 'show_products' || type === 'show_products_float') {
      emitAssistantPush({
        title: '产品查询',
        description: '已在副窗打开产品卡片编辑窗口，可直接查询并修改。',
        feature: 'products',
        query: actionQuery
      })
      const floatDetail: Record<string, unknown> = {
        feature: 'products',
        query: actionQuery,
        forceOpen: true
      }
      const hyd = action?.hydrateProductSearch
      if (hyd && Array.isArray(hyd.rows)) {
        floatDetail.hydrateProductSearch = { rows: hyd.rows, total: hyd.total }
      }
      window.dispatchEvent(new CustomEvent('xcagi:open-assistant-float', { detail: floatDetail }))
      // 原逻辑：仅专业 UI 下 show_products 会额外跳到产品页（show_products_float 不跳页）
      if (type === 'show_products' && isProMode.value) {
        window.dispatchEvent(new CustomEvent('xcagi:switch-view', { detail: { view: 'products' } }))
      }
      return
    }

    const viewMap: Record<string, string> = {
      'show_chat': 'chat',
      'show_products': 'products',
      'show_materials': 'materials',
      'show_orders': 'orders',
      'show_print': 'print',
      'show_customers': 'customers',
      'show_labels_export': 'print'
    }

    console.log('[AutoAction] 视图映射 type:', type, '-> 目标视图:', viewMap[type] || '未匹配')
    if (viewMap[type]) {
      console.log('[AutoAction] 派发 xcagi:switch-view 事件, detail:', { view: viewMap[type] })
      window.dispatchEvent(new CustomEvent('xcagi:switch-view', { detail: { view: viewMap[type] } }))
      if (viewMap[type] === 'products') {
        emitAssistantPush({
          title: '产品查询',
          description: '可在顶部副窗中直接查询并修改产品信息。',
          feature: 'products',
          query: userMessage || ''
        })
        window.dispatchEvent(new CustomEvent('xcagi:open-assistant-float', {
          detail: { feature: 'products', query: userMessage || '' }
        }))
      }
    }
    const event = new CustomEvent('auto-action', { detail: { action, userMessage } })
    window.dispatchEvent(event)

    if (!isProMode.value && ['set_work_mode', 'show_monitor'].includes(type)) {
      return
    }

    if (typeof (window as any).legacyAutoActionHandler === 'function') {
      ;(window as any).legacyAutoActionHandler(action, userMessage)
    }
  }

  function attachThinkingStepsToLastAiMessage(data: any): void {
    const thinkingSteps = String(
      data?.data?.data?.thinking_steps
      || data?.thinking_steps
      || ''
    ).trim()
    if (!thinkingSteps) return

    for (let i = messages.value.length - 1; i >= 0; i -= 1) {
      const msg = messages.value[i]
      if (msg?.role === 'ai') {
        msg.thinkingSteps = thinkingSteps
        break
      }
    }
  }

  function getLastAiMessageRef(): string {
    for (let i = messages.value.length - 1; i >= 0; i -= 1) {
      const msg = messages.value[i]
      if (msg?.role === 'ai') {
        return `${i}`
      }
    }
    return ''
  }

  function jumpToTaskMessage(task: TaskItem) {
    const refKey = String(task?.messageRef || '').trim()
    const index = Number(refKey)
    if (!Number.isFinite(index) || !chatMessagesRef.value) return
    const nodes = chatMessagesRef.value.querySelectorAll('.message')
    const target = nodes[index] as HTMLElement | undefined
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  function attachTodoStepsToLastAiMessage(data: any): void {
    const todoRaw = data?.data?.data?.todo
    if (!Array.isArray(todoRaw) || !todoRaw.length) return
    const todoSteps = todoRaw.map((x: any) => String(x || '').trim()).filter(Boolean)
    if (!todoSteps.length) return

    for (let i = messages.value.length - 1; i >= 0; i -= 1) {
      const msg = messages.value[i]
      if (msg?.role === 'ai') {
        msg.todoSteps = todoSteps
        break
      }
    }
  }

  function attachWorkflowTraceToLastAiMessage(data: any): void {
    const action = String(data?.data?.action || '').trim()
    const nodeResultsRaw = data?.data?.data?.node_results
    const nodeResults = Array.isArray(nodeResultsRaw)
      ? nodeResultsRaw.map((x: any) => ({
        node_id: String(x?.node_id || ''),
        success: !!x?.success,
        tool_id: String(x?.tool_id || ''),
        action: String(x?.action || ''),
        error: String(x?.error || '')
      })).filter((x: any) => x.node_id)
      : []
    if (!action && !nodeResults.length) return

    for (let i = messages.value.length - 1; i >= 0; i -= 1) {
      const msg = messages.value[i]
      if (msg?.role === 'ai') {
        msg.workflowAction = action
        if (nodeResults.length) {
          msg.nodeResults = nodeResults
        }
        break
      }
    }
  }

  function attachContextSummaryToLastAiMessage(): void {
    const summary = String(lastRequestContextSummary.value || '').trim()
    if (!summary) return
    for (let i = messages.value.length - 1; i >= 0; i -= 1) {
      const msg = messages.value[i]
      if (msg?.role === 'ai') {
        msg.contextSummary = summary
        break
      }
    }
  }

  function syncTaskFromChatResponse(resp: any, userText: string) {
    const action = String(resp?.data?.action || '').trim()
    const messageRef = getLastAiMessageRef()
    if (action === 'workflow_confirmation_required') {
      const pendingId = String(resp?.data?.data?.pending_workflow_id || createTaskId('wf'))
      upsertTask({
        id: pendingId,
        type: 'workflow',
        source: 'workflow',
        title: `工作流任务：${String(userText || '').slice(0, 30) || '待确认任务'}`,
        status: 'queued',
        progress: 10,
        summary: '等待确认执行',
        messageRef,
        payload: { response: resp }
      })
      return
    }
    if (action === 'workflow_done' || action === 'workflow_failed') {
      const target = taskList.value.find((t) => t.type === 'workflow' && (t.status === 'queued' || t.status === 'running'))
      if (!target) return
      if (action === 'workflow_done') {
        upsertTask({
          id: target.id,
          type: target.type,
          source: target.source,
          title: target.title,
          status: 'success',
          progress: 100,
          summary: '执行完成',
          messageRef
        })
      } else {
        upsertTask({
          id: target.id,
          type: target.type,
          source: target.source,
          title: target.title,
          status: 'failed',
          error: String(resp?.message || '工作流执行失败'),
          messageRef
        })
      }
      return
    }
    const nodeResults = Array.isArray(resp?.data?.data?.node_results) ? resp.data.data.node_results : []
    if (nodeResults.length) {
      const running = taskList.value.find((t) => t.type === 'workflow' && (t.status === 'queued' || t.status === 'running'))
      if (running) {
        const done = nodeResults.filter((x: any) => !!x?.success).length
        const progress = Math.max(15, Math.floor((done / nodeResults.length) * 100))
        upsertTask({
          id: running.id,
          type: running.type,
          source: running.source,
          title: running.title,
          status: 'running',
          progress,
          stage: `节点 ${done}/${nodeResults.length}`,
          messageRef
        })
      }
    }
  }

  function maybePrefetchProductAssistantFloat(userText: string) {
    // 教程进行中也需要与聊天请求并行预开产品副窗；否则会出现「不开教程立刻出副窗、走了教程反而要等 AI」的体验差。
    // 副窗切到「协助/产品查询」若与某步高亮冲突，用户仍可用教程卡片「下一步」或退出教程。
    const kw = extractLikelyProductQueryKeyword(userText)
    if (!kw) return
    window.dispatchEvent(
      new CustomEvent('xcagi:open-assistant-float', {
        detail: { feature: 'products', query: kw, forceOpen: true }
      })
    )
  }

  async function executeRemoteChatRound(remoteMessages: string[]) {
    if (!remoteMessages.length) return
    const primaryText = remoteMessages[0] || ''

    /** 未开专业版界面且未勾选「专业意图体验」时：查产品类话术不必等 /ai/chat 或连通性探测，直接走产品列表接口 */
    const kwFast =
      remoteMessages.length === 1 &&
      !resolveEffectiveProModeState() &&
      !proIntentExperienceEnabled?.value &&
      !resolveExcelAnalysisContextForRequest()
        ? extractLikelyProductQueryKeyword(primaryText)
        : null

    // 快路径会自己拉产品列表并注水副窗；再 prefetch 会多打一遍相同接口，徒增等待
    if (!kwFast) {
      maybePrefetchProductAssistantFloat(primaryText)
    }

    if (kwFast) {
      isLoading.value = true
      setLoadingProgress('正在查询产品库…')
      startWaitProgressTimer()
      try {
        const resp = await productsApi.searchProducts(kwFast)
        if (resp && (resp as any).success === false) {
          throw new Error(String((resp as any)?.message || '产品库查询失败'))
        }
        const raw = (resp as any)?.data ?? (resp as any)?.products ?? (resp as any)?.items
        const rows = Array.isArray(raw) ? raw : []
        const lines = rows.slice(0, 3).map((row: any) => {
          const m = String(row.model_number || '').trim()
          const n = String(row.name || row.product_name || '-').trim()
          const p = Number(row.price || 0)
          const pf = Number.isFinite(p) ? p.toFixed(2) : '0.00'
          return `- ${m || '-'} / ${n} / ￥${pf}`
        })
        const previewSuffix = lines.length
          ? `\n预览命中 ${rows.length} 条：\n${lines.join('\n')}`
          : '\n未命中具体产品，可在副窗调整关键词再查。'
        const responseText = `已帮你打开产品副窗并带入「${kwFast}」。可在卡片中查看与修改。${previewSuffix}`
        const payload: any = {
          success: true,
          response: responseText,
          autoAction: { type: 'show_products_float', query: kwFast }
        }
        const mappedRows = rows.slice(0, 20).map((r: any) => ({
          id: r.id,
          model_number: r.model_number || '',
          name: r.name || r.product_name || '',
          price: Number(r.price || 0),
          unit: r.unit || ''
        }))
        const totalFromApi = typeof (resp as any)?.total === 'number' ? (resp as any).total : rows.length
        await addAndSaveMessage(payload.response, 'ai')
        syncTaskFromChatResponse(payload, primaryText)
        attachContextSummaryToLastAiMessage()
        attachThinkingStepsToLastAiMessage(payload)
        attachTodoStepsToLastAiMessage(payload)
        attachWorkflowTraceToLastAiMessage(payload)
        if (!payload.task && (payload.autoAction?.type === 'show_products_float' || payload.autoAction?.type === 'show_products')) {
          currentTask.value = null
        }
        if (payload.autoAction) {
          handleAutoAction(
            {
              ...payload.autoAction,
              hydrateProductSearch: { rows: mappedRows, total: totalFromApi }
            },
            primaryText
          )
        }
        return
      } catch {
        /* 回退到下方 unified / chat 全链路 */
      } finally {
        isLoading.value = false
        stopLoadingProgress()
      }
    }

    isLoading.value = true
    const runtimeProForLoading = resolveEffectiveProModeState()
    const hybridNormalUiProChannel =
      !!proIntentExperienceEnabled?.value && !runtimeProForLoading
    setLoadingProgress(
      hybridNormalUiProChannel
        ? '专业意图处理中（普通界面槽位）...'
        : '正在理解你的问题...'
    )
    let data: any
    try {
      // 不再在发聊天前阻塞等待 /api/ai/test（最多 3s），否则「慢」往往来自这里而非 AI
      setLoadingProgress(
        remoteMessages.length > 1
          ? `正在批量处理 ${remoteMessages.length} 条消息...`
          : '正在整理上下文...'
      )
      startWaitProgressTimer()
      const base = resolveChatTimeoutMs(primaryText)
      const timeoutMs = Math.min(120000, remoteMessages.length <= 1 ? base : base * remoteMessages.length)
      if (remoteMessages.length === 1) {
        data = await requestChatByModeWithTimeout(remoteMessages[0], timeoutMs)
      } else {
        data = await requestChatByModeBatchWithTimeout(remoteMessages, timeoutMs)
      }
      const head = remoteMessages.length === 1 ? data : data?.results?.[0]
      setLoadingProgress('已收到响应，正在解析执行计划...')
      if (head?.data?.action === 'workflow_confirmation_required') {
        setLoadingProgress('已生成计划，等待你确认执行...')
      } else if (head?.data?.action === 'workflow_done') {
        setLoadingProgress('执行完成，正在整理结果...')
      } else if (head?.data?.action === 'workflow_failed') {
        setLoadingProgress('执行失败，正在整理错误信息...')
      }
    } catch (err: any) {
      data = {
        success: false,
        message: err?.message || '请求失败'
      }
    } finally {
      isLoading.value = false
      stopLoadingProgress()
    }

    if (data.batch && Array.isArray(data.results)) {
      if (data.success) {
        for (const part of data.results) {
          if (part && part.success) {
            await addAndSaveMessage(part.response, 'ai')
            syncTaskFromChatResponse(part, primaryText)
          } else {
            await addAndSaveMessage('处理失败: ' + (part?.message || '未知错误'), 'ai')
          }
        }
        attachContextSummaryToLastAiMessage()
        const lastOk = [...data.results].reverse().find((p: any) => p && p.success)
        if (lastOk) {
          attachThinkingStepsToLastAiMessage(lastOk)
          attachTodoStepsToLastAiMessage(lastOk)
          attachWorkflowTraceToLastAiMessage(lastOk)
        }
        const lastTask = [...data.results].reverse().find((p: any) => p?.task)
        if (lastTask?.task) {
          showTaskConfirm(lastTask.task)
          emitAssistantPush({
            title: lastTask.task.title || '新任务',
            description: lastTask.task.description || '收到一条任务，请处理'
          })
        }
        const lastFloat = [...data.results].reverse().find(
          (p: any) =>
            p?.autoAction?.type === 'show_products_float' || p?.autoAction?.type === 'show_products'
        )
        if (!lastTask?.task && lastFloat?.autoAction) {
          currentTask.value = null
        }
        const lastAction = [...data.results].reverse().find((p: any) => p?.autoAction)
        if (lastAction?.autoAction) {
          handleAutoAction(lastAction.autoAction, remoteMessages[remoteMessages.length - 1] || '')
        }
        if (lastTask?.task) {
          maybeCloseAssistantFloatForShipmentTask(lastTask.task, lastAction?.autoAction)
        }
      } else {
        await addAndSaveMessage('处理失败: ' + (data.message || '批量请求失败'), 'ai')
      }
      return
    }

    if (data.success) {
      await addAndSaveMessage(data.response, 'ai')
      syncTaskFromChatResponse(data, primaryText)
      attachContextSummaryToLastAiMessage()
      attachThinkingStepsToLastAiMessage(data)
      attachTodoStepsToLastAiMessage(data)
      attachWorkflowTraceToLastAiMessage(data)

      if (data.task) {
        showTaskConfirm(data.task)
        emitAssistantPush({
          title: data.task.title || '新任务',
          description: data.task.description || '收到一条任务，请处理'
        })
      }
      if (!data.task && (data?.autoAction?.type === 'show_products_float' || data?.autoAction?.type === 'show_products')) {
        currentTask.value = null
      }

      if (data.autoAction) {
        handleAutoAction(data.autoAction, primaryText)
      }
      if (data.task) {
        maybeCloseAssistantFloatForShipmentTask(data.task, data.autoAction)
      }
    } else {
      await addAndSaveMessage('处理失败: ' + data.message, 'ai')
    }
  }

  async function sendMessage(message: string) {
    await addAndSaveMessage(message, 'user')

    const modeHandled = await tryHandleRuntimeModeCommand(message)
    if (modeHandled) return

    const previewModified = await handleShipmentModify(message)
    if (previewModified) return

    if (
      isProMode.value &&
      typeof (window as any).isProTaskAcquisitionMessage === 'function' &&
      (window as any).isProTaskAcquisitionMessage(message) &&
      typeof (window as any).jarvisSendMessage === 'function'
    ) {
      ;(window as any).jarvisSendMessage(message)
      return
    }

    const printHandled = await handleStartPrintCommand(message)
    if (printHandled) return

    const debounceMs = getChatBatchDebounceMs()
    if (debounceMs <= 0) {
      await executeRemoteChatRound([message])
      return
    }
    chatBatchQueue.push(message)
    if (chatBatchTimer) clearTimeout(chatBatchTimer)
    chatBatchTimer = window.setTimeout(() => {
      chatBatchTimer = null
      const msgs = chatBatchQueue.splice(0)
      void executeRemoteChatRound(msgs)
    }, debounceMs)
  }

  async function showHistoryPanel() {
    try {
      const data = await chatApi.getConversations({ limit: 20 })
      if (data.success && data.sessions) {
        historySessions.value = data.sessions
        showHistory.value = true
      }
    } catch (e) {
      console.error('加载历史失败:', e)
    }
  }

  async function loadSession(targetSessionId: string) {
    sessionId.value = targetSessionId
    localStorage.setItem('ai_session_id', targetSessionId)
    showHistory.value = false

    try {
      const data = await chatApi.getConversation(targetSessionId)
      if (data.success && data.messages && data.messages.length > 0) {
        loadMessages(data.messages.map((msg: any) => ({
          role: msg.role,
          content: normalizeServerContentToHtml(msg.content),
          time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
        })))
      }
    } catch (e) {
      console.error('加载会话失败:', e)
    }
  }

  function newConversation() {
    const prev = String(sessionId.value || '').trim() || 'default'
    persistExcelAnalysisContext(prev, null)
    lastExcelAnalysisContext.value = null
    linkedExcelSheet.value = null
    sessionId.value = generateSessionId()
    localStorage.setItem('ai_session_id', sessionId.value)
    clearMessages()
  }

  function handleShipmentDownloadClick() {
    addAndSaveMessage('发货单已开始下载。是否现在执行打印？可点击"开始打印"按钮或直接发送"开始打印"。', 'ai')
  }

  async function startPrintFromTaskCard() {
    await handleStartPrintCommand('开始打印')
  }

  async function copyAssistantPushContent() {
    const title = String(latestAssistantPush.value?.title || '').trim()
    const desc = String(latestAssistantPush.value?.description || '').trim()
    const text = [title, desc].filter(Boolean).join('\n')
    if (!text) return
    try {
      pushCopied.value = true
      window.setTimeout(() => {
        pushCopied.value = false
      }, 1200)
    } catch (_e) {
      pushCopied.value = false
    }
  }

  function openAssistantFloatFromTaskPanel() {
    const detail = latestAssistantPush.value || {}
    window.dispatchEvent(new CustomEvent('xcagi:open-assistant-float', { detail }))
  }

  async function syncSessionMessages(): Promise<void> {
    await syncFromServer()
  }

  async function bindExcelSheetToChat(sheet: { sheet_name: string; sheet_index: number }): Promise<void> {
    const name = String(sheet?.sheet_name || '').trim()
    const idx = Number(sheet?.sheet_index || 0)
    if (!name || idx <= 0) return
    linkedExcelSheet.value = { sheet_name: name, sheet_index: idx }
    const excelCtx = resolveExcelAnalysisContextForRequest()
    window.dispatchEvent(new CustomEvent('xcagi:excel-sheet-context', {
      detail: {
        selected_sheet: linkedExcelSheet.value,
        excel_analysis: excelCtx
      }
    }))
    window.dispatchEvent(new CustomEvent('xcagi:open-assistant-float', {
      detail: {
        feature: 'assistant',
        forceOpen: true,
        task: true
      }
    }))
    // 仅更新上下文，不插入聊天提示，避免打断会话阅读。
  }

  return {
    messages,
    lastMessage,
    currentTask,
    orderNumberFetching,
    isLoading,
    isExecuting,
    latestAssistantPush,
    proRuntimeTask,
    taskList,
    filteredTaskList,
    activeTask,
    activeTaskId,
    expandedTaskIds,
    taskFilter,
    showHistory,
    historySessions,
    chatMessagesRef,
    pushCopied,
    loadingProgressText,
    excelAnalyzeUploading,
    excelAnalyzeInputRef,
    excelSheetOptions,
    linkedExcelSheet,
    isProMode,
    isPrinting,
    taskTableColumns,
    taskTableItems,
    taskOrderNumber,
    generateSessionId,
    scrollToBottom,
    syncProModeState,
    sendMessage,
    confirmTask,
    refetchTaskOrderNumber,
    cancelTask,
    showTaskConfirm,
    triggerExcelAnalyzeUpload,
    onExcelAnalyzeFileChange,
    showHistoryPanel,
    loadSession,
    newConversation,
    handleShipmentDownloadClick,
    startPrintFromTaskCard,
    copyAssistantPushContent,
    openAssistantFloatFromTaskPanel,
    syncSessionMessages,
    bindExcelSheetToChat,
    toggleTaskExpanded,
    setTaskFilter,
    clearTaskHistory,
    cancelTaskById,
    retryTask,
    jumpToTaskMessage,
    handleAutoAction,
    isStartPrintMessage
  }
}
