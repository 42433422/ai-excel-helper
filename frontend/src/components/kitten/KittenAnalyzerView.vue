<template>
  <div class="kitten-shell">
    <header class="kitten-header">
      <button class="kitten-back" type="button" @click="emit('back')">返回</button>
      <div class="kitten-brand">
        <span class="kitten-brand-icon" aria-hidden="true">🐱</span>
        <div class="kitten-brand-text">
          <div class="kitten-title">小猫分析</div>
          <div class="kitten-subtitle">智能对话</div>
        </div>
      </div>
      <button class="kitten-header-action" type="button" @click="resetSession">清空</button>
    </header>

    <div v-if="datasetSummary" class="kitten-dataset-bar">
      <span class="kitten-dataset-name">{{ datasetSummary.name }}</span>
      <span class="kitten-dataset-meta">{{ datasetSummary.rows }} 行 · {{ datasetSummary.columns }} 列</span>
    </div>

    <div class="chat-container">
      <div ref="chatMessagesRef" class="chat-messages">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          :class="['message', msg.role]"
        >
          <div v-html="sanitizeChatBubbleHtml(msg.content)"></div>
          <button
            v-if="extractKittenDocumentPickupUrl(msg.content)"
            class="download-btn"
            @click="openDownloadLink(extractKittenDocumentPickupUrl(msg.content)!)"
          >
            下载
          </button>
          <div class="time">{{ msg.time }}</div>
        </div>
        <div v-if="isDatasetParsing || (isChatLoading && !isKittenStreaming)" class="message ai">
          <div><span class="status-dot online"></span> {{ loadingStatusText }}</div>
        </div>
      </div>

      <KittenChartPanel
        v-if="datasetSummary && datasetRows.length"
        :rows="datasetRows"
        :field-profiles="fieldProfiles"
        :config="chartConfig"
        :recommendations="recommendedCharts"
        @update-config="setChartConfig"
        @apply-recommendation="applyChartRecommendation"
      />

      <aside class="side-panel" :class="{ 'is-collapsed': panelCollapsed }">
        <button class="panel-collapse-toggle" type="button" @click="panelCollapsed = !panelCollapsed">
          {{ panelCollapsed ? '设置' : '收起' }}
        </button>
        <div v-show="!panelCollapsed" class="panel-inner">
          <div class="panel-block">
            <div class="panel-label">数据</div>
            <template v-if="datasetSummary">
              <p class="panel-meta">{{ datasetSummary.rows }} 行 / {{ datasetSummary.columns }} 列</p>
              <div v-if="datasetFieldPreview.length" class="asset-chips">
                <span v-for="f in datasetFieldPreview" :key="f" class="asset-chip">{{ f }}</span>
                <span v-if="datasetSummary.fieldNames.length > 8" class="asset-chip muted">…</span>
              </div>
            </template>
            <p v-else class="panel-hint">上传表格后可预览字段</p>
            <label
              class="panel-check"
              title="可选：附带原材料 / 产品 / 出货的只读聚合摘要（非全库、非实时报表）"
            >
              <input type="checkbox" v-model="kittenIncludeBusinessDb" @change="onKittenBusinessDbToggle" />
              <span>业务库摘要</span>
            </label>
            <p v-if="kittenDbStatsHint" class="panel-hint small">{{ kittenDbStatsHint }}</p>
            <label class="panel-check" title="开启后由服务端检索网页摘要（需配置 WEB_SEARCH_PROVIDER）">
              <input type="checkbox" v-model="kittenIncludeWebSearch" />
              <span>联网</span>
            </label>
          </div>

          <div v-if="lastWebSearchHits.length" class="panel-block">
            <div class="panel-label">引用</div>
            <ul class="citation-list">
              <li v-for="(h, i) in lastWebSearchHits.slice(0, 5)" :key="i">
                <a :href="h.url" target="_blank" rel="noopener noreferrer">{{ h.title || h.url }}</a>
              </li>
            </ul>
          </div>

          <div class="panel-block">
            <div class="panel-label">导出</div>
            <div class="export-row">
              <button class="btn btn-sm btn-primary" type="button" :disabled="!currentResult" @click="exportResult">
                Excel
              </button>
              <button class="btn btn-sm btn-secondary" type="button" :disabled="!currentResult" @click="exportDocx">
                Word
              </button>
              <button class="btn btn-sm btn-ghost" type="button" :disabled="!currentResult" @click="clearResult">
                清除
              </button>
            </div>
            <div v-if="lastDocumentPickupUrl" class="pickup-download-row">
              <button class="btn btn-sm btn-primary" type="button" @click="openDownloadLink(lastDocumentPickupUrl)">
                下载本次生成的文档
              </button>
            </div>
            <div v-if="currentResult" class="result-preview">
              <strong>{{ currentResult.title }}</strong>
              <p>{{ currentResult.summary }}</p>
            </div>
          </div>
        </div>
      </aside>
    </div>

    <div class="kitten-input-tools">
      <select
        v-model="quickPick"
        class="quick-select"
        aria-label="快捷分析"
        :disabled="isChatLoading || isDatasetParsing"
        @change="onQuickPick"
      >
        <option value="">快捷…</option>
        <option v-for="btn in kittenQuickActions" :key="btn.text" :value="btn.text">{{ btn.label }}</option>
      </select>

      <details ref="moreMenuRef" class="more-menu">
        <summary class="more-summary">更多</summary>
        <div class="more-body">
          <button
            class="more-action"
            type="button"
            :disabled="isChatLoading || isDatasetParsing"
            @click="runFinancialBriefAndClose"
          >
            财务简报
          </button>
          <button class="more-action" type="button" @click="docGenExpanded = !docGenExpanded">
            {{ docGenExpanded ? '收起生成文档' : '生成 Word / Excel…' }}
          </button>
        </div>
      </details>
    </div>

    <div v-if="docGenExpanded" class="doc-gen-panel">
      <div class="doc-gen-title">按描述生成示范稿（正式用印前请审核）</div>
      <div class="doc-gen-row">
        <input
          v-model="docGenPrompt"
          class="doc-gen-input"
          type="text"
          placeholder="例：技术服务合同草案，Word"
          @keydown.enter.prevent="runDocGen"
        />
        <select v-model="docGenFormat" class="doc-gen-select">
          <option value="docx">Word (.docx)</option>
          <option value="xlsx">Excel (.xlsx)</option>
        </select>
        <button
          class="toolbar-chip toolbar-chip-primary"
          type="button"
          :disabled="isDocGenLoading || isChatLoading"
          @click="runDocGen"
        >
          {{ isDocGenLoading ? '生成中…' : '生成并下载' }}
        </button>
      </div>
    </div>

    <div class="input-area">
      <input
        ref="fileInput"
        type="file"
        accept=".xlsx,.xls,.csv,.txt,.json"
        class="kitten-file-input"
        @change="handleFileSelect"
      />
      <div class="input-wrapper">
        <button
          type="button"
          class="attach-btn"
          title="上传 Excel / CSV / JSON"
          :disabled="isDatasetParsing"
          @click="triggerFileUpload"
        >
          <span class="attach-icon" aria-hidden="true">&#128206;</span>
          <span class="sr-only">上传文件</span>
        </button>
        <button
          type="button"
          :class="voiceButtonClass"
          :disabled="voiceButtonDisabled"
          :title="voiceState === 'recording' ? '松开停止' : '按住说话，松开后自动识别'"
          @mousedown.prevent="startVoiceInput"
          @mouseup.prevent="stopVoiceInput"
          @mouseleave="stopVoiceInput"
          @touchstart.prevent="startVoiceInput"
          @touchend.prevent="stopVoiceInput"
          @touchcancel.prevent="stopVoiceInput"
        >
          <span class="attach-icon" aria-hidden="true">
            <i v-if="voiceState === 'recording'" class="fa fa-stop-circle" style="color:#ef4444"></i>
            <i v-else-if="voiceState === 'transcribing'" class="fa fa-spinner fa-pulse" style="color:#3b82f6"></i>
            <i v-else-if="voiceState === 'error'" class="fa fa-exclamation-circle" style="color:#ef4444"></i>
            <i v-else class="fa fa-microphone"></i>
          </span>
          <span class="sr-only">语音输入</span>
        </button>
        <textarea
          v-model="inputText"
          rows="3"
          placeholder="输入问题，Enter 发送；Shift+Enter 换行"
          @keydown="handleInputKeydown"
        />
        <button
          class="btn btn-primary send-btn"
          type="button"
          :disabled="isChatLoading || isDatasetParsing"
          @click="sendMessage"
        >
          发送
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { buildFullApiUrl } from '@/api/core'
import { sanitizeChatBubbleHtml } from '@/utils/sanitizeHtml'
import { downloadBlob, getFilenameFromDisposition } from '@/utils'
import { appAlert } from '@/utils/appDialog'
import KittenChartPanel from '@/components/kitten/KittenChartPanel.vue'
import {
  useKittenAnalyzer,
  kittenQuickActions,
  extractKittenDocumentPickupUrl,
} from '@/composables/useKittenAnalyzer'

