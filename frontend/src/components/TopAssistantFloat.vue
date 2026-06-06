<template>
  <div class="assistant-float-root">
    <button
      ref="floatToggleRef"
      class="assistant-float-toggle"
      type="button"
      @click="toggleOpen"
      :title="isOpen ? '收起副窗' : '打开副窗'"
      :aria-expanded="isOpen ? 'true' : 'false'"
      aria-controls="xcagi-assistant-float-panel"
      :class="{ pulse: hasUnreadPush }"
    >
      <i class="fa fa-comments-o" aria-hidden="true"></i>
      <span>副窗</span>
    </button>

    <div v-if="popupNotice" class="assistant-popup-notice" @click="openFromNotice">
      <div class="assistant-popup-title">{{ popupNotice.title }}</div>
      <div class="assistant-popup-desc">{{ popupNotice.description }}</div>
      <div class="assistant-popup-hint">点击查看</div>
    </div>

    <Teleport to="body">
    <div
      v-if="isOpen"
      id="xcagi-assistant-float-panel"
      ref="assistantPanelRef"
      class="assistant-float-panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="xcagi-assistant-float-title"
      data-tutorial-spotlight="assistant-panel"
      tabindex="-1"
      @keydown="onAssistantPanelKeydown"
    >
      <div class="assistant-float-header">
        <div id="xcagi-assistant-float-title" class="assistant-title">助手副窗</div>
        <button type="button" class="assistant-close" aria-label="关闭副窗" @click="closeAssistantPanelUi">
          ×
        </button>
      </div>

      <div class="assistant-tabs" role="tablist" aria-label="副窗分区">
        <button
          type="button"
          class="assistant-tab"
          role="tab"
          data-tutorial-id="tab-push"
          :aria-selected="activeTab === 'push'"
          :tabindex="activeTab === 'push' ? 0 : -1"
          :class="{ active: activeTab === 'push' }"
          @click="activeTab = 'push'"
        >
          推送
        </button>
        <button
          type="button"
          class="assistant-tab"
          role="tab"
          data-tutorial-id="tab-assistant"
          :aria-selected="activeTab === 'assistant'"
          :tabindex="activeTab === 'assistant' ? 0 : -1"
          :class="{ active: activeTab === 'assistant' }"
          @click="activeTab = 'assistant'"
        >
          协助副窗
        </button>
        <button
          type="button"
          class="assistant-tab"
          role="tab"
          data-tutorial-id="tab-one-click"
          :aria-selected="activeTab === 'oneClick'"
          :tabindex="activeTab === 'oneClick' ? 0 : -1"
          :class="{ active: activeTab === 'oneClick' }"
          @click="activeTab = 'oneClick'"
        >
          一键托管
        </button>
        <button
          type="button"
          class="assistant-tab"
          role="tab"
          data-tutorial-id="tab-lobster"
          :aria-selected="activeTab === 'lobster'"
          :tabindex="activeTab === 'lobster' ? 0 : -1"
          :class="{ active: activeTab === 'lobster' }"
          @click="activeTab = 'lobster'"
        >
          龙虾托管
        </button>
        <button
          type="button"
          class="assistant-tab"
          role="tab"
          data-tutorial-id="tab-starterPack"
          :aria-selected="activeTab === 'starterPack'"
          :tabindex="activeTab === 'starterPack' ? 0 : -1"
          :class="{ active: activeTab === 'starterPack' }"
          @click="activeTab = 'starterPack'"
        >
          新手对话包
        </button>
        <button
          type="button"
          class="assistant-tab"
          role="tab"
          data-tutorial-id="tab-tutorial"
          :aria-selected="activeTab === 'tutorial'"
          :tabindex="activeTab === 'tutorial' ? 0 : -1"
          :class="{ active: activeTab === 'tutorial' }"
          @click="openTutorialTab"
        >
          新手教程
        </button>
      </div>

      <div v-if="activeTab === 'push'" class="assistant-body">
        <div v-if="pushFeed.length === 0" class="assistant-empty">暂无推送</div>
        <div v-else class="push-list">
          <div v-for="item in pushFeed" :key="item.id" class="push-item">
            <div class="push-item-title">{{ item.title }}</div>
            <div class="push-item-desc">{{ item.description }}</div>
          </div>
        </div>
      </div>

      <div v-else-if="activeTab === 'oneClick' || activeTab === 'lobster'" class="assistant-body assistant-body-recommend">
        <div class="workflow-employee-section">
          <div class="workflow-employee-section-head">
            <div class="workflow-employee-heading">工作流员工选择</div>
            <router-link
              :to="workflowVisualizationLocation"
              class="workflow-employee-visual-link"
              :title="workflowPanoramaLinkTitle"
            >流程全景</router-link>
          </div>
          <div class="workflow-employee-list" role="group" aria-label="工作流 AI 员工">
            <button
              v-for="emp in workflowEmployeeDefs"
              :key="emp.id"
              type="button"
              class="workflow-employee-row"
              :aria-pressed="workflowEmployeesEnabled[emp.id] ? 'true' : 'false'"
              @click="toggleWorkflowEmployee(emp.id)"
            >
              <span class="workflow-employee-label">{{ emp.label }}</span>
              <div
                class="toggle-switch workflow-employee-toggle"
                :class="{ active: workflowEmployeesEnabled[emp.id] }"
              >
                <div class="toggle-slider"></div>
              </div>
            </button>
          </div>
        </div>
      </div>

      <div v-else-if="activeTab === 'assistant'" class="assistant-body" data-tutorial-assistant-body>
        <div class="assistant-block">
          <div class="assistant-block-title">{{ uiText.queryTitle.value }}</div>
          <div class="assistant-block-desc">{{ uiText.queryDescription.value }}</div>
        </div>
        <div class="product-search-row">
          <input
            v-model.trim="productKeyword"
            type="text"
            :placeholder="uiText.queryPlaceholder.value"
            @keydown.enter.prevent="searchProducts"
          >
          <button type="button" class="btn btn-primary btn-sm" @click="searchProducts" :disabled="loadingProducts">
            查询
          </button>
        </div>
        <div class="product-result">
          <div v-if="loadingProducts" class="assistant-empty">查询中...</div>
          <div v-else-if="productRows.length === 0" class="assistant-empty">{{ productEmptyMessage }}</div>
          <div v-else class="product-list">
            <div v-for="row in productRows" :key="row.id" class="product-item">
              <div class="product-item-head">
                <span class="product-id-label">编号 {{ row.id }}</span>
              </div>
              <div class="product-field">
                <label class="product-field-label" :for="'pf-name-' + row.id">{{ uiText.nameLabel.value }}</label>
                <input :id="'pf-name-' + row.id" v-model.trim="row.name" type="text" class="product-input" :placeholder="uiText.nameLabel.value">
              </div>
              <div class="product-field">
                <label class="product-field-label" :for="'pf-model-' + row.id">{{ uiText.modelLabel.value }}</label>
                <input :id="'pf-model-' + row.id" v-model.trim="row.model_number" type="text" class="product-input" :placeholder="uiText.modelLabel.value">
              </div>
              <div class="product-field">
                <label class="product-field-label" :for="'pf-price-' + row.id">{{ uiText.priceLabel.value }}</label>
                <input :id="'pf-price-' + row.id" v-model.number="row.price" type="number" step="0.01" class="product-input" :placeholder="uiText.priceLabel.value">
              </div>
              <div class="product-field">
                <label class="product-field-label" :for="'pf-unit-' + row.id">{{ uiText.categoryLabel.value }}/{{ uiText.unitLabel.value }}</label>
                <input :id="'pf-unit-' + row.id" v-model.trim="row.unit" type="text" class="product-input" :placeholder="`${uiText.categoryLabel.value}、${uiText.unitLabel.value}`">
              </div>
              <div class="product-actions">
                <button
                  type="button"
                  class="btn btn-secondary btn-sm"
                  @click="saveProductRow(row)"
                  :disabled="savingProductId === row.id"
                >
                  {{ savingProductId === row.id ? '保存中...' : '保存修改' }}
                </button>
              </div>
            </div>
          </div>
        </div>
        <div class="assistant-divider"></div>
        <div class="assistant-block">
          <div class="assistant-block-title">关联表网格布局</div>
          <div class="assistant-block-desc">
            <template v-if="linkedSheetName">
              当前：Sheet {{ linkedSheetIndex }}（{{ linkedSheetName }}）
            </template>
            <template v-else>
              尚未关联 Sheet，请先在聊天页点击关联工作表按钮
            </template>
          </div>
          <div class="assistant-grid-actions">
            <button type="button" class="btn btn-secondary btn-sm" @click="triggerGridReadFromChat">
              调用上传并提取读取网格
            </button>
          </div>
          <div v-if="linkedGridData && Array.isArray(linkedGridData.rows) && linkedGridData.rows.length" class="linked-grid-preview">
            <div class="linked-grid-caption">业务对接真实网格缩略预览</div>
            <div ref="topScrollRef" class="linked-grid-top-scroll" @scroll="onTopScroll">
              <div class="linked-grid-top-scroll-inner" :style="{ width: `${topScrollInnerWidth}px` }"></div>
            </div>
            <ExcelPreview
              ref="excelPreviewRef"
              :title="`Sheet ${linkedSheetIndex || ''}（${linkedSheetName || ''}）真实网格`"
              :fields="linkedSheetFields"
              :sample-rows="linkedSheetSampleRows"
              :grid-data="linkedGridData"
              :rows="24"
              :columns="16"
            />
          </div>
          <div v-else class="assistant-empty">当前关联表暂无可展示网格（可先分析Excel或上传并提取）。</div>
        </div>
      </div>

      <div v-else-if="activeTab === 'starterPack'" class="assistant-body assistant-body-starter">
        <div class="starter-pack-list">
          <button
            v-for="(item, idx) in starterPackPresets"
            :key="idx"
            type="button"
            class="starter-pack-item"
            @click="onStarterPackItemClick(item.text)"
          >
            <div class="starter-pack-label">{{ item.label }}</div>
            <div class="starter-pack-hint">{{ item.hint }}</div>
          </button>
        </div>
      </div>

      <div v-else-if="activeTab === 'tutorial'" class="assistant-body assistant-body-tutorial">
        <div class="tutorial-track-pick">
          <div class="tutorial-track-heading">选择教程</div>
          <ul class="tutorial-track-list">
            <li
              v-for="(track, index) in tutorialTracks"
              :key="track.id"
              class="tutorial-track-card"
            >
              <div class="tutorial-track-card-main">
                <div class="tutorial-track-card-title">{{ track.title }}</div>
                <p class="tutorial-track-card-summary">{{ track.summary }}</p>
                <p v-if="track.id === 'advanced'" class="tutorial-track-card-extra muted">
                  {{ advancedTrackHint }}
                </p>
              </div>
              <button
                type="button"
                class="btn btn-sm"
                :class="index === 0 || track.recommended ? 'btn-primary' : 'btn-secondary'"
                :title="track.description"
                @click="startTutorialGuide(track.id)"
              >
                开始
              </button>
            </li>
          </ul>
          <details class="tutorial-track-details">
            <summary>路线说明</summary>
            <p
              v-for="track in tutorialTracks"
              :key="`${track.id}-desc`"
              class="tutorial-track-hint"
            >
              <strong>{{ track.title }}</strong> — {{ track.description }}
            </p>
          </details>
        </div>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useRouter } from 'vue-router';
