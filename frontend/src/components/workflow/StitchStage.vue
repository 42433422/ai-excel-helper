<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import type { YuangongStitchHotspot } from '@/constants/yuangongStitchHotspots'
import type { StitchEmployeePlacement } from '@/constants/yuangongStitchPlacements'
import { WORKFLOW_DOC_CORE_EMPLOYEE_IDS } from '@/constants/workflowEmployeeDocIds'
import {
  YUANGONG_CANVAS_H,
  YUANGONG_CANVAS_W,
  yuangongComposedBaseSizeFromCanvas,
} from '@/constants/yuangongComposedTrim'
import { YUANGONG_ENTRY_STITCH_PNG } from '@/constants/yuangongAssets'
import { useYuangongDeskIntrinsicSize } from '@/composables/useYuangongDeskIntrinsicSize'
import type { WorkflowEmployeeDeskRow } from '@/composables/useWorkflowEmployeeDesks'
import YuangongStation from '@/components/workflow/YuangongStation.vue'

/** 中键 = auxiliary button */
const MIDDLE_BUTTON = 1

/**
 * 四工位拼接：单格缩放。默认按「舞台视口宽度」反算，使条带 + 外框余量与可视区域接近（全图时 zoom≈100%），
 * 避免固定 3.35 导致画布过宽、长期靠缩小显示。
 */
const COMPOSED_SCALE_MIN = 0.55
const COMPOSED_SCALE_MAX = 5.5
const COMPOSED_SCALE_FALLBACK = 3.35
/** 与 computeFitZoom 内边距一致 */
const COMPOSED_FIT_PAD = 20
/** 与模板 `composedStripW + 48` 中 +48 一致（外框水平余量） */
const COMPOSED_OUTER_WIDTH_EXTRA = 48
/**
 * 默认让横条几乎铺满舞台宽（保留 ~6% 安全留白以避免轻微溢出 / clampPan 抖动），
 * 同时不超过视口高度的安全上限——避免全景空一大片黑底而像素只占左上角。
 */
const COMPOSED_TARGET_SHRINK = 0.94
/** 视口高度的最大占比上限：strip 高 = baseH × scale，超过此比例则按高反算 scale */
const COMPOSED_TARGET_HEIGHT_RATIO = 0.78
/** 裁边后逻辑格高约 58px，scale 后低于此像素则人物头部与上半身难以辨认 */
const COMPOSED_MIN_STATION_H_PX = 96
/** 相邻工位格水平重叠（px），盖住 contain 左右留白与亚像素竖缝，横条视觉上连成一体 */
const COMPOSED_CELL_OVERLAP_PX = 3
/** 与 `.stitch-composed` 的 border(3+3) + padding(18+14) 一致，用于固定高度与 fit 测量 */
const COMPOSED_ROOT_VERTICAL_CHROME = 3 + 3 + 18 + 14

/** desk.png 实际像素（naturalWidth/Height）；未加载前为默认 80×58 */
const { deskW, deskH } = useYuangongDeskIntrinsicSize()

/**
 * 横拼格宽/高的「逻辑画布」：素材若是高清大图（远大于像素精灵），natural 尺寸会把单格算成上千像素，
 * scale 被下限夹死后仍塞不进视口，表现为工位层空白或错位。此时回退设计稿 80×58 做布局，图片仍 object-fit 缩进格内。
 */
const COMPOSED_DESK_LAYOUT_MAX_DIM = 240

const composedLayoutDeskW = computed(() =>
  deskW.value > COMPOSED_DESK_LAYOUT_MAX_DIM || deskH.value > COMPOSED_DESK_LAYOUT_MAX_DIM
    ? YUANGONG_CANVAS_W
    : deskW.value
)
const composedLayoutDeskH = computed(() =>
  deskW.value > COMPOSED_DESK_LAYOUT_MAX_DIM || deskH.value > COMPOSED_DESK_LAYOUT_MAX_DIM
    ? YUANGONG_CANVAS_H
    : deskH.value
)

