import { nextTick } from 'vue'
import type { Router } from 'vue-router'
import type { TutorialStep } from './types'

let tutorialRouter: Router | null = null

export function bindTutorialRouter(router: Router) {
  tutorialRouter = router
}

export const NEVER_AUTO_SKIP_STEP_IDS = new Set(['starter-pack-demo-3-start-print'])

export const shouldNeverAutoSkipStep = (step: TutorialStep | null) =>
  !!step && NEVER_AUTO_SKIP_STEP_IDS.has(step.id)

export const resolveElementRect = (selector: string) => {
  const el = document.querySelector(selector)
  if (!el) return null
  try {
    el.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  } catch (_e) {
    // ignore
  }
  const rect = el.getBoundingClientRect()
  if (!rect || rect.width <= 0 || rect.height <= 0) return null
  return {
    top: rect.top,
    left: rect.left,
    width: rect.width,
    height: rect.height,
  }
}

export const getTutorialFallbackHighlightRect = () => ({
  top: Math.max(24, window.innerHeight * 0.22),
  left: Math.max(24, window.innerWidth * 0.5 - 160),
  width: 320,
  height: 160,
})

export const resolveStepHighlightRect = (step: TutorialStep | null) => {
  if (!step) return null
  const sel = (step.highlightSelector || step.targetSelector).trim()
  const base = resolveElementRect(sel)
  if (!base) return null
  if (
    sel.includes('assistant-panel') ||
    sel.includes('tutorial-assistant-body') ||
    sel === '#taskPanel'
  ) {
    const pad = 6
    return {
      top: base.top - pad,
      left: base.left - pad,
      width: base.width + pad * 2,
      height: base.height + pad * 2,
    }
  }
  if (sel.includes('.page-content') || sel.match(/#view-[a-z0-9-]+\s*$/)) {
    const pad = 4
    return {
      top: base.top - pad,
      left: base.left - pad,
      width: base.width + pad * 2,
      height: base.height + pad * 2,
    }
  }
  return base
}

export const TUTORIAL_SET_ASSISTANT_TAB = 'xcagi:tutorial:set-assistant-tab'

export const dispatchAssistantTab = (tab: string) => {
  const t = String(tab || '').trim()
  if (!t) return
  window.dispatchEvent(
    new CustomEvent(TUTORIAL_SET_ASSISTANT_TAB, {
      detail: { tab: t, open: true },
    }),
  )
}

export const afterAssistantTabLayout = (fn: () => void) => {
  nextTick(() => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        fn()
      })
    })
  })
}

const currentRouteName = () => String(tutorialRouter?.currentRoute.value.name || '')

export const ensureRouteForStepThen = (step: TutorialStep, fn: () => void) => {
  const name = step.routeName?.trim()
  if (!name || currentRouteName() === name) {
    fn()
    return
  }
  const r = tutorialRouter
  if (!r) {
    fn()
    return
  }
  r.push({ name })
    .then(() => {
      nextTick(fn)
    })
    .catch(() => {
      fn()
    })
}