const emit = defineEmits<{ back: [] }>()

const panelCollapsed = ref(true)
const docGenPrompt = ref('')
const docGenFormat = ref<'docx' | 'xlsx'>('docx')
const docGenExpanded = ref(false)
const quickPick = ref('')
const moreMenuRef = ref<HTMLDetailsElement | null>(null)

const {
  messages,
  inputText,
  isChatLoading,
  isKittenStreaming,
  isDatasetParsing,
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
} = useKittenAnalyzer()

const runDocGen = () => {
  void generateAiOfficeDocument(docGenPrompt.value, docGenFormat.value)
}

const onQuickPick = () => {
  const v = quickPick.value
  quickPick.value = ''
  if (!v) return
  const btn = kittenQuickActions.find((b) => b.text === v)
  if (btn) sendQuickAction(btn)
}

const runFinancialBriefAndClose = () => {
  moreMenuRef.value?.removeAttribute('open')
  void runFinancialBrief()
}

type VoiceState = 'idle' | 'recording' | 'transcribing' | 'error'
const voiceState = ref<VoiceState>('idle')
const voiceErrorText = ref('')
let voiceRecognition: any = null

const voiceButtonDisabled = computed(() => voiceState.value === 'transcribing' || isChatLoading.value)
const voiceButtonClass = computed(() => ({
  'attach-btn': true,
  'voice-recording': voiceState.value === 'recording',
  'voice-transcribing': voiceState.value === 'transcribing',
  'voice-error': voiceState.value === 'error',
}))