/** 舞台视口宽高（ResizeObserver），用于 composed 动态缩放 */
const viewportW = ref(0)
const viewportH = ref(0)
let viewportResizeObserver: ResizeObserver | null = null

const composedBaseSize = computed(() =>
  yuangongComposedBaseSizeFromCanvas(composedLayoutDeskW.value, composedLayoutDeskH.value)
)
const composedBaseW = computed(() => composedBaseSize.value.width)
const composedBaseH = computed(() => composedBaseSize.value.height)

const composedStationScale = computed(() => {
  const bw = composedBaseW.value
  const bh = composedBaseH.value
  const w = viewportW.value
  const h = viewportH.value
  if (w < 64 || bw < 1 || bh < 1) return COMPOSED_SCALE_FALLBACK
  const usableW = Math.max(0, w - COMPOSED_FIT_PAD * 2)
  const widthFit = (usableW - COMPOSED_OUTER_WIDTH_EXTRA) / (4 * bw)
  let raw = widthFit * COMPOSED_TARGET_SHRINK
  if (h > 64) {
    const usableH = Math.max(0, h - COMPOSED_FIT_PAD * 2 - COMPOSED_ROOT_VERTICAL_CHROME)
    const heightFit = (usableH * COMPOSED_TARGET_HEIGHT_RATIO) / bh
    if (heightFit > 0) raw = Math.min(raw, heightFit)
  }
  if (!Number.isFinite(raw) || raw <= 0) raw = COMPOSED_SCALE_FALLBACK
  raw = Math.min(COMPOSED_SCALE_MAX, Math.max(COMPOSED_SCALE_MIN, Number(raw.toFixed(3))))
  const minScaleForHead = COMPOSED_MIN_STATION_H_PX / bh
  raw = Math.max(raw, minScaleForHead)
  return Math.min(COMPOSED_SCALE_MAX, raw)
})

const composedCellW = computed(() => composedBaseW.value * composedStationScale.value)
const composedStripW = computed(() =>
  Math.max(1, composedCellW.value * 4 - 3 * COMPOSED_CELL_OVERLAP_PX)
)
const composedStationH = computed(() => composedBaseH.value * composedStationScale.value)
/** 底部名称条与字号随单格宽度变化，避免大图时 7px 字看不见 */
const composedLabelBandH = computed(() => {
  const w = composedCellW.value
  if (w < 8) return 26
  return Math.max(22, Math.min(56, Math.round(w * 0.12)))
})
const composedLabelFontPx = computed(() => {
  const w = composedCellW.value
  if (w < 8) return 9
  return Math.max(8, Math.min(16, Math.round(w * 0.038)))
})
const composedTrackH = computed(() => composedStationH.value + composedLabelBandH.value)
const composedOuterHeightPx = computed(() => composedTrackH.value + COMPOSED_ROOT_VERTICAL_CHROME)

const props = withDefaults(
  defineProps<{
    /** tutorial：底图 + 可选锚点叠层；composed：仅四工位横拼成大图 */
    mode?: 'tutorial' | 'composed'
    imageSrc: string
    selectedEmpId: string | null
    hotspots: YuangongStitchHotspot[]
    /** 用于热点按钮的无障碍名称解析 */
    resolveHotspotLabel?: (empId: string) => string
    /** 与右侧列表同源；tutorial 模式可在图上叠层，composed 模式用于四格 */
    desks?: WorkflowEmployeeDeskRow[]
    stationPlacements?: StitchEmployeePlacement[]
    resolveStationAriaLabel?: (empId: string) => string
    /**
     * composed：是否在条带下铺一张横向全景（默认 `stitch-tutorial.png`，可用 `imageSrc` 覆盖）。
     * 为 false 时仍用逐格 desk 叠在渐变底上。
     */
    useComposedPanorama?: boolean
  }>(),
  {
    mode: 'tutorial',
    desks: () => [],
    stationPlacements: () => [],
    useComposedPanorama: true,
  }
)

