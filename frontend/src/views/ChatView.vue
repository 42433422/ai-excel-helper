<template>
  <div class="chat-view page-view active" id="view-chat">
    <div class="quick-actions">
      <button
        v-for="quickBtn in visibleQuickButtons"
        :key="quickBtn.text"
        class="quick-btn"
        :data-quick="quickBtn.text"
        :data-action="quickBtn.text === '测试预览' ? 'test-preview' : null"
        @click="sendQuick(quickBtn.text)"
      >
        {{ quickBtn.label }}
      </button>
    </div>
    <div class="chat-container">
      <div class="chat-messages" id="chatMessages" ref="chatMessagesRef">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          :class="['message', msg.role]"
        >
          <template v-if="msg.role === 'ai' && isMessageCollapsed(msg, idx)">
            <div class="collapsed-message">
              <div class="collapsed-message-text">{{ getCollapsedPreview(msg.content) }}</div>
              <button class="btn btn-secondary btn-sm" @click="expandMessage(idx)">展开详情</button>
            </div>
          </template>
          <template v-else>
            <div v-html="msg.content"></div>
            <div
              v-if="msg.role === 'ai' && msg.shipmentDownloadUrl"
              class="message-shipment-actions"
            >
              <a
                class="btn btn-primary btn-sm"
                :href="msg.shipmentDownloadUrl"
                download
                @click="handleShipmentDownloadClick"
              >
                下载发货单
              </a>
            </div>
            <button
              v-if="msg.role === 'ai' && idx < latestAiMessageIndex"
              class="btn btn-secondary btn-sm collapse-toggle"
              @click="collapseMessage(idx)"
            >
              收起
            </button>
          </template>
          <div v-if="msg.role === 'ai' && msg.contextSummary" class="context-summary">
            {{ msg.contextSummary }}
          </div>
          <details v-if="msg.role === 'ai' && msg.thinkingSteps" class="thinking-panel">
            <summary>查看思考步骤</summary>
            <pre>{{ msg.thinkingSteps }}</pre>
          </details>
          <div v-if="msg.role === 'ai' && msg.todoSteps && msg.todoSteps.length" class="todo-panel">
            <div class="todo-title">执行 TODO</div>
            <ul>
              <li v-for="(step, tIdx) in msg.todoSteps" :key="tIdx">{{ step }}</li>
            </ul>
          </div>
          <div v-if="msg.role === 'ai' && (msg.workflowAction || (msg.nodeResults && msg.nodeResults.length))" class="trace-panel">
            <div class="trace-title">执行轨迹</div>
            <div class="trace-stages">
              <span class="trace-chip">Thinking</span>
              <span class="trace-chip">Plan</span>
              <span class="trace-chip">Execute</span>
            </div>
            <div class="trace-action" v-if="msg.workflowAction">状态：{{ msg.workflowAction }}</div>
            <ul v-if="msg.nodeResults && msg.nodeResults.length" class="trace-list">
              <li v-for="(nr, nIdx) in msg.nodeResults" :key="nIdx">
                <span :class="['trace-status', nr.success ? 'ok' : 'fail']">{{ nr.success ? '成功' : '失败' }}</span>
                <span>{{ nr.node_id }} · {{ nr.tool_id }}.{{ nr.action }}</span>
              </li>
            </ul>
          </div>
          <div class="time">{{ msg.time }}</div>
        </div>
        <div v-if="isLoading" class="message ai">
          <div><span class="status-dot online"></span> {{ loadingProgressText }}</div>
        </div>
      </div>
      <div class="right-panel">
        <div class="panel-header">{{ currentTask ? '当前任务' : '当前任务' }}</div>
        <div class="panel-content panel-content-task" id="taskPanel">
          <div class="task-panel-body">
          <!-- 主任务卡片与任务列表可同时展示：confirmTask 会立刻 upsert 列表项，若仍用 v-else-if 会整卡消失，导致无法使用「下载 / 开始打印」 -->
          <template v-if="currentTask">
            <div class="task-card">
              <div class="task-header">{{ currentTask.title }}</div>
              <div>{{ currentTask.description }}</div>
              <div
                v-if="currentTask?.type === 'shipment_generate' && !currentTask?.completed"
                class="task-order-number-row"
              >
                <span>订单编号：</span>
                <input
                  v-model="currentTask.customOrderNumber"
                  type="text"
                  class="form-control form-control-sm"
                  style="max-width:180px;height:28px;"
                  placeholder="自动获取或手动输入"
                >
                <button
                  type="button"
                  class="btn btn-secondary btn-sm"
                  :disabled="orderNumberFetching || isExecuting"
                  title="从服务器重新拉取下一个可用编号"
                  @click="refetchTaskOrderNumber"
                >
                  {{ orderNumberFetching ? '获取中…' : '获取编号' }}
                </button>
              </div>
              <div v-else-if="taskOrderNumber" style="margin-top:6px;color:#4b5563;font-size:12px;">
                订单编号：{{ taskOrderNumber }}
              </div>
              <table v-if="currentTask.items && currentTask.items.length > 0" class="data-table" style="margin-top:10px;">
                <thead>
                  <tr>
                    <th v-for="(key, idx) in taskTableColumns" :key="idx">
                      {{ key }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, iIdx) in taskTableItems" :key="iIdx">
                    <td v-for="(key, vIdx) in taskTableColumns" :key="vIdx">
                      {{ item[key] }}
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-if="!currentTask.completed" class="task-actions">
                <button class="btn btn-success btn-sm" data-action="confirm-task" @click="confirmTask" :disabled="isExecuting">
                  {{ isExecuting ? '执行中...' : '确认执行' }}
                </button>
                <button class="btn btn-secondary btn-sm" data-action="cancel-task" @click="cancelTask" :disabled="isExecuting">取消</button>
              </div>
              <div v-else class="task-actions">
                <a
                  v-if="currentTask.downloadUrl"
                  class="btn btn-primary btn-sm"
                  :href="currentTask.downloadUrl"
                  download
                  @click="handleShipmentDownloadClick"
                >
                  下载发货单
                </a>
                <button
                  v-if="currentTask?.type === 'shipment_generate'"
                  type="button"
                  class="btn btn-success btn-sm"
                  data-action="start-print"
                  @click="startPrintFromTaskCard"
                >
                  开始打印
                </button>
                <button class="btn btn-secondary btn-sm" data-action="close-task" @click="cancelTask">关闭</button>
              </div>
            </div>
          </template>
          <template v-if="taskList.length">
            <div class="task-toolbar" :class="{ 'task-toolbar-below-card': !!currentTask }">
              <div class="task-filters">
                <button class="task-filter-btn" :class="{ active: taskFilter === 'all' }" @click="setTaskFilter('all')">全部</button>
                <button class="task-filter-btn" :class="{ active: taskFilter === 'running' }" @click="setTaskFilter('running')">进行中</button>
                <button class="task-filter-btn" :class="{ active: taskFilter === 'success' }" @click="setTaskFilter('success')">已完成</button>
                <button class="task-filter-btn" :class="{ active: taskFilter === 'failed' }" @click="setTaskFilter('failed')">失败</button>
              </div>
              <button class="btn btn-secondary btn-sm" @click="clearTaskHistory">清空历史</button>
            </div>
            <div class="task-list">
              <div
                v-for="task in filteredTaskList"
                :key="task.id"
                class="task-list-item"
                :class="{
                  'task-list-item-workflow-collapsed':
                    task.type === 'workflow_employee' && !expandedTaskIds.includes(task.id),
                }"
              >
                <button
                  type="button"
                  class="task-list-main"
                  :aria-expanded="expandedTaskIds.includes(task.id)"
                  @click="toggleTaskExpanded(task.id)"
                >
                  <span
                    class="task-dot"
                    :class="`status-${workflowTaskDotStatusClass(task)}`"
                    :title="workflowTaskDotTitle(task)"
                  />
                  <span class="task-list-title">{{ task.title }}</span>
                  <span
                    v-if="task.type === 'workflow_employee'"
                    class="task-list-chevron"
                    aria-hidden="true"
                  >{{ expandedTaskIds.includes(task.id) ? '▼' : '▶' }}</span>
                  <span class="task-list-time">{{ formatTaskTime(task.updatedAt) }}</span>
                </button>
                <div
                  v-if="task.type !== 'workflow_employee' || expandedTaskIds.includes(task.id)"
                  class="task-list-meta"
                >
                  <span>{{ formatTaskSourceLabel(task.source) }}</span>
                  <span
                    v-if="typeof task.progress === 'number' && task.status !== 'failed' && task.status !== 'cancelled' && !(task.type === 'workflow_employee' && task.payload?.workflowProgressStarted === false)"
                  >进度 {{ task.progress }}%</span>
                  <span v-if="task.stage">{{ task.stage }}</span>
                </div>
                <div
                  v-if="task.type === 'workflow_employee' && expandedTaskIds.includes(task.id) && (task.payload?.workflowProgressPct != null || task.payload?.workflowMonitorLine || task.payload?.workflowCurrentHint || (task.payload?.workflowSteps && task.payload.workflowSteps.length))"
                  class="task-workflow-body"
                >
                  <div
                    v-if="typeof task.payload?.workflowProgressPct === 'number'"
                    class="task-wf-progress"
                  >
                    <div class="task-wf-progress-head">
                      <span class="task-wf-progress-title">任务进度</span>
                      <span class="task-wf-progress-meta">
                        <template v-if="task.payload?.workflowProgressStarted === false">
                          {{ task.payload.workflowProgressLabel }}
                        </template>
                        <template v-else>
                          {{ task.payload.workflowProgressPct }}%
                          <template v-if="task.payload.workflowProgressLabel">
                            · {{ task.payload.workflowProgressLabel }}
                          </template>
                        </template>
                      </span>
                    </div>
                    <div
                      class="task-wf-progress-track"
                      role="progressbar"
                      :aria-valuenow="workflowProgressIsIdle(task.payload) ? 0 : task.payload.workflowProgressPct"
                      aria-valuemin="0"
                      aria-valuemax="100"
                      :aria-valuetext="workflowProgressIsIdle(task.payload) ? '未开始' : `${task.payload.workflowProgressPct}%`"
                    >
                      <div
                        class="task-wf-progress-fill"
                        :class="{ 'task-wf-progress-fill-idle': workflowProgressIsIdle(task.payload) }"
                        :style="{ width: workflowProgressIsIdle(task.payload) ? '0%' : Math.min(100, Math.max(0, task.payload.workflowProgressPct)) + '%' }"
                      />
                    </div>
                  </div>
                  <div v-if="task.payload?.workflowMonitorLine" class="task-wf-monitor">
                    <span class="task-wf-monitor-pulse" aria-hidden="true" />
                    <div class="task-wf-monitor-copy">
                      <div class="task-wf-monitor-kicker">工作状态 · 监控</div>
                      <div
                        class="task-wf-monitor-text"
                        :title="task.payload.workflowMonitorLine"
                      >
                        {{ task.payload.workflowMonitorLine }}
                      </div>
                    </div>
                  </div>
                  <div v-if="task.payload?.workflowCurrentHint" class="task-workflow-hint task-workflow-hint-secondary">
                    {{ task.payload.workflowCurrentHint }}
                  </div>
                  <details v-if="task.payload?.workflowSteps?.length" class="task-wf-steps-details">
                    <summary>步骤明细</summary>
                    <ol class="task-workflow-steps">
                      <li
                        v-for="s in task.payload.workflowSteps"
                        :key="s.id"
                        :class="['task-workflow-step', `task-workflow-step--${s.status}`]"
                      >
                        <span class="task-workflow-step-text">{{ s.label }}</span>
                        <span class="task-workflow-step-state">{{
                          s.status === 'done' ? '已完成' : s.status === 'active' ? '进行中' : '待触发'
                        }}</span>
                      </li>
                    </ol>
                  </details>
                </div>
                <div v-if="expandedTaskIds.includes(task.id)" class="task-list-detail">
                  <div v-if="task.summary" class="task-summary">{{ task.summary }}</div>
                  <div v-if="task.error" class="task-error">{{ task.error }}</div>
                  <div
                    v-if="task.type !== 'workflow_employee'"
                    class="task-actions"
                  >
                    <button
                      v-if="task.type === 'shipment_audit_hint'"
                      type="button"
                      class="btn btn-primary btn-sm"
                      @click="openShipmentRecordsFromAuditTask"
                    >打开出货记录</button>
                    <button class="btn btn-secondary btn-sm" @click="jumpToTaskMessage(task)">定位消息</button>
                    <button v-if="task.status === 'failed' || task.status === 'cancelled'" class="btn btn-primary btn-sm" @click="retryTask(task.id)">重试</button>
                    <button v-if="task.status === 'running' || task.status === 'queued'" class="btn btn-secondary btn-sm" @click="cancelTaskById(task.id)">取消</button>
                  </div>
                </div>
              </div>
            </div>
          </template>
          <template v-if="!currentTask && !taskList.length && isProMode && proRuntimeTask">
            <div class="task-card">
              <div class="task-header">{{ proRuntimeTask.title }}</div>
              <div style="margin-top:6px;">
                <span :class="['task-item-status', proRuntimeTask.statusClass]">
                  {{ proRuntimeTask.statusText }}
                </span>
              </div>
              <div style="margin-top:10px; color:#6b7280; font-size:13px;">
                {{ proRuntimeTask.description }}
              </div>
            </div>
          </template>
          <template v-else-if="!currentTask && !taskList.length && latestAssistantPush">
            <div class="task-card">
              <div class="task-header">助手推送</div>
              <div style="display:flex;align-items:center;gap:8px;margin-top:8px;">
                <span style="font-size:18px;">🤖</span>
                <span style="font-size:13px;color:#374151;">{{ latestAssistantPush.title || '新消息' }}</span>
              </div>
              <div style="margin-top:8px;color:#6b7280;font-size:13px;">
                {{ latestAssistantPush.description || '可在顶部副窗继续处理并保持聊天' }}
              </div>
              <div class="task-actions">
                <button class="btn btn-primary btn-sm" @click="copyAssistantPushContent">
                  {{ pushCopied ? '已复制推送' : '复制推送' }}
                </button>
                <button class="btn btn-secondary btn-sm" @click="openAssistantFloatFromTaskPanel">打开副窗</button>
              </div>
            </div>
          </template>
          <div v-else-if="!currentTask && !taskList.length" class="empty-state">暂无进行中任务（可先触发分析、打印或工作流）</div>
          </div>
        </div>
      </div>
    </div>
    <div class="input-area">
      <div class="input-toolbar">
        <button class="toolbar-btn" id="newConversationBtn" title="新建对话" @click="newConversation">
          <i class="fa fa-plus" aria-hidden="true"></i> 新对话
        </button>
        <button class="toolbar-btn" id="historyPanelBtn" title="历史记录" @click="showHistoryPanel">
          <i class="fa fa-history" aria-hidden="true"></i> 历史
        </button>
        <button
          class="toolbar-btn"
          type="button"
          data-tutorial-id="toolbar-excel-analyze"
          title="上传 Excel 分析词条和数据"
          @click="triggerExcelAnalyzeUpload"
          :disabled="excelAnalyzeUploading"
        >
          <i class="fa fa-file-excel-o" aria-hidden="true"></i>
          {{ excelAnalyzeUploading ? '分析中...' : '分析Excel' }}
        </button>
        <input
          ref="excelAnalyzeInputRef"
          type="file"
          accept=".xlsx,.xls"
          style="display:none"
          @change="onExcelAnalyzeFileChange"
        >
        <label
          class="intent-pro-toggle"
          data-tutorial-id="intent-pro-experience-toggle"
          title="仅在当前未处于专业版界面时切换对话意图链路；若已打开专业版（红色主题等），对话会始终走专业接口，与本勾选无关。"
        >
          <input
            type="checkbox"
            v-model="proIntentExperienceEnabled"
            @change="persistProIntentExperienceSetting"
          >
          <span class="intent-pro-toggle-text">专业模式AI意图体验</span>
        </label>
        <label
          data-tutorial-id="star-auto-refresh-toggle"
          style="margin-left:auto;display:flex;align-items:center;gap:6px;font-size:12px;color:#6b7280;cursor:pointer;user-select:none;"
        >
          <input
            type="checkbox"
            v-model="autoRefreshStarredWechat"
            @change="persistAutoRefreshWechatSetting"
          >
          星标聊天自动刷新（1分钟）
        </label>
      </div>
      <div v-if="excelSheetOptions.length" class="sheet-link-bar">
        <span class="sheet-link-label">关联工作表：</span>
        <button
          v-for="sheet in excelSheetOptions"
          :key="`${sheet.sheet_index}-${sheet.sheet_name}`"
          class="sheet-link-btn"
          :class="{ active: linkedExcelSheet && linkedExcelSheet.sheet_name === sheet.sheet_name && linkedExcelSheet.sheet_index === sheet.sheet_index }"
          @click="bindExcelSheetToChat(sheet)"
        >
          Sheet {{ sheet.sheet_index }}（{{ sheet.sheet_name }}）
        </button>
      </div>
      <div class="input-wrapper">
        <textarea
          id="messageInput"
          rows="2"
          :placeholder="inputPlaceholder"
          v-model="messageInput"
          @keydown="handleKeyDown"
        ></textarea>
        <button class="btn btn-primary" id="sendMessageBtn" @click="sendMessage">发送</button>
      </div>
    </div>

    <div v-if="showHistory" class="modal active">
      <div class="modal-content">
        <div class="modal-header">
          历史对话
          <span class="close" @click="showHistory = false">×</span>
        </div>
        <div class="modal-body">
          <div v-if="historySessions.length === 0" class="empty-state">暂无历史</div>
          <div
            v-for="session in historySessions"
            :key="session.session_id"
            class="task-card"
            style="margin-bottom:8px; cursor:pointer;"
            @click="loadSession(session.session_id)"
          >
            <div class="task-header">{{ session.title || '新会话' }}</div>
            <div>{{ session.message_count || 0 }} 条消息</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useModsStore } from '@/stores/mods'