import { ApiError } from '@/api';
import productsApi from '@/api/products';
import { useTutorialStore } from '@/stores/tutorial';
import { useTutorialCatalog } from '@/composables/useTutorialCatalog';
import { useModsStore } from '@/stores/mods';
import { useWorkflowAiEmployeesStore } from '@/stores/workflowAiEmployees';
import { WORKFLOW_EMPLOYEE_IDS } from '@/constants/workflowEmployeeMods';
import { useWorkflowModsRuntimeContext } from '@/composables/useWorkflowModsRuntimeContext';
import { resolveLabel } from '@/utils/workflowEmployeeRegistry';
import { useIndustryUiText } from '@/composables/useIndustryUiText';
import {
  inferWechatCustomerIntent,
  isLabelPrintRelatedWechatIntent,
  isReceiptConfirmRelatedWechatIntent,
} from '@/utils/wechatIntent';
import { shouldTryWechatShipmentPreview } from '@/utils/wechatShipmentDetect';
import { resolveErpApiPath } from '@/utils/erpDomainPaths';
import { resolveWorkflowVisualizationLocation } from '@/utils/workflowNav';
import ExcelPreview from '@/components/template/ExcelPreview.vue';

const router = useRouter();
const tutorialStore = useTutorialStore();
const { tutorialTracks, advancedTrackHint, buildContext: tutorialBuildContext } = useTutorialCatalog();
const modsStore = useModsStore();
const uiText = useIndustryUiText();
const { modWorkflowEmployeesActive } = useWorkflowModsRuntimeContext();
const workflowAiEmployeesStore = useWorkflowAiEmployeesStore();
const { enabled: workflowEmployeesEnabled, registryEntries: workflowRegistryEntries, registryLoaded: workflowRegistryLoaded } = storeToRefs(workflowAiEmployeesStore);

const isOpen = ref(false);
const activeTab = ref('push');
const floatToggleRef = ref(null);
const assistantPanelRef = ref(null);

const FLOAT_TAB_ORDER = ['push', 'assistant', 'oneClick', 'lobster', 'starterPack', 'tutorial'];
const FLOAT_TAB_DATA_ID = {
  push: 'tab-push',
  assistant: 'tab-assistant',
  oneClick: 'tab-one-click',
  lobster: 'tab-lobster',
  starterPack: 'tab-starterPack',
  tutorial: 'tab-tutorial',
};

function focusToggleAfterClose() {
  nextTick(() => {
    floatToggleRef.value?.focus?.();
  });
}

/** 关闭 Teleport 副窗并将焦点回到顶栏触发按钮（教程锁定副窗时不强制关） */
function closeAssistantPanelUi() {
  if (tutorialStore.isActive && tutorialStore.currentStep?.assistantTab) {
    return;
  }
  isOpen.value = false;
  focusToggleAfterClose();
}

