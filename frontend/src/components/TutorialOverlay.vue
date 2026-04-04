<template>
  <div v-if="tutorialStore.isActive && currentStep && rect" class="tutorial-overlay-root">
    <div class="tutorial-exit-wrap" data-tutorial-overlay="true">
      <button type="button" class="tutorial-exit-btn" @click="tutorialStore.exitTutorial">退出教程</button>
    </div>

    <div class="tutorial-spotlight" :style="spotlightStyle"></div>

    <div class="tutorial-card" :style="cardStyle" data-tutorial-overlay="true">
      <div class="tutorial-progress">
        <template v-if="trackLabel">{{ trackLabel }} · </template>
        步骤 {{ tutorialStore.currentStepIndex + 1 }} / {{ tutorialStore.steps.length }}
      </div>
      <div class="tutorial-title">{{ currentStep.title }}</div>
      <p class="tutorial-desc">{{ currentStep.description }}</p>
      <p class="tutorial-test">
        功能测试：通过 {{ tutorialStore.testSummary.passed }} / {{ tutorialStore.testSummary.total }}
        <span v-if="tutorialStore.testSummary.skipped > 0">，跳过 {{ tutorialStore.testSummary.skipped }}</span>
      </p>
      <p v-if="tutorialStore.proBasicFallbackNotice" class="tutorial-tip tutorial-fallback-notice">
        {{ tutorialStore.proBasicFallbackNotice }}
      </p>
      <p v-if="tutorialStore.blockedTip" class="tutorial-tip">{{ tutorialStore.blockedTip }}</p>

      <div class="tutorial-actions" data-tutorial-overlay="true">
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          :disabled="!tutorialStore.hasPrev"
          @click.stop="tutorialStore.prevStep"
        >
          上一步
        </button>
        <button
          type="button"
          class="btn btn-secondary btn-sm"
          @click.stop="tutorialStore.exitTutorial"
        >
          跳过
        </button>
        <button
          type="button"
          class="btn btn-primary btn-sm tutorial-primary-next"
          :title="primaryNextTitle"
          @click.stop="tutorialStore.nextStep"
        >
          {{ tutorialStore.isLastStep ? '完成' : '下一步' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getTutorialTtsWarmupTexts, useTutorialStore } from '@/stores/tutorial'

const tutorialStore = useTutorialStore()
const router = useRouter()

const trackLabel = computed(() => {
  const t = tutorialStore.currentTrack
  if (t === 'advanced') return '进阶教程'
  if (t === 'basic') return '基础教程'
  return ''
})
let wasActive = false
const ttsAudio = ref(null)
let ttsSeq = 0
const ttsCache = new Map()
const ttsInflight = new Map()
const TTS_CACHE_MAX = 80

/** 教程预热若同时发起几十个 /api/tts，会占满浏览器对同域并发连接（通常约 6），产品列表等请求只能排队 →「教程里点半天才出副窗」 */
const TTS_PREFETCH_MAX_CONCURRENT = 2
let ttsPrefetchSlots = 0
const ttsPrefetchPending = []

const clearTtsPrefetchPending = () => {
  cancelPrefetchIdleDrain()
  ttsPrefetchPending.length = 0
}

/** 首次入队不立刻抢网络，等浏览器空闲再 drain，避免与产品列表等用户关键请求并发争连接 */
let ttsPrefetchDrainIdleHandle = null
let ttsPrefetchDrainIdleScheduled = false

const schedulePrefetchDrainWhenIdle = () => {
  if (ttsPrefetchDrainIdleScheduled) return
  ttsPrefetchDrainIdleScheduled = true
  const run = () => {
    ttsPrefetchDrainIdleScheduled = false
    ttsPrefetchDrainIdleHandle = null
    drainTtsPrefetchQueue()
  }
  if (typeof requestIdleCallback === 'function') {
    ttsPrefetchDrainIdleHandle = requestIdleCallback(run, { timeout: 900 })
  } else {
    ttsPrefetchDrainIdleHandle = window.setTimeout(run, 0)
  }
}

const cancelPrefetchIdleDrain = () => {
  if (ttsPrefetchDrainIdleHandle != null) {
    if (typeof cancelIdleCallback === 'function' && typeof requestIdleCallback === 'function') {
      cancelIdleCallback(ttsPrefetchDrainIdleHandle)
    } else {
      window.clearTimeout(ttsPrefetchDrainIdleHandle)
    }
    ttsPrefetchDrainIdleHandle = null
  }
  ttsPrefetchDrainIdleScheduled = false
}

const enqueueTtsPrefetch = (text) => {
  const t = String(text || '').trim()
  if (!t || ttsCache.has(t) || ttsInflight.has(t)) return
  if (ttsPrefetchPending.includes(t)) return
  ttsPrefetchPending.push(t)
  schedulePrefetchDrainWhenIdle()
}

const drainTtsPrefetchQueue = () => {
  while (ttsPrefetchSlots < TTS_PREFETCH_MAX_CONCURRENT && ttsPrefetchPending.length) {
    const t = ttsPrefetchPending.shift()
    if (!t || ttsCache.has(t) || ttsInflight.has(t)) continue
    ttsPrefetchSlots += 1
    fetchTtsAudioBase64(t).finally(() => {
      ttsPrefetchSlots -= 1
      drainTtsPrefetchQueue()
    })
  }
}

const currentStep = computed(() => tutorialStore.currentStep)
const rect = computed(() => tutorialStore.highlightRect)

/** 提示文案；主按钮不再使用 HTML disabled（禁用态不接收 click，事件会穿透到下层被 capture 拦截，表现为「下一步点不了」） */
const primaryNextTitle = computed(() => {
  const step = currentStep.value
  if (step?.actionType === 'click' && step?.allowCardNext !== true) {
    return '建议先按高亮完成本步；也可点此跳过'
  }
  return ''
})

/** 外扩像素：略大于边框，避免「洞口」比目标区域小一圈（原 border 会吃掉内容区宽度） */
const SPOTLIGHT_OUTSET = 10

const spotlightStyle = computed(() => {
  if (!rect.value) return {}
  const o = SPOTLIGHT_OUTSET
  return {
    top: `${rect.value.top - o}px`,
    left: `${rect.value.left - o}px`,
    width: `${rect.value.width + o * 2}px`,
    height: `${rect.value.height + o * 2}px`
  }
})

const cardStyle = computed(() => {
  if (!rect.value) return {}
  const cardWidth = 320
  const gap = 16
  /** 高亮在视口下半区、卡片只能放在高亮上方时：高亮顶到卡片顶的距离（含卡片高度估算）。略大则卡片更靠上，避免压住输入区一行。 */
  const cardAboveHighlightPx = 288
  const viewportWidth = window.innerWidth
  const viewportHeight = window.innerHeight
  const r = rect.value
  const cx = r.left + r.width / 2
  // 高亮在屏幕右侧（如副窗）时，勿把教程卡片与洞口左缘对齐，否则会盖住整块副窗
  const highlightOnRight = cx > viewportWidth * 0.52
  /** 主工作区大块高亮（非侧栏窄条）：卡片居中于洞口，避免贴左 16px 被误认为还在讲侧栏列表 */
  const wideMainContentHighlight =
    r.width >= Math.min(520, viewportWidth * 0.38) &&
    r.left >= viewportWidth * 0.14 &&
    r.height >= 120

  const preferBottomTop = r.top + r.height + gap
  const preferTopTop = Math.max(gap, r.top - cardAboveHighlightPx)
  const top = preferBottomTop + 220 < viewportHeight ? preferBottomTop : preferTopTop

  let left
  if (wideMainContentHighlight) {
    const idealLeft = r.left + (r.width - cardWidth) / 2
    left = Math.max(gap, Math.min(idealLeft, viewportWidth - cardWidth - gap))
  } else if (highlightOnRight) {
    left = r.left - cardWidth - gap
    // 空间不足时把卡片贴左栏，避免再压到右侧副窗上
    if (left < gap) {
      left = gap
    }
  } else {
    const maxLeft = Math.max(gap, viewportWidth - cardWidth - gap)
    left = Math.min(maxLeft, Math.max(gap, r.left))
  }
  return {
    top: `${top}px`,
    left: `${left}px`,
    width: `${cardWidth}px`
  }
})

/** 路由/副窗/resize 触发的重算只更新高亮，不得调用 skipMissingTargets（否则会向前跳步，抵消「上一步」） */
const refreshOnFrame = () => {
  requestAnimationFrame(() => {
    tutorialStore.refreshHighlight({ skipMissingOnFail: false })
  })
}

const stopTutorialSpeech = (advanceSeq = true) => {
  if (advanceSeq) ttsSeq += 1
  if (ttsAudio.value) {
    try {
      ttsAudio.value.pause()
      ttsAudio.value.src = ''
    } catch (_e) {
      // ignore
    }
    ttsAudio.value = null
  }
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel()
  }
}

