<template>
  <div class="kitten-shell">
    <header class="kitten-header">
      <button class="kitten-back" type="button" @click="emit('back')">返回应用列表</button>
      <div class="kitten-brand">
        <span class="kitten-brand-icon" aria-hidden="true">🐱</span>
        <div class="kitten-brand-text">
          <div class="kitten-title">小猫分析</div>
          <div class="kitten-subtitle">数据接入 · 结构识别 · 洞察分析 · 报告输出</div>
        </div>
      </div>
      <button class="kitten-header-action" type="button" @click="resetSession">清空会话</button>
    </header>

    <KittenWorkflowNav :steps="kittenWorkflowSteps" :active-index="activeWorkflowStepIndex" />

    <div v-if="datasetSummary" class="kitten-dataset-bar">
      <span class="kitten-dataset-name"><strong>当前数据</strong> {{ datasetSummary.name }}</span>
      <span class="kitten-dataset-meta">{{ datasetSummary.rows }} 行 · {{ datasetSummary.columns }} 列</span>
    </div>

    <KittenOrgGrid :cards="kittenOrgCards" :active-layer-key="activeOrgLayerKey" />

    <div class="quick-actions">
      <button
        v-for="btn in kittenQuickActions"
        :key="btn.text"
        class="quick-btn"
        type="button"
        @click="sendQuickAction(btn)"
      >
        {{ btn.label }}
      </button>
    </div>

    <div class="chat-container">
      <div ref="chatMessagesRef" class="chat-messages">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          :class="['message', msg.role]"
        >
          <div v-html="msg.content"></div>
          <div class="time">{{ msg.time }}</div>
        </div>
        <div v-if="isDatasetParsing || isChatLoading" class="message ai">
          <div><span class="status-dot online"></span> {{ loadingStatusText }}</div>
        </div>
      </div>

      <aside class="right-panel">
        <div class="panel-header">数据资产</div>
        <div class="panel-section panel-asset">
          <template v-if="datasetSummary">
            <div class="asset-row">
              <span class="asset-label">文件</span>
              <span class="asset-value" :title="datasetSummary.name">{{ datasetSummary.name }}</span>
            </div>
            <div class="asset-row">
              <span class="asset-label">规模</span>
              <span class="asset-value">{{ datasetSummary.rows }} 行 / {{ datasetSummary.columns }} 列</span>
            </div>
            <div v-if="datasetFieldPreview.length" class="asset-fields">
              <span class="asset-label">字段预览</span>
              <div class="asset-chips">
                <span v-for="f in datasetFieldPreview" :key="f" class="asset-chip">{{ f }}</span>
                <span v-if="datasetSummary.fieldNames.length > 8" class="asset-chip muted">…</span>
              </div>
            </div>
          </template>
          <div v-else class="empty-state compact">
            上传文件后，此处展示文件名、行列规模与字段预览
          </div>
          <label class="kitten-db-toggle">
            <input
              type="checkbox"
              v-model="kittenIncludeBusinessDb"
              @change="onKittenBusinessDbToggle"
            />
            <span>分析时参考业务库（原材料 · 产品 · 出货）</span>
          </label>
          <p v-if="kittenDbStatsHint" class="kitten-db-hint">{{ kittenDbStatsHint }}</p>
        </div>

        <div class="panel-header panel-header-sub">分析输出</div>
        <div class="panel-section panel-content">
          <div v-if="currentResult" class="result-card">
            <div class="result-title">{{ currentResult.title }}</div>
            <div class="result-summary">{{ currentResult.summary }}</div>

            <div v-if="currentResult.chart" class="chart-container">
              <canvas :id="'chart-' + currentResult.id" height="180"></canvas>
            </div>

            <div class="result-actions">
              <button class="btn btn-sm btn-primary" type="button" @click="exportResult">导出报告</button>
              <button class="btn btn-sm btn-secondary" type="button" @click="clearResult">清除</button>
            </div>
          </div>
          <div v-else class="empty-state compact">
            输入分析需求或使用快捷按钮后，此处展示结论与图表
          </div>
        </div>
      </aside>
    </div>

    <div class="input-area">
      <div class="input-toolbar">
        <button class="toolbar-btn" type="button" @click="triggerFileUpload">
          <i class="fa fa-upload"></i> 上传文件
        </button>
        <input
          ref="fileInput"
          type="file"
          accept=".xlsx,.xls,.csv,.txt,.json"
          class="kitten-file-input"
          @change="handleFileSelect"
        />
      </div>

      <div class="input-wrapper">
        <textarea
          v-model="inputText"
          rows="3"
          placeholder="描述你的分析需求，例如：分析销量趋势、计算各渠道ROI、预测下个月销量..."
          @keydown="handleInputKeydown"
        ></textarea>
        <button
          class="btn btn-primary"
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
import { defineAsyncComponent } from 'vue'
import { useKittenAnalyzer, kittenWorkflowSteps, kittenOrgCards, kittenQuickActions } from '@/composables/useKittenAnalyzer'