function onDocumentKeydownCapture(e) {
  if (e.key !== 'Escape' || !isOpen.value) return;
  if (tutorialStore.isActive && tutorialStore.currentStep?.assistantTab) return;
  e.preventDefault();
  e.stopPropagation();
  isOpen.value = false;
  focusToggleAfterClose();
}
const pushFeed = ref([]);
const productKeyword = ref('');
const productRows = ref([]);
const linkedSheetName = ref('');
const linkedSheetIndex = ref(0);
const linkedGridData = ref(null);
const linkedSheetFields = ref([]);
const linkedSheetSampleRows = ref([]);
const topScrollRef = ref(null);
const excelPreviewRef = ref(null);
const topScrollInnerWidth = ref(0);
const loadingProducts = ref(false);
/** 最近一次「已完成」的检索关键词（用于区分未搜索 / 已搜无结果 / 改词未搜） */
const lastProductSearchQuery = ref('');
const productSearchFailed = ref(false);
const productSearchErrorText = ref('');
/** 最近一次成功请求时后端返回的 total（用于无结果时说明） */
const lastProductSearchTotal = ref(null);
const savingProductId = ref(null);
const popupNotice = ref(null);
const hasUnreadPush = ref(false);

const MAX_PUSH_ITEMS = 12;
const AUTO_REFRESH_STARRED_WECHAT_KEY = 'xcagi_auto_refresh_starred_wechat';
const FEED_POLL_INTERVAL_MS = 60 * 1000;
const MAX_OPERATION_LOG = 30;
const operationHistory = ref([]);

const PRO_INTENT_EXPERIENCE_KEY = 'xcagi_pro_intent_experience';

const workflowEmployeeDefs = computed(() => {
  const i18nResolver = (key) => {
    if (key === 'shipmentOrderName') return `${uiText.shipmentOrderName.value}管理 AI 员工`;
    return key;
  };
  return workflowRegistryEntries.value.map((entry) => ({
    id: entry.id,
    label: resolveLabel(entry, i18nResolver),
  }));
});

const workflowVisualizationLocation = resolveWorkflowVisualizationLocation();

const workflowPanoramaLinkTitle = computed(() =>
  modWorkflowEmployeesActive.value
    ? '查看固定六类与扩展工作流的执行逻辑与过程'
    : '查看固定六类工作流的执行逻辑与过程'
);

const coreWorkflowEnabled = (id) =>
  !!workflowEmployeesEnabled.value?.[id];

const isWechatMsgEmployeeEnabled = () => coreWorkflowEnabled('wechat_msg');
const isLabelPrintEmployeeEnabled = () => coreWorkflowEnabled('label_print');
const isReceiptConfirmEmployeeEnabled = () => coreWorkflowEnabled('receipt_confirm');

/** 星标新消息是否需要跑意图链路（微信任务 / 发货预览 / 标签与收货确认信号等） */
const shouldRunStarredWechatIntentPipeline = () =>
  WORKFLOW_EMPLOYEE_IDS.filter((id) => id !== 'shipment_mgmt').some((id) => coreWorkflowEnabled(id));

/**
 * 微信消息处理 AI 员工：星标 feed 发现新消息后，按「专业模式 AI 意图体验」走 /api/ai/intent/test，否则本地规则预处理；结果推到对话页任务列表（事件）。
 */
const runWechatMessageAiPipeline = async (item, latestMsg) => {
  const text = String(latestMsg?.text || '').trim();
  if (!text) return;

  const useProIntentApi = localStorage.getItem(PRO_INTENT_EXPERIENCE_KEY) === '1';
  let intentLabel = '';
  let intentDetail = '';
  let primaryIntent = '';
  let toolKey = '';
  let sourceApi = 'local';

  if (useProIntentApi) {
    try {
      const resp = await fetch('/api/ai/intent/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      const data = await resp.json().catch(() => ({}));
      if (data?.success && data?.data) {
        const d = data.data;
        primaryIntent = String(d.primary_intent || '').trim();
        toolKey = String(d.tool_key || '').trim();
        intentLabel = primaryIntent || '意图识别';
        const hints = Array.isArray(d.intent_hints) ? d.intent_hints.filter(Boolean).join('；') : '';
        intentDetail = hints || `confidence=${d.confidence ?? '—'}`;
        sourceApi = 'intent_test';
      } else {
        const local = inferWechatCustomerIntent(text);
        intentLabel = local.label;
        intentDetail = `${local.detail}（意图 API 未返回有效结果，已回退本地规则）`;
        sourceApi = 'local_fallback';
      }
    } catch {
      const local = inferWechatCustomerIntent(text);
      intentLabel = local.label;
      intentDetail = `${local.detail}（意图 API 请求失败，已回退本地规则）`;
      sourceApi = 'local_fallback';
    }
  } else {
    const local = inferWechatCustomerIntent(text);
    intentLabel = local.label;
    intentDetail = local.detail;
    sourceApi = 'local';
  }

  const we = workflowEmployeesEnabled.value;
  if (
    (we?.wechat_msg || we?.shipment_mgmt) &&
    shouldTryWechatShipmentPreview(text, {
      intentLabel,
      primaryIntent,
      toolKey,
    })
  ) {
    try {
      const resp = await fetch('/api/tools/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool_id: 'normal_slot_dispatch',
          action: 'shipment_preview',
          params: { order_text: text },
        }),
      });
      const data = await resp.json().catch(() => ({}));
      if (data?.success && data?.task?.type === 'shipment_generate') {
        window.dispatchEvent(
          new CustomEvent('xcagi:wechat-shipment-preview-task', {
            detail: {
              task: data.task,
              contactName: item?.contact_name || '星标联系人',
              contactId: item?.contact_id,
              messageText: text.slice(0, 800),
            },
          })
        );
      }
    } catch {
      /* 预览失败不影响意图条目写入 */
    }
  }

  if (
    we?.label_print &&
    isLabelPrintRelatedWechatIntent(text, { intentLabel, primaryIntent, toolKey })
  ) {
    window.dispatchEvent(
      new CustomEvent('xcagi:workflow-label-print-signal', {
        detail: {
          at: Date.now(),
          line: `${item?.contact_name || '星标联系人'}：${text.replace(/\s+/g, ' ').slice(0, 120)}`,
          contactName: item?.contact_name,
          contactId: item?.contact_id,
        },
      })
    );
  }

  if (
    we?.receipt_confirm &&
    isReceiptConfirmRelatedWechatIntent(text, { intentLabel, primaryIntent, toolKey })
  ) {
    window.dispatchEvent(
      new CustomEvent('xcagi:workflow-receipt-feedback-signal', {
        detail: {
          at: Date.now(),
          line: `${item?.contact_name || '星标联系人'}：${text.replace(/\s+/g, ' ').slice(0, 120)}`,
          contactName: item?.contact_name,
          contactId: item?.contact_id,
          messageText: text.slice(0, 500),
          intentLabel,
          intentDetail,
          primaryIntent,
          toolKey,
          sourceApi,
        },
      })
    );
  }

  if (isWechatMsgEmployeeEnabled()) {
    window.dispatchEvent(
      new CustomEvent('xcagi:wechat-ai-task-enqueue', {
        detail: {
          contactId: item?.contact_id,
          contactName: item?.contact_name || '星标联系人',
          messageText: text.slice(0, 500),
          intentLabel,
          intentDetail,
          primaryIntent,
          toolKey,
          sourceApi,
        },
      })
    );
  }
};
let noticeTimer = null;
let feedPollTimer = null;
let feedPolling = false;
let feedInitialized = false;
const lastFeedMessageByContact = new Map();

/** 产品副窗查询并发序号；仅最后一次请求可结束 loading */
let productSearchSeq = 0;
const PRODUCT_SEARCH_TIMEOUT_MS = 30000;