const setTtsCache = (text, audioBase64) => {
  if (!text || !audioBase64) return
  if (ttsCache.has(text)) {
    ttsCache.delete(text)
  }
  ttsCache.set(text, audioBase64)
  if (ttsCache.size > TTS_CACHE_MAX) {
    const oldest = ttsCache.keys().next().value
    if (oldest) ttsCache.delete(oldest)
  }
}

const fetchTtsAudioBase64 = async (text) => {
  const content = String(text || '').trim()
  if (!content) return ''
  if (ttsCache.has(content)) {
    return ttsCache.get(content)
  }
  if (ttsInflight.has(content)) {
    return ttsInflight.get(content)
  }
  const req = fetch('/api/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: content,
      lang: 'zh',
      voice: 'zh-CN-XiaoxiaoNeural'
    })
  })
    .then(async (resp) => {
      const data = await resp.json().catch(() => ({}))
      const audioBase64 = data?.data?.audioBase64
      if (resp.ok && data?.success && typeof audioBase64 === 'string' && audioBase64.startsWith('data:audio/')) {
        setTtsCache(content, audioBase64)
        return audioBase64
      }
      return ''
    })
    .catch(() => '')
    .finally(() => {
      ttsInflight.delete(content)
    })
  ttsInflight.set(content, req)
  return req
}

