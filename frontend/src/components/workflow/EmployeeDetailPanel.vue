<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  formatWorkDurationShort,
  totalWorkMs,
  useNowMsTicker,
  useWorkflowEmployeeDesks,
  type WorkflowEmployeeDeskRow,
} from '@/composables/useWorkflowEmployeeDesks'
import { databaseLinkForEmployee } from '@/constants/workflowEmployeeDatabaseLinks'
import { buildSyntheticManifestWorkflowFlow, getWorkflowEmployeeDocs } from '@/utils/workflowEmployeeDocs'
import type { WorkflowFlowDoc, WorkflowStepDoc } from '@/types/workflowEmployeeDocs'
import { findWorkflowEmployeeEntry } from '@/utils/modWorkflowEmployees'
import { useModsStore } from '@/stores/mods'
import { storeToRefs } from 'pinia'
import YuangongInteractiveWorkstation from '@/components/workflow/YuangongInteractiveWorkstation.vue'

const props = defineProps<{
  /** 当前选中的工位行；为 null 时显示空态 */
  row: WorkflowEmployeeDeskRow | null
}>()

const router = useRouter()
const modsStore = useModsStore()
const { modsForUi } = storeToRefs(modsStore)
const { statusLine, isBusy } = useWorkflowEmployeeDesks()
const nowMs = useNowMsTicker(30000)

const flowsByEmpId = ref<Record<string, WorkflowFlowDoc>>({})
const docsLoaded = ref(false)

onMounted(async () => {
  try {
    const docs = await getWorkflowEmployeeDocs()
    const map: Record<string, WorkflowFlowDoc> = {}
    for (const f of docs.flows || []) {
      if (f?.id) map[f.id] = f
    }
    flowsByEmpId.value = map
  } catch {
    /* ignore — fallback to "暂无说明" */
  } finally {
    docsLoaded.value = true
  }
})

const flow = computed<WorkflowFlowDoc | null>(() => {
  const id = props.row?.empId
  if (!id) return null
  const fromDocs = flowsByEmpId.value[id]
  if (fromDocs) return fromDocs
  const entry = findWorkflowEmployeeEntry(modsForUi.value, id)
  if (!entry) return null
  return buildSyntheticManifestWorkflowFlow(entry, entry.modId, entry.modName)
})

const steps = computed<WorkflowStepDoc[]>(() => flow.value?.steps ?? [])

const status = computed(() => (props.row ? statusLine(props.row) : '—'))

const workMs = computed(() => totalWorkMs(props.row?.session, nowMs.value))
const workLabel = computed(() => (props.row?.enabled ? formatWorkDurationShort(workMs.value) : '—'))

const processedLabel = computed(() => {
  const n = props.row?.session?.processedCount ?? 0
  return String(Math.max(0, n))
})

const stageLabel = computed(() => {
  if (!props.row || !props.row.enabled) return '已下班'
  if (!props.row.snapshot) return '待命中'
  return props.row.snapshot.stage || props.row.snapshot.progressLabel || '待命'
})

const progressPct = computed(() => {
  if (!props.row?.enabled) return 0
  const p = props.row.snapshot?.progressPct
  if (typeof p !== 'number' || !Number.isFinite(p)) return 0
  return Math.max(0, Math.min(100, p))
})

const hintLine = computed(() => {
  if (!props.row?.enabled) return ''
  return props.row.snapshot?.hintLine || ''
})

const dbLink = computed(() =>
  databaseLinkForEmployee(props.row?.empId ?? '')
)

const isCurrentlyBusy = computed(() => (props.row ? isBusy(props.row) : false))

function openDatabase() {
  router.push({
    name: dbLink.value.routeName,
    ...(dbLink.value.query ? { query: dbLink.value.query } : {}),
  })
}
</script>

<template>
  <aside
    class="edp"
    role="complementary"
    :aria-label="row ? `${row.shortName} 工位详情` : '工位详情'"
  >
    <header class="edp-head">
      <p class="edp-kicker">工位特写</p>
      <p class="edp-name">{{ row?.shortName ?? '—' }}</p>
      <p class="edp-title" :title="row?.panelTitle ?? ''">{{ row?.panelTitle ?? '—' }}</p>
    </header>

    <YuangongInteractiveWorkstation
      :status-line="status"
      :workflow-full-name="row?.panelTitle ?? '—'"
      :enabled="!!row?.enabled"
      :busy="isCurrentlyBusy"
    />

    <div class="edp-stats" role="list" aria-label="员工量化数据">
      <div class="edp-stat" role="listitem">
        <p class="edp-stat-k">已处理</p>
        <p class="edp-stat-v">{{ processedLabel }}</p>
        <p class="edp-stat-sub">累计派发任务数</p>
      </div>
      <div class="edp-stat" role="listitem">
        <p class="edp-stat-k">在岗工时</p>
        <p class="edp-stat-v">{{ workLabel }}</p>
        <p class="edp-stat-sub">{{ row?.enabled ? '副窗启用累计' : '副窗未启用' }}</p>
      </div>
      <div class="edp-stat edp-stat--wide" role="listitem">
        <p class="edp-stat-k">当前阶段</p>
        <p class="edp-stat-v edp-stat-v--text">{{ stageLabel }}</p>
        <span class="edp-stat-bar" aria-hidden="true">
          <span
            class="edp-stat-bar-fill"
            :class="{ 'edp-stat-bar-fill--busy': isCurrentlyBusy }"
            :style="{ width: progressPct + '%' }"
          />
        </span>
      </div>
    </div>

    <p v-if="hintLine" class="edp-hint" :title="hintLine">{{ hintLine }}</p>

    <section class="edp-section" aria-labelledby="edp-flow-h">
      <h5 id="edp-flow-h" class="edp-section-h">工作流程步骤</h5>
      <p v-if="!docsLoaded" class="edp-section-empty">说明加载中…</p>
      <p v-else-if="!steps.length" class="edp-section-empty">
        此员工由扩展提供专属流程，详情见对应扩展副窗。
      </p>
      <ol v-else class="edp-flow">
        <li v-for="(s, i) in steps" :key="i" class="edp-flow-step">
          <span class="edp-flow-idx">{{ i + 1 }}</span>
          <span class="edp-flow-body">
            <span class="edp-flow-label">{{ s.label }}</span>
            <span v-if="s.detail" class="edp-flow-detail">{{ s.detail }}</span>
          </span>
        </li>
      </ol>
    </section>

    <button
      type="button"
      class="edp-db-btn"
      :title="dbLink.description"
      :aria-label="dbLink.description"
      :disabled="!row"
      @click="openDatabase"
    >
      <span class="edp-db-btn-arrow" aria-hidden="true">→</span>
      <span class="edp-db-btn-label">{{ dbLink.label }}</span>
    </button>
  </aside>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

