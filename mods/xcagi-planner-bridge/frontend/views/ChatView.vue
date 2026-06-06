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
    <div class="chat-container" :style="chatPaneStyle">
      <div class="chat-messages-shell">
        <div class="chat-messages" id="chatMessages" ref="chatMessagesRef">
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            :class="['message', msg.role]"
            :style="{ minHeight: messageHeights.get(idx) ? messageHeights.get(idx) + 'px' : 'auto' }"
          >
          <template v-if="msg.role === 'ai' && isMessageCollapsed(msg, idx)">
            <div class="collapsed-message">
              <div class="collapsed-message-text">{{ getCollapsedPreview(msg.content) }}</div>
              <button class="btn btn-secondary btn-sm" @click="expandMessage(idx)">展开详情</button>
            </div>
          </template>
          <template v-else>
            <div
              class="message-html"
              v-html="
                msg.role === 'ai' ? sanitizeChatBubbleMarkdown(msg.content) : sanitizeChatBubbleHtml(msg.content)
              "
            ></div>
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
          <div :class="msg.role === 'ai' ? 'message-footer' : 'message-footer message-footer--user'">
            <div class="time">{{ msg.time }}</div>
            <button
              v-if="msg.role === 'ai' && canSpeakMessage(msg)"
              class="message-tts-btn"
              :class="{ 'is-playing': playingMsgIdx === idx }"
              :title="playingMsgIdx === idx ? '停止朗读' : '朗读这段回复'"
              :aria-label="playingMsgIdx === idx ? '停止朗读' : '朗读这段回复'"
              @click.stop="toggleMessageTts(idx, msg.content)"
            >
              <span aria-hidden="true">{{ playingMsgIdx === idx ? '⏹' : '🔊' }}</span>
            </button>
          </div>
        </div>
          <div v-if="isLoading && !isStreamingReply" class="message ai">
            <div><span class="status-dot online"></span> {{ loadingProgressText }}</div>
          </div>
        </div>
      </div>
      <div v-if="isTaskPaneResizable" class="chat-pane-handle-slot">
        <PaneResizeHandle
          orientation="vertical"
          label="调整任务面板宽度"
          @resize-start="onTaskPaneResizeStart"
          @reset="resetTaskPaneWidth"
        />
      </div>
      <div class="right-panel">
        <div class="panel-header">{{ currentTask ? '当前任务' : '当前任务' }}</div>
        <div class="panel-content panel-content-task" id="taskPanel">
          <div class="task-panel-body">
          <!-- 主任务卡片与任务列表可同时展示：confirmTask 会立刻 upsert 列表项，若仍用 v-else-if 会整卡消失，导致无法使用「下载 / 开始打印」 -->
          <template v-if="currentTask">
            <div class="task-card" :class="{ 'excel-import-task': currentTask?.type === 'excel_import' }">
              <div class="task-header">{{ currentTask.title }}</div>
              <div class="task-description">{{ currentTask.description }}</div>
              <!-- Excel 导入任务预览 -->
              <div v-if="currentTask?.type === 'excel_import' && !currentTask?.completed" class="excel-import-preview">
                <div class="excel-import-stats">
                  <div class="stat-item">
                    <span class="stat-label">待导入记录：</span>
                    <span class="stat-value">{{ currentTask?.payload?.params?.record_count || 0 }} 条</span>
                  </div>
                </div>
                <div class="excel-import-hint" style="margin-top:var(--app-space-sm);color:var(--app-text-caption);font-size:var(--app-font-size-caption);">
                  确认后将创建产品和购买单位（如不存在）
                </div>
              </div>
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
              <div v-else-if="taskOrderNumber" style="margin-top:6px;color:var(--app-text-secondary);font-size:var(--app-font-size-caption);">
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
                  {{ isExecuting ? '执行中...' : (currentTask?.type === 'excel_import' ? '确认导入' : '确认执行') }}
                </button>
                <button class="btn btn-secondary btn-sm" data-action="cancel-task" @click="cancelTask" :disabled="isExecuting">
                  {{ currentTask?.type === 'excel_import' ? '取消导入' : '取消' }}
                </button>
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
                <button
                  v-if="currentTask?.type === 'excel_import' && currentTask?.completed"
                  type="button"
                  class="btn btn-primary btn-sm"
                  data-action="view-products"
                  @click="$emit('switch-view', 'products')"
                >
                  查看产品
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
              <div style="margin-top:10px; color:var(--app-text-muted); font-size:13px;">
                {{ proRuntimeTask.description }}
              </div>
            </div>
          </template>
          <template v-else-if="!currentTask && !taskList.length && latestAssistantPush">
            <div class="task-card">
              <div class="task-header">助手推送</div>
              <div style="display:flex;align-items:center;gap:8px;margin-top:8px;">
                <span style="font-size:18px;">🤖</span>
                <span style="font-size:13px;color:var(--app-text-strong);">{{ latestAssistantPush.title || '新消息' }}</span>
              </div>
              <div style="margin-top:var(--app-space-sm);color:var(--app-text-muted);font-size:13px;">
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
          title="上传 Excel、图片或 PDF"
          @click="triggerUpload"
          :disabled="excelAnalyzeUploading"
        >
          <i class="fa fa-upload" aria-hidden="true"></i>
          {{ excelAnalyzeUploading ? '分析中...' : '上传' }}
          {{ multimodalPendingCount ? `(${multimodalPendingCount})` : '' }}
        </button>
        <input
          ref="excelAnalyzeInputRef"
          type="file"
          accept=".xlsx,.xlsm,image/jpeg,image/png,image/webp,image/gif,.pdf,application/pdf"
          multiple
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
          style="margin-left:auto;display:flex;align-items:center;gap:6px;font-size:var(--app-font-size-caption);color:var(--app-text-muted);cursor:pointer;user-select:none;"
        >
          <input
            type="checkbox"
            v-model="autoRefreshStarredWechat"
            @change="persistAutoRefreshWechatSetting"
          >
          星标聊天自动刷新（1分钟）
        </label>
        <label
          title="开启后 AI 回复将自动语音播报"
          style="margin-left:12px;display:flex;align-items:center;gap:6px;font-size:var(--app-font-size-caption);color:var(--app-text-muted);cursor:pointer;user-select:none;"
        >
          <input
            type="checkbox"
            :checked="ttsEnabled"
            @change="setTtsEnabled(!ttsEnabled)"
          >
          <i class="fa fa-volume-up" aria-hidden="true"></i> 语音播报
        </label>

      </div>
      <div v-if="excelSheetOptions.length" class="sheet-link-bar">
        <span class="sheet-link-label">关联工作表：</span>
        <button
          class="sheet-link-btn"
          :class="{ active: linkedExcelAllSheets }"
          @click="bindAllExcelSheetsToChat"
        >
          全部（{{ excelSheetOptions.length }}）
        </button>
        <button
          v-for="sheet in excelSheetOptions"
          :key="`${sheet.sheet_index}-${sheet.sheet_name}`"
          class="sheet-link-btn"
          :class="{ active: !linkedExcelAllSheets && linkedExcelSheet && linkedExcelSheet.sheet_name === sheet.sheet_name && linkedExcelSheet.sheet_index === sheet.sheet_index }"
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
        <button
          type="button"
          class="btn voice-input-btn"
          :class="voiceButtonClass"
          :disabled="voiceButtonDisabled"
          :title="voiceButtonTitle"
          data-tutorial-id="chat-voice-push-to-talk"
          @mousedown.prevent="startVoiceRecording"
          @mouseup.prevent="stopVoiceRecording(false)"
          @mouseleave="stopVoiceRecording(true)"
          @touchstart.prevent="startVoiceRecording"
          @touchend.prevent="stopVoiceRecording(false)"
          @touchcancel.prevent="stopVoiceRecording(true)"
        >
          <i class="fa" :class="voiceButtonIcon" aria-hidden="true"></i>
          <span class="voice-input-btn-label">{{ voiceButtonText }}</span>
        </button>
        <button class="btn btn-primary send-message-btn" id="sendMessageBtn" @click="sendMessage">
          发送
        </button>
      </div>
    </div>

    <div v-if="showHistory" class="modal active">
      <div class="modal-content history-modal-content">
        <div class="modal-header history-modal-header">
          <span>历史对话</span>
          <div class="history-modal-actions">
            <button
              type="button"
              class="btn btn-secondary btn-sm history-modal-btn"
              :disabled="historyLoading"
              @click="showHistoryPanel"
            >
              刷新
            </button>
            <button
              type="button"
              class="btn btn-secondary btn-sm history-modal-btn history-modal-btn-danger"
              :disabled="historyLoading || historySessions.length === 0"
              @click="clearHistorySessions"
            >
              清空
            </button>
            <span class="close" @click="showHistory = false">×</span>
          </div>
        </div>
        <div class="modal-body history-modal-body">
          <div v-if="historyLoading" class="empty-state">正在加载历史对话...</div>
          <div v-else-if="historyError" class="history-error-wrap">
            <div class="history-error-text">{{ historyError }}</div>
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              @click="showHistoryPanel"
            >
              重试
            </button>
          </div>
          <div v-else-if="historySessions.length === 0" class="empty-state">
            暂无历史
            <div class="history-empty-tip">发送消息后会自动记录在这里</div>
          </div>
          <template v-else>
            <button
              v-for="session in historySessions"
              :key="session.session_id"
              type="button"
              class="task-card history-session-item"
              :class="{ 'history-session-item-active': session.session_id === currentSessionId }"
              :disabled="historyLoading"
              @click="loadSession(session.session_id)"
            >
              <div class="task-header history-session-title">
                <span>{{ session.title || '新会话' }}</span>
                <span v-if="session.session_id === currentSessionId" class="history-current-badge">当前</span>
              </div>
              <div class="history-session-meta">
                <span>{{ session.message_count || 0 }} 条消息</span>
                <span v-if="session.last_message_at">
                  {{ formatTaskTime(new Date(session.last_message_at).getTime()) }}
                </span>
                <span v-if="session.is_local_only">仅本地</span>
              </div>
            </button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useIndustryStore } from '@/stores/industry'