const FILL_CHAT_MAX_ATTEMPTS = 4;
const FILL_CHAT_RETRY_MS = 80;

const starterPackPresets = uiText.starterPackPresets;

const recordOperation = (type, detail = {}) => {
  operationHistory.value = [
    {
      id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      type: String(type || ''),
      detail: detail || {},
      at: Date.now(),
    },
    ...operationHistory.value
  ].slice(0, MAX_OPERATION_LOG);
};

const recommendIntroText = computed(() => {
  if (activeTab.value === 'lobster') {
    return '龙虾托管：通过下方开关选择要参与托管流程的 AI 员工，设置会保存在本机。';
  }
  return '一键托管：通过下方开关选择要启用的 AI 员工，与侧栏专业版开关为同款交互。';
});

const toggleWorkflowEmployee = (id) => {
  workflowAiEmployeesStore.toggle(id);
  const next = workflowAiEmployeesStore.enabled;
  if (id === 'wechat_msg' && next.wechat_msg && isAutoRefreshEnabled()) {
    void pollStarredFeed();
  }
};

const tryFillChatInput = (text) => {
  const t = String(text || '').trim();
  if (!t) return false;
  if (typeof window.__VUE_CHAT_FILL__ === 'function') {
    return window.__VUE_CHAT_FILL__(t);
  }
  return false;
};

const fillChatInputWithRetry = async (text) => {
  const t = String(text || '').trim();
  if (!t) return;
  for (let i = 0; i < FILL_CHAT_MAX_ATTEMPTS; i += 1) {
    if (i > 0) {
      await new Promise((r) => setTimeout(r, FILL_CHAT_RETRY_MS));
    }
    if (tryFillChatInput(t)) return;
  }
};

const onStarterPackItemClick = async (text) => {
  recordOperation('starter_pack', { text: String(text || '').slice(0, 120) });
  await router.push({ name: 'chat' });
  await nextTick();
  await fillChatInputWithRetry(text);
  // 填入后收起副窗，避免遮挡主对话与右侧「当前任务」预览（发货单等流程主要看任务面板）
  closeAssistantPanelUi();
};

const toggleOpen = async () => {
  recordOperation('toggle_float', { open: !isOpen.value });
  const next = !isOpen.value;
  isOpen.value = next;
  if (next) {
    hasUnreadPush.value = false;
    popupNotice.value = null;
    if (noticeTimer) {
      clearTimeout(noticeTimer);
      noticeTimer = null;
    }
    await nextTick();
    assistantPanelRef.value?.querySelector?.('.assistant-close')?.focus?.();
  } else {
    focusToggleAfterClose();
  }
};

watch(
  () => [isOpen.value, activeTab.value],
  ([open, tab]) => {
    if (open && tab === 'tutorial') {
      queueMicrotask(() => {
        window.dispatchEvent(new CustomEvent('xcagi:warmup-tutorial-tts'));
      });
    }
  }
);

const openTutorialTab = () => {
  recordOperation('open_tutorial_tab', {});
  isOpen.value = true;
  hasUnreadPush.value = false;
  popupNotice.value = null;
  activeTab.value = 'tutorial';
};

function onAssistantPanelKeydown(e) {
  if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
  const t = e.target;
  if (!(t instanceof HTMLElement) || t.getAttribute('role') !== 'tab') return;
  e.preventDefault();
  const cur = FLOAT_TAB_ORDER.indexOf(activeTab.value);
  if (cur < 0) return;
  const dir = e.key === 'ArrowRight' ? 1 : -1;
  const nextI = (cur + dir + FLOAT_TAB_ORDER.length) % FLOAT_TAB_ORDER.length;
  const nextTab = FLOAT_TAB_ORDER[nextI];
  if (nextTab === 'tutorial') {
    openTutorialTab();
  } else {
    activeTab.value = nextTab;
  }
  nextTick(() => {
    const tid = FLOAT_TAB_DATA_ID[nextTab];
    assistantPanelRef.value?.querySelector?.(`[data-tutorial-id="${tid}"]`)?.focus?.();
  });
}

const startTutorialGuide = async (track = 'basic') => {
  const t = String(track || 'basic').trim() || 'basic';
  const extractChatMessagesSnapshot = () => {
    const nodes = Array.from(document.querySelectorAll('#chatMessages .message'));
    return nodes.slice(-30).map((node) => {
      const role = node.classList.contains('ai') ? 'assistant' : (node.classList.contains('user') ? 'user' : 'unknown');
      const text = String(node.textContent || '').trim().replace(/\s+/g, ' ');
      return { role, content: text.slice(0, 500) };
    }).filter((item) => item.content);
  };
  const cacheTutorialGuidePack = async (pack) => {
    try {
      await fetch('/api/preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: 'default',
          key: 'tutorial_guide_pack_cache',
          value: JSON.stringify(pack),
        }),
      });
    } catch (_e) {
      // 缓存失败不影响教程主流程
    }
  };
  const previousRouteName = String(router.currentRoute.value?.name || '');
  const previousOpen = isOpen.value;
  const previousTab = activeTab.value;
  const snapshotState = {
    pushFeed: [...pushFeed.value],
    productKeyword: productKeyword.value,
    productRows: [...productRows.value],
    linkedSheetName: linkedSheetName.value,
    linkedSheetIndex: linkedSheetIndex.value,
    linkedGridData: linkedGridData.value,
    linkedSheetFields: [...linkedSheetFields.value],
    linkedSheetSampleRows: [...linkedSheetSampleRows.value],
    topScrollInnerWidth: topScrollInnerWidth.value,
    loadingProducts: loadingProducts.value,
    lastProductSearchQuery: lastProductSearchQuery.value,
    productSearchFailed: productSearchFailed.value,
    productSearchErrorText: productSearchErrorText.value,
    lastProductSearchTotal: lastProductSearchTotal.value,
    popupNotice: popupNotice.value,
    hasUnreadPush: hasUnreadPush.value,
    operationHistory: [...operationHistory.value],
  };
  await router.push({ name: 'chat' }).catch(() => {});
  await nextTick();
  // 教程入口等同于「新对话」初始化，避免继承旧会话上下文。
  for (let i = 0; i < 4; i += 1) {
    const newConversationBtn = document.getElementById('newConversationBtn');
    if (newConversationBtn) {
      newConversationBtn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
      break;
    }
    await new Promise((resolve) => setTimeout(resolve, 80));
  }
  // 进入教程前统一回到初始教学态，避免沿用上一次副窗临时状态。
  pushFeed.value = [];
  productKeyword.value = '';
  productRows.value = [];
  linkedSheetName.value = '';
  linkedSheetIndex.value = 0;
  linkedGridData.value = null;
  linkedSheetFields.value = [];
  linkedSheetSampleRows.value = [];
  topScrollInnerWidth.value = 0;
  productSearchFailed.value = false;
  productSearchErrorText.value = '';
  lastProductSearchQuery.value = '';
  lastProductSearchTotal.value = null;
  operationHistory.value = [];
  isOpen.value = true;
  hasUnreadPush.value = false;
  popupNotice.value = null;
  activeTab.value = 'tutorial';
  // 若用户已在教程标签，startTutorial 前再触发一次预热（仅首次会真正请求）
  queueMicrotask(() => {
    window.dispatchEvent(new CustomEvent('xcagi:warmup-tutorial-tts'));
  });
  tutorialStore.startTutorial({
    isProMode: !!window.__XCAGI_IS_PRO_MODE,
    track: t,
    buildContext: tutorialBuildContext.value,
    returnContext: {
      routeName: previousRouteName || 'chat',
      assistantOpen: previousOpen,
      assistantTab: previousTab || 'push',
      assistantState: snapshotState,
    },
  });
  const tutorialPack = {
    version: 1,
    type: 'xcagi_tutorial_guide_pack',
    createdAt: new Date().toISOString(),
    context: {
      routeBeforeTutorial: previousRouteName || 'chat',
      assistantOpenBeforeTutorial: previousOpen,
      assistantTabBeforeTutorial: previousTab || 'push',
      chatMessages: extractChatMessagesSnapshot(),
    },
    tutorial: {
      track: tutorialStore.currentTrack ?? t,
      requestedTrack: t,
      stepCount: tutorialStore.steps.length,
      steps: tutorialStore.steps.map((step, idx) => ({
        index: idx + 1,
        id: step.id,
        title: step.title,
        description: step.description,
        actionType: step.actionType,
        targetSelector: step.targetSelector,
      })),
    },
  };
  void cacheTutorialGuidePack(tutorialPack);
};

