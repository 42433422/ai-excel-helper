<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useWorkflowAiEmployeesStore } from '@/stores/workflowAiEmployees'
import {
  formatWorkDurationShort,
  totalWorkMs,
  useNowMsTicker,
  useWorkflowEmployeeDesks,
  type WorkflowEmployeeDeskRow,
} from '@/composables/useWorkflowEmployeeDesks'
import YuangongStation from '@/components/workflow/YuangongStation.vue'
import EmployeeDetailPanel from '@/components/workflow/EmployeeDetailPanel.vue'
import {
  YUANGONG_ENTRY_STITCH_PNG,
  YUANGONG_ENTRY_WORKFLOW_PNG,
  YUANGONG_ENTRY_WORKFLOW_SVG,
} from '@/constants/yuangongAssets'

const ENTRY_BG_STITCH = YUANGONG_ENTRY_STITCH_PNG
const ENTRY_BG_WORKFLOW_PNG = YUANGONG_ENTRY_WORKFLOW_PNG
const ENTRY_BG_WORKFLOW_SVG = YUANGONG_ENTRY_WORKFLOW_SVG

const wfEmp = useWorkflowAiEmployeesStore()
const { desks, onDutyDesks, statusLine, ariaLabel, isBusy } = useWorkflowEmployeeDesks()
const nowMs = useNowMsTicker(30000)

const selectedEmpId = ref<string | null>(null)

watch(
  () => onDutyDesks.value.map((d) => d.empId).join('\0'),
  () => {
    const list = onDutyDesks.value
    if (!list.length) {
      selectedEmpId.value = null
      return
    }
    const cur = selectedEmpId.value
    if (!cur || !list.some((d) => d.empId === cur)) {
      selectedEmpId.value = list[0].empId
    }
  },
  { immediate: true }
)

const selectedRow = computed<WorkflowEmployeeDeskRow | null>(() => {
  const id = selectedEmpId.value
  if (!id) return null
  return onDutyDesks.value.find((d) => d.empId === id) ?? null
})

function selectDesk(empId: string) {
  selectedEmpId.value = empId
}

const entryBgUrl = ref(ENTRY_BG_STITCH)

function onEntryBgError() {
  if (entryBgUrl.value === ENTRY_BG_STITCH) {
    entryBgUrl.value = ENTRY_BG_WORKFLOW_PNG
  } else if (entryBgUrl.value === ENTRY_BG_WORKFLOW_PNG) {
    entryBgUrl.value = ENTRY_BG_WORKFLOW_SVG
  }
}

const totalCount = computed(() => desks.value.length)
const enabledCount = computed(() => desks.value.filter((d) => d.enabled).length)
const busyCount = computed(() => desks.value.filter((d) => isBusy(d)).length)
const idleEnabledCount = computed(() => Math.max(0, enabledCount.value - busyCount.value))

function progressPct(row: WorkflowEmployeeDeskRow): number {
  if (!row.enabled) return 0
  const p = row.snapshot?.progressPct
  if (typeof p !== 'number' || !Number.isFinite(p)) return 0
  return Math.max(0, Math.min(100, p))
}

function progressWidth(row: WorkflowEmployeeDeskRow): string {
  return `${progressPct(row)}%`
}

function toggleDesk(empId: string, ev: Event) {
  ev.stopPropagation()
  wfEmp.toggle(empId)
}

function processedShort(row: WorkflowEmployeeDeskRow): string {
  const n = row.session?.processedCount ?? 0
  if (n <= 999) return String(n)
  if (n <= 9_999) return `${(n / 1000).toFixed(1)}k`
  return `${Math.floor(n / 1000)}k`
}

function workShort(row: WorkflowEmployeeDeskRow): string {
  if (!row.enabled) return '—'
  return formatWorkDurationShort(totalWorkMs(row.session, nowMs.value))
}
</script>