import { getIndustryPreset, getIndustryQuickButtons } from '@/constants/industryPresets'
import { useRouter } from 'vue-router'
import PaneResizeHandle from '@/components/PaneResizeHandle.vue'
import { useResizablePane } from '@/composables/useResizablePane'
import { useModsStore } from '@/stores/mods'
import { useChatView } from '@/composables/useChatView'
import {
  coreWorkflowTaskDotStatusClass,
  coreWorkflowTaskDotTitle,
  workflowProgressIsIdle,
} from '@/workflow/coreWorkflowTaskUi'
import { sanitizeChatBubbleHtml, sanitizeChatBubbleMarkdown } from '@/utils/sanitizeHtml'
import { speakText, stopSpeaking, cleanTextForSpeech } from '@/utils/tts'
import { estimateMessageHeight, getPerformanceStats } from '@/utils/pretext'
import { resolveHostBusinessPageRedirect } from '@/utils/hostBusinessPageRedirect'

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
const CHAT_RIGHT_PANE_MQ = '(max-width: 1023px)'
// 默认开启星标轮询（首次无 localStorage 时视为 '1'）；用户可手动关闭
const autoRefreshStarredWechat = ref(localStorage.getItem(AUTO_REFRESH_STARRED_WECHAT_KEY) !== '0')
const proIntentExperienceEnabled = ref(localStorage.getItem(PRO_INTENT_EXPERIENCE_KEY) === '1')
const isTaskPaneResizable = ref(true)
let taskPaneViewportMedia: MediaQueryList | null = null
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
  isStreamingReply,
  isExecuting,
  latestAssistantPush,
  proRuntimeTask,
  taskList,
  filteredTaskList,
  expandedTaskIds,
  taskFilter,
  showHistory,
  historySessions,
  historyLoading,
  historyError,
  chatMessagesRef,
  pushCopied,
  loadingProgressText,
  excelAnalyzeUploading,
  excelAnalyzeInputRef,
  multimodalPendingCount,
  excelSheetOptions,
  linkedExcelSheet,
  linkedExcelAllSheets,
  isProMode,
  taskTableColumns,
  taskTableItems,
  taskOrderNumber,
  sendMessage: chatSendMessage,
  confirmTask,
  refetchTaskOrderNumber,
  cancelTask,
  showTaskConfirm,
  triggerUpload,
  onExcelAnalyzeFileChange,
  bindExcelSheetToChat,
  bindAllExcelSheetsToChat,
  toggleTaskExpanded,
  setTaskFilter,
  clearTaskHistory,
  retryTask,
  cancelTaskById,
  jumpToTaskMessage,
  showHistoryPanel,
  loadSession,
  clearHistorySessions,
  newConversation,
  handleShipmentDownloadClick,
  startPrintFromTaskCard,
  copyAssistantPushContent,
  openAssistantFloatFromTaskPanel,
  syncProModeState,
  syncSessionMessages,
  handleAutoAction: chatHandleAutoAction,
  ttsEnabled,
  setTtsEnabled
} = useChatView({
  sessionId: currentSessionId,
  proIntentExperienceEnabled
})

