import { ref } from 'vue'

export function useProModeSync() {
  const isProMode = ref(false)

  function readProModeStateFromDom() {
    const overlay = document.getElementById('proModeOverlay')
    if (!overlay && typeof (window as any).__XCAGI_IS_PRO_MODE === 'boolean') {
      return !!(window as any).__XCAGI_IS_PRO_MODE
    }
    const bodyActive = document.body.classList.contains('pro-mode-active')
    const overlayActive = !!overlay?.classList.contains('active')
    const overlayVisible = !!overlay && overlay.style.display !== 'none'
    return bodyActive || (overlayActive && overlayVisible)
  }

  function syncGlobalProMode() {
    try {
      ;(window as any).__XCAGI_IS_PRO_MODE = isProMode.value
      window.dispatchEvent(new CustomEvent('xcagi:pro-mode-changed', { detail: { enabled: isProMode.value } }))
    } catch {
      // ignore
    }
  }

  function handleToggleProMode() {
    isProMode.value = !isProMode.value
    syncGlobalProMode()
  }

  return {
    isProMode,
    readProModeStateFromDom,
    syncGlobalProMode,
    handleToggleProMode,
  }
}

