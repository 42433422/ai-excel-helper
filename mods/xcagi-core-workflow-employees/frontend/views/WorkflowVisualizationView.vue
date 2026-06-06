<template>
  <div class="page-view wf-viz-page" id="view-workflow-visualization">
    <div class="page-content wf-viz-inner">
      <p v-if="loadState === 'loading'" class="wf-viz-loading">正在加载说明文档…</p>
      <p v-else-if="loadState === 'error'" class="wf-viz-error">{{ loadErrorMessage }}</p>
      <template v-else-if="docs">
        <header class="wf-viz-header">
          <div>
            <h2 class="wf-viz-title">{{ docs.pageTitle }}</h2>
            <p class="wf-viz-sub">{{ docs.pageSubtitle }}</p>
          </div>
          <router-link :to="{ name: 'chat' }" class="wf-viz-back">返回对话</router-link>
        </header>

        <section class="wf-viz-section wf-viz-overview" aria-labelledby="wf-overview-h">
          <h3 id="wf-overview-h" class="wf-viz-h3">总览</h3>
          <div class="wf-viz-pipeline" role="img" aria-label="工作流总览">
            <div class="wf-viz-node wf-viz-node--start">副窗 · 一键托管 / 龙虾托管</div>
            <span class="wf-viz-arrow" aria-hidden="true">→</span>
            <div class="wf-viz-node">员工开关（本机 localStorage）</div>
            <span class="wf-viz-arrow" aria-hidden="true">→</span>
            <div class="wf-viz-node wf-viz-node--branch">{{ docs.pipelineBranchLabel }}</div>
          </div>
          <div class="wf-viz-branch-grid">
            <div
              v-for="b in docs.branches"
              :key="b.id"
              class="wf-viz-branch-card"
              :class="'wf-viz-branch-card--' + branchKindClass(b.kind)"
            >
              <span class="wf-viz-kind-badge wf-viz-kind-badge--sm">{{ branchKindLabel(b.kind) }}</span>
              <div class="wf-viz-branch-title">{{ b.title }}</div>
              <div class="wf-viz-branch-triggers">{{ b.trigger }}</div>
            </div>
          </div>
          <p class="wf-viz-overview-mod">{{ docs.overviewNote }}</p>
        </section>

        <section
          v-for="flow in docs.flows"
          :key="flow.id"
          class="wf-viz-section"
          :class="'wf-viz-section--kind-' + flowKindClass(flow.kind)"
          :aria-labelledby="'wf-' + flow.id"
        >
          <div class="wf-viz-flow-head">
            <span class="wf-viz-kind-badge">{{ flowKindLabel(flow.kind) }}</span>
            <h3 :id="'wf-' + flow.id" class="wf-viz-h3 wf-viz-h3--inline">{{ flow.title }}</h3>
          </div>
          <p class="wf-viz-lead">{{ flow.lead }}</p>
          <ol class="wf-viz-steps">
            <li v-for="(step, i) in flow.steps" :key="i" class="wf-viz-step">
              <span class="wf-viz-step-index">{{ i + 1 }}</span>
              <div class="wf-viz-step-body">
                <div class="wf-viz-step-label">{{ step.label }}</div>
                <p v-if="step.detail" class="wf-viz-step-detail">{{ step.detail }}</p>
              </div>
            </li>
          </ol>
          <div v-if="flow.notes?.length" class="wf-viz-notes">
            <div class="wf-viz-notes-k">要点</div>
            <ul>
              <li v-for="(n, j) in flow.notes" :key="j">{{ n }}</li>
            </ul>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { WorkflowEmployeeDocsV1, WorkflowEmployeeKind } from '@/types/workflowEmployeeDocs'
import { applyWorkflowEmployeeDocsRuntime, getWorkflowEmployeeDocs } from '@/utils/workflowEmployeeDocs'
import { useWorkflowModsRuntimeContext } from '@/composables/useWorkflowModsRuntimeContext'

function branchKindLabel(kind?: WorkflowEmployeeKind): string {
  /** 与文档一致：固定 id 行，非 manifest 动态追加；勿写「Mod」以免与原版模式混淆 */
  return kind === 'fixed_extension' ? '固定扩展' : '内置 AI'
}

function branchKindClass(kind?: WorkflowEmployeeKind): string {
  return kind === 'fixed_extension' ? 'fixed' : 'core'
}

function flowKindLabel(kind?: WorkflowEmployeeKind): string {
  return branchKindLabel(kind)
}

function flowKindClass(kind?: WorkflowEmployeeKind): string {
  return branchKindClass(kind)
}

const loadedDocs = ref<WorkflowEmployeeDocsV1 | null>(null)
const loadState = ref<'loading' | 'ready' | 'error'>('loading')
const loadErrorMessage = ref('')

const { ctx: wfModsCtx } = useWorkflowModsRuntimeContext()

const docs = computed(() => {
  if (!loadedDocs.value) return null
  return applyWorkflowEmployeeDocsRuntime(loadedDocs.value, wfModsCtx.value)
})

onMounted(async () => {
  try {
    loadedDocs.value = await getWorkflowEmployeeDocs()
    loadState.value = 'ready'
  } catch (e) {
    loadState.value = 'error'
    loadErrorMessage.value = e instanceof Error ? e.message : '说明文档加载失败'
  }
})
</script>

