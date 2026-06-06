<template>
  <section class="kitten-chart-panel">
    <div class="chart-panel-head">
      <div>
        <div class="chart-title">图表分析</div>
        <div class="chart-subtitle">{{ rows.length }} 条样本 · {{ fieldProfiles.length }} 个字段</div>
      </div>
      <div class="chart-type-tabs">
        <button
          v-for="item in chartTypes"
          :key="item.value"
          type="button"
          :class="['chart-type-tab', { active: localConfig.type === item.value }]"
          @click="updateConfig({ type: item.value })"
        >
          {{ item.label }}
        </button>
      </div>
    </div>

    <div v-if="recommendations.length" class="recommendation-row">
      <button
        v-for="rec in recommendations"
        :key="rec.id"
        type="button"
        class="recommendation-chip"
        :title="rec.description"
        @click="emit('applyRecommendation', rec)"
      >
        {{ rec.label }}
      </button>
    </div>

    <div class="chart-controls">
      <label>
        <span>X / 分类</span>
        <select :value="localConfig.xField" @change="updateConfig({ xField: ($event.target as HTMLSelectElement).value })">
          <option value="">选择字段</option>
          <option v-for="field in fieldProfiles" :key="field.name" :value="field.name">
            {{ field.name }} · {{ fieldLabel(field.type) }}
          </option>
        </select>
      </label>
      <label>
        <span>Y / 数值</span>
        <select :value="localConfig.yField" @change="updateConfig({ yField: ($event.target as HTMLSelectElement).value })">
          <option value="">记录数</option>
          <option v-for="field in numericFields" :key="field.name" :value="field.name">
            {{ field.name }}
          </option>
        </select>
      </label>
      <label>
        <span>聚合</span>
        <select :value="localConfig.aggregate" @change="updateConfig({ aggregate: ($event.target as HTMLSelectElement).value as KittenChartAggregate })">
          <option value="count">计数</option>
          <option value="sum">求和</option>
          <option value="avg">平均</option>
          <option value="max">最大</option>
          <option value="min">最小</option>
        </select>
      </label>
      <label>
        <span>分组</span>
        <select :value="localConfig.groupField" @change="updateConfig({ groupField: ($event.target as HTMLSelectElement).value })">
          <option value="">不分组</option>
          <option v-for="field in categoryFields" :key="field.name" :value="field.name">
            {{ field.name }}
          </option>
        </select>
      </label>
    </div>

    <div v-if="!localConfig.xField" class="chart-empty">
      请选择一个 X / 分类字段，或点击上方推荐图表。
    </div>
    <div v-else ref="chartEl" class="chart-canvas" />
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart, ScatterChart } from 'echarts/charts'
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
  DatasetComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsCoreOption } from 'echarts/core'
import type {
  KittenChartAggregate,
  KittenChartConfig,
  KittenChartRecommendation,
  KittenChartType,
} from '@/composables/useKittenAnalyzer'
import type { KittenFieldProfile, KittenFieldType } from '@/utils/kittenDatasetParser'

echarts.use([BarChart, LineChart, PieChart, ScatterChart, GridComponent, LegendComponent, TooltipComponent, DatasetComponent, CanvasRenderer])

const props = defineProps<{
  rows: Record<string, unknown>[]
  fieldProfiles: KittenFieldProfile[]
  config: KittenChartConfig
  recommendations: KittenChartRecommendation[]
}>()

const emit = defineEmits<{
  updateConfig: [config: Partial<KittenChartConfig>]
  applyRecommendation: [recommendation: KittenChartRecommendation]
}>()

const chartEl = ref<HTMLDivElement | null>(null)
let chart: echarts.ECharts | null = null

const chartTypes: Array<{ value: KittenChartType; label: string }> = [
  { value: 'bar', label: '柱状' },
  { value: 'line', label: '折线' },
  { value: 'area', label: '面积' },
  { value: 'pie', label: '饼图' },
  { value: 'scatter', label: '散点' },
]

const localConfig = computed(() => props.config)
const numericFields = computed(() => props.fieldProfiles.filter((field) => field.type === 'number'))
const categoryFields = computed(() => props.fieldProfiles.filter((field) => field.type === 'category' || field.type === 'text'))

function fieldLabel(type: KittenFieldType) {
  return type === 'number' ? '数值' : type === 'date' ? '日期' : type === 'category' ? '分类' : '文本'
}

function updateConfig(next: Partial<KittenChartConfig>) {
  emit('updateConfig', next)
}

function toFiniteNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value !== 'string') return null
  const cleaned = value.replace(/[,，\s¥￥%]/g, '').trim()
  if (!cleaned) return null
  const n = Number(cleaned)
  return Number.isFinite(n) ? n : null
}

function categoryKey(value: unknown): string {
  if (value === null || value === undefined || String(value).trim() === '') return '空值'
  return String(value)
}