const emit = defineEmits<{
  (e: 'select', empId: string): void
  (e: 'image-error'): void
}>()

const viewportRef = ref<HTMLElement | null>(null)
const imgRef = ref<HTMLImageElement | null>(null)
const composedRootRef = ref<HTMLElement | null>(null)

const isComposed = computed(() => props.mode === 'composed')

type ComposedBackdropState = 'idle' | 'ready' | 'error'
const composedBackdropState = ref<ComposedBackdropState>('idle')

const composedPanoramaUrl = computed(() => {
  if (props.mode !== 'composed' || props.useComposedPanorama === false) return ''
  const trimmed = (props.imageSrc || '').trim()
  return trimmed || YUANGONG_ENTRY_STITCH_PNG
})

const showComposedBackdrop = computed(() => isComposed.value && Boolean(composedPanoramaUrl.value))

/** 全景底图加载成功后，空闲格不再叠整张 desk，避免与底图「双工位」 */
const composedIdleDeskVisible = computed(
  () => !showComposedBackdrop.value || composedBackdropState.value !== 'ready'
)

watch(composedPanoramaUrl, () => {
  composedBackdropState.value = 'idle'
})

watch(
  () => props.mode,
  (m) => {
    if (m !== 'composed') composedBackdropState.value = 'idle'
  }
)

const zoom = ref(1)
const minZoom = 0.25
const maxZoom = 2.5
const zoomStep = 0.25

const panX = ref(0)
const panY = ref(0)
const middlePanning = ref(false)
let lastPanClientX = 0
let lastPanClientY = 0
let panPointerId: number | null = null

const zoomPct = computed(() => Math.round(zoom.value * 100))

const zoomLayerStyle = computed(() => ({
  transform: `translate(${panX.value}px, ${panY.value}px) scale(${zoom.value})`,
  transformOrigin: '0 0',
}))

function contentPixelSize(): { w: number; h: number } | null {
  if (props.mode === 'composed') {
    const el = composedRootRef.value
    if (!el || el.offsetWidth < 4) return null
    const h = Math.max(el.offsetHeight, composedOuterHeightPx.value)
    return { w: el.offsetWidth, h }
  }
  const im = imgRef.value
  if (!im?.naturalWidth) return null
  return { w: im.naturalWidth, h: im.naturalHeight }
}

function clampPan(): void {
  const vp = viewportRef.value
  const size = contentPixelSize()
  if (!vp || !size) return
  const z = zoom.value
  const sw = size.w * z
  const sh = size.h * z
  const vw = vp.clientWidth
  const vh = vp.clientHeight
  const minPx = Math.min(0, vw - sw)
  const maxPx = Math.max(0, vw - sw)
  const minPy = Math.min(0, vh - sh)
  const maxPy = Math.max(0, vh - sh)
  panX.value = Math.min(maxPx, Math.max(minPx, panX.value))
  panY.value = Math.min(maxPy, Math.max(minPy, panY.value))
}

function onViewportPointerDown(e: PointerEvent) {
  if (e.button !== MIDDLE_BUTTON) return
  e.preventDefault()
  middlePanning.value = true
  panPointerId = e.pointerId
  lastPanClientX = e.clientX
  lastPanClientY = e.clientY
  viewportRef.value?.setPointerCapture(e.pointerId)
}

function onViewportPointerMove(e: PointerEvent) {
  if (!middlePanning.value || panPointerId !== e.pointerId) return
  e.preventDefault()
  const dx = e.clientX - lastPanClientX
  const dy = e.clientY - lastPanClientY
  lastPanClientX = e.clientX
  lastPanClientY = e.clientY
  panX.value += dx
  panY.value += dy
  clampPan()
}

function onViewportPointerUp(e: PointerEvent) {
  if (!middlePanning.value || panPointerId !== e.pointerId) return
  middlePanning.value = false
  panPointerId = null
  try {
    viewportRef.value?.releasePointerCapture(e.pointerId)
  } catch {
    /* ignore */
  }
}