const prefetchTutorialSpeech = () => {
  const steps = Array.isArray(tutorialStore.steps) ? tutorialStore.steps : []
  for (const step of steps) {
    const desc = String(step?.description || '').trim()
    if (!desc) continue
    enqueueTtsPrefetch(desc)
  }
}

/** 副窗「选择教程」页：只预热少量首句，避免一次性排队几十条 TTS 抢连接 */
let tutorialTtsPickWarmupDone = false
const prefetchTtsForTexts = (texts) => {
  for (const raw of texts) {
    const t = String(raw || '').trim()
    if (!t) continue
    enqueueTtsPrefetch(t)
  }
}
const onWarmupTutorialTtsFromPick = () => {
  if (tutorialTtsPickWarmupDone) return
  tutorialTtsPickWarmupDone = true
  const texts = getTutorialTtsWarmupTexts(!!window.__XCAGI_IS_PRO_MODE).slice(0, 6)
  prefetchTtsForTexts(texts)
}

const speakTutorialStep = async (text) => {
  const content = String(text || '').trim()
  if (!content) return
  const currentSeq = ++ttsSeq
  stopTutorialSpeech(false)
  try {
    const audioBase64 = await fetchTtsAudioBase64(content)
    if (currentSeq !== ttsSeq) return
    if (audioBase64) {
      const audio = new Audio(audioBase64)
      ttsAudio.value = audio
      await audio.play().catch(() => {})
      return
    }
  } catch (_e) {
    if (currentSeq !== ttsSeq) return
    // 中文 TTS 不可用时保持静默，不回退浏览器语音。
  }
}