function aggregateValues(values: number[], aggregate: KittenChartAggregate): number {
  if (aggregate === 'count') return values.length
  if (!values.length) return 0
  if (aggregate === 'sum') return values.reduce((sum, value) => sum + value, 0)
  if (aggregate === 'avg') return values.reduce((sum, value) => sum + value, 0) / values.length
  if (aggregate === 'max') return Math.max(...values)
  return Math.min(...values)
}

function buildGroupedData() {
  const cfg = props.config
  const bucketMap = new Map<string, { label: string; group: string; values: number[] }>()
  for (const row of props.rows) {
    const label = categoryKey(row[cfg.xField])
    const group = cfg.groupField ? categoryKey(row[cfg.groupField]) : '数据'
    const rawValue = cfg.aggregate === 'count' || !cfg.yField ? 1 : toFiniteNumber(row[cfg.yField])
    if (rawValue === null) continue
    const key = `${label}\u0000${group}`
    const bucket = bucketMap.get(key) || { label, group, values: [] }
    bucket.values.push(rawValue)
    bucketMap.set(key, bucket)
  }
  return Array.from(bucketMap.values())
    .map((bucket) => ({
      label: bucket.label,
      group: bucket.group,
      value: aggregateValues(bucket.values, cfg.yField ? cfg.aggregate : 'count')
    }))
    .sort((a, b) => String(a.label).localeCompare(String(b.label), 'zh-CN'))
    .slice(0, 80)
}

function buildScatterData() {
  const cfg = props.config
  if (!cfg.xField || !cfg.yField) return []
  return props.rows
    .map((row) => [toFiniteNumber(row[cfg.xField]), toFiniteNumber(row[cfg.yField])])
    .filter((pair): pair is [number, number] => pair[0] !== null && pair[1] !== null)
    .slice(0, 500)
}

function buildOption(): EChartsCoreOption {
  const cfg = props.config
  if (!cfg.xField) return {}
  if (cfg.type === 'scatter') {
    return {
      tooltip: { trigger: 'item' },
      grid: { left: 40, right: 20, top: 28, bottom: 42 },
      xAxis: { type: 'value', name: cfg.xField },
      yAxis: { type: 'value', name: cfg.yField },
      series: [{ type: 'scatter', data: buildScatterData(), symbolSize: 8 }]
    }
  }

  const rows = buildGroupedData()
  const labels = Array.from(new Set(rows.map((row) => row.label)))
  const groups = Array.from(new Set(rows.map((row) => row.group)))
  if (cfg.type === 'pie') {
    return {
      tooltip: { trigger: 'item' },
      legend: { top: 0, type: 'scroll' },
      series: [
        {
          type: 'pie',
          radius: ['35%', '68%'],
          top: 28,
          data: labels.map((label) => ({
            name: label,
            value: rows.filter((row) => row.label === label).reduce((sum, row) => sum + row.value, 0)
          }))
        }
      ]
    }
  }

  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, type: 'scroll' },
    grid: { left: 42, right: 20, top: 42, bottom: 52 },
    xAxis: { type: 'category', data: labels, axisLabel: { rotate: labels.length > 8 ? 35 : 0 } },
    yAxis: { type: 'value' },
    series: groups.map((group) => ({
      name: group,
      type: cfg.type === 'bar' ? 'bar' : 'line',
      areaStyle: cfg.type === 'area' ? {} : undefined,
      smooth: cfg.type !== 'bar',
      data: labels.map((label) => rows.find((row) => row.label === label && row.group === group)?.value ?? 0)
    }))
  }
}

function renderChart() {
  if (!chartEl.value || !props.config.xField) return
  if (!chart) chart = echarts.init(chartEl.value)
  chart.setOption(buildOption(), true)
  chart.resize()
}

function onResize() {
  chart?.resize()
}

watch(
  () => [props.rows, props.fieldProfiles, props.config],
  () => nextTick(renderChart),
  { deep: true }
)

onMounted(() => {
  nextTick(renderChart)
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.kitten-chart-panel {
  margin: 0 16px 16px;
  padding: 14px;
  border: 1px solid #dbeafe;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}
.chart-panel-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}
.chart-title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}
.chart-subtitle {
  margin-top: 2px;
  font-size: 12px;
  color: #64748b;
}
.chart-type-tabs,
.recommendation-row,
.chart-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chart-type-tab,
.recommendation-chip {
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
  padding: 5px 10px;
  cursor: pointer;
}
.chart-type-tab.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.recommendation-row {
  margin-bottom: 12px;
}
.recommendation-chip {
  background: #f8fafc;
  border-color: #e2e8f0;
  color: #334155;
}
.chart-controls {
  margin-bottom: 12px;
}
.chart-controls label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 140px;
  flex: 1;
  font-size: 12px;
  color: #475569;
}
.chart-controls select {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 7px 8px;
  font-size: 12px;
  background: #fff;
  color: #0f172a;
}
.chart-canvas {
  width: 100%;
  height: 320px;
}
.chart-empty {
  padding: 36px 12px;
  border-radius: 12px;
  background: #f8fafc;
  color: #64748b;
  text-align: center;
  font-size: 13px;
}
</style>