const addPush = (detail) => {
  const title = (detail?.title || '').trim() || '新推送';
  const description = (detail?.description || '').trim() || '收到一条助手消息';
  recordOperation('assistant_push', { title, description });
  pushFeed.value = [
    {
      id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      title,
      description,
    },
    ...pushFeed.value
  ].slice(0, MAX_PUSH_ITEMS);

  if (!isOpen.value) {
    hasUnreadPush.value = true;
    popupNotice.value = {
      title,
      description,
    };
    if (noticeTimer) clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => {
      popupNotice.value = null;
      noticeTimer = null;
    }, 6000);
  }
};

const openFromNotice = () => {
  isOpen.value = true;
  hasUnreadPush.value = false;
  popupNotice.value = null;
  if (noticeTimer) {
    clearTimeout(noticeTimer);
    noticeTimer = null;
  }
};

const isWechatPush = (detail) => {
  const feature = String(detail?.feature || '').trim().toLowerCase();
  const source = String(detail?.source || '').trim().toLowerCase();
  return (
    feature === 'wechat' ||
    feature === 'wechat_contacts' ||
    feature === 'wechat-message' ||
    source.includes('wechat')
  );
};

const searchProducts = async () => {
  const kw = String(productKeyword.value || '').trim();
  if (!kw) {
    productRows.value = [];
    lastProductSearchQuery.value = '';
    lastProductSearchTotal.value = null;
    productSearchFailed.value = false;
    productSearchErrorText.value = '';
    loadingProducts.value = false;
    return;
  }
  const seq = ++productSearchSeq;
  loadingProducts.value = true;
  productSearchFailed.value = false;
  productSearchErrorText.value = '';
  const timeoutPromise = new Promise((_, reject) => {
    setTimeout(() => reject(new Error(`请求超时（${PRODUCT_SEARCH_TIMEOUT_MS / 1000} 秒），请检查后端是否卡住或未启动`)), PRODUCT_SEARCH_TIMEOUT_MS);
  });
  try {
    const resp = await Promise.race([productsApi.searchProducts(kw), timeoutPromise]);
    if (seq !== productSearchSeq) return;
    if (resp && resp.success === false) {
      productRows.value = [];
      lastProductSearchQuery.value = kw;
      lastProductSearchTotal.value = 0;
      productSearchFailed.value = true;
      productSearchErrorText.value = String(resp?.message || `${uiText.entityName.value}库查询失败`);
      return;
    }
    const raw = resp?.data ?? resp?.products ?? resp?.items;
    const rows = Array.isArray(raw) ? raw : [];
    const totalFromApi = typeof resp?.total === 'number' ? resp.total : rows.length;
    lastProductSearchTotal.value = totalFromApi;
    productRows.value = rows.slice(0, 20).map((r) => ({
      id: r.id,
      model_number: r.model_number || '',
      name: r.name || r.product_name || '',
      price: Number(r.price || 0),
      unit: r.unit || '',
    }));
    recordOperation('search_products', { keyword: kw, hasResult: rows.length > 0, total: totalFromApi });
    lastProductSearchQuery.value = kw;
  } catch (e) {
    if (seq !== productSearchSeq) return;
    productRows.value = [];
    lastProductSearchQuery.value = kw;
    lastProductSearchTotal.value = null;
    productSearchFailed.value = true;
    if (e instanceof ApiError) {
      const st = e.status ? `HTTP ${e.status}` : '';
      productSearchErrorText.value = [st, e.message].filter(Boolean).join(' · ');
    } else {
      productSearchErrorText.value = (e && e.message) ? String(e.message) : '网络异常';
    }
    recordOperation('search_products', { keyword: kw, hasResult: false, failed: true });
  } finally {
    if (seq === productSearchSeq) {
      loadingProducts.value = false;
    }
  }
};

const productEmptyMessage = computed(() => {
  const cur = String(productKeyword.value || '').trim();
  if (productSearchFailed.value) {
    const detail = productSearchErrorText.value ? `（${productSearchErrorText.value}）` : '';
    return `${uiText.searchFailedMessage.value}${detail}`;
  }
  if (!lastProductSearchQuery.value) {
    return uiText.emptyBeforeSearch.value;
  }
  if (cur && cur !== lastProductSearchQuery.value) {
    return uiText.keywordChanged.value;
  }
  const kw = lastProductSearchQuery.value;
  const n = lastProductSearchTotal.value;
  const totalHint = typeof n === 'number' ? `${uiText.entityName.value}库中本次条件共 ${n} 条。` : '';
  return `未找到与「${kw}」匹配的${uiText.entityName.value}。${totalHint}可缩短关键词、只输入${uiText.modelLabel.value}，或到左侧「${uiText.entityListName.value}」浏览全库核对${uiText.nameLabel.value}/${uiText.modelLabel.value}。`;
});

const saveProductRow = async (row) => {
  if (!row?.id) return;
  savingProductId.value = row.id;
  try {
    await productsApi.updateProduct(row.id, {
      model_number: row.model_number || '',
      name: row.name || '',
      price: Number(row.price || 0),
      unit: row.unit || '',
    });
    recordOperation('save_product', {
      id: row.id,
      name: row.name || '',
      model: row.model_number || '',
    });
  } finally {
    savingProductId.value = null;
  }
};

const onAssistantPush = (evt) => {
  const detail = evt?.detail || {};
  if (!isWechatPush(detail)) return;
  addPush(detail);
};

