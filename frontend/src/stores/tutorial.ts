// @ts-nocheck
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { createTutorialBuildContext } from '@/tutorial/buildContext'
import { getTrackLabel } from '@/tutorial/catalog'
import { resolveAllWarmupSteps, resolveTrackSteps } from '@/tutorial/resolveSteps'
import {
  afterAssistantTabLayout,
  bindTutorialRouter,
  dispatchAssistantTab,
  ensureRouteForStepThen,
  getTutorialFallbackHighlightRect,
  resolveStepHighlightRect,
  shouldNeverAutoSkipStep,
} from '@/tutorial/runtime'
import type { TutorialStep, TutorialTrackId } from '@/tutorial/types'

export { bindTutorialRouter }
export type { TutorialStep, TutorialTrackId, TutorialActionType } from '@/tutorial/types'

const PRO_INTENT_EXPERIENCE_STORAGE_KEY = 'xcagi_pro_intent_experience'
type ProIntentLocalSnapshot = false | string | null

type TutorialTestStatus = 'pending' | 'passed' | 'skipped'
type TutorialReturnContext = {
  routeName?: string
  assistantOpen?: boolean
  assistantTab?: string
  assistantState?: Record<string, unknown> | null
}

/** 构建上下文由调用方注入（副窗启动教程时传入 visibleNav / industry / mods） */
let tutorialBuildContextFactory: (() => import('@/tutorial/types').TutorialBuildContext) | null = null

export function setTutorialBuildContextFactory(
  factory: () => import('@/tutorial/types').TutorialBuildContext,
) {
  tutorialBuildContextFactory = factory
}

function getBuildContext(isProMode: boolean) {
  if (tutorialBuildContextFactory) {
    return tutorialBuildContextFactory()
  }
  return createTutorialBuildContext({
    industryId: '考勤',
    mods: [],
    visibleNav: [],
    isProMode,
  })
}

export function getTutorialTtsWarmupTexts(isProMode: boolean): string[] {
  const ctx = getBuildContext(isProMode)
  const merged = resolveAllWarmupSteps(ctx)
  const seen = new Set<string>()
  const out: string[] = []
  for (const step of merged) {
    const d = String(step.description || '').trim()
    if (!d || seen.has(d)) continue
    seen.add(d)
    out.push(d)
  }
  return out
}