<template>
  <section class="ews" aria-labelledby="ews-heading">
    <h3 id="ews-heading" class="ews-sr-only">员工工作流：入口与工位实况</h3>

    <router-link
      :to="{ name: 'workflow-employee-stitch-full' }"
      class="ews-entry"
      role="link"
      aria-label="进入员工工作流全景页面"
    >
      <div class="ews-entry-bg" aria-hidden="true">
        <img
          class="ews-entry-bg-img"
          :src="entryBgUrl"
          alt=""
          decoding="async"
          fetchpriority="low"
          @error="onEntryBgError"
        />
        <div class="ews-entry-vignette" />
      </div>
      <div class="ews-entry-ui">
        <p class="ews-entry-kicker">工作流员工 · 入口</p>
        <p class="ews-entry-lead">
          像素工位入口；点击进入横向拼接全景，与右侧开关、任务面板快照同步。
        </p>
        <div class="ews-entry-cta" aria-hidden="true">
          <span class="ews-entry-cta-arrow">→</span>
          <span class="ews-entry-cta-text">进入工作流全景</span>
        </div>
      </div>
    </router-link>

    <div class="ews-stats" role="list" aria-label="员工工位概要">
      <div class="ews-stat" role="listitem">
        <p class="ews-stat-k">总工位</p>
        <p class="ews-stat-v">{{ totalCount }}</p>
        <p class="ews-stat-sub">仅已安装工作流员工 Mod</p>
      </div>
      <div class="ews-stat" role="listitem">
        <p class="ews-stat-k">已托管</p>
        <p class="ews-stat-v ews-stat-v--ok">{{ enabledCount }}</p>
        <p class="ews-stat-sub">副窗「一键托管」开</p>
      </div>
      <div class="ews-stat" role="listitem">
        <p class="ews-stat-k">工作中</p>
        <p class="ews-stat-v ews-stat-v--busy">{{ busyCount }}</p>
        <p class="ews-stat-sub">最近活跃 · 视觉态忙</p>
      </div>
      <div class="ews-stat" role="listitem">
        <p class="ews-stat-k">待命</p>
        <p class="ews-stat-v ews-stat-v--idle">{{ idleEnabledCount }}</p>
        <p class="ews-stat-sub">已托管但暂无忙态</p>
      </div>
    </div>

    <div
      id="ews-workflow-monitor"
      class="ews-monitor"
      role="region"
      aria-labelledby="ews-monitor-h"
      tabindex="-1"
    >
      <div class="ews-monitor-head">
        <div>
          <h4 id="ews-monitor-h" class="ews-monitor-title">工位实况</h4>
          <p class="ews-monitor-desc">
            实时工位状态来自副窗「一键托管」开关与任务面板快照；点击工位卡片可在右侧详情查看像素特写。
          </p>
        </div>
      </div>

      <div class="ews-layout">
        <div class="ews-grid" role="list" aria-label="工位卡片列表">
          <div
            v-for="row in onDutyDesks"
            :key="row.empId"
            class="ews-desk"
            :class="{
              'ews-desk--off': !row.enabled,
              'ews-desk--busy': isBusy(row),
              'ews-desk--selected': row.empId === selectedEmpId,
            }"
            role="listitem"
          >
            <button
              type="button"
              class="ews-desk-hit"
              :aria-current="row.empId === selectedEmpId ? 'true' : undefined"
              :aria-label="ariaLabel(row)"
              @click="selectDesk(row.empId)"
            >
              <span class="ews-desk-art" aria-hidden="true">
                <YuangongStation
                  :enabled="row.enabled"
                  :busy="isBusy(row)"
                  :ariaLabel="ariaLabel(row)"
                />
                <span
                  v-if="row.enabled"
                  class="ews-desk-rpg"
                  :class="{ 'ews-desk-rpg--busy': isBusy(row) }"
                  aria-hidden="true"
                >
                  <span class="ews-desk-rpg-row">
                    <span class="ews-desk-rpg-icon" aria-hidden="true">📄</span>
                    <span class="ews-desk-rpg-num">{{ processedShort(row) }}</span>
                  </span>
                  <span class="ews-desk-rpg-row">
                    <span class="ews-desk-rpg-icon" aria-hidden="true">⏱</span>
                    <span class="ews-desk-rpg-num">{{ workShort(row) }}</span>
                  </span>
                </span>
                <span
                  v-if="isBusy(row)"
                  class="ews-desk-pill ews-desk-pill--busy"
                >忙</span>
                <span
                  v-else-if="row.enabled"
                  class="ews-desk-pill ews-desk-pill--idle"
                >待命</span>
                <span v-else class="ews-desk-pill ews-desk-pill--off">未启</span>
              </span>

              <span class="ews-desk-meta">
                <span class="ews-desk-name" :title="row.panelTitle">{{ row.shortName }}</span>
                <span class="ews-desk-status">{{ statusLine(row) }}</span>
                <span class="ews-desk-progress" aria-hidden="true">
                  <span
                    class="ews-desk-progress-bar"
                    :class="{ 'ews-desk-progress-bar--busy': isBusy(row) }"
                    :style="{ width: progressWidth(row) }"
                  />
                </span>
              </span>
            </button>

            <button
              type="button"
              class="ews-desk-toggle"
              :class="{ 'ews-desk-toggle--on': row.enabled }"
              role="switch"
              :aria-checked="row.enabled"
              :aria-label="(row.enabled ? '关闭' : '开启') + '副窗托管：' + row.shortName"
              @click="toggleDesk(row.empId, $event)"
            >
              <span class="ews-desk-toggle-track" aria-hidden="true">
                <span class="ews-desk-toggle-thumb" />
              </span>
              <span class="ews-desk-toggle-label">{{ row.enabled ? '已开' : '已关' }}</span>
            </button>
          </div>
        </div>

        <EmployeeDetailPanel :row="selectedRow" />
      </div>
    </div>
  </section>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