const onOpenAssistantFloat = (evt) => {
  const detail = evt?.detail || {};
  recordOperation('open_float_event', { feature: detail?.feature || '' });
  const feature = String(detail?.feature || '').trim().toLowerCase();
  const shouldAutoOpen = !!(
    detail?.forceOpen ||
    detail?.task ||
    ['products', 'assistant', 'print', 'shipment', 'shipment_generate', 'tutorial'].includes(feature)
  );
  if (shouldAutoOpen) {
    isOpen.value = true;
  } else {
    hasUnreadPush.value = true;
  }
  if (detail?.feature === 'products' || detail?.feature === 'assistant') {
    activeTab.value = 'assistant';
    const hyd = detail?.hydrateProductSearch;
    if (hyd && Array.isArray(hyd.rows)) {
      const q = String(detail.query || '').trim();
      productKeyword.value = q;
      productRows.value = hyd.rows;
      lastProductSearchQuery.value = q;
      lastProductSearchTotal.value = typeof hyd.total === 'number' ? hyd.total : hyd.rows.length;
      loadingProducts.value = false;
      productSearchFailed.value = false;
      productSearchErrorText.value = '';
      recordOperation('search_products', {
        keyword: q,
        hasResult: hyd.rows.length > 0,
        total: lastProductSearchTotal.value,
        hydrated: true
      });
    } else if (detail?.query) {
      const q = String(detail.query).trim();
      const sameKw = q && q === String(productKeyword.value || '').trim();
      if (!sameKw) {
        productKeyword.value = q;
        searchProducts();
      } else if (!loadingProducts.value && productRows.value.length === 0) {
        searchProducts();
      }
    }
  } else if (detail?.feature === 'starterPack') {
    activeTab.value = 'starterPack';
  } else if (detail?.feature === 'tutorial') {
    isOpen.value = true;
    activeTab.value = 'tutorial';
  } else {
    activeTab.value = 'push';
  }
};

const applyExcelSheetContext = (detail) => {
  const selected = detail?.selected_sheet || {};
  const excel = detail?.excel_analysis || {};
  linkedSheetName.value = String(selected?.sheet_name || '').trim();
  linkedSheetIndex.value = Number(selected?.sheet_index || 0);
  const allSheets = Array.isArray(excel?.preview_data?.all_sheets) ? excel.preview_data.all_sheets : [];
  const target = allSheets.find((s) => {
    const n = String(s?.sheet_name || '').trim();
    const i = Number(s?.sheet_index || 0);
    return (linkedSheetName.value && n === linkedSheetName.value) || (linkedSheetIndex.value > 0 && i === linkedSheetIndex.value);
  }) || allSheets[0];
  linkedGridData.value = target?.grid_preview && typeof target.grid_preview === 'object' ? target.grid_preview : null;
  linkedSheetFields.value = Array.isArray(target?.fields) ? target.fields : [];
  linkedSheetSampleRows.value = Array.isArray(target?.sample_rows) ? target.sample_rows : [];
};

const syncTopScrollMetrics = async () => {
  await nextTick();
  const root = excelPreviewRef.value?.$el || excelPreviewRef.value;
  const excelContainer = root?.querySelector?.('.excel-container');
  if (!excelContainer) {
    topScrollInnerWidth.value = 0;
    return;
  }
  excelContainer.removeEventListener('scroll', onExcelScroll);
  excelContainer.addEventListener('scroll', onExcelScroll, { passive: true });
  const targetWidth = Math.max(excelContainer.scrollWidth || 0, excelContainer.clientWidth || 0);
  topScrollInnerWidth.value = targetWidth;
};

const onTopScroll = (evt) => {
  const root = excelPreviewRef.value?.$el || excelPreviewRef.value;
  const excelContainer = root?.querySelector?.('.excel-container');
  if (!excelContainer) return;
  excelContainer.scrollLeft = evt?.target?.scrollLeft || 0;
};

const onExcelScroll = () => {
  const root = excelPreviewRef.value?.$el || excelPreviewRef.value;
  const excelContainer = root?.querySelector?.('.excel-container');
  if (!excelContainer || !topScrollRef.value) return;
  topScrollRef.value.scrollLeft = excelContainer.scrollLeft || 0;
};

const onExcelSheetContext = (evt) => {
  const detail = evt?.detail || {};
  applyExcelSheetContext(detail);
};

const triggerGridReadFromChat = async () => {
  if (!linkedSheetName.value) return;
  const text = `请调用业务对接的上传并提取能力，读取并展示 Sheet ${linkedSheetIndex.value || ''}（${linkedSheetName.value}）的网格结构`;
  await router.push({ name: 'chat' });
  await nextTick();
  await fillChatInputWithRetry(text);
};

/**
 * 根据副窗当前展示主题决定跳转到哪个主页面。
 * 若已在目标路由则不重复跳；不能识别主题时 fallback 到聊天页。
 */
const SUBJECT_ROUTE_MAP = {
  products: 'products',
  product: 'products',
  customers: 'customers',
  customer: 'customers',
  shipment: 'shipment-records',
  'shipment-records': 'shipment-records',
  template: 'template-preview',
  templates: 'template-preview',
  materials: 'materials',
  inventory: 'inventory',
  approval: 'approval-hub',
};

const navigateToSubjectPage = async (subject) => {
  const routeName = SUBJECT_ROUTE_MAP[String(subject || '').toLowerCase()] || 'chat';
  if (router.currentRoute.value.name !== routeName) {
    await router.push({ name: routeName }).catch(() => {});
  }
};

const isAutoRefreshEnabled = () => {
  return localStorage.getItem(AUTO_REFRESH_STARRED_WECHAT_KEY) === '1';
};

const normalizeMsgSignature = (msg) => {
  const role = String(msg?.role || '');
  const text = String(msg?.text || '').trim();
  return `${role}::${text}`;
};

const pollStarredFeed = async () => {
  if (feedPolling || !isAutoRefreshEnabled()) return;
  feedPolling = true;
  try {
    const resp = await fetch(resolveErpApiPath('/api/wechat_contacts/work_mode_feed?per_contact=1'));
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || !data?.success || !Array.isArray(data.feed)) {
      return;
    }

    const alive = new Set();
    for (const item of data.feed) {
      const contactId = item?.contact_id;
      if (!contactId) continue;
      alive.add(String(contactId));
      const latestMsg = Array.isArray(item.messages) && item.messages.length ? item.messages[0] : null;
      if (!latestMsg) continue;

      const signature = normalizeMsgSignature(latestMsg);
      const oldSig = lastFeedMessageByContact.get(String(contactId));
      if (feedInitialized && oldSig && oldSig !== signature) {
        window.dispatchEvent(new CustomEvent('xcagi:assistant-push', { detail: {
          title: `${item.contact_name || '星标联系人'} 有新消息`,
          description: String(latestMsg.text || '').slice(0, 80) || '收到一条新消息',
          feature: 'wechat',
          source: 'wechat_contacts',
        }}));
        if (shouldRunStarredWechatIntentPipeline()) {
          void runWechatMessageAiPipeline(item, latestMsg);
        }
      }
      lastFeedMessageByContact.set(String(contactId), signature);
    }

    for (const key of Array.from(lastFeedMessageByContact.keys())) {
      if (!alive.has(key)) {
        lastFeedMessageByContact.delete(key);
      }
    }
    feedInitialized = true;

    window.dispatchEvent(
      new CustomEvent('xcagi:wechat-star-feed-polled', {
        detail: {
          at: Date.now(),
          intervalMs: FEED_POLL_INTERVAL_MS,
          contactCount: Array.isArray(data.feed) ? data.feed.length : 0,
          ok: true,
        },
      })
    );
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err || '');
    if (err instanceof TypeError && msg.includes('Failed to fetch')) {
      console.debug('[TopAssistantFloat] pollStarredFeed network unavailable:', msg);
      return;
    }
    console.warn('[TopAssistantFloat] pollStarredFeed failed:', err);
  } finally {
    feedPolling = false;
  }
};

const stopFeedPolling = () => {
  if (feedPollTimer) {
    clearInterval(feedPollTimer);
    feedPollTimer = null;
  }
};