import { useChatView } from '../composables/useChatView'

const router = useRouter()
const modsStore = useModsStore()
const { mods: modsFromStore } = storeToRefs(modsStore)

const loadedModChips = computed(() =>
  (modsFromStore.value || []).map((m) => ({
    id: m.id,
    name: (m.name && String(m.name).trim()) || m.id,
    description: (m.description && String(m.description).trim()) || '',
  }))
)

const AUTO_REFRESH_STARRED_WECHAT_KEY = 'xcagi_auto_refresh_starred_wechat'
const PRO_INTENT_EXPERIENCE_KEY = 'xcagi_pro_intent_experience'
const autoRefreshStarredWechat = ref(localStorage.getItem(AUTO_REFRESH_STARRED_WECHAT_KEY) === '1')
const proIntentExperienceEnabled = ref(localStorage.getItem(PRO_INTENT_EXPERIENCE_KEY) === '1')
function generateSessionId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substr(2)
}

// 首次进入时若未写入 ai_session_id，切换路由再回来会生成新会话 ID，导致 localStorage 中的消息键对不上
const _storedSessionId = localStorage.getItem('ai_session_id')
const currentSessionId = ref(_storedSessionId || generateSessionId())
if (!_storedSessionId) {
  localStorage.setItem('ai_session_id', currentSessionId.value)
}