function onViewportPointerCancel(e: PointerEvent) {
  if (!middlePanning.value || panPointerId !== e.pointerId) return
  middlePanning.value = false
  panPointerId = null
  try {
    viewportRef.value?.releasePointerCapture(e.pointerId)
  } catch {
    /* ignore */
  }
}

/** 禁止中键触发滚动条/自动滚动等默认行为 */
function onViewportMouseDown(e: MouseEvent) {
  if (e.button === MIDDLE_BUTTON) {
    e.preventDefault()
  }
}

function onViewportAuxClick(e: MouseEvent) {
  if (e.button === MIDDLE_BUTTON) {
    e.preventDefault()
  }
}

function computeFitZoom(): void {
  const vp = viewportRef.value
  if (!vp || vp.clientWidth < 48 || vp.clientHeight < 48) return
  const pad = 20
  const vw = Math.max(40, vp.clientWidth - pad * 2)
  const vh = Math.max(40, vp.clientHeight - pad * 2)

  let cw: number
  let ch: number
  if (props.mode === 'composed') {
    const el = composedRootRef.value
    if (!el || el.offsetWidth < 4) {
      void nextTick(() => scheduleFit())
      return
    }
    cw = el.offsetWidth
    ch = Math.max(el.offsetHeight, composedOuterHeightPx.value)
  } else {
    const im = imgRef.value
    if (!im?.naturalWidth) return
    cw = im.naturalWidth
    ch = im.naturalHeight
  }

  /**
   * composed: 允许填满视口的 fit zoom（最高 maxZoom），并把条带在视口中居中——
   * 以前夹在 ≤1 导致 strip 永远只占左上角一小块。tutorial: 仍夹在 ≤1，避免大底图被强行放大失真。
   */
  const upperBound = props.mode === 'composed' ? maxZoom : 1
  const z = Math.min(upperBound, vw / cw, vh / ch)
  const next = Math.max(minZoom, Math.min(maxZoom, Number(z.toFixed(4)) || minZoom))
  zoom.value = next

  const totalVw = vp.clientWidth
  const totalVh = vp.clientHeight
  const sw = cw * next
  const sh = ch * next
  panX.value = sw < totalVw ? Math.max(0, (totalVw - sw) / 2) : 0
  panY.value = sh < totalVh ? Math.max(0, (totalVh - sh) / 2) : 0
  void nextTick(() => clampPan())
}

function scheduleFit() {
  void nextTick(() => computeFitZoom())
}

function onComposedBackdropLoad() {
  composedBackdropState.value = 'ready'
  void nextTick(() => scheduleFit())
}

function onComposedBackdropError() {
  composedBackdropState.value = 'error'
  emit('image-error')
}

function zoomIn() {
  zoom.value = Math.min(maxZoom, Math.round((zoom.value + zoomStep) * 100) / 100)
  void nextTick(() => clampPan())
}

function zoomOut() {
  zoom.value = Math.max(minZoom, Math.round((zoom.value - zoomStep) * 100) / 100)
  void nextTick(() => clampPan())
}

function resetZoom() {
  computeFitZoom()
}

function onZoomInput(e: Event) {
  const v = Number((e.target as HTMLInputElement).value)
  if (!Number.isFinite(v)) return
  zoom.value = Math.min(maxZoom, Math.max(minZoom, v / 100))
  void nextTick(() => clampPan())
}

function onImgLoad() {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => scheduleFit())
  })
}

function updateViewportSize(): void {
  const el = viewportRef.value
  if (el) {
    viewportW.value = el.clientWidth
    viewportH.value = el.clientHeight
  }
}