const emit = defineEmits<{ back: [] }>()

const KittenWorkflowNav = defineAsyncComponent(() => import('@/components/kitten/KittenWorkflowNav.vue'))
const KittenOrgGrid = defineAsyncComponent(() => import('@/components/kitten/KittenOrgGrid.vue'))

const {
  messages,
  inputText,
  isChatLoading,
  isDatasetParsing,
  currentResult,
  fileInput,
  chatMessagesRef,
  datasetSummary,
  kittenIncludeBusinessDb,
  kittenDbStatsHint,
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
} = useKittenAnalyzer()
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
  grid-template-columns: minmax(0, auto) 1fr minmax(0, auto);
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
}
.kitten-back,
.kitten-header-action {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}
.kitten-back:hover,
.kitten-header-action:hover {
  background: #f1f5f9;
}
.kitten-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-width: 0;
}
.kitten-brand-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  background: linear-gradient(135deg, #dbeafe, #bfdbfe);
  flex-shrink: 0;
}
.kitten-brand-text {
  text-align: center;
  min-width: 0;
}
.kitten-title {
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.25;
}
.kitten-subtitle {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}
.kitten-dataset-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 16px;
  font-size: 12px;
  color: #334155;
  background: #eff6ff;
  border-bottom: 1px solid #bfdbfe;
}
.kitten-dataset-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.kitten-dataset-meta {
  color: #1d4ed8;
  font-weight: 600;
  flex-shrink: 0;
}
@media (max-width: 640px) {
  .kitten-header {
    grid-template-columns: 1fr;
    justify-items: stretch;
  }
  .kitten-brand {
    order: -1;
  }
}
.quick-actions {
  padding: 12px 20px;
  background: #f1f5f9;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.quick-btn {
  padding: 6px 14px;
  font-size: 13px;
  background: white;
  border: 1px solid #cbd5e1;
  border-radius: 9999px;
  cursor: pointer;
}
.chat-container {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}
.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #f8fafc;
}
.message {
  margin-bottom: 20px;
  max-width: 75%;
  padding: 14px 18px;
  border-radius: 12px;
  line-height: 1.5;
}
.message.user {
  background: #dbeafe;
  margin-left: auto;
  border-bottom-right-radius: 4px;
}
.message.ai {
  background: white;
  border: 1px solid #e2e8f0;
  border-bottom-left-radius: 4px;
}
.right-panel {
  width: 320px;
  min-width: 260px;
  background: #fff;
  border-left: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.panel-header {
  padding: 12px 16px;
  font-weight: 600;
  font-size: 13px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}
.panel-header-sub {
  padding-top: 10px;
  border-top: 1px solid #e2e8f0;
}
.panel-section {
  flex: 1;
  min-height: 0;
  padding: 12px 16px;
  overflow-y: auto;
}
.panel-asset {
  flex: 0 1 auto;
  max-height: 42%;
}
.panel-content {
  flex: 1;
  min-height: 0;
}
.message .time {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 8px;
}
.empty-state.compact {
  padding: 16px 8px;
  font-size: 12px;
  line-height: 1.5;
}
.asset-row {
  display: flex;
  gap: 8px;
  align-items: baseline;
  margin-bottom: 8px;
  font-size: 12px;
}
.asset-label {
  color: #64748b;
  flex-shrink: 0;
  width: 52px;
}
.asset-value {
  color: #0f172a;
  word-break: break-all;
}
.asset-fields {
  margin-top: 4px;
}
.asset-fields .asset-label {
  display: block;
  margin-bottom: 6px;
}
.asset-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.asset-chip {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 9999px;
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
.kitten-db-toggle {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
  font-size: 12px;
  color: #334155;
  cursor: pointer;
  user-select: none;
}
.kitten-db-toggle input {
  margin-top: 2px;
  flex-shrink: 0;
}
.kitten-db-hint {
  margin: 8px 0 0;
  font-size: 11px;
  color: #64748b;
  line-height: 1.45;
}
.result-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
}
.result-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: #1e40af;
}
.chart-container {
  margin: 12px 0;
  background: #f8fafc;
  border-radius: 6px;
  padding: 8px;
}
.input-area {
  border-top: 1px solid #e2e8f0;
  background: white;
}
.input-toolbar {
  padding: 8px 16px;
  display: flex;
  gap: 12px;
  border-bottom: 1px solid #f1f5f9;
}
.toolbar-btn {
  padding: 6px 12px;
  background: none;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.kitten-file-input {
  display: none;
}
.input-wrapper {
  display: flex;
  padding: 12px;
  gap: 8px;
}
.input-wrapper textarea {
  flex: 1;
  resize: none;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
}
</style>