const {
  messages,
  currentTask,
  orderNumberFetching,
  isLoading,
  isExecuting,
  latestAssistantPush,
  proRuntimeTask,
  taskList,
  filteredTaskList,
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
  taskTableColumns,
  taskTableItems,
  taskOrderNumber,
  sendMessage: chatSendMessage,
  confirmTask,
  refetchTaskOrderNumber,
  cancelTask,
  showTaskConfirm,
  triggerExcelAnalyzeUpload,
  onExcelAnalyzeFileChange,
  bindExcelSheetToChat,
  toggleTaskExpanded,
  setTaskFilter,
  clearTaskHistory,
  retryTask,
  cancelTaskById,
  jumpToTaskMessage,
  showHistoryPanel,
  loadSession,
  newConversation,
  handleShipmentDownloadClick,
  startPrintFromTaskCard,
  copyAssistantPushContent,
  openAssistantFloatFromTaskPanel,
  syncProModeState,
  syncSessionMessages,
  handleAutoAction: chatHandleAutoAction
} = useChatView({
  sessionId: currentSessionId,
  proIntentExperienceEnabled
})

const messageInput = ref('')
const expandedMessageIndexes = ref<number[]>([])
let legacyAutoActionHandler: ((action: any, userMessage?: string) => void) | null = null
let proRuntimeClearTimer: number | null = null
let switchViewHandler: ((evt: any) => void) | null = null
let proModeObserver: MutationObserver | null = null
let onProModeChanged: ((evt: any) => void) | null = null
let onAssistantPush: ((evt: any) => void) | null = null