const ensureStepRoute = async () => {
  if (!currentStep.value?.routeName) return
  const currentName = String(router.currentRoute.value.name || '')
  if (currentName === currentStep.value.routeName) return
  await router.push({ name: currentStep.value.routeName })
  await nextTick()
}

const ensureAssistantTab = async () => {
  const tab = String(currentStep.value?.assistantTab || '').trim()
  if (!tab) return
  window.dispatchEvent(new CustomEvent('xcagi:tutorial:set-assistant-tab', {
    detail: { tab, open: true }
  }))
  await nextTick()
}

const handleCaptureClick = (event) => {
  const target = event.target
  if (!(target instanceof Element)) return
  // 必须先放行教程 UI：disabled 按钮上的点击会穿透到下层，不能依赖 isActive/click 判断之后再判断 overlay
  if (target.closest('[data-tutorial-overlay="true"]')) return

  if (!tutorialStore.isActive || !currentStep.value || currentStep.value.actionType !== 'click') return

  const sel = String(currentStep.value.targetSelector || '').trim()
  if (!sel) return
  // 使用 closest：同一选择器若匹配多个节点（如多条示例），只认当前点击所在的那一项。
  const hit = target.closest(sel)
  if (hit) {
    tutorialStore.markCurrentStepClicked()
    // 新手对话包点击后会 await 路由与填入输入框，切步过早会与副窗/输入竞态；略加长延迟
    const starter = hit.closest('.starter-pack-item')
    const delayMs = starter ? 560 : 320
    window.setTimeout(() => {
      tutorialStore.nextStep()
    }, delayMs)
    return
  }

  event.preventDefault()
  event.stopPropagation()
  event.stopImmediatePropagation()
  tutorialStore.blockOutsideClick()
}

const awaitLayoutFrame = () =>
  new Promise((resolve) => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => resolve(undefined))
    })
  })

const START_PRINT_STEP_ID = 'starter-pack-demo-3-start-print'
const START_PRINT_BUTTON_SEL = '#taskPanel button[data-action="start-print"]'
let startPrintPollTimer = null

const clearStartPrintPoll = () => {
  if (startPrintPollTimer) {
    clearInterval(startPrintPollTimer)
    startPrintPollTimer = null
  }
}

watch(
  () => currentStep.value?.id,
  async (id) => {
    if (!tutorialStore.isActive || !currentStep.value) return
    clearStartPrintPoll()
    clearTtsPrefetchPending()
    // 先保证路由，再并行：副窗 tab 派发 与 双 rAF 量布局互不依赖，减少串行等待
    await ensureStepRoute()
    await Promise.all([ensureAssistantTab(), awaitLayoutFrame()])
    await nextTick()
    refreshOnFrame()
    // TTS 异步拉取与播放，不阻塞教程切步；延后一帧避免与 refreshHighlight 抢主线程
    const speechText = String(currentStep.value.description || '').trim()
    requestAnimationFrame(() => {
      void speakTutorialStep(speechText)
    })

    if (id !== START_PRINT_STEP_ID) return
    // 确认执行后按钮晚于切步才挂载；找到目标即停轮询，避免每 400ms scrollIntoView 反复触发抖动
    const tick = () => {
      if (!tutorialStore.isActive || tutorialStore.currentStep?.id !== START_PRINT_STEP_ID) {
        clearStartPrintPoll()
        return
      }
      if (document.querySelector(START_PRINT_BUTTON_SEL)) {
        tutorialStore.refreshHighlight({ skipMissingOnFail: false })
        clearStartPrintPoll()
        return
      }
      tutorialStore.refreshHighlight({ skipMissingOnFail: false })
    }
    tick()
    startPrintPollTimer = window.setInterval(tick, 600)
  },
  { immediate: true }
)

