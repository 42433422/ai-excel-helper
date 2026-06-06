import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export type StartupRevealPhase =
  | 'hidden'
  | 'step1'
  | 'step2'
  | 'step3'
  | 'unboxing'
  | 'done'

const UNBOXING_FALLBACK_MS = 900

export const useStartupRevealStore = defineStore('startupReveal', () => {
  const phase = ref<StartupRevealPhase>('hidden')
  const giftFlowDisabled = ref(false)
  const triggerNavReveal = ref(false)

  let unboxingResolve: (() => void) | null = null

  const activeStep = computed(() => {
    if (phase.value === 'step1') return 1
    if (phase.value === 'step2') return 2
    if (phase.value === 'step3' || phase.value === 'unboxing') return 3
    return 0
  })

  const isUnboxing = computed(() => phase.value === 'unboxing')

  function disableGiftFlow() {
    giftFlowDisabled.value = true
    phase.value = 'hidden'
    triggerNavReveal.value = false
  }

  function begin() {
    if (giftFlowDisabled.value) return
    phase.value = 'step1'
  }

  function completeStep1() {
    if (giftFlowDisabled.value) return
    if (phase.value === 'step1') phase.value = 'step2'
  }

  function completeStep2() {
    if (giftFlowDisabled.value) return
    if (phase.value === 'step1' || phase.value === 'step2') phase.value = 'step3'
  }

  function startUnboxing() {
    if (giftFlowDisabled.value) {
      markDone()
      return Promise.resolve()
    }
    phase.value = 'unboxing'
    return new Promise<void>((resolve) => {
      unboxingResolve = resolve
      window.setTimeout(() => {
        if (unboxingResolve) {
          unboxingResolve()
          unboxingResolve = null
        }
      }, UNBOXING_FALLBACK_MS)
    })
  }

  function notifyUnboxed() {
    if (unboxingResolve) {
      unboxingResolve()
      unboxingResolve = null
    }
  }

  function markDone() {
    phase.value = 'done'
  }

  /** 主界面 app-shell 就绪后再触发侧栏落下，避免在 opacity:0 时播完动画 */
  function notifyAppReady() {
    if (!giftFlowDisabled.value && phase.value === 'done') {
      triggerNavReveal.value = true
    }
  }

  function skipToDone() {
    notifyUnboxed()
    markDone()
  }

  return {
    phase,
    giftFlowDisabled,
    triggerNavReveal,
    activeStep,
    isUnboxing,
    disableGiftFlow,
    begin,
    completeStep1,
    completeStep2,
    startUnboxing,
    notifyUnboxed,
    markDone,
    notifyAppReady,
    skipToDone,
  }
})