export const useTutorialStore = defineStore('tutorial', () => {
  const isActive = ref(false)
  const isExited = ref(false)
  const currentStepIndex = ref(0)
  const currentTrack = ref<TutorialTrackId | null>(null)
  const steps = ref<TutorialStep[]>([])
  const highlightRect = ref<{ top: number; left: number; width: number; height: number } | null>(null)
  const canNext = ref(false)
  const blockedTip = ref('')
  const testResults = ref<Record<string, TutorialTestStatus>>({})
  const lastTestReport = ref<{ total: number; passed: number; skipped: number } | null>(null)
  const returnContext = ref<TutorialReturnContext | null>(null)
  const proBasicFallbackNotice = ref('')
  const tutorialProIntentSnapshot = ref<ProIntentLocalSnapshot>(false)

  const captureTutorialProIntentSnapshot = () => {
    tutorialProIntentSnapshot.value = localStorage.getItem(PRO_INTENT_EXPERIENCE_STORAGE_KEY)
  }

  const restoreTutorialProIntentSnapshot = () => {
    if (tutorialProIntentSnapshot.value === false) return
    const snap = tutorialProIntentSnapshot.value
    tutorialProIntentSnapshot.value = false
    if (snap === null || snap === '') {
      localStorage.removeItem(PRO_INTENT_EXPERIENCE_STORAGE_KEY)
    } else {
      localStorage.setItem(PRO_INTENT_EXPERIENCE_STORAGE_KEY, snap)
    }
    const enabled = snap === '1'
    window.dispatchEvent(
      new CustomEvent('xcagi:pro-intent-experience-changed', { detail: { enabled } }),
    )
  }

  const currentStep = computed(() => steps.value[currentStepIndex.value] || null)
  const hasPrev = computed(() => currentStepIndex.value > 0)
  const isLastStep = computed(() => currentStepIndex.value >= steps.value.length - 1)
  const testSummary = computed(() => {
    const total = steps.value.length
    const values = Object.values(testResults.value)
    const passed = values.filter((x) => x === 'passed').length
    const skipped = values.filter((x) => x === 'skipped').length
    const pending = Math.max(0, total - passed - skipped)
    return { total, passed, skipped, pending }
  })

  const clearBlockedTip = () => {
    blockedTip.value = ''
  }

  let stepTargetPollTimer: ReturnType<typeof setTimeout> | null = null
  const clearStepTargetPoll = () => {
    if (stepTargetPollTimer !== null) {
      clearTimeout(stepTargetPollTimer)
      stepTargetPollTimer = null
    }
  }

  const resetRuntime = () => {
    clearStepTargetPoll()
    currentStepIndex.value = 0
    highlightRect.value = null
    canNext.value = false
    blockedTip.value = ''
    testResults.value = {}
    currentTrack.value = null
  }

  const markStepStatus = (stepId: string, status: TutorialTestStatus) => {
    if (!stepId) return
    testResults.value = {
      ...testResults.value,
      [stepId]: status,
    }
  }

  const pollUntilStepTargetReady = (stepId: string) => {
    clearStepTargetPoll()
    highlightRect.value = getTutorialFallbackHighlightRect()
    blockedTip.value = '正在加载本页…'
    let attempts = 0
    const poll = () => {
      stepTargetPollTimer = null
      if (!isActive.value || currentStep.value?.id !== stepId) return
      const rect = resolveStepHighlightRect(currentStep.value)
      if (rect) {
        highlightRect.value = rect
        clearBlockedTip()
        if (currentStep.value.actionType === 'observe') {
          canNext.value = true
          markStepStatus(currentStep.value.id, 'passed')
        }
        return
      }
      attempts += 1
      if (attempts >= 50) {
        blockedTip.value = '若仍未出现本页高亮，请再点侧栏进入该菜单，或点「下一步」。'
        canNext.value = true
        markStepStatus(currentStep.value.id, 'passed')
        return
      }
      stepTargetPollTimer = window.setTimeout(poll, 100)
    }
    stepTargetPollTimer = window.setTimeout(poll, 80)
  }

  const skipMissingTargets = () => {
    const tryResolveCurrent = () => {
      if (!currentStep.value) {
        finishTutorial()
        return
      }
      if (window.__XCAGI_IS_PRO_MODE && currentStep.value.excludeInPro) {
        if (import.meta.env.DEV) {
          console.info('[tutorial] skip pro-only guarded step:', currentStep.value.id)
        }
        markStepStatus(currentStep.value.id, 'skipped')
        currentStepIndex.value += 1
        canNext.value = false
        skipMissingTargets()
        return
      }
      const step = currentStep.value
      const applyRect = () => {
        if (!currentStep.value) {
          finishTutorial()
          return
        }
        const rect = resolveStepHighlightRect(currentStep.value)
        if (rect) {
          highlightRect.value = rect
          if (currentStep.value.actionType === 'observe') {
            canNext.value = true
            markStepStatus(currentStep.value.id, 'passed')
          }
          return
        }
        if (shouldNeverAutoSkipStep(currentStep.value)) {
          highlightRect.value = getTutorialFallbackHighlightRect()
          blockedTip.value = '请稍候，待任务执行完成出现「开始打印」后再点击该按钮。'
          return
        }
        if (currentStep.value.noAutoSkipWhenMissing) {
          pollUntilStepTargetReady(currentStep.value.id)
          return
        }
        blockedTip.value = '当前功能在此页面不可用，已自动跳过。'
        markStepStatus(currentStep.value.id, 'skipped')
        currentStepIndex.value += 1
        canNext.value = false
        skipMissingTargets()
      }
      const runAfterRoute = () => {
        if (step.assistantTab) {
          dispatchAssistantTab(step.assistantTab)
          afterAssistantTabLayout(applyRect)
        } else {
          afterAssistantTabLayout(applyRect)
        }
      }
      if (step.routeName?.trim()) {
        ensureRouteForStepThen(step, runAfterRoute)
        return
      }
      if (step.assistantTab) {
        dispatchAssistantTab(step.assistantTab)
        afterAssistantTabLayout(applyRect)
        return
      }
      applyRect()
    }
    tryResolveCurrent()
  }

  const startTutorial = (
    options: {
      isProMode?: boolean
      returnContext?: TutorialReturnContext
      track?: TutorialTrackId
      buildContext?: import('@/tutorial/types').TutorialBuildContext
    } = {},
  ) => {
    const isProMode = !!options.isProMode
    proBasicFallbackNotice.value = ''
    let effectiveTrack: TutorialTrackId = options.track ?? 'basic'
    returnContext.value = options.returnContext || null
    const ctx = options.buildContext || getBuildContext(isProMode)

    let resolved = resolveTrackSteps(effectiveTrack, ctx)
    if (!resolved.length && effectiveTrack === 'basic' && isProMode) {
      proBasicFallbackNotice.value =
        '当前为专业版界面：基础教程面向普通版布局，已自动切换为「进阶教程」路线（仍可分步熟悉菜单与页面）。'
      effectiveTrack = 'advanced'
      resolved = resolveTrackSteps(effectiveTrack, ctx)
    }
    steps.value = resolved
    if (!steps.value.length) {
      finishTutorial()
      return
    }
    captureTutorialProIntentSnapshot()
    isActive.value = true
    isExited.value = false
    lastTestReport.value = null
    resetRuntime()
    currentTrack.value = effectiveTrack
    for (const step of steps.value) {
      markStepStatus(step.id, 'pending')
    }
    skipMissingTargets()
  }

  const refreshHighlight = (opts?: { skipMissingOnFail?: boolean }) => {
    const skipMissingOnFail = opts?.skipMissingOnFail !== false
    if (!isActive.value || !currentStep.value) return
    const step = currentStep.value
    const apply = () => {
      if (!isActive.value || !currentStep.value) return
      const rect = resolveStepHighlightRect(currentStep.value)
      if (rect) {
        highlightRect.value = rect
        clearBlockedTip()
        clearStepTargetPoll()
        if (currentStep.value.actionType === 'observe') {
          canNext.value = true
          markStepStatus(currentStep.value.id, 'passed')
        }
        return
      }
      if (shouldNeverAutoSkipStep(currentStep.value)) {
        highlightRect.value = getTutorialFallbackHighlightRect()
        blockedTip.value = '请稍候，待任务执行完成出现「开始打印」后再点击该按钮。'
        return
      }
      if (currentStep.value.noAutoSkipWhenMissing) {
        pollUntilStepTargetReady(currentStep.value.id)
        return
      }
      if (skipMissingOnFail) {
        skipMissingTargets()
      } else {
        highlightRect.value = getTutorialFallbackHighlightRect()
      }
    }
    const runAfterRoute = () => {
      if (step.assistantTab) {
        dispatchAssistantTab(step.assistantTab)
        afterAssistantTabLayout(apply)
      } else {
        afterAssistantTabLayout(apply)
      }
    }
    if (step.routeName?.trim()) {
      ensureRouteForStepThen(step, runAfterRoute)
      return
    }
    if (step.assistantTab) {
      dispatchAssistantTab(step.assistantTab)
      afterAssistantTabLayout(apply)
      return
    }
    apply()
  }

  const prevStep = () => {
    if (!hasPrev.value) return
    currentStepIndex.value -= 1
    canNext.value = false
    clearBlockedTip()
  }

  const nextStep = () => {
    if (!currentStep.value) {
      exitTutorial()
      return
    }
    if (isLastStep.value) {
      finishTutorial()
      return
    }
    currentStepIndex.value += 1
    canNext.value = false
    clearBlockedTip()
    refreshHighlight()
    if (currentStep.value?.actionType === 'observe') {
      canNext.value = true
    }
  }

  const markCurrentStepClicked = () => {
    if (!currentStep.value || currentStep.value.actionType !== 'click') return
    canNext.value = true
    blockedTip.value = ''
    markStepStatus(currentStep.value.id, 'passed')
  }

  const blockOutsideClick = () => {
    if (!currentStep.value || currentStep.value.actionType !== 'click') return
    blockedTip.value = '请先点击高亮区域完成当前步骤。'
  }

  const finishTutorial = () => {
    restoreTutorialProIntentSnapshot()
    proBasicFallbackNotice.value = ''
    lastTestReport.value = {
      total: testSummary.value.total,
      passed: testSummary.value.passed,
      skipped: testSummary.value.skipped,
    }
    isActive.value = false
    isExited.value = false
    resetRuntime()
  }

  const exitTutorial = () => {
    restoreTutorialProIntentSnapshot()
    proBasicFallbackNotice.value = ''
    lastTestReport.value = {
      total: testSummary.value.total,
      passed: testSummary.value.passed,
      skipped: testSummary.value.skipped,
    }
    isActive.value = false
    isExited.value = true
    resetRuntime()
  }

  const currentTrackLabel = computed(() => {
    const ctx = getBuildContext(!!window.__XCAGI_IS_PRO_MODE)
    return getTrackLabel(currentTrack.value, ctx)
  })

  return {
    isActive,
    isExited,
    currentStepIndex,
    currentTrack,
    currentTrackLabel,
    steps,
    currentStep,
    highlightRect,
    canNext,
    blockedTip,
    proBasicFallbackNotice,
    testResults,
    testSummary,
    lastTestReport,
    returnContext,
    hasPrev,
    isLastStep,
    startTutorial,
    refreshHighlight,
    prevStep,
    nextStep,
    markCurrentStepClicked,
    blockOutsideClick,
    clearBlockedTip,
    finishTutorial,
    exitTutorial,
  }
})