/** 缓存图已就绪时（含磁盘缓存）补一次适配；composed 在布局后量宽 */
onMounted(() => {
  void nextTick(() => {
    updateViewportSize()
    const el = viewportRef.value
    if (el && typeof ResizeObserver !== 'undefined') {
      viewportResizeObserver = new ResizeObserver(() => {
        updateViewportSize()
        void nextTick(() => scheduleFit())
      })
      viewportResizeObserver.observe(el)
    }
  })
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (props.mode === 'composed') {
        scheduleFit()
      } else if (imgRef.value?.complete && imgRef.value.naturalWidth) {
        scheduleFit()
      }
    })
  })
})

onUnmounted(() => {
  viewportResizeObserver?.disconnect()
  viewportResizeObserver = null
})

function hotspotLabel(h: YuangongStitchHotspot): string {
  if (h.label) return h.label
  if (props.resolveHotspotLabel) return props.resolveHotspotLabel(h.empId)
  return `选择员工 ${h.empId}`
}

function hotspotStyle(h: YuangongStitchHotspot) {
  return {
    left: `${h.leftPct}%`,
    top: `${h.topPct}%`,
    width: `${h.widthPct}%`,
    height: `${h.heightPct}%`,
  }
}

const placedStations = computed(() => {
  const list: { placement: StitchEmployeePlacement; row: WorkflowEmployeeDeskRow }[] = []
  for (const placement of props.stationPlacements) {
    const row = props.desks.find((d) => d.empId === placement.empId)
    if (row) list.push({ placement, row })
  }
  return list
})

function placementStyle(p: StitchEmployeePlacement) {
  const s = p.scale ?? 4
  return {
    left: `${p.leftPct}%`,
    top: `${p.topPct}%`,
    transform: `translate(-50%, -100%) scale(${s})`,
    transformOrigin: '50% 100%',
  }
}

function stationBusy(row: WorkflowEmployeeDeskRow): boolean {
  if (!row.enabled) return false
  return row.snapshot?.visuallyBusy === true
}

function stationAriaLabel(empId: string, row: WorkflowEmployeeDeskRow): string {
  if (props.resolveStationAriaLabel) return props.resolveStationAriaLabel(empId)
  return `员工 ${row.shortName}`
}

const composedSlots = computed(() => {
  const ids = WORKFLOW_DOC_CORE_EMPLOYEE_IDS as unknown as string[]
  return ids.map((empId) => {
    const row = props.desks.find((d) => d.empId === empId)
    const r: WorkflowEmployeeDeskRow =
      row ??
      ({
        empId,
        panelTitle: `工作流 · ${empId}`,
        shortName: empId,
        enabled: false,
        snapshot: undefined,
      } as WorkflowEmployeeDeskRow)
    return { empId, row: r }
  })
})

/** 单格内工位层：用最终像素宽高铺满格宽，避免父级 transform: scale 与布局/子项百分比不一致 */
const composedStationWrapStyle = computed(() => ({
  height: `${composedStationH.value}px`,
}))

/** 换图后待 load 再适配全图 */
watch(
  () => props.imageSrc,
  () => {
    if (props.mode === 'composed') return
    void nextTick(() => {
      if (imgRef.value?.complete && imgRef.value.naturalWidth) {
        scheduleFit()
      }
    })
  }
)

watch(
  () => props.mode,
  () => {
    void nextTick(() => scheduleFit())
  }
)

watch(
  () => props.desks.map((d) => `${d.empId}:${d.enabled}:${d.snapshot?.visuallyBusy}`).join('|'),
  () => {
    if (props.mode === 'composed') {
      void nextTick(() => clampPan())
    }
  }
)

watch([deskW, deskH], () => {
  if (props.mode !== 'composed') return
  void nextTick(() => scheduleFit())
})

watch(composedStationScale, () => {
  if (props.mode !== 'composed') return
  void nextTick(() => scheduleFit())
})
</script>