.ews-sr-only {
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

.ews {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-top: 0;
}

/* —— 入口横幅 —— */
.ews-entry {
  position: relative;
  display: block;
  border-radius: 12px;
  overflow: hidden;
  min-height: 180px;
  border: 1px solid #e5e7eb;
  background: #0f172a;
  text-decoration: none;
  color: inherit;
  isolation: isolate;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.ews-entry:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.18);
}

.ews-entry:focus {
  outline: none;
}

.ews-entry:focus-visible {
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.45);
}

.ews-entry-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.ews-entry-bg-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center bottom;
  image-rendering: pixelated;
  image-rendering: crisp-edges;
  display: block;
}

.ews-entry-vignette {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(90deg, rgba(15, 23, 42, 0.78) 0%, rgba(15, 23, 42, 0.32) 45%, rgba(15, 23, 42, 0.05) 100%),
    linear-gradient(180deg, rgba(15, 23, 42, 0.05) 0%, rgba(15, 23, 42, 0.55) 100%);
}

.ews-entry-ui {
  position: relative;
  z-index: 1;
  min-height: 180px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 10px;
  padding: 20px 24px;
  max-width: 32rem;
}

.ews-entry-kicker {
  margin: 0;
  font-family: 'Press Start 2P', ui-monospace, monospace;
  font-size: 10px;
  line-height: 1.5;
  letter-spacing: 0.08em;
  color: #93c5fd;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.55);
}

.ews-entry-lead {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.92);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.45);
}

.ews-entry-cta {
  margin-top: 4px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.92);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.35);
}

.ews-entry-cta-arrow {
  font-size: 14px;
  transition: transform 0.2s ease;
}

.ews-entry:hover .ews-entry-cta-arrow {
  transform: translateX(3px);
}

/* —— 概要数据条 —— */
.ews-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}

.ews-stat {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ews-stat-k {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  letter-spacing: 0.04em;
}

.ews-stat-v {
  margin: 0;
  font-family: 'Press Start 2P', ui-monospace, monospace;
  font-size: 22px;
  line-height: 1.3;
  color: #111827;
  font-variant-numeric: tabular-nums;
}

.ews-stat-v--ok {
  color: #059669;
}

.ews-stat-v--busy {
  color: #2563eb;
}

.ews-stat-v--idle {
  color: #7c3aed;
}

.ews-stat-sub {
  margin: 0;
  font-size: 11px;
  line-height: 1.45;
  color: #9ca3af;
}

/* —— 工位实况 —— */
.ews-monitor {
  padding: 14px 14px 16px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: linear-gradient(180deg, #f9fafb 0%, #fff 50%);
  outline: none;
}

.ews-monitor-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.ews-monitor-title {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 700;
  color: #111827;
}

.ews-monitor-desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.55;
  color: #6b7280;
  max-width: 56rem;
}

.ews-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 280px);
  gap: 14px;
  align-items: start;
}

@media (max-width: 880px) {
  .ews-layout {
    grid-template-columns: 1fr;
  }
}

.ews-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.ews-desk {
  position: relative;
  display: flex;
  flex-direction: column;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  overflow: hidden;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}

.ews-desk:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.1);
  border-color: #cbd5e1;
}

.ews-desk--off {
  background: #f9fafb;
}

.ews-desk--off .ews-desk-art {
  filter: grayscale(0.35);
  opacity: 0.85;
}

.ews-desk--busy {
  border-color: #93c5fd;
  background: linear-gradient(180deg, #f5faff 0%, #ffffff 60%);
}

.ews-desk--selected {
  border-color: #2563eb;
  box-shadow: 0 0 0 1px #93c5fd inset, 0 8px 24px rgba(37, 99, 235, 0.18);
}

.ews-desk-hit {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  padding: 10px 12px 10px;
  margin: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  text-align: left;
  font: inherit;
  color: inherit;
}

.ews-desk-hit:focus {
  outline: none;
}

.ews-desk-hit:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: -2px;
  border-radius: 10px;
}

