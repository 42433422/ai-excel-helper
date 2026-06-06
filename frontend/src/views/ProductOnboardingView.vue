<template>
  <div class="product-flow">
    <header class="product-flow-header">
      <div class="brand">XCAGI 宿主</div>
      <div class="edition-tag">发行版：{{ editionLabel }}</div>
    </header>

    <nav class="step-rail" aria-label="设置流程">
      <div
        v-for="step in steps"
        :key="step.id"
        class="step-rail-item"
        :class="{ active: step.id === currentStep, done: step.index < currentIndex }"
      >
        <span class="step-num">{{ step.index }}</span>
        <span class="step-label">{{ step.title }}</span>
      </div>
    </nav>

    <section class="step-panel">
      <!-- 1 认识宿主 -->
      <template v-if="currentStep === 'welcome'">
        <h1>欢迎使用独立宿主</h1>
        <p class="lead">通用宿主：安装 Mod 后扩展为行业系统。</p>
        <div class="actions">
          <button type="button" class="btn primary" @click="goStep('host-pack')">下一步：检查宿主包</button>
        </div>
      </template>

      <!-- 2 宿主就绪 -->
      <template v-else-if="currentStep === 'host-pack'">
        <h1>宿主能力包</h1>
        <p class="lead">安装宿主基础员工包后即可继续。</p>
        <div class="status-card" :class="{ ok: deliverableOk, warn: !deliverableOk && !loading }">
          <template v-if="loading">
            <i class="fa fa-spinner fa-spin"></i> 正在检测…
          </template>
          <template v-else-if="deliverableOk">
            <i class="fa fa-check-circle"></i> 宿主已就绪，可进入下一步。
          </template>
          <template v-else>
            <i class="fa fa-exclamation-circle"></i>
            {{ hostPackStatusTitle }}
            <span v-if="missingHint" class="mono">（{{ missingHint }}）</span>
          </template>
        </div>
        <div class="actions">
          <button type="button" class="btn primary" :disabled="bootstrapBusy" @click="runBootstrap">
            <i class="fa" :class="bootstrapBusy ? 'fa-spinner fa-spin' : 'fa-download'"></i>
            一键装齐通用包
          </button>
          <button type="button" class="btn ghost" :disabled="loading" @click="refreshStatus">重新检测</button>
          <button
            v-if="deliverableOk"
            type="button"
            class="btn link"
            @click="goStep('industry')"
          >
            下一步：行业定型
          </button>
        </div>
      </template>

      <!-- 3 行业定型 -->
      <template v-else-if="currentStep === 'industry'">
        <h1>行业定型（可选）</h1>
        <p class="lead">可在扩展市场安装行业 Mod，或稍后再装。</p>
        <div class="actions">
          <button type="button" class="btn primary" @click="openModStore">打开扩展市场</button>
          <button type="button" class="btn ghost" @click="finishToChat">先使用对话，稍后再装 MOD</button>
        </div>
      </template>

      <!-- 4 完成 -->
      <template v-else>
        <h1>可以开始使用</h1>
        <p class="lead">可从智能对话或扩展市场开始。</p>
        <div class="actions">
          <button type="button" class="btn primary" @click="finishToChat">进入智能对话</button>
        </div>
      </template>
    </section>

    <footer class="product-flow-footer">
      <button type="button" class="btn text" @click="skipEntireFlow">跳过引导（高级用户）</button>
      <span class="doc-hint">完整流程见仓库 docs/guides/PRODUCT_USER_FLOW.md</span>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { installHostFoundation } from '@/api/modStore'
import { readBuildEdition } from '@/constants/genericModPack'
import { PRODUCT_FLOW_STEPS, parseFlowStepQuery } from '@/constants/productFlow'
import { useProductFlow } from '@/composables/useProductFlow'
import { appAlert } from '@/utils/appDialog'

const route = useRoute()
const router = useRouter()
const flow = useProductFlow()

const steps = PRODUCT_FLOW_STEPS.filter((s) => s.id !== 'done')
const currentStep = ref(parseFlowStepQuery(route.query.step))
const loading = ref(false)
const bootstrapBusy = ref(false)

const deliverableOk = computed(() => flow.deliverable.value?.deliverable !== false)
const hostEmployeeInstalled = computed(
  () => flow.deliverable.value?.host_foundation_employee_installed === true,
)
const hostPackStatusTitle = computed(() => {
  if (deliverableOk.value) return ''
  if (hostEmployeeInstalled.value) return '员工包已安装，bridge 尚未展开'
  return '宿主包未齐'
})
const missingHint = computed(() => {
  const st = flow.deliverable.value
  if (!st || deliverableOk.value) return ''
  if (hostEmployeeInstalled.value) {
    const missing = (st.missing_mod_ids || []).filter(Boolean)
    return missing.length
      ? `待展开：${missing.join('、')}`
      : '请点击「一键装齐」或「重新检测」'
  }
  return `缺少：${(st.missing_mod_ids || []).join(', ')}`
})