const startVoiceInput = () => {
  if (voiceState.value === 'recording' || voiceState.value === 'transcribing') return
  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  if (!SpeechRecognition) {
    voiceState.value = 'error'
    voiceErrorText.value = '当前浏览器不支持语音识别'
    return
  }
  if (voiceRecognition) {
    voiceRecognition.abort()
  }
  voiceRecognition = new SpeechRecognition()
  voiceRecognition.lang = 'zh-CN'
  voiceRecognition.continuous = false
  voiceRecognition.interimResults = false
  voiceRecognition.maxAlternatives = 1

  voiceRecognition.onstart = () => {
    voiceState.value = 'recording'
    voiceErrorText.value = ''
  }
  voiceRecognition.onresult = (event: any) => {
    const text = event.results[0][0].transcript
    inputText.value = (inputText.value || '') + text
  }
  voiceRecognition.onerror = (event: any) => {
    if (event.error === 'no-speech') {
      voiceState.value = 'idle'
      return
    }
    voiceState.value = 'error'
    voiceErrorText.value = event.error || '语音识别失败'
  }
  voiceRecognition.onend = () => {
    if (voiceState.value === 'recording') voiceState.value = 'idle'
  }
  voiceRecognition.start()
}

const stopVoiceInput = () => {
  if (voiceRecognition) {
    voiceRecognition.stop()
    voiceRecognition = null
  }
  if (voiceState.value === 'recording') voiceState.value = 'idle'
}