.edp {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 14px 12px;
  border: 1px solid #1e293b;
  border-radius: 12px;
  background: linear-gradient(180deg, #0f172a 0%, #0b1120 100%);
  color: #f1f5f9;
  position: sticky;
  top: 12px;
  min-width: 0;
}

.edp-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.edp-kicker {
  margin: 0;
  font-family: 'Press Start 2P', ui-monospace, monospace;
  font-size: 9px;
  letter-spacing: 0.08em;
  color: #93c5fd;
}

.edp-name {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #f8fafc;
}

.edp-title {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: rgba(248, 250, 252, 0.72);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.edp :deep(.yiw) {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}

.edp :deep(.yiw-title),
.edp :deep(.yiw-lead) {
  display: none;
}

.edp :deep(.yiw-frame) {
  max-width: 100%;
}

.edp-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.edp-stat {
  padding: 10px;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.18);
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.edp-stat--wide {
  grid-column: 1 / -1;
}

.edp-stat-k {
  margin: 0;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: rgba(148, 200, 255, 0.85);
  text-transform: uppercase;
}

.edp-stat-v {
  margin: 0;
  font-family: 'Press Start 2P', ui-monospace, monospace;
  font-size: 18px;
  line-height: 1.3;
  color: #f8fafc;
  font-variant-numeric: tabular-nums;
}

.edp-stat-v--text {
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.edp-stat-sub {
  margin: 0;
  font-size: 10px;
  line-height: 1.4;
  color: rgba(248, 250, 252, 0.55);
}

.edp-stat-bar {
  display: block;
  width: 100%;
  height: 6px;
  margin-top: 6px;
  border-radius: 999px;
  background: rgba(30, 41, 59, 0.95);
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.edp-stat-bar-fill {
  display: block;
  height: 100%;
  width: 0%;
  border-radius: 999px;
  background: linear-gradient(90deg, #cbd5e1 0%, #94a3b8 100%);
  transition: width 0.25s ease;
}

.edp-stat-bar-fill--busy {
  background: linear-gradient(90deg, #60a5fa 0%, #38bdf8 100%);
}

.edp-hint {
  margin: 0;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(56, 189, 248, 0.08);
  border: 1px solid rgba(56, 189, 248, 0.22);
  font-size: 11px;
  line-height: 1.5;
  color: #bfdbfe;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.edp-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.edp-section-h {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  color: #e2e8f0;
  letter-spacing: 0.04em;
}

.edp-section-empty {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
  color: rgba(248, 250, 252, 0.55);
}

.edp-flow {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 240px;
  overflow: auto;
  padding-right: 2px;
}

.edp-flow-step {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.62);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.edp-flow-idx {
  flex: 0 0 auto;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(56, 189, 248, 0.18);
  color: #7dd3fc;
  font-family: 'Press Start 2P', ui-monospace, monospace;
  font-size: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
}

.edp-flow-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.edp-flow-label {
  font-size: 12px;
  font-weight: 600;
  color: #e2e8f0;
  line-height: 1.4;
}

.edp-flow-detail {
  font-size: 11px;
  line-height: 1.45;
  color: rgba(248, 250, 252, 0.62);
}

.edp-db-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #2563eb;
  background: rgba(37, 99, 235, 0.18);
  color: #93c5fd;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease, color 0.15s ease;
}

.edp-db-btn:hover:not(:disabled) {
  background: rgba(37, 99, 235, 0.32);
  color: #fff;
  transform: translateY(-1px);
}

.edp-db-btn:focus {
  outline: none;
}

.edp-db-btn:focus-visible {
  outline: 2px solid #60a5fa;
  outline-offset: 2px;
}

.edp-db-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.edp-db-btn-arrow {
  font-size: 14px;
  transition: transform 0.15s ease;
}

.edp-db-btn:hover:not(:disabled) .edp-db-btn-arrow {
  transform: translateX(2px);
}
</style>
