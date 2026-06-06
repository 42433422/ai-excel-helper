import { computed, ref, watch } from 'vue'
import { useStartupRevealStore } from '@/stores/startupReveal'

const NAV_REVEAL_SESSION_KEY = 'xcagi.navReveal.done'

export function useSidebarNavReveal() {
  const startupReveal = useStartupRevealStore()
  const navRevealPlaying = ref(false)

  const prefersReducedMotion = computed(() => {
    if (typeof window === 'undefined') return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  })

  function shouldPlayReveal(): boolean {
    if (startupReveal.giftFlowDisabled) return false
    try {
      const params = new URLSearchParams(window.location.search)
      if (params.has('replayNav')) return true
      return sessionStorage.getItem(NAV_REVEAL_SESSION_KEY) !== '1'
    } catch {
      return true
    }
  }

  function markRevealPlayed() {
    try {
      sessionStorage.setItem(NAV_REVEAL_SESSION_KEY, '1')
    } catch {
      /* private mode */
    }
  }

  watch(
    () => startupReveal.triggerNavReveal,
    (on) => {
      if (!on) return
      if (!shouldPlayReveal() || prefersReducedMotion.value) {
        navRevealPlaying.value = false
        markRevealPlayed()
        return
      }
      navRevealPlaying.value = true
      markRevealPlayed()
      const maxItems = 24
      const delayMs = 48 * Math.min(maxItems, 20) + 400
      window.setTimeout(() => {
        navRevealPlaying.value = false
      }, delayMs)
    },
    { immediate: true },
  )

  function staggerStyle(index: number): Record<string, string | number> {
    if (!navRevealPlaying.value) return {}
    const stagger = Math.min(Math.max(0, index), 20)
    return { '--nav-stagger': stagger }
  }

  function navRevealClass(index: number): Record<string, boolean> {
    if (!navRevealPlaying.value) return {}
    return {
      'nav-reveal-active': true,
    }
  }

  return {
    navRevealPlaying,
    prefersReducedMotion,
    staggerStyle,
    navRevealClass,
  }
}