const startFeedPolling = () => {
  stopFeedPolling();
  if (!isAutoRefreshEnabled()) return;
  pollStarredFeed();
  feedPollTimer = setInterval(() => {
    pollStarredFeed();
  }, FEED_POLL_INTERVAL_MS);
};

const onAutoRefreshWechatChanged = () => {
  if (!isAutoRefreshEnabled()) {
    stopFeedPolling();
    return;
  }
  startFeedPolling();
};

const onRestoreFloatState = (evt) => {
  const detail = evt?.detail || {};
  const state = detail.assistantState || null;
  if (state) {
    pushFeed.value = Array.isArray(state.pushFeed) ? [...state.pushFeed] : [];
    productKeyword.value = String(state.productKeyword || '');
    productRows.value = Array.isArray(state.productRows) ? [...state.productRows] : [];
    linkedSheetName.value = String(state.linkedSheetName || '');
    linkedSheetIndex.value = Number(state.linkedSheetIndex || 0);
    linkedGridData.value = state.linkedGridData || null;
    linkedSheetFields.value = Array.isArray(state.linkedSheetFields) ? [...state.linkedSheetFields] : [];
    linkedSheetSampleRows.value = Array.isArray(state.linkedSheetSampleRows) ? [...state.linkedSheetSampleRows] : [];
    topScrollInnerWidth.value = Number(state.topScrollInnerWidth || 0);
    loadingProducts.value = !!state.loadingProducts;
    lastProductSearchQuery.value = String(state.lastProductSearchQuery || '');
    productSearchFailed.value = !!state.productSearchFailed;
    productSearchErrorText.value = String(state.productSearchErrorText || '');
    lastProductSearchTotal.value = state.lastProductSearchTotal ?? null;
    popupNotice.value = state.popupNotice || null;
    hasUnreadPush.value = !!state.hasUnreadPush;
    operationHistory.value = Array.isArray(state.operationHistory) ? [...state.operationHistory] : [];
  }
  isOpen.value = !!detail.isOpen;
  activeTab.value = String(detail.activeTab || 'push');
};

const onTutorialSetAssistantTab = (evt) => {
  const detail = evt?.detail || {};
  if (detail.open) {
    isOpen.value = true;
  }
  const tab = String(detail.tab || '').trim();
  if (tab) {
    activeTab.value = tab;
  }
};

const onCloseAssistantFloat = () => {
  if (tutorialStore.isActive && tutorialStore.currentStep?.assistantTab) {
    return;
  }
  recordOperation('close_float_event', { source: 'shipment_task' });
  isOpen.value = false;
  focusToggleAfterClose();
};

onMounted(() => {
  window.addEventListener('keydown', onDocumentKeydownCapture, true);
  window.addEventListener('xcagi:assistant-push', onAssistantPush);
  window.addEventListener('xcagi:open-assistant-float', onOpenAssistantFloat);
  window.addEventListener('xcagi:close-assistant-float', onCloseAssistantFloat);
  window.addEventListener('xcagi:auto-refresh-wechat-changed', onAutoRefreshWechatChanged);
  window.addEventListener('xcagi:excel-sheet-context', onExcelSheetContext);
  window.addEventListener('xcagi:tutorial:restore-float', onRestoreFloatState);
  window.addEventListener('xcagi:tutorial:set-assistant-tab', onTutorialSetAssistantTab);
  startFeedPolling();
  syncTopScrollMetrics();
  if (modsStore.clientModsUiOff) {
    workflowAiEmployeesStore.stripModWorkflowEmployeeKeys();
  } else {
    workflowAiEmployeesStore.hydrateFromMods(modsStore.modsForUi);
    workflowAiEmployeesStore.pruneOrphanWorkflowEmployeeToggles(modsStore.modsForUi);
  }
  if (!workflowRegistryLoaded.value) {
    workflowAiEmployeesStore.loadRegistry(modsStore.modsForUi);
  }
});

watch(
  () => modsStore.modsForUi,
  (list) => {
    workflowAiEmployeesStore.hydrateFromMods(list);
    workflowAiEmployeesStore.pruneOrphanWorkflowEmployeeToggles(list);
    if (workflowRegistryLoaded.value) {
      workflowAiEmployeesStore.loadRegistry(list);
    }
  },
  { deep: true }
);

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onDocumentKeydownCapture, true);
  window.removeEventListener('xcagi:assistant-push', onAssistantPush);
  window.removeEventListener('xcagi:open-assistant-float', onOpenAssistantFloat);
  window.removeEventListener('xcagi:close-assistant-float', onCloseAssistantFloat);
  window.removeEventListener('xcagi:auto-refresh-wechat-changed', onAutoRefreshWechatChanged);
  window.removeEventListener('xcagi:excel-sheet-context', onExcelSheetContext);
  window.removeEventListener('xcagi:tutorial:restore-float', onRestoreFloatState);
  window.removeEventListener('xcagi:tutorial:set-assistant-tab', onTutorialSetAssistantTab);
  stopFeedPolling();
  if (noticeTimer) {
    clearTimeout(noticeTimer);
    noticeTimer = null;
  }
  const root = excelPreviewRef.value?.$el || excelPreviewRef.value;
  const excelContainer = root?.querySelector?.('.excel-container');
  if (excelContainer) {
    excelContainer.removeEventListener('scroll', onExcelScroll);
  }
});

watch(() => linkedGridData.value, () => {
  syncTopScrollMetrics();
});
</script>