const messageInput = ref('')
const expandedMessageIndexes = ref<number[]>([])

// —— Pretext.js 消息高度预计算 ——
const messageHeights = ref<Map<number, number>>(new Map())
const chatContainerWidth = ref(600)

// 使用 Pretext.js 预计算消息高度
function calculateMessageHeight(content: string, index: number): number {
  const cached = messageHeights.value.get(index)
  if (cached) return cached

  const role = messages.value[index]?.role
  const plainSource =
    role === 'ai'
      ? sanitizeChatBubbleMarkdown(content).replace(/<[^>]*>/g, '')
      : String(content || '').replace(/<[^>]*>/g, '')
  const height = estimateMessageHeight(plainSource, chatContainerWidth.value - 32, 14)
  messageHeights.value.set(index, height)
  return height
}

// 批量计算消息高度（用于虚拟列表）
function batchCalculateHeights() {
  if (!chatMessagesRef.value) return
  
  // 更新容器宽度
  chatContainerWidth.value = chatMessagesRef.value.clientWidth
  
  // 清除旧缓存
  messageHeights.value.clear()
  
  // 预计算所有消息高度
  messages.value.forEach((msg, idx) => {
    calculateMessageHeight(msg.content, idx)
  })
  
  // 输出性能统计
  const stats = getPerformanceStats()
  console.log('📊 Pretext.js 性能统计:', stats)
}