<template>
  <div
    class="stitch-stage"
    role="region"
    :aria-label="
      isComposed
        ? '四工位拼接全景：由实时工位像素拼成；鼠标中键拖动平移，工具栏缩放；点击工位可选中员工'
        : '拼接图舞台：背景图与实时工位叠层；鼠标中键拖动平移，工具栏缩放；热点与工位可点选员工'
    "
  >
    <div class="stitch-stage-toolbar" role="toolbar" aria-label="缩放与中键平移说明">
      <button type="button" class="stitch-stage-btn" :disabled="zoom <= minZoom" @click="zoomOut">
        缩小
      </button>
      <label class="stitch-stage-zoom-label">
        <span class="stitch-stage-sr">缩放比例</span>
        <input
          class="stitch-stage-range"
          type="range"
          :min="minZoom * 100"
          :max="maxZoom * 100"
          :step="zoomStep * 100"
          :value="zoom * 100"
          @input="onZoomInput"
        />
        <span class="stitch-stage-zoom-readout" aria-hidden="true">{{ zoomPct }}%</span>
      </label>
      <button type="button" class="stitch-stage-btn" :disabled="zoom >= maxZoom" @click="zoomIn">
        放大
      </button>
      <button type="button" class="stitch-stage-btn stitch-stage-btn--ghost" title="缩放至可见整图" @click="resetZoom">
        全图
      </button>
      <span class="stitch-stage-hint" aria-hidden="true">中键拖移</span>
    </div>

    <div
      ref="viewportRef"
      class="stitch-stage-viewport"
      :class="{ 'stitch-stage-viewport--grabbing': middlePanning }"
      tabindex="0"
      @pointerdown="onViewportPointerDown"
      @pointermove="onViewportPointerMove"
      @pointerup="onViewportPointerUp"
      @pointercancel="onViewportPointerCancel"
      @mousedown="onViewportMouseDown"
      @auxclick="onViewportAuxClick"
    >
      <div class="stitch-stage-zoom-layer" :style="zoomLayerStyle">
        <div
          v-if="isComposed"
          ref="composedRootRef"
          class="stitch-composed"
          :style="{
            width: `${composedStripW + 48}px`,
            minHeight: `${composedOuterHeightPx}px`,
            height: `${composedOuterHeightPx}px`,
          }"
        >
          <div class="stitch-composed-strip" role="presentation">
            <div
              class="stitch-composed-track"
              :style="{
                width: `${composedStripW}px`,
                height: `${composedTrackH}px`,
                '--stitch-composed-label-font': `${composedLabelFontPx}px`,
              }"
            >
              <img
                v-if="showComposedBackdrop"
                :key="composedPanoramaUrl"
                class="stitch-composed-backdrop"
                :src="composedPanoramaUrl"
                alt=""
                decoding="async"
                draggable="false"
                @load="onComposedBackdropLoad"
                @error="onComposedBackdropError"
              />
              <div
                v-for="(slot, idx) in composedSlots"
                :key="'cmp-' + slot.empId"
                class="stitch-composed-cell"
                role="button"
                tabindex="0"
                :aria-label="stationAriaLabel(slot.empId, slot.row)"
                :aria-current="selectedEmpId === slot.empId ? 'true' : undefined"
                :style="{
                  left: `${idx * (composedCellW - COMPOSED_CELL_OVERLAP_PX)}px`,
                  width: `${composedCellW}px`,
                  height: `${composedTrackH}px`,
                  zIndex: selectedEmpId === slot.empId ? 8 : idx + 1,
                }"
                @click.stop="emit('select', slot.empId)"
                @keydown.enter.prevent="emit('select', slot.empId)"
              >
                <div
                  class="stitch-composed-station-wrap"
                  :class="{ 'stitch-composed-station-wrap--selected': selectedEmpId === slot.empId }"
                  :style="composedStationWrapStyle"
                >
                  <span class="stitch-composed-station-vis" aria-hidden="true">
                    <YuangongStation
                      pixel-layout="composed"
                      :composed-idle-desk-visible="composedIdleDeskVisible"
                      :enabled="slot.row.enabled"
                      :busy="stationBusy(slot.row)"
                      :ariaLabel="stationAriaLabel(slot.empId, slot.row)"
                    />
                  </span>
                </div>
                <p class="stitch-composed-label" :title="slot.row.panelTitle">{{ slot.row.shortName }}</p>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="stitch-stage-img-shell">
          <img
            ref="imgRef"
            class="stitch-stage-img"
            :src="imageSrc"
            alt=""
            decoding="async"
            draggable="false"
            @load="onImgLoad"
            @error="emit('image-error')"
          />
          <div
            v-for="{ placement, row } in placedStations"
            :key="'st-' + placement.empId"
            class="stitch-stage-station"
            :class="{ 'stitch-stage-station--selected': selectedEmpId === placement.empId }"
            :style="placementStyle(placement)"
            role="button"
            tabindex="0"
            :aria-label="stationAriaLabel(placement.empId, row)"
            :aria-current="selectedEmpId === placement.empId ? 'true' : undefined"
            @click.stop="emit('select', placement.empId)"
            @keydown.enter.prevent="emit('select', placement.empId)"
          >
            <span class="stitch-stage-station-vis" aria-hidden="true">
              <YuangongStation
                :enabled="row.enabled"
                :busy="stationBusy(row)"
                :ariaLabel="stationAriaLabel(placement.empId, row)"
              />
            </span>
          </div>
          <button
            v-for="h in hotspots"
            :key="h.empId"
            type="button"
            class="stitch-stage-hotspot"
            :class="{ 'stitch-stage-hotspot--selected': selectedEmpId === h.empId }"
            :style="hotspotStyle(h)"
            :aria-label="hotspotLabel(h)"
            :aria-pressed="selectedEmpId === h.empId"
            @click="emit('select', h.empId)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