const openDownloadLink = async (link: string) => {
  const fullUrl = /^https?:\/\//i.test(link.trim()) ? link.trim() : buildFullApiUrl(link.trim())
  try {
    const resp = await fetch(fullUrl, { credentials: 'include' })
    const ct = (resp.headers.get('content-type') || '').toLowerCase()
    if (!resp.ok) {
      if (ct.includes('application/json')) {
        const j = (await resp.json().catch(() => null)) as { message?: string } | null
        throw new Error(j?.message || `下载失败（${resp.status}）`)
      }
      throw new Error(`下载失败（${resp.status}）`)
    }
    if (ct.includes('application/json')) {
      const j = (await resp.json().catch(() => null)) as { message?: string } | null
      throw new Error(j?.message || '下载失败：服务器返回了 JSON 而非文件')
    }
    const blob = await resp.blob()
    const ext = blob.type.includes('spreadsheet')
      ? 'xlsx'
      : blob.type.includes('word') || blob.type.includes('msword')
        ? 'docx'
        : 'bin'
    const filename = getFilenameFromDisposition(
      resp.headers.get('content-disposition'),
      `文档.${ext}`
    )
    downloadBlob(blob, filename)
  } catch (err) {
    console.error('Download failed:', err)
    const msg = err instanceof Error ? err.message : String(err)
    await appAlert(`无法下载：${msg}`)
    try {
      window.open(fullUrl, '_blank', 'noopener,noreferrer')
    } catch {
      /* ignore */
    }
  }
}
</script>