.ews-desk-art {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 3;
  border-radius: 10px;
  overflow: hidden;
  background:
    radial-gradient(ellipse at 50% 90%, rgba(37, 99, 235, 0.08) 0%, transparent 65%),
    linear-gradient(180deg, #eef2ff 0%, #ffffff 75%);
  display: block;
  border: 1px solid #e5e7eb;
}

.ews-desk-art :deep(.yuangong-stack) {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.ews-desk-art :deep(.yuangong-desk) {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center bottom;
  max-width: none;
  max-height: none;
}

.ews-desk-art :deep(.yuangong-staff) {
  position: absolute;
  inset: 0;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center bottom;
  max-width: none;
  max-height: none;
}

/* —— RPG 风格量化数据：员工头顶悬浮的「已处理 / 在岗工时」 —— */
.ews-desk-rpg {
  position: absolute;
  top: 6px;
  left: 6px;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 6px;
  border-radius: 4px;
  background: rgba(11, 17, 32, 0.78);
  box-shadow: inset 0 0 0 1px rgba(56, 189, 248, 0.45), 0 1px 0 rgba(0, 0, 0, 0.45);
  color: #f1f5f9;
  font-family: 'Press Start 2P', ui-monospace, monospace;
  font-size: 8px;
  line-height: 1.3;
  letter-spacing: 0.03em;
  pointer-events: none;
  image-rendering: pixelated;
}

.ews-desk-rpg--busy {
  box-shadow:
    inset 0 0 0 1px rgba(96, 165, 250, 0.85),
    0 0 0 2px rgba(96, 165, 250, 0.18),
    0 1px 0 rgba(0, 0, 0, 0.45);
}

.ews-desk-rpg-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.ews-desk-rpg-icon {
  font-size: 10px;
  line-height: 1;
}

.ews-desk-rpg-num {
  color: #7dd3fc;
  font-variant-numeric: tabular-nums;
}

.ews-desk-pill {
  position: absolute;
  top: 6px;
  right: 6px;
  z-index: 2;
  padding: 3px 7px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #fff;
  background: rgba(15, 23, 42, 0.55);
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.4);
}

.ews-desk-pill--busy {
  background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%);
}

.ews-desk-pill--idle {
  background: linear-gradient(180deg, #7c3aed 0%, #6d28d9 100%);
}

.ews-desk-pill--off {
  background: rgba(107, 114, 128, 0.85);
}

.ews-desk-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.ews-desk-name {
  display: block;
  font-size: 14px;
  font-weight: 700;
  color: #111827;
  letter-spacing: 0.02em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ews-desk-status {
  display: -webkit-box;
  font-size: 12px;
  line-height: 1.45;
  color: #6b7280;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 2.9em;
}

.ews-desk-progress {
  display: block;
  width: 100%;
  height: 5px;
  border-radius: 999px;
  background: #e5e7eb;
  overflow: hidden;
  margin-top: 2px;
}

.ews-desk-progress-bar {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #cbd5e1 0%, #94a3b8 100%);
  transition: width 0.25s ease;
}

.ews-desk-progress-bar--busy {
  background: linear-gradient(90deg, #60a5fa 0%, #2563eb 100%);
}

.ews-desk-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  align-self: flex-start;
  margin: 0 12px 12px;
  padding: 4px 10px 4px 4px;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #f9fafb;
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  cursor: pointer;
  user-select: none;
  text-align: left;
}

.ews-desk-toggle:focus {
  outline: none;
}

.ews-desk-toggle:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}

.ews-desk-toggle--on {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #1d4ed8;
}

.ews-desk-toggle-track {
  position: relative;
  width: 26px;
  height: 14px;
  border-radius: 999px;
  background: #cbd5e1;
  display: inline-block;
  transition: background 0.2s ease;
}

.ews-desk-toggle--on .ews-desk-toggle-track {
  background: #2563eb;
}

.ews-desk-toggle-thumb {
  position: absolute;
  top: 1px;
  left: 1px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
  transition: transform 0.2s ease;
}

.ews-desk-toggle--on .ews-desk-toggle-thumb {
  transform: translateX(12px);
}

.ews-desk-toggle-label {
  font-variant-numeric: tabular-nums;
}

/* —— 右侧特写卡片由 <EmployeeDetailPanel> 统一负责，自带样式 —— */
</style>