<style scoped>
.assistant-float-root {
  position: relative;
}
.assistant-float-toggle {
  margin-left: 10px;
  border: 1px solid var(--app-border-strong, #d1d5db);
  background: var(--card-bg, #fff);
  color: var(--app-text-strong, #374151);
  border-radius: 999px;
  padding: var(--app-space-sm, 8px) 10px;
  min-height: 40px;
  font-size: var(--app-font-size-caption, 12px);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}
.assistant-float-toggle.pulse {
  animation: assistant-pulse 1.4s ease-in-out infinite;
}
.assistant-popup-notice {
  position: fixed;
  right: 18px;
  top: 56px;
  width: 320px;
  border: 1px solid #dbeafe;
  background: #eff6ff;
  color: #1e3a8a;
  border-radius: 8px;
  padding: 10px;
  box-shadow: 0 8px 20px rgba(30, 58, 138, 0.18);
  z-index: 3050;
  cursor: pointer;
}
.assistant-popup-title {
  font-size: 13px;
  font-weight: 600;
}
.assistant-popup-desc {
  font-size: 12px;
  margin-top: 4px;
  color: #1f2937;
}
.assistant-popup-hint {
  margin-top: 6px;
  font-size: 11px;
  color: #2563eb;
}
.assistant-float-panel {
  position: fixed;
  right: 18px;
  top: 56px;
  width: 360px;
  max-height: 70vh;
  background: var(--card-bg, #fff);
  border: 1px solid var(--app-border-subtle, #e5e7eb);
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.14);
  z-index: 3000;
  display: flex;
  flex-direction: column;
  outline: none;
}
.assistant-float-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #f1f5f9;
  padding: 8px 10px;
}
.assistant-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--app-text-strong, #111827);
}
.assistant-close {
  border: none;
  background: transparent;
  font-size: 18px;
  line-height: 1;
  min-width: 40px;
  min-height: 40px;
  cursor: pointer;
  color: var(--app-text-muted, #6b7280);
}
.assistant-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 6px;
  padding: 8px 10px 0;
}
.assistant-tab {
  border: 1px solid var(--app-border-subtle, #e5e7eb);
  background: #f9fafb;
  color: var(--app-text-strong, #374151);
  border-radius: 6px;
  padding: var(--app-space-xs, 4px) var(--app-space-sm, 8px);
  min-height: 40px;
  font-size: var(--app-font-size-caption, 12px);
  cursor: pointer;
}
.assistant-tab.active {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}
.assistant-body {
  padding: 10px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}
.assistant-empty {
  color: #9ca3af;
  font-size: 12px;
  padding: 8px 0;
}
.push-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.push-item {
  border: 1px solid #eef2ff;
  background: #f8fafc;
  border-radius: 8px;
  padding: 8px;
}
.push-item-title {
  font-size: 12px;
  font-weight: 600;
  color: #1f2937;
}
.push-item-desc {
  margin-top: 4px;
  font-size: 12px;
  color: #4b5563;
}
.product-search-row {
  display: flex;
  gap: 8px;
}
.product-search-row input {
  flex: 1;
}
.product-result {
  margin-top: 10px;
}
.product-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.product-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px;
  background: #fff;
}
.product-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.product-id-label {
  font-size: 11px;
  font-weight: 600;
  color: #374151;
}
.product-field {
  margin-bottom: 6px;
}
.product-field-label {
  display: block;
  font-size: 11px;
  color: #6b7280;
  margin-bottom: 2px;
}
.product-input {
  width: 100%;
  box-sizing: border-box;
}
.product-actions {
  display: flex;
  justify-content: flex-end;
}
.assistant-divider {
  height: 1px;
  background: #eef2f7;
  margin: 12px 0;
}
.assistant-block-title {
  font-size: 12px;
  font-weight: 600;
  color: #111827;
}
.assistant-block-desc {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}
.assistant-grid-actions {
  margin-top: 8px;
}
.linked-grid-preview {
  margin-top: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 6px;
  background: #f8fafc;
  max-height: min(52vh, 420px);
  overflow: auto;
}
.linked-grid-caption {
  font-size: 10px;
  color: #6b7280;
  margin-bottom: 4px;
}
.linked-grid-top-scroll {
  height: 10px;
  overflow-x: auto;
  overflow-y: hidden;
  margin-bottom: 6px;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #eef2f7;
}
.linked-grid-top-scroll-inner {
  height: 1px;
}
.linked-grid-preview :deep(.excel-toolbar) {
  padding: 4px 6px;
}
.linked-grid-preview :deep(.excel-title) {
  font-size: 10px;
}
.linked-grid-preview :deep(.real-row-num) {
  width: 24px;
  min-width: 24px;
  padding: 2px;
  font-size: 10px;
}
.linked-grid-preview :deep(.real-grid-cell) {
  min-width: 52px;
  height: 22px;
  padding: 1px 3px;
  font-size: 10px;
}
.linked-grid-preview :deep(.cell-text) {
  font-size: 10px;
  line-height: 1.2;
}
.linked-grid-preview :deep(.fake-excel) {
  border-radius: 6px;
}
.starter-pack-intro {
  font-size: 12px;
  color: #6b7280;
  margin: 0 0 10px;
  line-height: 1.45;
}
.starter-pack-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.starter-pack-item {
  text-align: left;
  width: 100%;
  border: 1px solid #eef2ff;
  background: #f8fafc;
  border-radius: 8px;
  padding: 8px;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.starter-pack-item:hover {
  background: #eff6ff;
  border-color: #bfdbfe;
}
.assistant-body-recommend {
  max-height: min(52vh, 420px);
}
.recommend-intro {
  margin: 0 0 10px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.45;
}
.workflow-employee-section {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 10px 8px;
  background: #fff;
}
.workflow-employee-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}
.workflow-employee-heading {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 0;
  flex: 1;
  min-width: 0;
}
.workflow-employee-visual-link {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  color: #2563eb;
  text-decoration: none;
  padding: 4px 9px;
  border-radius: 6px;
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  line-height: 1.2;
  white-space: nowrap;
}
.workflow-employee-visual-link:hover {
  background: #dbeafe;
  color: #1d4ed8;
}
.workflow-employee-hint {
  margin: 0 0 10px;
  font-size: 11px;
  color: #6b7280;
  line-height: 1.4;
}
.workflow-employee-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.workflow-employee-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
  text-align: left;
  padding: 8px 10px;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  background: #f9fafb;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.workflow-employee-row:hover {
  background: #f3f4f6;
  border-color: #e5e7eb;
}
.workflow-employee-label {
  font-size: 12px;
  font-weight: 500;
  color: #1f2937;
  line-height: 1.35;
  flex: 1;
  min-width: 0;
}
/* 与侧栏 #proModeToggle 同款尺寸与动效，适配浅色副窗背景 */
.workflow-employee-toggle.toggle-switch {
  flex-shrink: 0;
  width: 40px;
  height: 20px;
  background: #d1d5db;
  border-radius: 10px;
  position: relative;
  transition: background 0.3s;
  pointer-events: none;
}
.workflow-employee-toggle.toggle-switch.active {
  background: #4a90d9;
}
.workflow-employee-toggle .toggle-slider {
  width: 16px;
  height: 16px;
  background: #fff;
  border-radius: 50%;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: transform 0.3s;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
}
.workflow-employee-toggle.toggle-switch.active .toggle-slider {
  transform: translateX(20px);
}
.starter-pack-label {
  font-size: 12px;
  font-weight: 600;
  color: #1f2937;
}
.starter-pack-hint {
  margin-top: 4px;
  font-size: 12px;
  color: #4b5563;
  line-height: 1.4;
}
.tutorial-track-pick {
  margin-bottom: 14px;
  padding: 10px 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: linear-gradient(180deg, #f9fafb 0%, #ffffff 100%);
}
.tutorial-track-heading {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 6px;
}
.tutorial-track-lead {
  margin: 0 0 10px;
  font-size: 12px;
  color: #4b5563;
  line-height: 1.45;
}
.tutorial-track-list {
  list-style: none;
  margin: 0 0 10px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.tutorial-track-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}
.tutorial-track-card-main {
  flex: 1;
  min-width: 0;
}
.tutorial-track-card-title {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}
.tutorial-track-card-summary {
  margin: 4px 0 0;
  font-size: 12px;
  color: #4b5563;
  line-height: 1.4;
}
.tutorial-track-card-extra {
  margin: 6px 0 0;
  font-size: 11px;
  line-height: 1.45;
}
.tutorial-track-details {
  margin-top: 4px;
  font-size: 11px;
  color: #6b7280;
}
.tutorial-track-details summary {
  cursor: pointer;
  color: #374151;
  font-weight: 500;
}
.tutorial-track-hint {
  margin: 8px 0 0;
  font-size: 11px;
  color: #6b7280;
  line-height: 1.5;
}
.tutorial-track-hint strong {
  color: #374151;
}
/* 仅保留「选择教程」卡片时仍占满副窗内容区，避免 flex 子项高度为 0 导致看不见 */
.assistant-body.assistant-body-tutorial {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  color: #111827;
}
@keyframes assistant-pulse {
  0% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.35); }
  70% { box-shadow: 0 0 0 8px rgba(37, 99, 235, 0); }
  100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }
}
</style>