<style scoped>
.kitten-shell {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #f8fafc;
}
.kitten-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}
.kitten-back,
.kitten-header-action {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #334155;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
}
.kitten-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-width: 0;
}
.kitten-brand-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  background: linear-gradient(135deg, #dbeafe, #bfdbfe);
  flex-shrink: 0;
}
.kitten-brand-text {
  text-align: center;
  min-width: 0;
}
.kitten-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}
.kitten-subtitle {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}
.kitten-dataset-bar {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 14px;
  font-size: 12px;
  color: #334155;
  background: #eff6ff;
  border-bottom: 1px solid #bfdbfe;
}
.kitten-dataset-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 70%;
}
.kitten-dataset-meta {
  color: #1d4ed8;
  font-weight: 600;
  flex-shrink: 0;
}
.kitten-input-tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #fff;
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #f1f5f9;
}
.quick-select {
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #334155;
  min-width: 100px;
  max-width: 160px;
}
.more-menu {
  position: relative;
  font-size: 12px;
}
.more-summary {
  list-style: none;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #334155;
}
.more-summary::-webkit-details-marker {
  display: none;
}
.more-body {
  position: absolute;
  bottom: 100%;
  left: 0;
  margin-bottom: 6px;
  min-width: 180px;
  padding: 6px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.08);
  z-index: 6;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.more-action {
  text-align: left;
  padding: 8px 10px;
  border: none;
  border-radius: 8px;
  background: #f8fafc;
  font-size: 12px;
  color: #334155;
  cursor: pointer;
}
.more-action:hover:not(:disabled) {
  background: #e2e8f0;
}
.more-action:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.doc-gen-panel {
  padding: 10px 14px;
  background: #f0fdf4;
  border-bottom: 1px solid #bbf7d0;
}
.doc-gen-title {
  font-size: 11px;
  color: #166534;
  margin-bottom: 8px;
  line-height: 1.4;
}
.doc-gen-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.doc-gen-input {
  flex: 1;
  min-width: 200px;
  border: 1px solid #86efac;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  background: #fff;
}
.doc-gen-select {
  border: 1px solid #86efac;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  background: #fff;
  color: #14532d;
}
.toolbar-chip-primary {
  background: #22c55e;
  border-color: #16a34a;
  color: #fff;
  font-weight: 600;
}
.toolbar-chip-primary:hover {
  background: #16a34a;
}
.toolbar-chip {
  padding: 5px 12px;
  font-size: 12px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  cursor: pointer;
  color: #334155;
}
.toolbar-chip:hover {
  background: #e2e8f0;
}
.chat-container {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}
.chat-messages {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  background: #f8fafc;
}
.kitten-chart-panel {
  width: min(520px, 42vw);
  flex-shrink: 0;
  align-self: stretch;
  margin: 16px 0 16px 16px;
  overflow-y: auto;
}
.message {
  margin-bottom: 14px;
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.5;
  font-size: 14px;
  position: relative;
  padding-right: 60px;
}
.message.user {
  background: #4e8ddf;
  color: #050505;
  margin-left: auto;
  border-bottom-right-radius: 4px;
}
.message.ai {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-bottom-left-radius: 4px;
}
.message .time {
  font-size: 11px;
  color: #000000;
  margin-top: 6px;
}
.message .download-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  padding: 4px 10px;
  font-size: 12px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
}
.message .download-btn:hover {
  background: #1d4ed8;
}
.status-dot.online {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  margin-right: 6px;
}
.side-panel {
  width: 280px;
  min-width: 220px;
  background: #fff;
  border-left: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
}
.side-panel.is-collapsed {
  width: 52px;
  min-width: 52px;
}
.panel-collapse-toggle {
  align-self: stretch;
  padding: 8px;
  border: none;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
  font-size: 12px;
  cursor: pointer;
  color: #475569;
}
.panel-inner {
  flex: 1;
  overflow-y: auto;
  padding: 10px 12px;
}
.panel-block {
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}
.panel-block:last-child {
  border-bottom: none;
}
.panel-label {
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 8px;
}
.panel-meta {
  font-size: 12px;
  color: #64748b;
  margin: 0 0 8px;
}
.panel-hint {
  font-size: 12px;
  color: #64748b;
  margin: 0 0 8px;
  line-height: 1.4;
}
.panel-hint.small {
  font-size: 11px;
}
.panel-check {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: #334155;
  margin-top: 10px;
  cursor: pointer;
}
.panel-check input {
  margin-top: 2px;
}
.asset-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.asset-chip {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #e0f2fe;
  color: #0369a1;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}
.asset-chip.muted {
  background: #f1f5f9;
  color: #64748b;
}
.citation-list {
  margin: 0;
  padding-left: 18px;
  font-size: 11px;
}
.citation-list a {
  color: #2563eb;
  word-break: break-all;
}
.export-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
.pickup-download-row {
  margin-bottom: 10px;
}
.pickup-download-row .btn {
  width: 100%;
}
.btn-ghost {
  background: transparent;
  border: 1px dashed #cbd5e1;
  color: #64748b;
}
.result-preview {
  font-size: 12px;
  color: #334155;
  line-height: 1.4;
}
.result-preview p {
  margin: 6px 0 0;
}
.input-area {
  border-top: 1px solid #e2e8f0;
  background: #fff;
}
.kitten-file-input {
  display: none;
}
.input-wrapper {
  display: flex;
  padding: 10px 12px;
  gap: 8px;
  align-items: flex-end;
}
.attach-btn {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  cursor: pointer;
  color: #475569;
  margin-bottom: 2px;
}
.attach-btn:hover:not(:disabled) {
  background: #e2e8f0;
}
.attach-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.attach-btn.voice-recording {
  background: #fee2e2;
  border-color: #ef4444;
}
.attach-btn.voice-transcribing {
  background: #dbeafe;
  border-color: #3b82f6;
}
.attach-btn.voice-error {
  background: #fee2e2;
  border-color: #ef4444;
}
.attach-icon {
  font-size: 18px;
  line-height: 1;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.input-wrapper textarea {
  flex: 1;
  resize: none;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
  min-height: 72px;
}
.send-btn {
  flex-shrink: 0;
  align-self: stretch;
  min-width: 72px;
}
@media (max-width: 900px) {
  .chat-container {
    flex-direction: column;
  }
  .kitten-chart-panel {
    width: auto;
    max-height: 420px;
    margin: 12px;
    align-self: stretch;
  }
  .side-panel:not(.is-collapsed) {
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    z-index: 5;
    box-shadow: -4px 0 16px rgba(15, 23, 42, 0.08);
  }
  .chat-container {
    position: relative;
  }
}
@media (max-width: 640px) {
  .kitten-header {
    grid-template-columns: 1fr;
  }
  .kitten-brand {
    order: -1;
  }
}
</style>