<style scoped>
.wf-viz-page {
  --wf-accent: #1d4ed8;
  --wf-accent-soft: #dbeafe;
  --wf-border: #e5e7eb;
  --wf-text: #111827;
  --wf-muted: #6b7280;
  background: linear-gradient(165deg, #f8fafc 0%, #f1f5f9 40%, #fff 100%);
  min-height: 100%;
}

.wf-viz-inner {
  max-width: 920px;
  margin: 0 auto;
  padding: 20px 20px 48px;
}

.wf-viz-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.wf-viz-title {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 700;
  color: var(--wf-text);
  letter-spacing: -0.02em;
}

.wf-viz-sub {
  margin: 0;
  font-size: 13px;
  color: var(--wf-muted);
  line-height: 1.55;
  max-width: 52rem;
}

.wf-viz-back {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--wf-accent);
  text-decoration: none;
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid #93c5fd;
  background: #fff;
}
.wf-viz-back:hover {
  background: var(--wf-accent-soft);
}

.wf-viz-loading,
.wf-viz-error {
  margin: 0;
  padding: 24px 20px;
  font-size: 14px;
  color: var(--wf-muted);
}

.wf-viz-error {
  color: #b91c1c;
}

.wf-viz-section {
  margin-bottom: 32px;
  padding: 20px 22px;
  background: #fff;
  border: 1px solid var(--wf-border);
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.wf-viz-h3 {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 700;
  color: var(--wf-text);
}

.wf-viz-flow-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 10px;
}

.wf-viz-h3--inline {
  margin: 0;
  flex: 1;
  min-width: 12rem;
}

.wf-viz-kind-badge {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.03em;
  padding: 4px 10px;
  border-radius: 999px;
  text-transform: none;
}

.wf-viz-kind-badge--sm {
  font-size: 10px;
  padding: 2px 7px;
  margin-bottom: 6px;
  display: inline-block;
}

.wf-viz-branch-card--core .wf-viz-kind-badge {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #93c5fd;
}

.wf-viz-branch-card--fixed .wf-viz-kind-badge {
  background: #ffedd5;
  color: #9a3412;
  border: 1px solid #fdba74;
}

.wf-viz-flow-head .wf-viz-kind-badge {
  background: #dbeafe;
  color: #1e40af;
  border: 1px solid #93c5fd;
}

.wf-viz-section--kind-fixed .wf-viz-flow-head .wf-viz-kind-badge {
  background: #ffedd5;
  color: #9a3412;
  border-color: #fdba74;
}

.wf-viz-section--kind-fixed {
  border-left: 3px solid #f59e0b;
}

.wf-viz-overview-mod {
  margin: 16px 0 0;
  padding: 12px 14px;
  font-size: 12px;
  color: #5b21b6;
  line-height: 1.55;
  background: #f5f3ff;
  border: 1px solid #ddd6fe;
  border-radius: 10px;
}

.wf-viz-overview-mod code {
  font-size: 11px;
  padding: 1px 5px;
  border-radius: 4px;
  background: #ede9fe;
}

.wf-viz-lead {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--wf-muted);
  line-height: 1.55;
}

.wf-viz-pipeline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
  margin-bottom: 18px;
}

.wf-viz-node {
  font-size: 12px;
  font-weight: 600;
  padding: 10px 14px;
  border-radius: 10px;
  background: #f9fafb;
  border: 1px solid var(--wf-border);
  color: #374151;
}

.wf-viz-node--start {
  background: var(--wf-accent-soft);
  border-color: #93c5fd;
  color: #1e3a8a;
}

.wf-viz-node--branch {
  background: #fef3c7;
  border-color: #fcd34d;
  color: #92400e;
}

.wf-viz-arrow {
  color: var(--wf-muted);
  font-weight: 700;
}

.wf-viz-branch-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}

.wf-viz-branch-card {
  padding: 12px 14px;
  border-radius: 10px;
  background: #fafafa;
  border: 1px dashed #d1d5db;
}

.wf-viz-branch-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--wf-text);
  margin-bottom: 6px;
}

.wf-viz-branch-triggers {
  font-size: 11px;
  color: var(--wf-muted);
  line-height: 1.45;
}

.wf-viz-steps {
  list-style: none;
  margin: 0;
  padding: 0;
  position: relative;
}

.wf-viz-steps::before {
  content: '';
  position: absolute;
  left: 15px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: linear-gradient(180deg, #bfdbfe, #e5e7eb);
  border-radius: 1px;
}

.wf-viz-step {
  display: flex;
  gap: 14px;
  margin-bottom: 16px;
  position: relative;
}

.wf-viz-step:last-child {
  margin-bottom: 0;
}

.wf-viz-step-index {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--wf-accent);
  color: #fff;
  font-size: 13px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  box-shadow: 0 2px 6px rgba(29, 78, 216, 0.25);
}

.wf-viz-step-body {
  flex: 1;
  min-width: 0;
  padding-top: 2px;
}

.wf-viz-step-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--wf-text);
  margin-bottom: 4px;
}

.wf-viz-step-detail {
  margin: 0;
  font-size: 12px;
  color: var(--wf-muted);
  line-height: 1.5;
}

.wf-viz-notes {
  margin-top: 18px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.wf-viz-notes-k {
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #166534;
  margin-bottom: 8px;
}

.wf-viz-notes ul {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 12px;
  color: #14532d;
  line-height: 1.5;
}
</style>