const quickButtons = [
  { text: '查一下A001的价格', label: '查产品' },
  { text: '有哪些客户？', label: '客户列表' },
  { text: '今天的出货单', label: '出货单' },
  { text: '库存不足的材料', label: '库存预警' },
  { text: '帮我打印A001标签', label: '打印标签' },
  { text: '测试预览', label: '测试预览' }
]

const visibleQuickButtons = computed(() => {
  if (isProMode.value) return quickButtons
  return quickButtons.filter(btn => btn.text !== '测试预览')
})

const inputPlaceholder = computed(() => {
  if (isProMode.value) {
    return '专业版：可直接下达复合任务，例如「给成都客户生成并打印今天发货单」'
  }
  return '普通版：输入查询或单步操作，例如「查产品」「看客户列表」'
})

const latestAiMessageIndex = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i -= 1) {
    if (messages.value[i]?.role === 'ai') return i
  }
  return -1
})

const isMessageCollapsed = (msg: any, idx: number) => {
  if (msg?.role !== 'ai') return false
  if (idx >= latestAiMessageIndex.value) return false
  return !expandedMessageIndexes.value.includes(idx)
}

const expandMessage = (idx: number) => {
  if (!expandedMessageIndexes.value.includes(idx)) {
    expandedMessageIndexes.value = [...expandedMessageIndexes.value, idx]
  }
}