watch(
  () => tutorialStore.isActive,
  (active) => {
    document.documentElement.classList.toggle('xcagi-tutorial-active', !!active)
    if (!active) return
    prefetchTutorialSpeech()
    refreshOnFrame()
  },
  { immediate: true }
)

onMounted(() => {
  window.addEventListener('xcagi:warmup-tutorial-tts', onWarmupTutorialTtsFromPick)
  window.addEventListener('resize', refreshOnFrame)
  window.addEventListener('scroll', refreshOnFrame, true)
  document.addEventListener('click', handleCaptureClick, true)
})

watch(
  () => tutorialStore.isActive,
  async (active) => {
    if (!active && wasActive) {
      stopTutorialSpeech()
      clearTtsPrefetchPending()
      const restore = tutorialStore.returnContext || null
      if (restore?.routeName) {
        const currentName = String(router.currentRoute.value.name || '')
        if (currentName !== restore.routeName) {
          await router.push({ name: restore.routeName })
        }
      }
      window.dispatchEvent(new CustomEvent('xcagi:tutorial:restore-float', {
        detail: {
          isOpen: !!restore?.assistantOpen,
          activeTab: restore?.assistantTab || 'push',
          assistantState: restore?.assistantState || null
        }
      }))
    }
    wasActive = active
  }
)

onBeforeUnmount(() => {
  document.documentElement.classList.remove('xcagi-tutorial-active')
  clearStartPrintPoll()
  stopTutorialSpeech()
  window.removeEventListener('xcagi:warmup-tutorial-tts', onWarmupTutorialTtsFromPick)
  window.removeEventListener('resize', refreshOnFrame)
  window.removeEventListener('scroll', refreshOnFrame, true)
  document.removeEventListener('click', handleCaptureClick, true)
})
</script>

<style scoped>
.tutorial-overlay-root {
  position: fixed;
  inset: 0;
  z-index: 3800;
  pointer-events: none;
}

.tutorial-exit-wrap {
  position: absolute;
  right: 16px;
  top: 16px;
  pointer-events: auto;
}

.tutorial-exit-btn {
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #374151;
  border-radius: 999px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.18);
}

.tutorial-exit-btn:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

.tutorial-spotlight {
  position: absolute;
  box-sizing: border-box;
  /* 洞口必须与下层可点元素穿透，否则会挡住「确认执行」「开始打印」等，教程里任务看似无法执行 */
  pointer-events: none;
  /* 用 outline 画环，避免 border 占用内容盒导致透明洞口比量到的 rect 更小 */
  border: none;
  outline: 2px solid #60a5fa;
  outline-offset: 0;
  border-radius: 10px;
  background: transparent;
  box-shadow: 0 0 0 9999px rgba(2, 6, 23, 0.55);
  transition: all 0.2s ease;
}

.tutorial-card {
  position: absolute;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.24);
  padding: 12px;
  pointer-events: auto;
}

.tutorial-progress {
  font-size: 11px;
  color: #2563eb;
  font-weight: 600;
}

.tutorial-title {
  margin-top: 6px;
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}

.tutorial-desc {
  margin: 8px 0 0;
  font-size: 12px;
  color: #374151;
  line-height: 1.5;
}

.tutorial-tip {
  margin: 8px 0 0;
  font-size: 12px;
  color: #b91c1c;
}

.tutorial-fallback-notice {
  color: #92400e;
  background: rgba(251, 191, 36, 0.15);
  padding: 8px 10px;
  border-radius: 6px;
  line-height: 1.45;
}

.tutorial-test {
  margin: 8px 0 0;
  font-size: 12px;
  color: #065f46;
}

.tutorial-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.tutorial-primary-next {
  pointer-events: auto;
  cursor: pointer;
}
</style>