.stitch-stage {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  flex: 1;
}

.stitch-stage-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-family: 'Press Start 2P', ui-monospace, monospace;
}

.stitch-stage-btn {
  padding: 8px 10px;
  border-radius: 0;
  border: 3px solid #64748b;
  box-shadow: inset 0 -3px 0 rgba(0, 0, 0, 0.35);
  background: #334155;
  color: #f1f5f9;
  font-size: 8px;
  line-height: 1.4;
  letter-spacing: 0.02em;
  cursor: pointer;
  image-rendering: pixelated;
}

.stitch-stage-btn:hover:not(:disabled) {
  background: #475569;
  color: #fff;
}

.stitch-stage-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.stitch-stage-btn--ghost {
  border-style: solid;
  border-color: #94a3b8;
}

.stitch-stage-zoom-label {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1 1 160px;
  min-width: 0;
  color: #cbd5e1;
  font-size: 7px;
  line-height: 1.5;
}

.stitch-stage-range {
  flex: 1;
  min-width: 80px;
  accent-color: #38bdf8;
}

.stitch-stage-zoom-readout {
  min-width: 3rem;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.stitch-stage-hint {
  margin-left: 4px;
  font-size: 6px;
  line-height: 1.5;
  color: #94a3b8;
  white-space: nowrap;
}

.stitch-stage-sr {
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

.stitch-stage-viewport {
  flex: 1;
  min-height: 200px;
  min-width: 0;
  overflow: hidden;
  border-radius: 0;
  border: 4px solid #1e293b;
  box-shadow: inset 0 0 0 2px #0f172a;
  background: #020617;
  cursor: grab;
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
}

.stitch-stage-viewport--grabbing {
  cursor: grabbing;
}

.stitch-stage-viewport:focus-visible {
  outline: 2px solid #38bdf8;
  outline-offset: 2px;
}

.stitch-stage-zoom-layer {
  display: inline-block;
  vertical-align: top;
}

.stitch-composed {
  box-sizing: border-box;
  /* 宽度由脚本 :style（composedStripW + padding）控制 */
  padding: 18px 24px 14px;
  background: #0b1120;
  border: 3px solid #334155;
  box-shadow: inset 0 0 0 2px #0f172a;
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 0;
}

.stitch-composed-strip {
  margin: 0;
  padding: 0;
}

/* 单块连续底板：四工位仅在上层绝对定位，视觉上一条整图 */
.stitch-composed-track {
  position: relative;
  margin: 0;
  padding: 0;
  overflow: visible;
  background: linear-gradient(180deg, #1e293b 0%, #0f172a 42%, #020617 100%);
  border: 2px solid #1e293b;
  box-shadow: inset 0 -3px 0 rgba(0, 0, 0, 0.35);
  image-rendering: pixelated;
  --stitch-composed-label-font: 9px;
}

.stitch-composed-backdrop {
  position: absolute;
  left: 0;
  top: 0;
  z-index: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center bottom;
  pointer-events: none;
  user-select: none;
  -webkit-user-drag: none;
  image-rendering: pixelated;
  image-rendering: crisp-edges;
}

.stitch-composed-cell {
  position: absolute;
  top: 0;
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  border: none;
  cursor: pointer;
  outline: none;
  background: transparent;
  overflow: visible;
}

.stitch-composed-cell:hover .stitch-composed-station-vis {
  filter: brightness(1.12);
}

.stitch-composed-cell:focus-visible {
  z-index: 2;
}

.stitch-composed-cell:focus-visible .stitch-composed-station-vis {
  box-shadow: 0 0 0 2px #facc15;
}

.stitch-composed-station-wrap--selected {
  z-index: 1;
}

.stitch-composed-station-wrap--selected .stitch-composed-station-vis {
  box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.95);
}

.stitch-composed-station-wrap {
  position: absolute;
  z-index: 0;
  left: 0;
  right: 0;
  top: 0;
  margin: 0;
  padding: 0;
  overflow: visible;
  box-sizing: border-box;
}

.stitch-composed-station-vis {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 1px;
}

.stitch-composed-station-vis :deep(.yuangong-stack) {
  pointer-events: none;
}

.stitch-composed-label {
  position: absolute;
  z-index: 3;
  left: 0;
  right: 0;
  bottom: 3px;
  margin: 0;
  padding: 2px 4px 1px;
  font-family: 'Press Start 2P', ui-monospace, monospace;
  font-size: var(--stitch-composed-label-font, 9px);
  line-height: 1.35;
  color: #e2e8f0;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  pointer-events: none;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.85);
  background: linear-gradient(180deg, transparent 0%, rgba(2, 6, 23, 0.72) 55%, rgba(2, 6, 23, 0.88) 100%);
}

.stitch-stage-img-shell {
  position: relative;
  display: inline-block;
  vertical-align: top;
  line-height: 0;
}

.stitch-stage-station {
  position: absolute;
  z-index: 2;
  pointer-events: auto;
  cursor: pointer;
  outline: none;
}

.stitch-stage-station:focus-visible {
  box-shadow: 0 0 0 3px rgba(250, 204, 21, 0.9);
}

.stitch-stage-station--selected {
  filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.85));
}

.stitch-stage-station :deep(.yuangong-stack) {
  pointer-events: none;
}

.stitch-stage-station-vis {
  display: block;
}

.stitch-stage-img {
  display: block;
  width: auto;
  height: auto;
  max-width: none;
  image-rendering: pixelated;
  image-rendering: crisp-edges;
}

.stitch-stage-hotspot {
  position: absolute;
  z-index: 4;
  margin: 0;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  box-sizing: border-box;
}

.stitch-stage-hotspot:hover {
  border-color: rgba(147, 197, 253, 0.55);
  background: rgba(147, 197, 253, 0.12);
}

.stitch-stage-hotspot:focus {
  outline: none;
}

.stitch-stage-hotspot:focus-visible {
  border-color: #fff;
  box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.9);
}

.stitch-stage-hotspot--selected {
  border-color: rgba(96, 165, 250, 0.95);
  background: rgba(59, 130, 246, 0.18);
}
</style>