const collapseMessage = (idx: number) => {
  if (idx >= latestAiMessageIndex.value) return
  if (expandedMessageIndexes.value.includes(idx)) {
    expandedMessageIndexes.value = expandedMessageIndexes.value.filter((x) => x !== idx)
  }
}

const getCollapsedPreview = (htmlText: string) => {
  const text = String(htmlText || '')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<[^>]*>/g, '')
    .replace(/\s+/g, ' ')
    .trim()
  if (!text) return '（无内容）'
  return text.length > 120 ? `${text.slice(0, 120)}...` : text
}

watch(
  () => messages.value.length,
  () => {
    // 保留当前消息范围内的展开状态，避免历史索引漂移
    expandedMessageIndexes.value = expandedMessageIndexes.value.filter(
      (idx) => idx >= 0 && idx < messages.value.length
    )
  }
)

const sendMessage = async () => {
  const domInput = document.getElementById('messageInput') as HTMLTextAreaElement | null
  const raw = messageInput.value || (domInput && domInput.value) || ''
  const message = raw.trim()
  if (!message || isLoading.value) return

  messageInput.value = ''
  await chatSendMessage(message)
}

const sendQuick = (text: string) => {
  messageInput.value = text
  sendMessage()
}

function openShipmentRecordsFromAuditTask() {
  window.dispatchEvent(
    new CustomEvent('xcagi:switch-view', { detail: { view: 'shipment-records' } })
  )
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

const formatTaskTime = (ts: number) => {
  if (!ts) return ''
  return new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

const formatTaskSourceLabel = (source: string) => {
  const s = String(source || '').trim()
  const map: Record<string, string> = {
    workflow: '工作流',
    excel: 'Excel',
    print: '打印',
    shipment: '发货单',
    manual: '手动',
    system: 'AI 员工',
    wechat: '微信',
    pro: '专业模式',
    normal: '对话',
  }
  return map[s] || s || '—'
}

/** 与 useChatView 工作流 payload（workflowProgressIdle / workflowProgressStarted）一致 */
function workflowProgressIsIdle(pl: Record<string, unknown> | null | undefined): boolean {
  if (!pl || typeof pl !== 'object') return true
  if (typeof pl.workflowProgressIdle === 'boolean') return pl.workflowProgressIdle
  if (typeof pl.workflowProgressStarted === 'boolean') return !pl.workflowProgressStarted
  return false
}

/** 任务列表圆点：工作流员工按监控/进度语义着色，其它任务沿用 task.status */
const workflowTaskDotStatusClass = (task: any): string => {
  if (task?.type !== 'workflow_employee') {
    return String(task?.status || 'queued')
  }
  const pl = task.payload || {}
  const empId = String(pl.employeeId || '')
  const mon = pl.monitor as { pollOk?: boolean } | undefined
  if (mon && mon.pollOk === false) return 'failed'

  if (empId === 'wechat_msg') {
    const started = pl.workflowProgressStarted === true
    if (!started) {
      try {
        const refreshOn = localStorage.getItem(AUTO_REFRESH_STARRED_WECHAT_KEY) === '1'
        return refreshOn ? 'queued' : 'workflow-warn'
      } catch {
        return 'queued'
      }
    }
    const pct = Number(pl.workflowProgressPct)
    if (pct >= 100) return 'success'
    return 'running'
  }

  if (empId === 'label_print') {
    const started = pl.workflowProgressStarted === true
    if (!started) {
      try {
        const refreshOn = localStorage.getItem(AUTO_REFRESH_STARRED_WECHAT_KEY) === '1'
        return refreshOn ? 'queued' : 'workflow-warn'
      } catch {
        return 'queued'
      }
    }
    const pctLp = Number(pl.workflowProgressPct)
    if (pctLp >= 100) return 'success'
    return 'running'
  }

  if (empId === 'shipment_mgmt') {
    const started = pl.workflowProgressStarted === true
    if (!started) return 'queued'
    const pctSm = Number(pl.workflowProgressPct)
    if (pctSm >= 100) return 'success'
    return 'running'
  }

  if (empId === 'receipt_confirm') {
    const started = pl.workflowProgressStarted === true
    if (!started) {
      try {
        const refreshOn = localStorage.getItem(AUTO_REFRESH_STARRED_WECHAT_KEY) === '1'
        return refreshOn ? 'queued' : 'workflow-warn'
      } catch {
        return 'queued'
      }
    }
    const pctRc = Number(pl.workflowProgressPct)
    if (pctRc >= 100) return 'success'
    return 'running'
  }

  const pct = Number(pl.workflowProgressPct)
  if (pct >= 100) return 'success'
  if (pct > 0) return 'running'
  return 'queued'
}

const workflowTaskDotTitle = (task: any): string => {
  if (task?.type !== 'workflow_employee') {
    const m: Record<string, string> = {
      queued: '排队中',
      running: '进行中',
      success: '已完成',
      failed: '失败',
      cancelled: '已取消',
    }
    return `状态：${m[String(task?.status)] || String(task?.status || '')}`
  }
  const pl = task.payload || {}
  const empId = String(pl.employeeId || '')
  const mon = pl.monitor as { pollOk?: boolean } | undefined
  if (mon && mon.pollOk === false) return '状态：上次星标会话拉取失败（红）'
  if (empId === 'wechat_msg') {
    if (workflowProgressIsIdle(pl)) {
      try {
        const refreshOn = localStorage.getItem(AUTO_REFRESH_STARRED_WECHAT_KEY) === '1'
        return refreshOn
          ? '状态：待命，等待新消息后再计进度（灰）'
          : '状态：未开星标自动刷新，监控未就绪（橙）'
      } catch {
        return '状态：待命（灰）'
      }
    }
    const pct = Number(pl.workflowProgressPct)
    if (pct >= 100) return '状态：本轮流程已跑通，仍持续监控（绿）'
    return '状态：已处理消息，流程推进中（蓝）'
  }
  if (empId === 'label_print') {
    if (workflowProgressIsIdle(pl)) {
      try {
        const refreshOn = localStorage.getItem(AUTO_REFRESH_STARRED_WECHAT_KEY) === '1'
        return refreshOn
          ? '状态：等待微信侧标签/打印信号，未计进度（灰）'
          : '状态：未开星标自动刷新，无法收微信信号（橙）'
      } catch {
        return '状态：待命（灰）'
      }
    }
    const pctLp = Number(pl.workflowProgressPct)
    if (pctLp >= 100) return '状态：流程已推进，可在对话中完成打印（绿）'
    return '状态：已收到标签/打印信号，待对话执行打印（蓝）'
  }
  if (empId === 'shipment_mgmt') {
    if (workflowProgressIsIdle(pl)) return '状态：等待打印完成后出货审计（灰）'
    const pctSm = Number(pl.workflowProgressPct)
    if (pctSm >= 100) return '状态：已输出审计建议，可核对出货记录（绿）'
    return '状态：审计已生成，建议核对并导出（蓝）'
  }
  if (empId === 'receipt_confirm') {
    if (workflowProgressIsIdle(pl)) {
      try {
        const refreshOn = localStorage.getItem(AUTO_REFRESH_STARRED_WECHAT_KEY) === '1'
        return refreshOn
          ? '状态：等待微信侧收货/对账类客户反馈（灰）'
          : '状态：未开星标自动刷新，无法收客户进程（橙）'
      } catch {
        return '状态：待命（灰）'
      }
    }
    const pctRc = Number(pl.workflowProgressPct)
    if (pctRc >= 100) return '状态：已捕获客户业务进程，可对话跟进（绿）'
    return '状态：已收到客户反馈摘要（蓝）'
  }
  if (empId === 'wechat_phone') {
    if (workflowProgressIsIdle(pl)) {
      const idleLabel = typeof pl.workflowProgressLabel === 'string' ? pl.workflowProgressLabel.trim() : ''
      return idleLabel ? `状态：${idleLabel}（灰）` : '状态：等待后端 phone-agent 状态同步（灰）'
    }
    const pctPh = Number(pl.workflowProgressPct)
    if (pctPh >= 100) return '状态：工作流步骤已就绪（绿）'
    return '状态：按 phone-agent 状态推进中（蓝）'
  }
  if (Number(pl.workflowProgressPct) >= 100) return '状态：步骤已完成（绿）'
  if (Number(pl.workflowProgressPct) > 0) return '状态：进行中（蓝）'
  return '状态：待命（灰）'
}

const persistAutoRefreshWechatSetting = () => {
  const enabled = !!autoRefreshStarredWechat.value
  localStorage.setItem(AUTO_REFRESH_STARRED_WECHAT_KEY, enabled ? '1' : '0')
  window.dispatchEvent(new CustomEvent('xcagi:auto-refresh-wechat-changed', {
    detail: { enabled }
  }))
}

const persistProIntentExperienceSetting = () => {
  const enabled = !!proIntentExperienceEnabled.value
  localStorage.setItem(PRO_INTENT_EXPERIENCE_KEY, enabled ? '1' : '0')
  window.dispatchEvent(new CustomEvent('xcagi:pro-intent-experience-changed', {
    detail: { enabled }
  }))
}

const syncProIntentExperienceFromStorage = () => {
  proIntentExperienceEnabled.value = localStorage.getItem(PRO_INTENT_EXPERIENCE_KEY) === '1'
}

const onStorageForProIntent = (e: StorageEvent) => {
  if (e.key != null && e.key !== PRO_INTENT_EXPERIENCE_KEY) return
  syncProIntentExperienceFromStorage()
}

function mapProRuntimeStatus(status: string) {
  const s = String(status || '').toLowerCase()
  if (s === 'running' || s === 'in-progress' || s === 'dispatch' || s === 'matched') {
    return { statusText: '进行中', statusClass: 'in-progress' }
  }
  if (s === 'done' || s === 'completed' || s === 'complete') {
    return { statusText: '已完成', statusClass: 'completed' }
  }
  if (s === 'failed' || s === 'failure') {
    return { statusText: '失败', statusClass: 'completed' }
  }
  if (s === 'error' || s === 'exception') {
    return { statusText: '异常', statusClass: 'completed' }
  }
  if (s === 'idle' || s === '') {
    return { statusText: '', statusClass: '' }
  }
  return { statusText: s || '进行中', statusClass: 'in-progress' }
}

function clearProRuntimeTimer() {
  if (proRuntimeClearTimer) {
    clearTimeout(proRuntimeClearTimer)
    proRuntimeClearTimer = null
  }
}

let lastProRuntimeUpdatedAt: string | null = null
function setProRuntimeTaskFromEvent(evt: any) {
  if (currentTask.value) return

  const payload = evt && evt.detail ? evt.detail : (evt || {})
  const statusRaw = payload.status
  const s = String(statusRaw || '').toLowerCase()
  if (s === 'idle' || s === '') {
    clearProRuntimeTimer()
    lastProRuntimeUpdatedAt = null
    proRuntimeTask.value = null
    return
  }

  clearProRuntimeTimer()

  const { statusText, statusClass } = mapProRuntimeStatus(statusRaw)
  const title = (payload.current_task || '').trim() || '工具执行'
  const toolName = (payload.current_tool || '').trim()
  const updatedAt = payload.updated_at || ''
  lastProRuntimeUpdatedAt = updatedAt || lastProRuntimeUpdatedAt

  const timeText = updatedAt
    ? new Date(updatedAt).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    : ''

  proRuntimeTask.value = {
    title,
    statusText,
    statusClass,
    description: [
      toolName ? `工具：${toolName}` : '',
      timeText ? `更新时间：${timeText}` : ''
    ].filter(Boolean).join('；')
  }

  if (['done', 'completed', 'failed', 'error', 'exception'].includes(s)) {
    proRuntimeClearTimer = window.setTimeout(() => {
      if (currentTask.value) return
      if (!lastProRuntimeUpdatedAt || lastProRuntimeUpdatedAt === updatedAt) {
        proRuntimeTask.value = null
      }
      proRuntimeClearTimer = null
    }, 4500)
  }
}

watch(
  () => currentTask.value,
  (task) => {
    if (!task || task?.type !== 'shipment_generate' || task?.completed) return
    if (String(task?.customOrderNumber || '').trim()) return
  }
)

onMounted(() => {
  void (async () => {
    await modsStore.initialize()
    if (!modsStore.isLoaded || modsFromStore.value.length === 0) {
      await modsStore.initialize()
    }
  })()
  syncSessionMessages().catch(() => {})
  legacyAutoActionHandler = typeof window.handleAutoAction === 'function' ? window.handleAutoAction : null
  ;(window as any).__VUE_CHAT_SEND__ = async (message: string) => {
    const text = String(message || '').trim()
    if (!text) return false
    messageInput.value = text
    await sendMessage()
    return true
  }
  ;(window as any).__VUE_CHAT_FILL__ = (message: string) => {
    const text = String(message || '').trim()
    if (!text) return false
    messageInput.value = text
    const domInput = document.getElementById('messageInput') as HTMLTextAreaElement | null
    if (domInput) domInput.value = text
    return true
  }
  ;(window as any).__VUE_HANDLE_AUTO_ACTION__ = true
  ;(window as any).handleAutoAction = (action: any, userMessage?: string) => {
    chatHandleAutoAction(action, userMessage)
  }
  syncProModeState()
  window.addEventListener('xcagi:pro-task-status', setProRuntimeTaskFromEvent)

  switchViewHandler = (evt: any) => {
    const targetView = evt?.detail?.view
    console.log('[xcagi:switch-view] 收到切换视图事件, targetView:', targetView)
    if (targetView && typeof targetView === 'string') {
      router.push({ name: targetView })
    }
  }
  window.addEventListener('xcagi:switch-view', switchViewHandler)
  onProModeChanged = (evt: any) => {
    isProMode.value = !!evt?.detail?.isProMode
  }
  window.addEventListener('xcagi:pro-mode-changed', onProModeChanged)
  onAssistantPush = (evt: any) => {
    if (!evt?.detail) return
    latestAssistantPush.value = evt.detail
  }
  window.addEventListener('xcagi:assistant-push', onAssistantPush)
  window.addEventListener('xcagi:pro-intent-experience-changed', syncProIntentExperienceFromStorage)
  window.addEventListener('storage', onStorageForProIntent)

  proModeObserver = new MutationObserver(() => {
    syncProModeState()
  })
  proModeObserver.observe(document.body, { attributes: true, attributeFilter: ['class'] })
  const overlay = document.getElementById('proModeOverlay')
  if (overlay) {
    proModeObserver.observe(overlay, { attributes: true, attributeFilter: ['class', 'style'] })
  }
})

onBeforeUnmount(() => {
  if ((window as any).__VUE_CHAT_SEND__) {
    delete (window as any).__VUE_CHAT_SEND__
  }
  if ((window as any).__VUE_CHAT_FILL__) {
    delete (window as any).__VUE_CHAT_FILL__
  }
  ;(window as any).__VUE_HANDLE_AUTO_ACTION__ = false
  if (legacyAutoActionHandler) {
    ;(window as any).handleAutoAction = legacyAutoActionHandler
  }
  window.removeEventListener('xcagi:pro-task-status', setProRuntimeTaskFromEvent)
  window.removeEventListener('xcagi:switch-view', switchViewHandler!)
  if (onProModeChanged) {
    window.removeEventListener('xcagi:pro-mode-changed', onProModeChanged)
    onProModeChanged = null
  }
  if (onAssistantPush) {
    window.removeEventListener('xcagi:assistant-push', onAssistantPush)
    onAssistantPush = null
  }
  window.removeEventListener('xcagi:pro-intent-experience-changed', syncProIntentExperienceFromStorage)
  window.removeEventListener('storage', onStorageForProIntent)
  if (proModeObserver) {
    proModeObserver.disconnect()
    proModeObserver = null
  }
  clearProRuntimeTimer()
})
</script>

<style scoped>
.sheet-link-bar {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.sheet-link-label {
  font-size: 12px;
  color: #6b7280;
}

.sheet-link-btn {
  border: 1px solid #d1d5db;
  background: #fff;
  color: #374151;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
}

.sheet-link-btn.active {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #1d4ed8;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  gap: 8px;
}

.task-toolbar-below-card {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #e5e7eb;
}

.task-filters {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.task-order-number-row {
  margin-top: 6px;
  color: #4b5563;
  font-size: 12px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.task-filter-btn {
  border: 1px solid #d1d5db;
  background: #fff;
  color: #374151;
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 12px;
  cursor: pointer;
}

.task-filter-btn.active {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #1d4ed8;
}

.task-list-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px;
  background: #fff;
}

.task-list-main {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  border: none;
  background: transparent;
  text-align: left;
  padding: 0;
  cursor: pointer;
}

.task-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  flex: none;
}

.status-queued { background: #9ca3af; }
.status-running { background: #3b82f6; }
.status-success { background: #10b981; }
.status-failed { background: #ef4444; }
.status-cancelled { background: #6b7280; }
/* 工作流：星标刷新未开、无法就绪监控 */
.status-workflow-warn { background: #f59e0b; }

.task-list-chevron {
  flex: none;
  width: 14px;
  text-align: center;
  font-size: 10px;
  color: #9ca3af;
  user-select: none;
}

.task-list-item-workflow-collapsed {
  padding-bottom: 6px;
}

.task-list-title {
  flex: 1;
  font-size: 13px;
  color: #111827;
}

.task-list-time {
  font-size: 12px;
  color: #6b7280;
}

.task-list-meta {
  margin-top: 4px;
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #6b7280;
  flex-wrap: wrap;
}

.task-workflow-body {
  margin-top: 10px;
  padding: 10px 10px 8px;
  border-radius: 8px;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
}

.task-wf-progress {
  margin-bottom: 10px;
}

.task-wf-progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.task-wf-progress-title {
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
}

.task-wf-progress-meta {
  font-size: 11px;
  color: #475569;
  font-variant-numeric: tabular-nums;
}

.task-wf-progress-track {
  height: 8px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}

.task-wf-progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #3b82f6, #6366f1);
  transition: width 0.35s ease;
}

.task-wf-progress-fill-idle {
  background: transparent;
}

.task-wf-monitor {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px 10px;
  margin-bottom: 8px;
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 8px;
}

.task-wf-monitor-pulse {
  flex: none;
  width: 10px;
  height: 10px;
  margin-top: 4px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.5);
  animation: task-wf-pulse 1.8s ease-out infinite;
}

@keyframes task-wf-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.45);
  }
  70% {
    box-shadow: 0 0 0 8px rgba(34, 197, 94, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(34, 197, 94, 0);
  }
}

.task-wf-monitor-kicker {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #94a3b8;
  margin-bottom: 4px;
}

.task-wf-monitor-text {
  font-size: 12px;
  line-height: 1.5;
  color: #f1f5f9;
  white-space: pre-line;
  word-break: break-word;
  min-width: 0;
}

.task-workflow-hint {
  font-size: 12px;
  line-height: 1.5;
  color: #0f172a;
  margin: 0 0 10px;
  padding: 8px 10px;
  background: #fff;
  border-radius: 6px;
  border-left: 3px solid #3b82f6;
}

.task-workflow-hint-secondary {
  border-left-color: #94a3b8;
  color: #334155;
  margin-bottom: 8px;
}

.task-wf-steps-details {
  font-size: 12px;
  color: #475569;
}

.task-wf-steps-details summary {
  cursor: pointer;
  font-weight: 600;
  color: #334155;
  padding: 4px 0;
  list-style: none;
}

.task-wf-steps-details summary::-webkit-details-marker {
  display: none;
}

.task-wf-steps-details[open] summary {
  margin-bottom: 6px;
}

.task-workflow-steps {
  margin: 0;
  padding-left: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.task-workflow-step {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  line-height: 1.45;
  padding: 6px 8px;
  border-radius: 6px;
  background: #fff;
  border: 1px solid #e5e7eb;
}

.task-workflow-step--done {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.task-workflow-step--active {
  border-color: #93c5fd;
  background: #eff6ff;
  box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.12);
}

.task-workflow-step--pending {
  opacity: 0.92;
}

.task-workflow-step-text {
  flex: 1;
  min-width: 0;
  color: #1e293b;
}

.task-workflow-step-state {
  flex: none;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  white-space: nowrap;
}

.task-workflow-step--done .task-workflow-step-state {
  color: #15803d;
}

.task-workflow-step--active .task-workflow-step-state {
  color: #1d4ed8;
}

.task-list-detail {
  margin-top: 8px;
  border-top: 1px dashed #e5e7eb;
  padding-top: 8px;
}

.task-summary {
  font-size: 12px;
  color: #374151;
}

.task-error {
  margin-top: 4px;
  font-size: 12px;
  color: #dc2626;
}

.collapsed-message {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
  padding: 8px;
  background: #f9fafb;
}

.collapsed-message-text {
  font-size: 13px;
  color: #4b5563;
  line-height: 1.4;
}

.collapse-toggle {
  margin-top: 8px;
}

.message-shipment-actions {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.panel-content.panel-content-task {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.task-panel-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.task-panel-mods-footer {
  flex-shrink: 0;
  padding-top: 10px;
  border-top: 1px solid #e5e7eb;
  background: linear-gradient(to top, #fff 70%, rgba(255, 255, 255, 0.96));
}

.task-panel-mods-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: #6b7280;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.task-panel-mods-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.task-panel-mod-chip {
  display: inline-block;
  max-width: 100%;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  line-height: 1.35;
  color: #1e40af;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