// —— AI 回复逐条朗读 ——
// 单一正在播放索引即可：同一时刻只有一条在读。切到别条或再次点击自己都会先 stop。
const playingMsgIdx = ref<number>(-1)

function extractSpeakableText(raw: string | undefined | null): string {
  const s = String(raw || '')
  if (!s) return ''
  try {
    const el = document.createElement('div')
    el.innerHTML = sanitizeChatBubbleMarkdown(s)
    return (el.textContent || el.innerText || '').replace(/\s+/g, ' ').trim()
  } catch {
    return s.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  }
}

function canSpeakMessage(msg: any): boolean {
  return !!extractSpeakableText(msg?.content)
}

async function toggleMessageTts(idx: number, rawContent: string | undefined | null) {
  // 再次点击同一条 → 停
  if (playingMsgIdx.value === idx) {
    stopSpeaking()
    playingMsgIdx.value = -1
    return
  }
  // 切换到另一条：先停旧的
  if (playingMsgIdx.value !== -1) {
    stopSpeaking()
  }
  const text = cleanTextForSpeech(extractSpeakableText(rawContent))
  if (!text) return
  const myIdx = idx
  playingMsgIdx.value = myIdx
  try {
    await speakText(text, {
      onEnd: () => {
        if (playingMsgIdx.value === myIdx) playingMsgIdx.value = -1
      },
      onError: () => {
        if (playingMsgIdx.value === myIdx) playingMsgIdx.value = -1
      },
    })
  } finally {
    if (playingMsgIdx.value === myIdx) playingMsgIdx.value = -1
  }
}

let legacyAutoActionHandler: ((action: any, userMessage?: string) => void) | null = null
let proRuntimeClearTimer: number | null = null
let switchViewHandler: ((evt: any) => void) | null = null
let proModeObserver: MutationObserver | null = null
let onProModeChanged: ((evt: any) => void) | null = null
let onAssistantPush: ((evt: any) => void) | null = null

const industryStore = useIndustryStore()
const { currentIndustryId } = storeToRefs(industryStore)

const quickButtons = computed(() => getIndustryQuickButtons(currentIndustryId.value))

const visibleQuickButtons = computed(() => {
  const list = quickButtons.value || []
  if (isProMode.value) return list
  return list.filter((btn) => btn.text !== '测试预览')
})

const inputPlaceholder = computed(() => {
  const preset = getIndustryPreset(currentIndustryId.value)
  if (isProMode.value) return preset.placeholderPro
  return preset.placeholderNormal
})