const currentIndex = computed(() => {
  const row = steps.find((s) => s.id === currentStep.value)
  return row?.index ?? 1
})

const editionLabel = computed(() => {
  const e = readBuildEdition()
  if (e === 'minimal') return '空壳 minimal'
  if (e === 'generic') return '通用 generic'
  return '完整 full'
})

watch(
  () => route.query.step,
  (q) => {
    currentStep.value = parseFlowStepQuery(q)
  },
)

async function refreshStatus() {
  loading.value = true
  try {
    await flow.refreshDeliverable(true)
  } finally {
    loading.value = false
  }
}

async function runBootstrap() {
  bootstrapBusy.value = true
  try {
    const e = readBuildEdition()
    const edition = e === 'minimal' ? 'minimal' : 'generic'
    const res = await installHostFoundation(edition)
    await flow.refreshDeliverable(true)
    if (res.success && deliverableOk.value) {
      flow.markHostPackAcknowledged()
      await appAlert('宿主基础能力员工包已就绪。')
      goStep('industry')
    } else {
      const data = res.data && typeof res.data === 'object' ? res.data : {}
      const failed = Array.isArray(data.missing_mod_ids)
        ? data.missing_mod_ids.map((id) => String(id || '').trim()).filter(Boolean)
        : []
      const detail =
        failed.length > 0
          ? `未装齐：${failed.join('、')}`
          : res.message || '部分 Mod 未装齐，请检查本机 mods 目录或 MOD 商店网络。'
      await appAlert(detail)
    }
  } catch (err) {
    await appAlert(err instanceof Error ? err.message : '装包失败')
  } finally {
    bootstrapBusy.value = false
  }
}

function goStep(id) {
  void router.replace({ name: 'product-onboarding', query: { step: id } })
}

function openModStore() {
  flow.markProductFlowCompleted()
  void router.push({ name: 'mod-store', query: { onboarding: '1' } })
}

function finishToChat() {
  flow.completeFlowAndGoChat(router)
}

function skipEntireFlow() {
  flow.markProductFlowCompleted()
  flow.markHostPackAcknowledged()
  finishToChat()
}

onMounted(() => {
  currentStep.value = flow.resolveEntryStep(route.query.step)
  if (currentStep.value !== parseFlowStepQuery(route.query.step)) {
    void router.replace({ name: 'product-onboarding', query: { step: currentStep.value } })
  }
  void refreshStatus()
})
</script>

<style scoped>
.product-flow {
  min-height: 100vh;
  padding: 32px 24px 48px;
  max-width: 720px;
  margin: 0 auto;
  box-sizing: border-box;
  background: #f8fafc;
  color: #0f172a;
}

.product-flow-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 28px;
}

.brand {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.edition-tag {
  font-size: 13px;
  color: #64748b;
}

.step-rail {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.step-rail-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  background: #e2e8f0;
  font-size: 13px;
  color: #475569;
}

.step-rail-item.active {
  background: #2563eb;
  color: #fff;
}

.step-rail-item.done {
  background: #dcfce7;
  color: #166534;
}

.step-num {
  font-weight: 700;
}

.step-panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 28px 24px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.step-panel h1 {
  margin: 0 0 12px;
  font-size: 22px;
}

.lead {
  margin: 0 0 16px;
  line-height: 1.65;
  color: #475569;
  font-size: 15px;
}

.flow-list {
  margin: 0 0 20px 20px;
  padding: 0;
  line-height: 1.7;
  color: #334155;
}

.flow-list.bullets {
  list-style: disc;
}

.status-card {
  padding: 14px 16px;
  border-radius: 10px;
  margin-bottom: 20px;
  font-size: 14px;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
}

.status-card.ok {
  background: #f0fdf4;
  border-color: #86efac;
  color: #166534;
}

.status-card.warn {
  background: #fffbeb;
  border-color: #fcd34d;
  color: #92400e;
}

.mono {
  font-family: ui-monospace, monospace;
  font-size: 12px;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.btn {
  border: none;
  border-radius: 8px;
  padding: 10px 18px;
  font-size: 14px;
  cursor: pointer;
  font-weight: 600;
}

.btn.primary {
  background: #2563eb;
  color: #fff;
}

.btn.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn.ghost {
  background: #f1f5f9;
  color: #334155;
  border: 1px solid #cbd5e1;
}

.btn.link {
  background: transparent;
  color: #2563eb;
}

.btn.text {
  background: transparent;
  color: #64748b;
  font-weight: 500;
  padding: 6px 0;
}

.product-flow-footer {
  margin-top: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.doc-hint {
  color: #64748b;
  font-size: 12px;
}
</style>