const {
  paneStyle: chatPaneStyle,
  startResize: onTaskPaneResizeStart,
  resetSize: resetTaskPaneWidth,
  stopResize: stopTaskPaneResize,
} = useResizablePane({
  paneKey: 'chat.task-panel',
  cssVarName: '--chat-right-pane-width',
  orientation: 'vertical',
  invertDelta: true,
  defaultSize: 300,
  minSize: 240,
  maxSize: 420,
  enabled: () => isTaskPaneResizable.value,
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

// =========================================================================
// 按住说话（Push-to-Talk） → 后端 /api/voice/transcribe (faster-whisper)
// - 仅在鼠标/触摸按下时录音，松开立即提交；leave/cancel 视为「取消本次录音」。
// - MediaRecorder 选用 webm;codecs=opus 优先，其它浏览器自动降级为浏览器默认 mime。
// - 最短录音 300ms，过短视为误触（避免一瞬间的空音频误发后端）。
// =========================================================================
const MIN_RECORD_MS = 300
const MAX_RECORD_MS = 60_000 // 60 秒硬上限，防止用户忘了松手
const VOICE_PREFERRED_MIME_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/ogg',
  'audio/mp4',
  'audio/wav',
]

type VoiceState = 'idle' | 'recording' | 'transcribing' | 'error'

const voiceState = ref<VoiceState>('idle')
const voiceErrorText = ref('')
const voiceElapsedSecs = ref(0)

let voiceMediaRecorder: MediaRecorder | null = null
let voiceMediaStream: MediaStream | null = null
let voiceChunks: Blob[] = []
let voiceStartedAt = 0
let voiceMimeType = ''
let voiceCancelRequested = false
let voiceMaxTimer: number | null = null
let voiceTickTimer: number | null = null
let voiceErrorClearTimer: number | null = null

const voiceButtonDisabled = computed(() => {
  if (voiceState.value === 'transcribing') return true
  if (isLoading.value) return true
  return false
})

const voiceButtonClass = computed(() => ({
  'voice-input-btn-idle': voiceState.value === 'idle',
  'voice-input-btn-recording': voiceState.value === 'recording',
  'voice-input-btn-transcribing': voiceState.value === 'transcribing',
  'voice-input-btn-error': voiceState.value === 'error',
}))

const voiceButtonIcon = computed(() => {
  if (voiceState.value === 'recording') return 'fa-stop-circle'
  if (voiceState.value === 'transcribing') return 'fa-spinner fa-pulse'
  if (voiceState.value === 'error') return 'fa-exclamation-circle'
  return 'fa-microphone'
})

const voiceButtonText = computed(() => {
  if (voiceState.value === 'recording') {
    return `松开发送 ${voiceElapsedSecs.value.toFixed(1)}s`
  }
  if (voiceState.value === 'transcribing') return '识别中...'
  if (voiceState.value === 'error') return voiceErrorText.value || '语音失败'
  return '按住说话'
})

const voiceButtonTitle = computed(() => {
  if (voiceState.value === 'recording') return '松开立即识别并填入输入框；移出按钮可取消本次录音'
  if (voiceState.value === 'transcribing') return '正在把语音转成文字...'
  if (voiceState.value === 'error') return voiceErrorText.value || '语音识别失败'
  return '按住这里说话，松开后会自动转写成文字填入输入框'
})

const pickSupportedMimeType = (): string => {
  const MR: any = (window as any).MediaRecorder
  if (!MR || typeof MR.isTypeSupported !== 'function') return ''
  for (const mt of VOICE_PREFERRED_MIME_TYPES) {
    try {
      if (MR.isTypeSupported(mt)) return mt
    } catch {
      // 某些老浏览器 isTypeSupported 会抛异常，直接跳过
    }
  }
  return ''
}

const setVoiceError = (msg: string) => {
  voiceErrorText.value = msg
  voiceState.value = 'error'
  if (voiceErrorClearTimer) {
    window.clearTimeout(voiceErrorClearTimer)
  }
  // 错误态停留 4 秒便于用户看到具体原因，然后回到 idle
  voiceErrorClearTimer = window.setTimeout(() => {
    if (voiceState.value === 'error') {
      voiceState.value = 'idle'
      voiceErrorText.value = ''
    }
    voiceErrorClearTimer = null
  }, 4000)
}

const resetVoiceTimers = () => {
  if (voiceMaxTimer) {
    window.clearTimeout(voiceMaxTimer)
    voiceMaxTimer = null
  }
  if (voiceTickTimer) {
    window.clearInterval(voiceTickTimer)
    voiceTickTimer = null
  }
}

const releaseVoiceStream = () => {
  if (voiceMediaStream) {
    try {
      voiceMediaStream.getTracks().forEach((t) => t.stop())
    } catch {
      // 忽略重复 stop
    }
    voiceMediaStream = null
  }
  voiceMediaRecorder = null
}

const extractMimeExtension = (mime: string): string => {
  const m = String(mime || '').toLowerCase()
  if (m.includes('webm')) return 'webm'
  if (m.includes('ogg')) return 'ogg'
  if (m.includes('mp4') || m.includes('m4a')) return 'm4a'
  if (m.includes('wav') || m.includes('wave')) return 'wav'
  return 'bin'
}

const submitVoiceBlob = async (blob: Blob) => {
  voiceState.value = 'transcribing'
  try {
    const ext = extractMimeExtension(blob.type || voiceMimeType)
    const form = new FormData()
    form.append('file', blob, `chat-voice.${ext}`)
    const resp = await fetch('/api/voice/transcribe', { method: 'POST', body: form })
    const raw = await resp.text()
    let data: any = null
    try {
      data = raw ? JSON.parse(raw) : null
    } catch {
      data = null
    }
    if (!resp.ok || !data || data.success === false) {
      const detail =
        (data && (data.detail || data.message || data.error)) || raw || `HTTP ${resp.status}`
      throw new Error(String(detail))
    }
    const text = String(data?.data?.text || '').trim()
    if (!text) {
      setVoiceError('未识别到内容，请靠近麦克风再试')
      return
    }
    // 追加到已有文字后（保留用户之前手敲的半句话）；之间用空格分隔
    const existing = (messageInput.value || '').trimEnd()
    messageInput.value = existing ? `${existing} ${text}` : text
    voiceState.value = 'idle'
    voiceErrorText.value = ''
    // 回显后聚焦输入框，方便用户继续修改或直接回车发送
    const domInput = document.getElementById('messageInput') as HTMLTextAreaElement | null
    if (domInput) {
      domInput.focus()
      try {
        const pos = domInput.value.length
        domInput.setSelectionRange(pos, pos)
      } catch {
        // 某些浏览器禁止调整 selection 位置，忽略
      }
    }
  } catch (err: any) {
    const msg = err && err.message ? String(err.message) : '语音识别失败'
    setVoiceError(msg.length > 48 ? `${msg.slice(0, 48)}...` : msg)
  }
}

const startVoiceRecording = async () => {
  if (voiceButtonDisabled.value) return
  if (voiceState.value === 'recording' || voiceState.value === 'transcribing') return

  if (!navigator.mediaDevices || typeof navigator.mediaDevices.getUserMedia !== 'function') {
    setVoiceError('当前浏览器不支持麦克风采集')
    return
  }
  if (typeof (window as any).MediaRecorder === 'undefined') {
    setVoiceError('当前浏览器不支持 MediaRecorder')
    return
  }

  voiceCancelRequested = false
  voiceChunks = []
  voiceElapsedSecs.value = 0

  try {
    voiceMediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
  } catch (err: any) {
    const name = err && err.name ? String(err.name) : ''
    if (name === 'NotAllowedError' || name === 'SecurityError') {
      setVoiceError('麦克风权限被拒绝，请在浏览器地址栏授权后重试')
    } else if (name === 'NotFoundError' || name === 'OverconstrainedError') {
      setVoiceError('未检测到可用麦克风设备')
    } else {
      setVoiceError(`获取麦克风失败：${err?.message || name || '未知错误'}`)
    }
    return
  }

  const mime = pickSupportedMimeType()
  voiceMimeType = mime
  try {
    voiceMediaRecorder = mime
      ? new MediaRecorder(voiceMediaStream, { mimeType: mime })
      : new MediaRecorder(voiceMediaStream)
  } catch (err: any) {
    setVoiceError(`无法创建录音器：${err?.message || '未知错误'}`)
    releaseVoiceStream()
    return
  }

  voiceMediaRecorder.addEventListener('dataavailable', (e: BlobEvent) => {
    if (e.data && e.data.size > 0) voiceChunks.push(e.data)
  })
  voiceMediaRecorder.addEventListener('stop', () => {
    resetVoiceTimers()
    const stream = voiceMediaStream
    releaseVoiceStream()
    void stream // already released

    const duration = Date.now() - voiceStartedAt
    if (voiceCancelRequested) {
      if (voiceState.value === 'recording') voiceState.value = 'idle'
      voiceChunks = []
      return
    }
    if (duration < MIN_RECORD_MS) {
      setVoiceError('录音太短（<0.3s），请稍微按久一点再松开')
      voiceChunks = []
      return
    }
    const blob = new Blob(voiceChunks, { type: voiceMimeType || 'audio/webm' })
    voiceChunks = []
    if (blob.size === 0) {
      setVoiceError('未采到音频数据，请检查麦克风')
      return
    }
    void submitVoiceBlob(blob)
  })
  voiceMediaRecorder.addEventListener('error', (evt: any) => {
    const msg = (evt && evt.error && evt.error.message) || '录音失败'
    setVoiceError(String(msg))
    resetVoiceTimers()
    releaseVoiceStream()
  })

  try {
    voiceMediaRecorder.start()
  } catch (err: any) {
    setVoiceError(`启动录音失败：${err?.message || '未知错误'}`)
    releaseVoiceStream()
    return
  }

  voiceStartedAt = Date.now()
  voiceState.value = 'recording'
  voiceErrorText.value = ''

  voiceMaxTimer = window.setTimeout(() => {
    // 硬上限：超过 60s 自动松手，按提交处理
    stopVoiceRecording(false)
  }, MAX_RECORD_MS)

  voiceTickTimer = window.setInterval(() => {
    voiceElapsedSecs.value = (Date.now() - voiceStartedAt) / 1000
  }, 100)
}

const stopVoiceRecording = (cancel: boolean) => {
  if (voiceState.value !== 'recording') return
  // 鼠标从按钮上离开但还没按下时也会触发 mouseleave，这里用 voiceMediaRecorder 做双重保险
  if (!voiceMediaRecorder) return

  voiceCancelRequested = cancel
  try {
    if (voiceMediaRecorder.state !== 'inactive') {
      voiceMediaRecorder.stop()
    }
  } catch {
    // 某些浏览器在已 stop 的 recorder 上再 stop 会抛异常，忽略即可
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

/** 任务列表圆点：工作流员工按监控/进度语义着色，其它任务沿用 task.status */
const workflowTaskDotStatusClass = (task: any): string => {
  if (task?.type !== 'workflow_employee') {
    return String(task?.status || 'queued')
  }
  const pl = (task.payload || {}) as Record<string, unknown>
  const empId = String(pl.employeeId || '')
  const core = coreWorkflowTaskDotStatusClass(empId, pl)
  if (core) return core
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
  const pl = (task.payload || {}) as Record<string, unknown>
  const empId = String(pl.employeeId || '')
  const coreTitle = coreWorkflowTaskDotTitle(empId, pl)
  if (coreTitle) return coreTitle
  if (pl.phoneStatus != null || String(pl.phoneChannel || '').trim()) {
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

const onTaskPaneViewportChange = (event: MediaQueryList | MediaQueryListEvent) => {
  isTaskPaneResizable.value = !event.matches
  if (!isTaskPaneResizable.value) {
    stopTaskPaneResize()
  }
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

// 监听消息变化，重新计算高度
watch(
  () => messages.value.length,
  () => {
    // 使用 nextTick 确保 DOM 更新后再计算
    setTimeout(() => {
      batchCalculateHeights()
    }, 50)
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
  
  // 初始化 Pretext.js 高度计算
  setTimeout(() => {
    batchCalculateHeights()
  }, 100)
  
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
      const modPath = resolveHostBusinessPageRedirect(targetView)
      if (modPath) {
        router.push(modPath)
      } else {
        router.push({ name: targetView })
      }
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
  taskPaneViewportMedia = window.matchMedia(CHAT_RIGHT_PANE_MQ)
  onTaskPaneViewportChange(taskPaneViewportMedia)
  if (typeof taskPaneViewportMedia.addEventListener === 'function') {
    taskPaneViewportMedia.addEventListener('change', onTaskPaneViewportChange)
  } else if (typeof taskPaneViewportMedia.addListener === 'function') {
    taskPaneViewportMedia.addListener(onTaskPaneViewportChange)
  }

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
  stopTaskPaneResize()
  if (taskPaneViewportMedia) {
    if (typeof taskPaneViewportMedia.removeEventListener === 'function') {
      taskPaneViewportMedia.removeEventListener('change', onTaskPaneViewportChange)
    } else if (typeof taskPaneViewportMedia.removeListener === 'function') {
      taskPaneViewportMedia.removeListener(onTaskPaneViewportChange)
    }
  }
  clearProRuntimeTimer()

  // 切走页面时停掉仍在朗读的 TTS，避免离开后还能听到声音
  try { stopSpeaking() } catch { /* ignore */ }
  playingMsgIdx.value = -1

  // 切走页面时主动释放麦克风资源，避免浏览器继续占用
  resetVoiceTimers()
  if (voiceMediaRecorder && voiceMediaRecorder.state !== 'inactive') {
    try {
      voiceCancelRequested = true
      voiceMediaRecorder.stop()
    } catch {
      // 忽略已 stop 的情况
    }
  }
  releaseVoiceStream()
  if (voiceErrorClearTimer) {
    window.clearTimeout(voiceErrorClearTimer)
    voiceErrorClearTimer = null
  }
})
</script>

<style scoped>
.input-area {
  flex-shrink: 0;
}

.input-toolbar {
  align-items: center;
  flex-wrap: wrap;
}

#messageInput {
  min-height: 54px;
  max-height: 150px;
}

.voice-input-btn,
.send-message-btn {
  min-height: 48px;
  border-radius: 16px;
}

.send-message-btn {
  min-width: 84px;
}

.sheet-link-bar {
  margin-top: var(--app-space-sm);
  display: flex;
  align-items: center;
  gap: var(--app-space-sm);
  flex-wrap: wrap;
}

.sheet-link-label {
  font-size: var(--app-font-size-caption);
  color: var(--app-text-muted);
}

.sheet-link-btn {
  border: 1px solid var(--app-border-strong);
  background: var(--card-bg);
  color: var(--app-text-strong);
  border-radius: 6px;
  padding: var(--app-space-xs) 10px;
  font-size: var(--app-font-size-caption);
  cursor: pointer;
}

.sheet-link-btn.active {
  border-color: var(--app-interactive);
  background: var(--app-interactive-bg);
  color: var(--app-interactive-text);
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: var(--app-space-sm);
}

.task-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--app-space-sm);
  gap: var(--app-space-sm);
}

.task-toolbar-below-card {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--app-border-subtle);
}

.task-filters {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.task-order-number-row {
  margin-top: 6px;
  color: var(--app-text-secondary);
  font-size: var(--app-font-size-caption);
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.task-filter-btn {
  border: 1px solid var(--app-border-strong);
  background: var(--card-bg);
  color: var(--app-text-strong);
  border-radius: 6px;
  padding: 2px var(--app-space-sm);
  font-size: var(--app-font-size-caption);
  cursor: pointer;
}

.task-filter-btn.active {
  border-color: var(--app-interactive);
  background: var(--app-interactive-bg);
  color: var(--app-interactive-text);
}

.task-list-item {
  border: 1px solid var(--app-border-subtle);
  border-radius: 8px;
  padding: var(--app-space-sm);
  background: var(--card-bg);
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

.history-modal-content {
  max-width: 560px;
}

.history-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.history-modal-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.history-modal-btn {
  min-width: 54px;
}

.history-modal-btn-danger {
  border-color: #fecaca;
  color: #b91c1c;
  background: #fff5f5;
}

.history-modal-body {
  max-height: 420px;
  overflow-y: auto;
}

.history-error-wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px;
  border-radius: 8px;
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.history-error-text {
  color: #b91c1c;
  font-size: 13px;
}

.history-empty-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}

.history-session-item {
  width: 100%;
  border: 1px solid #e5e7eb;
  background: #fff;
  text-align: left;
  cursor: pointer;
  margin-bottom: 8px;
}

.history-session-item:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.history-session-item-active {
  border-color: #93c5fd;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.12);
}

.history-session-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.history-current-badge {
  font-size: 11px;
  color: #1d4ed8;
  background: #dbeafe;
  border-radius: 999px;
  padding: 2px 8px;
}

.history-session-meta {
  margin-top: 4px;
  color: #6b7280;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 按住说话按钮：沿用 .btn 的圆角/内边距，通过状态色替换 background 即可 */
.voice-input-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 108px;
  justify-content: center;
  user-select: none;
  touch-action: none;
  transition: background-color 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}

.voice-input-btn .voice-input-btn-label {
  font-variant-numeric: tabular-nums;
}

.voice-input-btn-idle {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.voice-input-btn-idle:hover:not(:disabled) {
  background: #e5e7eb;
}

.voice-input-btn-recording {
  background: #dc2626;
  color: #fff;
  border: 1px solid #b91c1c;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.2);
  animation: voice-input-pulse 1s ease-in-out infinite;
}

.voice-input-btn-transcribing {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
  cursor: wait;
}

.voice-input-btn-error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.voice-input-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

@keyframes voice-input-pulse {
  0%, 100% {
    box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.2);
  }
  50% {
    box-shadow: 0 0 0 6px rgba(220, 38, 38, 0.05);
  }
}
</style>

